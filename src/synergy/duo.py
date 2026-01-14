# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Duo Synergy Metrics
Trade rates, refrag times, flash assists between player pairs.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Any
from collections import defaultdict


@dataclass
class DuoStats:
    """
    Synergy statistics for a player pair.
    
    Symmetry: DuoStats(A, B) == DuoStats(B, A)
    """
    player1: str
    player2: str
    
    # Trade metrics
    trade_attempts: int = 0
    trade_successes: int = 0
    avg_refrag_time_ms: float = 0.0
    
    # Flash assist
    flash_assists: int = 0
    flash_assist_kills: int = 0
    
    # Round performance
    shared_rounds: int = 0
    shared_round_wins: int = 0
    
    # Clutch support
    clutch_support_attempts: int = 0
    clutch_support_successes: int = 0
    
    @property
    def trade_success_rate(self) -> float:
        if self.trade_attempts == 0:
            return 0.0
        return self.trade_successes / self.trade_attempts
    
    @property
    def flash_assist_success(self) -> float:
        if self.flash_assists == 0:
            return 0.0
        return self.flash_assist_kills / self.flash_assists
    
    @property
    def shared_round_win_rate(self) -> float:
        if self.shared_rounds == 0:
            return 0.0
        return self.shared_round_wins / self.shared_rounds
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['trade_success_rate'] = self.trade_success_rate
        d['flash_assist_success'] = self.flash_assist_success
        d['shared_round_win_rate'] = self.shared_round_win_rate
        return d
    
    def __eq__(self, other):
        """Duo symmetry: (A,B) == (B,A)"""
        if not isinstance(other, DuoStats):
            return False
        return set([self.player1, self.player2]) == set([other.player1, other.player2])
    
    def __hash__(self):
        return hash(frozenset([self.player1, self.player2]))


def _duo_key(p1: str, p2: str) -> Tuple[str, str]:
    """Canonical key for duo (sorted for symmetry)."""
    return tuple(sorted([p1, p2]))


def compute_duo_metrics(timelines, round_results: Dict[int, str] = None) -> List[DuoStats]:
    """
    Compute duo synergy metrics from timelines.
    
    Args:
        timelines: List of RoundTimeline objects
        round_results: Optional dict mapping round -> winner team ('CT' or 'T')
        
    Returns:
        List of DuoStats for all observed player pairs
    """
    # Track trades
    trades: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
    # Track flash assists
    flash_assists: Dict[Tuple[str, str], Dict] = defaultdict(lambda: {'attempts': 0, 'kills': 0})
    # Track shared rounds
    shared_rounds: Dict[Tuple[str, str], Dict] = defaultdict(lambda: {'total': 0, 'wins': 0})
    
    # Players per round per team
    for timeline in timelines:
        round_num = timeline.round
        team_players: Dict[str, List[str]] = defaultdict(list)
        
        # Collect players and detect trades
        recent_deaths: List[Dict] = []
        
        for event in timeline.events:
            if event.player:
                team_players[event.team].append(event.player)
            
            # Trade detection
            if event.event == 'DEATH':
                recent_deaths.append({
                    'player': event.player,
                    'team': event.team,
                    'timestamp_ms': event.timestamp_ms
                })
            
            if event.event in ['KILL', 'ENTRY_KILL', 'TRADE']:
                # Check if this avenges a teammate death
                for death in recent_deaths:
                    if death['team'] == event.team and death['player'] != event.player:
                        time_diff = event.timestamp_ms - death['timestamp_ms']
                        if 0 < time_diff <= 3000:  # Within 3 seconds
                            key = _duo_key(event.player, death['player'])
                            trades[key].append({
                                'success': True,
                                'refrag_ms': time_diff
                            })
        
        # Update shared rounds for all player pairs on same team
        for team, players in team_players.items():
            unique_players = list(set(players))
            for i, p1 in enumerate(unique_players):
                for p2 in unique_players[i+1:]:
                    key = _duo_key(p1, p2)
                    shared_rounds[key]['total'] += 1
                    if round_results and round_results.get(round_num) == team:
                        shared_rounds[key]['wins'] += 1
    
    # Build DuoStats
    all_keys = set(trades.keys()) | set(shared_rounds.keys())
    results: List[DuoStats] = []
    
    for key in all_keys:
        p1, p2 = key
        
        trade_data = trades.get(key, [])
        trade_successes = len([t for t in trade_data if t['success']])
        avg_refrag = sum(t['refrag_ms'] for t in trade_data) / len(trade_data) if trade_data else 0
        
        sr = shared_rounds.get(key, {'total': 0, 'wins': 0})
        
        results.append(DuoStats(
            player1=p1,
            player2=p2,
            trade_attempts=len(trade_data),
            trade_successes=trade_successes,
            avg_refrag_time_ms=avg_refrag,
            shared_rounds=sr['total'],
            shared_round_wins=sr['wins']
        ))
    
    return results
