"""
Enhanced Heatmap Generation Module
Professional-quality heatmaps with map overlays, round phases, and high-res output.

Features:
- Map overlay support (radar images)
- Round-phase separation (early/mid/late)
- Professional color schemes (hot/reds)
- 1920x1080 high DPI output
- Per-map coordinate normalization
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Literal
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.image import imread
import pandas as pd
from scipy.ndimage import gaussian_filter

from src.parser.demo_parser import ParsedDemo


# =============================================================================
# MAP COORDINATE BOUNDS
# CS2 uses different coordinate systems per map
# Format: (min_x, max_x, min_y, max_y, radar_pos_x, radar_pos_y, radar_scale)
# =============================================================================
MAP_CONFIG: Dict[str, Dict] = {
    "de_dust2": {
        "bounds": (-2476, 2127, -1262, 3239),
        "radar_offset": (-2476, 3239),
        "radar_scale": 4.4,
    },
    "de_mirage": {
        "bounds": (-3230, 1855, -3420, 1713),
        "radar_offset": (-3230, 1713),
        "radar_scale": 5.0,
    },
    "de_inferno": {
        "bounds": (-2087, 2800, -1150, 3870),
        "radar_offset": (-2087, 3870),
        "radar_scale": 4.9,
    },
    "de_nuke": {
        "bounds": (-3453, 3607, -4290, -790),
        "radar_offset": (-3453, -790),
        "radar_scale": 7.0,
    },
    "de_overpass": {
        "bounds": (-4831, 511, -3551, 1781),
        "radar_offset": (-4831, 1781),
        "radar_scale": 5.2,
    },
    "de_ancient": {
        "bounds": (-2953, 2164, -2296, 2382),
        "radar_offset": (-2953, 2382),
        "radar_scale": 5.0,
    },
    "de_anubis": {
        "bounds": (-2796, 1869, -2458, 2279),
        "radar_offset": (-2796, 2279),
        "radar_scale": 5.2,
    },
    "de_vertigo": {
        "bounds": (-3168, 672, -1792, 2048),
        "radar_offset": (-3168, 2048),
        "radar_scale": 4.0,
    },
}

DEFAULT_CONFIG = {
    "bounds": (-4000, 4000, -4000, 4000),
    "radar_offset": (-4000, 4000),
    "radar_scale": 8.0,
}

# Round phase time boundaries (in seconds from round start)
ROUND_PHASES = {
    "early": (0, 20),
    "mid": (20, 60),
    "late": (60, 999),
}

# Tick rate for CS2
TICK_RATE = 64


class HeatmapGenerator:
    """
    Generate professional-quality heatmaps from CS2 demo data.
    
    Features:
    - Kill/death/movement heatmaps
    - Map image overlays
    - Round phase filtering
    - High-resolution output (1920x1080)
    """
    
    def __init__(
        self,
        parsed_demo: ParsedDemo,
        output_dir: str = "outputs/heatmaps",
        resolution: int = 384,
        sigma_kills: float = 4.0,
        sigma_movement: float = 2.0,
        phase: Optional[str] = None
    ):
        """
        Initialize heatmap generator.
        
        Args:
            parsed_demo: ParsedDemo object from parser
            output_dir: Base directory to save PNG files
            resolution: Grid resolution (default 384 for quality)
            sigma_kills: Gaussian sigma for kill/death heatmaps
            sigma_movement: Gaussian sigma for movement (lower = sharper)
            phase: Round phase filter ("early", "mid", "late", or None for all)
        """
        self.demo = parsed_demo
        self.resolution = resolution
        self.sigma_kills = sigma_kills
        self.sigma_movement = sigma_movement
        self.phase = phase
        
        # Detect map (try parser, then fallback to filename)
        self.map_name = self._detect_map_name(parsed_demo)
        self.map_config = MAP_CONFIG.get(self.map_name, DEFAULT_CONFIG)
        self.bounds = self.map_config["bounds"]
        
        # Output directory (per-map)
        map_folder = self.map_name.replace("de_", "") if self.map_name.startswith("de_") else self.map_name
        self.output_dir = Path(output_dir) / map_folder
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Map image path
        self.map_image_path = Path("assets/maps") / f"{map_folder}.png"
        self.has_map_image = self.map_image_path.exists()
        
        # Create professional colormaps
        self.cmap_hot = self._create_hot_colormap()
        self.cmap_cool = self._create_cool_colormap()
    
    def _detect_map_name(self, parsed_demo: ParsedDemo) -> str:
        """
        Detect map name from parser or filename.
        
        Priority:
        1. Parser-provided map name
        2. Map name extracted from demo filename
        """
        # Known map names to look for
        known_maps = ["dust2", "mirage", "inferno", "nuke", "overpass", "ancient", "anubis", "vertigo"]
        
        # Try parser first
        if parsed_demo.map_name:
            name = parsed_demo.map_name.lower().strip()
            if "/" in name:
                name = name.split("/")[-1]
            if not name.startswith("de_"):
                for km in known_maps:
                    if km in name:
                        return f"de_{km}"
            return name
        
        # Fallback: extract from filename
        if parsed_demo.demo_path:
            filename = Path(parsed_demo.demo_path).stem.lower()
            for km in known_maps:
                if km in filename:
                    return f"de_{km}"
        
        return "unknown"
    
    def _normalize_map_name(self, map_name: str) -> str:
        """Normalize map name to standard format."""
        if not map_name:
            return "unknown"
        name = map_name.lower().strip()
        # Handle various formats
        if "/" in name:
            name = name.split("/")[-1]
        if not name.startswith("de_") and name in ["dust2", "mirage", "inferno", "nuke", "overpass", "ancient", "anubis", "vertigo"]:
            name = f"de_{name}"
        return name
    
    def _create_hot_colormap(self) -> LinearSegmentedColormap:
        """Create professional hot colormap for kills/deaths."""
        colors = [
            (0.0, 0.0, 0.0, 0.0),       # Transparent (no data)
            (0.1, 0.0, 0.0, 0.3),       # Very dark red
            (0.3, 0.0, 0.0, 0.5),       # Dark red
            (0.6, 0.1, 0.0, 0.7),       # Red
            (0.9, 0.3, 0.0, 0.85),      # Orange-red
            (1.0, 0.6, 0.0, 0.95),      # Orange
            (1.0, 1.0, 0.2, 1.0),       # Yellow (hot spots)
        ]
        return LinearSegmentedColormap.from_list("heatmap_hot", colors, N=256)
    
    def _create_cool_colormap(self) -> LinearSegmentedColormap:
        """Create cool colormap for movement density."""
        colors = [
            (0.0, 0.0, 0.0, 0.0),       # Transparent
            (0.0, 0.1, 0.2, 0.3),       # Dark blue
            (0.0, 0.3, 0.5, 0.5),       # Blue
            (0.0, 0.5, 0.7, 0.7),       # Cyan-blue
            (0.2, 0.8, 0.8, 0.85),      # Cyan
            (0.5, 1.0, 0.8, 0.95),      # Light cyan
            (1.0, 1.0, 1.0, 1.0),       # White (hot spots)
        ]
        return LinearSegmentedColormap.from_list("heatmap_cool", colors, N=256)
    
    def _extract_coordinates(
        self,
        df: pd.DataFrame,
        x_col: str = "X",
        y_col: str = "Y",
        tick_col: str = "tick"
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extract coordinates and ticks from DataFrame.
        
        Returns:
            Tuple of (x_coords, y_coords, ticks) as numpy arrays
        """
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return np.array([]), np.array([]), np.array([])
        
        if isinstance(df, list):
            return np.array([]), np.array([]), np.array([])
        
        # Find coordinate columns
        x_candidates = [x_col, x_col.lower(), 'attacker_X', 'user_X', 'x']
        y_candidates = [y_col, y_col.lower(), 'attacker_Y', 'user_Y', 'y']
        tick_candidates = [tick_col, 'tick', 'Tick']
        
        actual_x, actual_y, actual_tick = None, None, None
        
        for col in x_candidates:
            if col in df.columns:
                actual_x = col
                break
        
        for col in y_candidates:
            if col in df.columns:
                actual_y = col
                break
        
        for col in tick_candidates:
            if col in df.columns:
                actual_tick = col
                break
        
        if actual_x is None or actual_y is None:
            return np.array([]), np.array([]), np.array([])
        
        # Extract data
        cols = [actual_x, actual_y]
        if actual_tick:
            cols.append(actual_tick)
        
        coords = df[cols].dropna()
        x = coords[actual_x].to_numpy(dtype=np.float64)
        y = coords[actual_y].to_numpy(dtype=np.float64)
        ticks = coords[actual_tick].to_numpy(dtype=np.int64) if actual_tick else np.zeros(len(x), dtype=np.int64)
        
        return x, y, ticks
    
    def _filter_by_phase(
        self,
        x: np.ndarray,
        y: np.ndarray,
        ticks: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Filter coordinates by round phase."""
        if self.phase is None or len(x) == 0:
            return x, y
        
        if self.phase not in ROUND_PHASES:
            return x, y
        
        start_sec, end_sec = ROUND_PHASES[self.phase]
        start_tick = start_sec * TICK_RATE
        end_tick = end_sec * TICK_RATE
        
        # Filter by tick (relative to round start - simplified)
        # In practice, would need round start ticks for accurate filtering
        mask = (ticks >= start_tick) & (ticks < end_tick)
        
        return x[mask], y[mask]
    
    def _normalize_coordinates(
        self,
        x: np.ndarray,
        y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Normalize CS2 coordinates to [0, resolution] range.
        
        Uses per-map bounds for accurate positioning.
        """
        min_x, max_x, min_y, max_y = self.bounds
        
        x_range = max_x - min_x
        y_range = max_y - min_y
        
        if x_range == 0:
            x_range = 1
        if y_range == 0:
            y_range = 1
        
        x_norm = (x - min_x) / x_range * (self.resolution - 1)
        y_norm = (y - min_y) / y_range * (self.resolution - 1)
        
        x_norm = np.clip(x_norm, 0, self.resolution - 1)
        y_norm = np.clip(y_norm, 0, self.resolution - 1)
        
        return x_norm, y_norm
    
    def _create_density_grid(
        self,
        x: np.ndarray,
        y: np.ndarray
    ) -> np.ndarray:
        """Create 2D density grid using vectorized histogram."""
        if len(x) == 0 or len(y) == 0:
            return np.zeros((self.resolution, self.resolution))
        
        grid, _, _ = np.histogram2d(
            y, x,
            bins=self.resolution,
            range=[[0, self.resolution], [0, self.resolution]]
        )
        
        return grid
    
    def _render_heatmap(
        self,
        grid: np.ndarray,
        title: str,
        output_path: Path,
        cmap: LinearSegmentedColormap,
        sigma: float
    ) -> str:
        """
        Render high-quality heatmap to PNG.
        
        Args:
            grid: 2D density grid
            title: Plot title
            output_path: Path to save PNG
            cmap: Colormap to use
            sigma: Gaussian smoothing sigma
            
        Returns:
            Path to saved file
        """
        # Apply Gaussian smoothing
        if sigma > 0:
            grid = gaussian_filter(grid, sigma=sigma)
        
        # Create figure (1920x1080 at 100 DPI = 19.2 x 10.8 inches)
        fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
        
        # Dark background
        fig.patch.set_facecolor('#1a1a2e')
        ax.set_facecolor('#1a1a2e')
        
        # Load and display map image if available
        if self.has_map_image:
            try:
                map_img = imread(str(self.map_image_path))
                ax.imshow(
                    map_img,
                    extent=[0, self.resolution, 0, self.resolution],
                    aspect='equal',
                    alpha=0.7,
                    zorder=1
                )
            except Exception as e:
                print(f"  Warning: Could not load map image: {e}")
        
        # Normalize grid for visualization
        if grid.max() > 0:
            grid_norm = grid / grid.max()
        else:
            grid_norm = grid
        
        # Plot heatmap overlay
        im = ax.imshow(
            grid_norm,
            cmap=cmap,
            origin='lower',
            aspect='equal',
            interpolation='bilinear',
            extent=[0, self.resolution, 0, self.resolution],
            zorder=2
        )
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        cbar.set_label('Density', rotation=270, labelpad=20, color='white', fontsize=12)
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color='white')
        
        # Title
        map_display = self.map_name.replace("de_", "").upper() if self.map_name != "unknown" else "UNKNOWN MAP"
        phase_text = f" ({self.phase.upper()} ROUND)" if self.phase else ""
        full_title = f"{title}\n{map_display}{phase_text}"
        ax.set_title(full_title, fontsize=18, fontweight='bold', color='white', pad=20)
        
        # Hide axes
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        # Stats box
        total_events = int(grid.sum()) if sigma == 0 else "~" + str(int(grid.sum()))
        stats_text = f"Events: {total_events}"
        ax.text(
            0.02, 0.98, stats_text,
            transform=ax.transAxes,
            fontsize=12,
            verticalalignment='top',
            color='white',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#16213e', alpha=0.9, edgecolor='#0f3460')
        )
        
        # Credit
        ax.text(
            0.98, 0.02, 'CS2 AI Coach',
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='bottom',
            horizontalalignment='right',
            color='#888888',
            style='italic'
        )
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='#1a1a2e', edgecolor='none')
        plt.close(fig)
        
        return str(output_path)
    
    def generate_kills_heatmap(self) -> str:
        """Generate heatmap of kill locations."""
        kills_df = self.demo.kills
        
        x, y, ticks = self._extract_coordinates(kills_df, "attacker_X", "attacker_Y")
        if len(x) == 0:
            x, y, ticks = self._extract_coordinates(kills_df, "X", "Y")
        
        x, y = self._filter_by_phase(x, y, ticks)
        x_norm, y_norm = self._normalize_coordinates(x, y)
        grid = self._create_density_grid(x_norm, y_norm)
        
        suffix = f"_{self.phase}" if self.phase else ""
        output_path = self.output_dir / f"kills_heatmap{suffix}.png"
        
        return self._render_heatmap(grid, "KILL LOCATIONS", output_path, self.cmap_hot, self.sigma_kills)
    
    def generate_deaths_heatmap(self) -> str:
        """Generate heatmap of death locations."""
        kills_df = self.demo.kills
        
        x, y, ticks = self._extract_coordinates(kills_df, "user_X", "user_Y")
        if len(x) == 0:
            x, y, ticks = self._extract_coordinates(kills_df, "X", "Y")
        
        x, y = self._filter_by_phase(x, y, ticks)
        x_norm, y_norm = self._normalize_coordinates(x, y)
        grid = self._create_density_grid(x_norm, y_norm)
        
        suffix = f"_{self.phase}" if self.phase else ""
        output_path = self.output_dir / f"deaths_heatmap{suffix}.png"
        
        return self._render_heatmap(grid, "DEATH LOCATIONS", output_path, self.cmap_hot, self.sigma_kills)
    
    def generate_movement_heatmap(self) -> str:
        """Generate heatmap of player movement density."""
        positions_df = self.demo.player_positions
        
        x, y, ticks = self._extract_coordinates(positions_df, "X", "Y")
        
        if len(x) == 0:
            print("  Warning: No position data, using kill/death locations as proxy")
            kills_df = self.demo.kills
            x1, y1, t1 = self._extract_coordinates(kills_df, "attacker_X", "attacker_Y")
            x2, y2, t2 = self._extract_coordinates(kills_df, "user_X", "user_Y")
            x = np.concatenate([x1, x2]) if len(x1) > 0 or len(x2) > 0 else np.array([])
            y = np.concatenate([y1, y2]) if len(y1) > 0 or len(y2) > 0 else np.array([])
            ticks = np.concatenate([t1, t2]) if len(t1) > 0 or len(t2) > 0 else np.array([])
        
        x, y = self._filter_by_phase(x, y, ticks)
        x_norm, y_norm = self._normalize_coordinates(x, y)
        grid = self._create_density_grid(x_norm, y_norm)
        
        suffix = f"_{self.phase}" if self.phase else ""
        output_path = self.output_dir / f"movement_heatmap{suffix}.png"
        
        return self._render_heatmap(grid, "MOVEMENT DENSITY", output_path, self.cmap_cool, self.sigma_movement)
    
    def generate_all(self) -> Dict[str, str]:
        """Generate all heatmaps."""
        results = {}
        
        phase_text = f" [{self.phase}]" if self.phase else ""
        print(f"Generating heatmaps{phase_text}...")
        print(f"  Map: {self.map_name}")
        print(f"  Output: {self.output_dir}/")
        
        try:
            results["kills"] = self.generate_kills_heatmap()
            print(f"  ✓ Kills: {Path(results['kills']).name}")
        except Exception as e:
            print(f"  ✗ Kills failed: {e}")
        
        try:
            results["deaths"] = self.generate_deaths_heatmap()
            print(f"  ✓ Deaths: {Path(results['deaths']).name}")
        except Exception as e:
            print(f"  ✗ Deaths failed: {e}")
        
        try:
            results["movement"] = self.generate_movement_heatmap()
            print(f"  ✓ Movement: {Path(results['movement']).name}")
        except Exception as e:
            print(f"  ✗ Movement failed: {e}")
        
        return results


def generate_heatmaps(
    parsed_demo: ParsedDemo,
    output_dir: str = "outputs/heatmaps",
    resolution: int = 384,
    phase: Optional[str] = None
) -> Dict[str, str]:
    """
    Convenience function to generate all heatmaps.
    
    Args:
        parsed_demo: ParsedDemo object
        output_dir: Base output directory
        resolution: Grid resolution
        phase: Round phase filter ("early", "mid", "late", or None)
        
    Returns:
        Dictionary mapping heatmap type to file path
    """
    generator = HeatmapGenerator(
        parsed_demo=parsed_demo,
        output_dir=output_dir,
        resolution=resolution,
        phase=phase
    )
    return generator.generate_all()
