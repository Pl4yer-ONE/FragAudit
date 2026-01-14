# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Player Tracker - Cross-Demo Analytics
Compares player performance across multiple demos and tracks trends.
"""

import json
import os
from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PlayerMatch:
    """Single match data for a player."""
    match_id: str
    map_name: str
    timestamp: str
    role: str
    final_rating: int
    kills: int
    deaths: int
    kdr: float
    kast: float
    raw_impact: float
    exit_frags: int


@dataclass
class PlayerProfile:
    """Aggregated player data across matches."""
    steam_id: str
    name: str
    matches: List[PlayerMatch] = field(default_factory=list)
    
    @property
    def avg_rating(self) -> float:
        if not self.matches:
            return 0
        return sum(m.final_rating for m in self.matches) / len(self.matches)
    
    @property
    def rating_variance(self) -> float:
        if len(self.matches) < 2:
            return 0
        avg = self.avg_rating
        return sum((m.final_rating - avg) ** 2 for m in self.matches) / len(self.matches)
    
    @property
    def consistency_score(self) -> float:
        """Higher = more consistent. 100 = no variance."""
        if not self.matches:
            return 0
        variance = self.rating_variance
        return max(0, 100 - variance)
    
    @property
    def avg_kdr(self) -> float:
        if not self.matches:
            return 0
        return sum(m.kdr for m in self.matches) / len(self.matches)
    
    @property
    def trend(self) -> str:
        """Calculate trend: improving, declining, or stable."""
        if len(self.matches) < 2:
            return "insufficient_data"
        
        # Compare first half to second half
        sorted_matches = sorted(self.matches, key=lambda m: m.timestamp)
        mid = len(sorted_matches) // 2
        first_half = sorted_matches[:mid]
        second_half = sorted_matches[mid:]
        
        first_avg = sum(m.final_rating for m in first_half) / len(first_half)
        second_avg = sum(m.final_rating for m in second_half) / len(second_half)
        
        diff = second_avg - first_avg
        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        else:
            return "stable"
    
    @property
    def form_rating(self) -> float:
        """Recent form - last 3 matches."""
        if not self.matches:
            return 0
        sorted_matches = sorted(self.matches, key=lambda m: m.timestamp, reverse=True)
        recent = sorted_matches[:3]
        return sum(m.final_rating for m in recent) / len(recent)
    
    @property
    def primary_role(self) -> str:
        """Most common role."""
        if not self.matches:
            return "Unknown"
        roles = {}
        for m in self.matches:
            roles[m.role] = roles.get(m.role, 0) + 1
        return max(roles, key=roles.get)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "steam_id": self.steam_id,
            "name": self.name,
            "matches_played": len(self.matches),
            "primary_role": self.primary_role,
            "avg_rating": round(self.avg_rating, 1),
            "form_rating": round(self.form_rating, 1),
            "consistency": round(self.consistency_score, 1),
            "rating_variance": round(self.rating_variance, 1),
            "avg_kdr": round(self.avg_kdr, 2),
            "trend": self.trend,
            "match_history": [
                {
                    "match_id": m.match_id,
                    "map": m.map_name,
                    "role": m.role,
                    "rating": m.final_rating,
                    "kdr": round(m.kdr, 2)
                }
                for m in sorted(self.matches, key=lambda x: x.timestamp, reverse=True)
            ]
        }


class PlayerTracker:
    """Track players across multiple demos."""
    
    def __init__(self):
        self.players: Dict[str, PlayerProfile] = {}
    
    def load_report(self, report_path: str) -> None:
        """Load a single match report."""
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        meta = data.get("meta", {})
        match_id = meta.get("match_id", os.path.basename(report_path))
        map_name = meta.get("map", "unknown")
        timestamp = meta.get("timestamp", datetime.now().isoformat())
        
        for steam_id, player_data in data.get("players", {}).items():
            stats = player_data.get("stats", {})
            scores = player_data.get("scores", {})
            
            match = PlayerMatch(
                match_id=match_id,
                map_name=map_name,
                timestamp=timestamp,
                role=player_data.get("role", "Unknown"),
                final_rating=player_data.get("final_rating", 0),
                kills=stats.get("kills", 0),
                deaths=stats.get("deaths", 1),
                kdr=stats.get("kdr", stats.get("kills", 0) / max(1, stats.get("deaths", 1))),
                kast=stats.get("kast_percentage", 0),
                raw_impact=scores.get("raw_impact", 0),
                exit_frags=stats.get("exit_frags", 0)
            )
            
            if steam_id not in self.players:
                self.players[steam_id] = PlayerProfile(
                    steam_id=steam_id,
                    name=player_data.get("name", "Unknown")
                )
            
            self.players[steam_id].matches.append(match)
    
    def load_directory(self, directory: str) -> int:
        """Load all match reports from a directory recursively."""
        count = 0
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.startswith("match_report_") and file.endswith(".json"):
                    path = os.path.join(root, file)
                    try:
                        self.load_report(path)
                        count += 1
                    except Exception as e:
                        print(f"Error loading {path}: {e}")
        return count
    
    def get_multi_match_players(self, min_matches: int = 2) -> List[PlayerProfile]:
        """Get players who appear in multiple matches."""
        return [p for p in self.players.values() if len(p.matches) >= min_matches]
    
    def compare_players(self, steam_ids: List[str] = None) -> Dict[str, Any]:
        """Compare players across matches."""
        if steam_ids:
            profiles = [self.players[sid] for sid in steam_ids if sid in self.players]
        else:
            profiles = self.get_multi_match_players()
        
        # Sort by average rating
        profiles = sorted(profiles, key=lambda p: p.avg_rating, reverse=True)
        
        return {
            "comparison_type": "multi_demo",
            "players_analyzed": len(profiles),
            "players": [p.to_dict() for p in profiles]
        }
    
    def generate_leaderboard(self, min_matches: int = 2) -> Dict[str, Any]:
        """Generate leaderboard from multi-match players."""
        multi = self.get_multi_match_players(min_matches)
        
        # Sort by form rating (recent performance)
        by_form = sorted(multi, key=lambda p: p.form_rating, reverse=True)
        
        # Sort by consistency
        by_consistency = sorted(multi, key=lambda p: p.consistency_score, reverse=True)
        
        # Sort by average
        by_average = sorted(multi, key=lambda p: p.avg_rating, reverse=True)
        
        return {
            "by_form": [{"name": p.name, "form": round(p.form_rating, 1)} for p in by_form[:10]],
            "by_consistency": [{"name": p.name, "consistency": round(p.consistency_score, 1)} for p in by_consistency[:10]],
            "by_average": [{"name": p.name, "avg": round(p.avg_rating, 1)} for p in by_average[:10]]
        }


def main():
    """Run player comparison on all available outputs."""
    import sys
    
    tracker = PlayerTracker()
    
    # Load from outputs directory
    outputs_dir = "outputs"
    if len(sys.argv) > 1:
        outputs_dir = sys.argv[1]
    
    count = tracker.load_directory(outputs_dir)
    print(f"Loaded {count} match reports")
    
    # Get comparison
    comparison = tracker.compare_players()
    
    print(f"\n=== PLAYER COMPARISON ({comparison['players_analyzed']} multi-match players) ===\n")
    
    for p in comparison["players"]:
        print(f"{p['name']:<15} | Matches: {p['matches_played']} | Avg: {p['avg_rating']:<5} | "
              f"Form: {p['form_rating']:<5} | Consistency: {p['consistency']:<5} | "
              f"Trend: {p['trend']}")
        for m in p["match_history"][:3]:
            print(f"   └─ {m['map']:<12} {m['role']:<12} Rating: {m['rating']}")
    
    # Output JSON
    output_path = os.path.join(outputs_dir, "player_comparison.json")
    with open(output_path, 'w') as f:
        json.dump(comparison, f, indent=2)
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
