"""
Heatmap Generation Module
Generates kill, death, and movement heatmaps from CS2 demo data.

Uses vectorized numpy operations for performance.
Outputs matplotlib PNG files.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import pandas as pd
from scipy.ndimage import gaussian_filter

from src.parser.demo_parser import ParsedDemo


# CS2 map coordinate bounds (approximate, map-specific)
# Format: (min_x, max_x, min_y, max_y)
MAP_BOUNDS: Dict[str, Tuple[float, float, float, float]] = {
    "de_dust2": (-2476, 1768, -1262, 3239),
    "de_mirage": (-3230, 1855, -3420, 1713),
    "de_inferno": (-2087, 2800, -1150, 3870),
    "de_nuke": (-3453, 3607, -4290, -790),
    "de_overpass": (-4831, 511, -3551, 1781),
    "de_ancient": (-2953, 2164, -2296, 2382),
    "de_anubis": (-2796, 1869, -2458, 2279),
    "de_vertigo": (-3168, 672, -1792, 2048),
}

# Default bounds when map not recognized
DEFAULT_BOUNDS = (-4000, 4000, -4000, 4000)


class HeatmapGenerator:
    """
    Generate heatmaps from CS2 demo data.
    
    Produces:
    - Kill heatmap: Where kills occurred
    - Death heatmap: Where deaths occurred
    - Movement heatmap: Player density over time
    """
    
    def __init__(
        self,
        parsed_demo: ParsedDemo,
        output_dir: str = "outputs/heatmaps",
        resolution: int = 256,
        sigma: float = 3.0
    ):
        """
        Initialize heatmap generator.
        
        Args:
            parsed_demo: ParsedDemo object from parser
            output_dir: Directory to save PNG files
            resolution: Grid resolution (default 256x256)
            sigma: Gaussian smoothing sigma (default 3.0)
        """
        self.demo = parsed_demo
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.resolution = resolution
        self.sigma = sigma
        
        # Detect map and get bounds
        self.map_name = self._normalize_map_name(parsed_demo.map_name)
        self.bounds = MAP_BOUNDS.get(self.map_name, DEFAULT_BOUNDS)
        
        # Custom colormap: transparent -> blue -> cyan -> green -> yellow -> red
        self.cmap = self._create_heatmap_colormap()
    
    def _normalize_map_name(self, map_name: str) -> str:
        """Normalize map name to standard format."""
        if not map_name:
            return "unknown"
        name = map_name.lower().strip()
        if not name.startswith("de_"):
            name = f"de_{name}"
        return name
    
    def _create_heatmap_colormap(self) -> LinearSegmentedColormap:
        """Create custom heatmap colormap with transparency."""
        colors = [
            (0.0, 0.0, 0.0, 0.0),      # Transparent
            (0.0, 0.0, 0.5, 0.3),      # Dark blue
            (0.0, 0.5, 1.0, 0.5),      # Cyan
            (0.0, 1.0, 0.0, 0.7),      # Green
            (1.0, 1.0, 0.0, 0.85),     # Yellow
            (1.0, 0.0, 0.0, 1.0),      # Red
        ]
        return LinearSegmentedColormap.from_list("heatmap", colors, N=256)
    
    def _extract_coordinates(
        self,
        df: pd.DataFrame,
        x_col: str = "X",
        y_col: str = "Y"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract and validate coordinates from DataFrame.
        
        Args:
            df: DataFrame with coordinate columns
            x_col: Name of X coordinate column
            y_col: Name of Y coordinate column
            
        Returns:
            Tuple of (x_coords, y_coords) as numpy arrays
        """
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return np.array([]), np.array([])
        
        if isinstance(df, list):
            return np.array([]), np.array([])
        
        # Find coordinate columns (case-insensitive)
        x_candidates = [x_col, x_col.lower(), 'attacker_X', 'user_X', 'x']
        y_candidates = [y_col, y_col.lower(), 'attacker_Y', 'user_Y', 'y']
        
        actual_x = None
        actual_y = None
        
        for col in x_candidates:
            if col in df.columns:
                actual_x = col
                break
        
        for col in y_candidates:
            if col in df.columns:
                actual_y = col
                break
        
        if actual_x is None or actual_y is None:
            return np.array([]), np.array([])
        
        # Extract as numpy arrays, dropping NaN values
        coords = df[[actual_x, actual_y]].dropna()
        x = coords[actual_x].to_numpy(dtype=np.float64)
        y = coords[actual_y].to_numpy(dtype=np.float64)
        
        return x, y
    
    def _normalize_coordinates(
        self,
        x: np.ndarray,
        y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Normalize CS2 coordinates to [0, resolution] range.
        
        CS2 uses game units where maps have different coordinate systems.
        This normalizes to grid indices for binning.
        
        Args:
            x: X coordinates in game units
            y: Y coordinates in game units
            
        Returns:
            Normalized (x_norm, y_norm) in range [0, resolution]
        """
        min_x, max_x, min_y, max_y = self.bounds
        
        # Handle edge case of zero range
        x_range = max_x - min_x
        y_range = max_y - min_y
        
        if x_range == 0:
            x_range = 1
        if y_range == 0:
            y_range = 1
        
        # Normalize to [0, 1] then scale to resolution
        x_norm = (x - min_x) / x_range * (self.resolution - 1)
        y_norm = (y - min_y) / y_range * (self.resolution - 1)
        
        # Clip to valid range
        x_norm = np.clip(x_norm, 0, self.resolution - 1)
        y_norm = np.clip(y_norm, 0, self.resolution - 1)
        
        return x_norm, y_norm
    
    def _create_density_grid(
        self,
        x: np.ndarray,
        y: np.ndarray
    ) -> np.ndarray:
        """
        Create 2D density grid using vectorized histogram.
        
        Args:
            x: Normalized X coordinates
            y: Normalized Y coordinates
            
        Returns:
            2D numpy array with frequency counts
        """
        if len(x) == 0 or len(y) == 0:
            return np.zeros((self.resolution, self.resolution))
        
        # Use numpy histogram2d for vectorized binning
        grid, _, _ = np.histogram2d(
            y, x,  # Note: y first for correct orientation
            bins=self.resolution,
            range=[[0, self.resolution], [0, self.resolution]]
        )
        
        return grid
    
    def _apply_gaussian_smoothing(self, grid: np.ndarray) -> np.ndarray:
        """
        Apply Gaussian smoothing to density grid.
        
        Args:
            grid: 2D density grid
            
        Returns:
            Smoothed grid
        """
        if self.sigma > 0:
            return gaussian_filter(grid, sigma=self.sigma)
        return grid
    
    def _render_heatmap(
        self,
        grid: np.ndarray,
        title: str,
        output_path: Path
    ) -> str:
        """
        Render heatmap to PNG file.
        
        Args:
            grid: 2D density grid (smoothed)
            title: Plot title
            output_path: Path to save PNG
            
        Returns:
            Path to saved file
        """
        fig, ax = plt.subplots(figsize=(10, 10), dpi=100)
        
        # Plot heatmap
        if grid.max() > 0:
            # Normalize grid for visualization
            grid_norm = grid / grid.max()
        else:
            grid_norm = grid
        
        im = ax.imshow(
            grid_norm,
            cmap=self.cmap,
            origin='lower',
            aspect='equal',
            interpolation='bilinear'
        )
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Density', rotation=270, labelpad=15)
        
        # Labels
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('X Position')
        ax.set_ylabel('Y Position')
        
        # Map info
        map_label = self.map_name if self.map_name != "unknown" else "Unknown Map"
        ax.text(
            0.02, 0.98, f"Map: {map_label}",
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
        )
        
        # Event count
        total_events = int(grid.sum())
        ax.text(
            0.98, 0.98, f"Events: {total_events:,}",
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
        )
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='black')
        plt.close(fig)
        
        return str(output_path)
    
    def generate_kills_heatmap(self) -> str:
        """
        Generate heatmap of kill locations.
        
        Returns:
            Path to saved PNG file
        """
        kills_df = self.demo.kills
        
        # Extract attacker positions (where kills happened)
        x, y = self._extract_coordinates(kills_df, "attacker_X", "attacker_Y")
        
        # If no attacker coords, try victim coords
        if len(x) == 0:
            x, y = self._extract_coordinates(kills_df, "X", "Y")
        
        # Normalize and bin
        x_norm, y_norm = self._normalize_coordinates(x, y)
        grid = self._create_density_grid(x_norm, y_norm)
        grid = self._apply_gaussian_smoothing(grid)
        
        # Render
        output_path = self.output_dir / "kills_heatmap.png"
        return self._render_heatmap(grid, "Kill Locations Heatmap", output_path)
    
    def generate_deaths_heatmap(self) -> str:
        """
        Generate heatmap of death locations.
        
        Returns:
            Path to saved PNG file
        """
        kills_df = self.demo.kills  # Deaths are recorded as kills from victim perspective
        
        # Extract victim positions
        x, y = self._extract_coordinates(kills_df, "user_X", "user_Y")
        
        # Fallback to generic columns
        if len(x) == 0:
            x, y = self._extract_coordinates(kills_df, "X", "Y")
        
        # Normalize and bin
        x_norm, y_norm = self._normalize_coordinates(x, y)
        grid = self._create_density_grid(x_norm, y_norm)
        grid = self._apply_gaussian_smoothing(grid)
        
        # Render
        output_path = self.output_dir / "deaths_heatmap.png"
        return self._render_heatmap(grid, "Death Locations Heatmap", output_path)
    
    def generate_movement_heatmap(self) -> str:
        """
        Generate heatmap of player movement density.
        
        Uses per-tick position data for comprehensive coverage.
        
        Returns:
            Path to saved PNG file
        """
        positions_df = self.demo.player_positions
        
        # Extract positions
        x, y = self._extract_coordinates(positions_df, "X", "Y")
        
        # If no position data, fall back to kill locations as proxy
        if len(x) == 0:
            print("  Warning: No position data, using kill/death locations as proxy")
            kills_df = self.demo.kills
            x1, y1 = self._extract_coordinates(kills_df, "attacker_X", "attacker_Y")
            x2, y2 = self._extract_coordinates(kills_df, "user_X", "user_Y")
            x = np.concatenate([x1, x2]) if len(x1) > 0 or len(x2) > 0 else np.array([])
            y = np.concatenate([y1, y2]) if len(y1) > 0 or len(y2) > 0 else np.array([])
        
        # Normalize and bin
        x_norm, y_norm = self._normalize_coordinates(x, y)
        grid = self._create_density_grid(x_norm, y_norm)
        grid = self._apply_gaussian_smoothing(grid)
        
        # Render
        output_path = self.output_dir / "movement_heatmap.png"
        return self._render_heatmap(grid, "Movement Density Heatmap", output_path)
    
    def generate_all(self) -> Dict[str, str]:
        """
        Generate all heatmaps.
        
        Returns:
            Dictionary mapping heatmap type to file path
        """
        results = {}
        
        print("Generating heatmaps...")
        
        try:
            results["kills"] = self.generate_kills_heatmap()
            print(f"  ✓ Kills heatmap: {results['kills']}")
        except Exception as e:
            print(f"  ✗ Kills heatmap failed: {e}")
        
        try:
            results["deaths"] = self.generate_deaths_heatmap()
            print(f"  ✓ Deaths heatmap: {results['deaths']}")
        except Exception as e:
            print(f"  ✗ Deaths heatmap failed: {e}")
        
        try:
            results["movement"] = self.generate_movement_heatmap()
            print(f"  ✓ Movement heatmap: {results['movement']}")
        except Exception as e:
            print(f"  ✗ Movement heatmap failed: {e}")
        
        return results


def generate_heatmaps(
    parsed_demo: ParsedDemo,
    output_dir: str = "outputs/heatmaps",
    resolution: int = 256,
    sigma: float = 3.0
) -> Dict[str, str]:
    """
    Convenience function to generate all heatmaps from parsed demo.
    
    Args:
        parsed_demo: ParsedDemo object from parser
        output_dir: Directory to save PNG files
        resolution: Grid resolution
        sigma: Gaussian smoothing sigma
        
    Returns:
        Dictionary mapping heatmap type to file path
    """
    generator = HeatmapGenerator(
        parsed_demo=parsed_demo,
        output_dir=output_dir,
        resolution=resolution,
        sigma=sigma
    )
    return generator.generate_all()
