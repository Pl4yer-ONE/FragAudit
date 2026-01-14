# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Role Classifier
Per-round dynamic role detection for CS2 players.

Roles:
- ENTRY: First contact, aggressive positioning, low survival
- LURK: High distance from team, late rotates, flanking
- ANCHOR: Site holder, low mobility, defensive positioning
- ROTATOR: Mid-round repositioning, support plays
- SUPPORT: Utility-focused, trades, assists

Detection based on:
- Time to first contact
- Distance from teammates
- Bomb proximity
- Kill timing (entry frags vs trades)
- Flash assists
- Position in team formation
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import math


class RoleType(Enum):
    """Player role taxonomy."""
    ENTRY = "ENTRY"
    LURK = "LURK"
    ANCHOR = "ANCHOR"
    ROTATOR = "ROTATOR"
    SUPPORT = "SUPPORT"
    UNKNOWN = "UNKNOWN"


@dataclass
class RoleAssignment:
    """
    Role assignment for a player in a specific round.
    
    Attributes:
        round: Round number
        player: Player name
        steam_id: Steam ID
        team: CT or T
        role: Detected role
        confidence: Confidence score (0.0 - 1.0)
        metrics: Supporting metrics used for classification
    """
    round: int
    player: str
    team: str
    role: str
    confidence: float
    steam_id: str = ""
    metrics: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        d = asdict(self)
        if d['metrics'] is None:
            d['metrics'] = {}
        return d


def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate 2D Euclidean distance."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def _get_avg_teammate_distance(
    player_x: float, 
    player_y: float, 
    teammates: List[Dict]
) -> float:
    """Calculate average distance to teammates."""
    if not teammates:
        return 0.0
    
    total_dist = 0.0
    for tm in teammates:
        tm_x = float(tm.get('x', tm.get('X', 0)) or 0)
        tm_y = float(tm.get('y', tm.get('Y', 0)) or 0)
        total_dist += _distance(player_x, player_y, tm_x, tm_y)
    
    return total_dist / len(teammates)


class RoleClassifier:
    """
    Classifies player roles per round based on behavioral metrics.
    
    Metrics used:
    - entry_kill: Was this player the first killer in round?
    - first_death: Was this player the first death?
    - avg_teammate_dist: Average distance from teammates at key moments
    - kill_timing: When in round did kills happen (early/late)
    - trade_given: Did player get traded after death?
    - trade_taken: Did player trade a teammate's death?
    """
    
    # Thresholds
    LURK_DISTANCE_THRESHOLD = 1500  # Units from team avg
    ENTRY_TIMING_THRESHOLD = 10000  # First 10s of round
    ANCHOR_MOBILITY_THRESHOLD = 500  # Low movement
    
    def __init__(self):
        self.role_scores: Dict[str, Dict[RoleType, float]] = {}
    
    def classify_round(
        self, 
        parsed_demo, 
        round_num: int,
        team: str = "CT"
    ) -> List[RoleAssignment]:
        """
        Classify all players' roles for a specific round.
        
        Args:
            parsed_demo: Parsed demo object
            round_num: Round to analyze
            team: Team to classify (CT or T)
            
        Returns:
            List of RoleAssignment objects
        """
        assignments = []
        
        kills = parsed_demo.kills
        if kills is None or kills.empty:
            return assignments
        
        # Get round kills
        round_col = 'total_rounds_played' if 'total_rounds_played' in kills.columns else 'round_num'
        if round_col not in kills.columns:
            return assignments
        
        round_kills = kills[kills[round_col] == round_num].sort_values('tick')
        
        if round_kills.empty:
            return assignments
        
        # Get unique players who participated
        players_in_round = set()
        team_filter = team.upper()
        
        for _, kill in round_kills.iterrows():
            attacker = kill.get('attacker_name', '')
            attacker_team = str(kill.get('attacker_team_name', ''))
            victim = kill.get('user_name', kill.get('victim_name', ''))
            victim_team = str(kill.get('user_team_name', kill.get('victim_team_name', '')))
            
            if team_filter in attacker_team.upper():
                players_in_round.add(attacker)
            if team_filter in victim_team.upper():
                players_in_round.add(victim)
        
        # Classify each player
        for player in players_in_round:
            if not player:
                continue
            
            role, confidence, metrics = self._classify_player(
                round_kills, player, team_filter, round_num
            )
            
            assignments.append(RoleAssignment(
                round=round_num,
                player=player,
                team=team_filter,
                role=role.value,
                confidence=confidence,
                metrics=metrics
            ))
        
        return assignments
    
    def _classify_player(
        self,
        round_kills,
        player: str,
        team: str,
        round_num: int
    ) -> Tuple[RoleType, float, Dict[str, float]]:
        """
        Classify a single player's role.
        
        Returns:
            (role, confidence, metrics)
        """
        metrics = {
            'entry_kill': 0.0,
            'first_death': 0.0,
            'kill_timing': 0.0,
            'trade_given': 0.0,
            'trade_taken': 0.0,
            'total_kills': 0.0,
            'total_deaths': 0.0,
        }
        
        # Check if player got entry kill
        if len(round_kills) > 0:
            first_kill = round_kills.iloc[0]
            if first_kill.get('attacker_name', '') == player:
                metrics['entry_kill'] = 1.0
            
            first_victim = first_kill.get('user_name', first_kill.get('victim_name', ''))
            if first_victim == player:
                metrics['first_death'] = 1.0
        
        # Count kills and deaths
        for _, kill in round_kills.iterrows():
            attacker = kill.get('attacker_name', '')
            victim = kill.get('user_name', kill.get('victim_name', ''))
            
            if attacker == player:
                metrics['total_kills'] += 1
            if victim == player:
                metrics['total_deaths'] += 1
        
        # Check trade activity
        prev_victim = None
        prev_tick = 0
        for _, kill in round_kills.iterrows():
            attacker = kill.get('attacker_name', '')
            victim = kill.get('user_name', kill.get('victim_name', ''))
            tick = int(kill.get('tick', 0))
            
            # Was player traded?
            if prev_victim == player and (tick - prev_tick) <= 192:  # 3s
                metrics['trade_given'] = 1.0
            
            # Did player trade?
            if attacker == player and prev_victim and (tick - prev_tick) <= 192:
                metrics['trade_taken'] = 1.0
            
            prev_victim = victim
            prev_tick = tick
        
        # Calculate kill timing (early = entry, late = lurk)
        player_kill_ticks = []
        for _, kill in round_kills.iterrows():
            if kill.get('attacker_name', '') == player:
                player_kill_ticks.append(int(kill.get('tick', 0)))
        
        if player_kill_ticks and len(round_kills) > 0:
            first_tick = int(round_kills.iloc[0]['tick'])
            avg_kill_tick = sum(player_kill_ticks) / len(player_kill_ticks)
            metrics['kill_timing'] = (avg_kill_tick - first_tick) / 1000  # Normalize
        
        # Score each role
        role_scores = {
            RoleType.ENTRY: 0.0,
            RoleType.LURK: 0.0,
            RoleType.ANCHOR: 0.0,
            RoleType.ROTATOR: 0.0,
            RoleType.SUPPORT: 0.0,
        }
        
        # ENTRY scoring
        if metrics['entry_kill'] > 0:
            role_scores[RoleType.ENTRY] += 0.5
        if metrics['first_death'] > 0 and team == 'T':
            role_scores[RoleType.ENTRY] += 0.3  # T side entry dies first often
        if metrics['kill_timing'] < 5:  # Early kills
            role_scores[RoleType.ENTRY] += 0.2
        
        # LURK scoring
        if metrics['kill_timing'] > 15:  # Late kills
            role_scores[RoleType.LURK] += 0.4
        if metrics['trade_given'] == 0 and metrics['total_deaths'] > 0:
            role_scores[RoleType.LURK] += 0.3  # Died without trade = isolated
        
        # SUPPORT scoring
        if metrics['trade_taken'] > 0:
            role_scores[RoleType.SUPPORT] += 0.5
        if metrics['total_kills'] == 0 and metrics['total_deaths'] == 0:
            role_scores[RoleType.SUPPORT] += 0.2  # Survived without kills = support
        
        # ANCHOR scoring (CT-focused)
        if team == 'CT':
            if metrics['first_death'] == 0 and metrics['entry_kill'] == 0:
                role_scores[RoleType.ANCHOR] += 0.3
            if metrics['kill_timing'] > 10:
                role_scores[RoleType.ANCHOR] += 0.2
        
        # ROTATOR scoring
        if metrics['trade_taken'] > 0 and metrics['kill_timing'] > 5:
            role_scores[RoleType.ROTATOR] += 0.4
        
        # Normalize and pick best
        total_score = sum(role_scores.values())
        if total_score == 0:
            return RoleType.UNKNOWN, 0.0, metrics
        
        best_role = max(role_scores, key=role_scores.get)
        confidence = role_scores[best_role] / total_score
        
        # Clamp confidence
        confidence = min(1.0, max(0.0, confidence))
        
        return best_role, round(confidence, 2), metrics


def classify_roles(parsed_demo, team: str = "both") -> List[RoleAssignment]:
    """
    Classify roles for all rounds in a demo.
    
    Args:
        parsed_demo: Parsed demo object
        team: "CT", "T", or "both"
        
    Returns:
        List of all role assignments
    """
    classifier = RoleClassifier()
    all_assignments = []
    
    # Get round numbers
    kills = parsed_demo.kills
    if kills is None or kills.empty:
        return all_assignments
    
    round_col = 'total_rounds_played' if 'total_rounds_played' in kills.columns else 'round_num'
    if round_col not in kills.columns:
        return all_assignments
    
    round_nums = sorted(kills[round_col].unique())
    
    teams = []
    if team.lower() in ['ct', 'both']:
        teams.append('CT')
    if team.lower() in ['t', 'both']:
        teams.append('T')
    
    for round_num in round_nums:
        for t in teams:
            assignments = classifier.classify_round(parsed_demo, int(round_num), t)
            all_assignments.extend(assignments)
    
    # Sort by round, then player
    all_assignments.sort(key=lambda a: (a.round, a.player))
    
    return all_assignments


def export_roles_json(assignments: List[RoleAssignment], output_path: str) -> str:
    """Export role assignments to JSON file."""
    import json
    from pathlib import Path
    
    # Aggregate stats
    role_counts = {}
    player_role_freq = {}
    
    for a in assignments:
        # Count by role
        role_counts[a.role] = role_counts.get(a.role, 0) + 1
        
        # Track player's most common role
        if a.player not in player_role_freq:
            player_role_freq[a.player] = {}
        player_role_freq[a.player][a.role] = player_role_freq[a.player].get(a.role, 0) + 1
    
    # Determine primary role per player
    player_primary_roles = {}
    for player, roles in player_role_freq.items():
        if roles:
            primary = max(roles, key=roles.get)
            total = sum(roles.values())
            player_primary_roles[player] = {
                "role": primary,
                "frequency": round(roles[primary] / total, 2),
                "rounds": total
            }
    
    output = {
        "schema_version": "1.0",
        "total_assignments": len(assignments),
        "role_distribution": role_counts,
        "player_primary_roles": player_primary_roles,
        "assignments": [a.to_dict() for a in assignments]
    }
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    return str(path)
