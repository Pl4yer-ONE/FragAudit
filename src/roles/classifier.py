# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Role Classifier v2
Per-round dynamic role detection for CS2 players.

FIXED:
- No more dual classification (CT+T in same round)
- Real team detection from demo data
- Spatial metrics (teammate distance) now used
- Evidence-based confidence with thresholds
- Minimum score floor for UNKNOWN

Roles:
- ENTRY: First contact, early kills, aggressive
- LURK: Far from team, late kills, flanking
- ANCHOR: Low mobility, site holder (CT)
- ROTATOR: Mid-round repositioning
- SUPPORT: Trades, flash assists
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple, Set
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
    """
    round: int
    player: str
    team: str
    role: str
    confidence: float
    raw_score: float = 0.0
    evidence_count: int = 0
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


class RoleClassifier:
    """
    Classifies player roles per round based on behavioral + spatial metrics.
    """
    
    # Thresholds
    LURK_DISTANCE_THRESHOLD = 1800  # Units - must be truly isolated
    MIN_EVIDENCE_FOR_CONFIDENCE = 2
    MIN_SCORE_THRESHOLD = 0.25  # Lowered to reduce UNKNOWN
    
    def classify_round(self, parsed_demo, round_num: int) -> List[RoleAssignment]:
        """
        Classify all players' roles for a specific round.
        Team is auto-detected from demo data (no dual classification).
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
        
        # Build player->team mapping from this round's data
        # Each player belongs to ONE team per round
        player_teams: Dict[str, str] = {}
        player_positions: Dict[str, List[Tuple[float, float]]] = {}
        
        for _, kill in round_kills.iterrows():
            attacker = str(kill.get('attacker_name', '') or '')
            attacker_team = str(kill.get('attacker_team_name', '') or '')
            attacker_x = float(kill.get('attacker_X', 0) or 0)
            attacker_y = float(kill.get('attacker_Y', 0) or 0)
            
            victim = str(kill.get('user_name', kill.get('victim_name', '')) or '')
            victim_team = str(kill.get('user_team_name', kill.get('victim_team_name', '')) or '')
            victim_x = float(kill.get('user_X', kill.get('victim_X', 0)) or 0)
            victim_y = float(kill.get('user_Y', kill.get('victim_Y', 0)) or 0)
            
            # Store team (first occurrence wins)
            if attacker and attacker not in player_teams:
                player_teams[attacker] = self._normalize_team(attacker_team)
            if victim and victim not in player_teams:
                player_teams[victim] = self._normalize_team(victim_team)
            
            # Store positions for spatial analysis
            if attacker:
                if attacker not in player_positions:
                    player_positions[attacker] = []
                player_positions[attacker].append((attacker_x, attacker_y))
            if victim:
                if victim not in player_positions:
                    player_positions[victim] = []
                player_positions[victim].append((victim_x, victim_y))
        
        # Classify each player (once per round, not per team)
        for player, team in player_teams.items():
            if not player:
                continue
            
            role, confidence, raw_score, evidence, metrics = self._classify_player(
                round_kills, 
                player, 
                team, 
                player_teams,
                player_positions
            )
            
            assignments.append(RoleAssignment(
                round=round_num,
                player=player,
                team=team,
                role=role.value,
                confidence=confidence,
                raw_score=raw_score,
                evidence_count=evidence,
                metrics=metrics
            ))
        
        return assignments
    
    def _normalize_team(self, team_str: str) -> str:
        """Normalize team name to CT or T."""
        team_upper = team_str.upper()
        if 'CT' in team_upper or 'COUNTER' in team_upper:
            return 'CT'
        elif 'T' in team_upper or 'TERRORIST' in team_upper:
            return 'T'
        return 'UNKNOWN'
    
    def _calculate_avg_teammate_distance(
        self,
        player: str,
        player_positions: Dict[str, List[Tuple[float, float]]],
        player_teams: Dict[str, str]
    ) -> float:
        """Calculate average distance from teammates at kill moments."""
        if player not in player_positions or player not in player_teams:
            return 0.0
        
        player_team = player_teams[player]
        player_pos = player_positions[player]
        
        if not player_pos:
            return 0.0
        
        # Get teammates
        teammates = [
            p for p, t in player_teams.items() 
            if t == player_team and p != player and p in player_positions
        ]
        
        if not teammates:
            return 0.0
        
        # Calculate average distance across all position samples
        total_dist = 0.0
        count = 0
        
        for px, py in player_pos:
            for tm in teammates:
                if player_positions.get(tm):
                    # Use first position of teammate
                    tx, ty = player_positions[tm][0]
                    total_dist += _distance(px, py, tx, ty)
                    count += 1
        
        return total_dist / count if count > 0 else 0.0
    
    def _classify_player(
        self,
        round_kills,
        player: str,
        team: str,
        player_teams: Dict[str, str],
        player_positions: Dict[str, List[Tuple[float, float]]]
    ) -> Tuple[RoleType, float, float, int, Dict[str, float]]:
        """
        Classify a single player's role with evidence-based confidence.
        
        Returns:
            (role, confidence, raw_score, evidence_count, metrics)
        """
        metrics = {
            'entry_kill': 0.0,
            'first_death': 0.0,
            'kill_timing': 0.0,
            'trade_given': 0.0,
            'trade_taken': 0.0,
            'total_kills': 0.0,
            'total_deaths': 0.0,
            'avg_teammate_dist': 0.0,
        }
        
        evidence_count = 0
        
        # Calculate spatial metric - ACTUALLY USE IT NOW
        avg_dist = self._calculate_avg_teammate_distance(player, player_positions, player_teams)
        metrics['avg_teammate_dist'] = round(avg_dist, 1)
        
        # Entry kill check
        if len(round_kills) > 0:
            first_kill = round_kills.iloc[0]
            if first_kill.get('attacker_name', '') == player:
                metrics['entry_kill'] = 1.0
                evidence_count += 1
            
            first_victim = first_kill.get('user_name', first_kill.get('victim_name', ''))
            if first_victim == player:
                metrics['first_death'] = 1.0
                evidence_count += 1
        
        # Count kills and deaths
        for _, kill in round_kills.iterrows():
            attacker = kill.get('attacker_name', '')
            victim = kill.get('user_name', kill.get('victim_name', ''))
            
            if attacker == player:
                metrics['total_kills'] += 1
            if victim == player:
                metrics['total_deaths'] += 1
        
        if metrics['total_kills'] > 0:
            evidence_count += 1
        if metrics['total_deaths'] > 0:
            evidence_count += 1
        
        # Trade activity
        prev_victim = None
        prev_tick = 0
        prev_victim_team = None
        
        for _, kill in round_kills.iterrows():
            attacker = kill.get('attacker_name', '')
            victim = kill.get('user_name', kill.get('victim_name', ''))
            victim_team = str(kill.get('user_team_name', kill.get('victim_team_name', '')))
            tick = int(kill.get('tick', 0))
            
            # Was player traded?
            if prev_victim == player and (tick - prev_tick) <= 192:
                metrics['trade_given'] = 1.0
                evidence_count += 1
            
            # Did player trade a teammate?
            if attacker == player and prev_victim and (tick - prev_tick) <= 192:
                # Check if prev_victim was on same team as player
                if player_teams.get(prev_victim) == team:
                    metrics['trade_taken'] = 1.0
                    evidence_count += 1
            
            prev_victim = victim
            prev_victim_team = victim_team
            prev_tick = tick
        
        # Kill timing
        player_kill_ticks = []
        for _, kill in round_kills.iterrows():
            if kill.get('attacker_name', '') == player:
                player_kill_ticks.append(int(kill.get('tick', 0)))
        
        if player_kill_ticks and len(round_kills) > 0:
            first_tick = int(round_kills.iloc[0]['tick'])
            avg_kill_tick = sum(player_kill_ticks) / len(player_kill_ticks)
            metrics['kill_timing'] = round((avg_kill_tick - first_tick) / 64, 1)  # Seconds
        
        # Score each role
        role_scores = {
            RoleType.ENTRY: 0.0,
            RoleType.LURK: 0.0,
            RoleType.ANCHOR: 0.0,
            RoleType.ROTATOR: 0.0,
            RoleType.SUPPORT: 0.0,
        }
        
        # ENTRY scoring - strongest signal
        if metrics['entry_kill'] > 0:
            role_scores[RoleType.ENTRY] += 0.7  # Strong signal
        if metrics['first_death'] > 0 and team == 'T':
            role_scores[RoleType.ENTRY] += 0.2
        if metrics['kill_timing'] < 3 and metrics['total_kills'] > 0:
            role_scores[RoleType.ENTRY] += 0.2
        
        # LURK scoring - requires BOTH distance AND late timing
        is_far = metrics['avg_teammate_dist'] > self.LURK_DISTANCE_THRESHOLD
        is_late = metrics['kill_timing'] > 8
        is_isolated = metrics['trade_given'] == 0 and metrics['total_deaths'] > 0
        
        if is_far and is_late:
            role_scores[RoleType.LURK] += 0.6  # Strong lurk evidence
        elif is_far and is_isolated:
            role_scores[RoleType.LURK] += 0.4
        elif is_late and is_isolated:
            role_scores[RoleType.LURK] += 0.3
        
        # SUPPORT scoring
        if metrics['trade_taken'] > 0:
            role_scores[RoleType.SUPPORT] += 0.6  # Strong signal
        if metrics['avg_teammate_dist'] < 600 and metrics['avg_teammate_dist'] > 0:
            role_scores[RoleType.SUPPORT] += 0.15
        
        # ANCHOR scoring (CT only)
        if team == 'CT':
            if metrics['first_death'] == 0 and metrics['entry_kill'] == 0 and metrics['total_kills'] > 0:
                role_scores[RoleType.ANCHOR] += 0.4
            elif metrics['first_death'] == 0 and metrics['total_deaths'] == 0:
                role_scores[RoleType.ANCHOR] += 0.3  # Survived = site held
            if metrics['avg_teammate_dist'] < 800 and metrics['avg_teammate_dist'] > 0:
                role_scores[RoleType.ANCHOR] += 0.2
        
        # ROTATOR scoring
        if metrics['trade_taken'] > 0 and metrics['kill_timing'] > 3:
            role_scores[RoleType.ROTATOR] += 0.4
        if team == 'CT' and metrics['total_kills'] > 0 and metrics['kill_timing'] > 5:
            role_scores[RoleType.ROTATOR] += 0.2
        
        # Find best role
        best_role = max(role_scores, key=role_scores.get)
        raw_score = role_scores[best_role]
        
        # FALLBACK for low signal players
        if raw_score < self.MIN_SCORE_THRESHOLD:
            # Assign default based on team and basic metrics
            if team == 'CT':
                if metrics['total_deaths'] == 0:
                    best_role = RoleType.ANCHOR  # Survived = held site
                else:
                    best_role = RoleType.SUPPORT  # Default CT role
            else:  # T side
                if metrics['first_death'] > 0:
                    best_role = RoleType.ENTRY  # First to die on T = entry
                else:
                    best_role = RoleType.SUPPORT
            
            raw_score = 0.25
            confidence = 0.3  # Low confidence for fallback
            return best_role, confidence, raw_score, evidence_count, metrics
        
        # Confidence calculation
        if evidence_count < self.MIN_EVIDENCE_FOR_CONFIDENCE:
            confidence = raw_score * 0.5
        else:
            sorted_scores = sorted(role_scores.values(), reverse=True)
            if len(sorted_scores) > 1 and sorted_scores[1] > 0:
                margin = raw_score - sorted_scores[1]
                confidence = min(1.0, 0.5 + margin)
            else:
                confidence = min(1.0, raw_score)
        
        confidence = round(max(0.0, min(1.0, confidence)), 2)
        
        return best_role, confidence, round(raw_score, 2), evidence_count, metrics


def classify_roles(parsed_demo) -> List[RoleAssignment]:
    """
    Classify roles for all rounds in a demo.
    NO TEAM PARAMETER - team is auto-detected per player.
    """
    classifier = RoleClassifier()
    all_assignments = []
    
    kills = parsed_demo.kills
    if kills is None or kills.empty:
        return all_assignments
    
    round_col = 'total_rounds_played' if 'total_rounds_played' in kills.columns else 'round_num'
    if round_col not in kills.columns:
        return all_assignments
    
    round_nums = sorted(kills[round_col].unique())
    
    for round_num in round_nums:
        assignments = classifier.classify_round(parsed_demo, int(round_num))
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
        role_counts[a.role] = role_counts.get(a.role, 0) + 1
        
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
        "schema_version": "2.0",
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
