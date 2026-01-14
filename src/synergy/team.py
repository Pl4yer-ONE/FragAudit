# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Team Synergy Metrics
Entry success, trade chains, utility efficiency.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from collections import defaultdict


@dataclass
class TeamStats:
    """
    Team-level synergy statistics.
    """
    team: str  # 'CT' or 'T'
    
    # Entry metrics
    entry_attempts: int = 0
    entry_successes: int = 0
    
    # Trade chain
    total_trade_chains: int = 0
    avg_trade_chain_length: float = 0.0
    
    # Utility
    utility_throws: int = 0
    utility_kills_assisted: int = 0
    
    # Retake/Postplant
    retake_attempts: int = 0
    retake_successes: int = 0
    postplant_rounds: int = 0
    postplant_wins: int = 0
    
    @property
    def entry_success_rate(self) -> float:
        if self.entry_attempts == 0:
            return 0.0
        return self.entry_successes / self.entry_attempts
    
    @property
    def utility_efficiency(self) -> float:
        if self.utility_throws == 0:
            return 0.0
        return self.utility_kills_assisted / self.utility_throws
    
    @property
    def retake_success_rate(self) -> float:
        if self.retake_attempts == 0:
            return 0.0
        return self.retake_successes / self.retake_attempts
    
    @property
    def postplant_win_rate(self) -> float:
        if self.postplant_rounds == 0:
            return 0.0
        return self.postplant_wins / self.postplant_rounds
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['entry_success_rate'] = self.entry_success_rate
        d['utility_efficiency'] = self.utility_efficiency
        d['retake_success_rate'] = self.retake_success_rate
        d['postplant_win_rate'] = self.postplant_win_rate
        return d


def compute_team_metrics(timelines, round_results: Dict[int, str] = None) -> Dict[str, TeamStats]:
    """
    Compute team-level synergy metrics.
    
    Args:
        timelines: List of RoundTimeline objects
        round_results: Optional dict mapping round -> winner team
        
    Returns:
        Dict with 'CT' and 'T' TeamStats
    """
    stats = {
        'CT': TeamStats(team='CT'),
        'T': TeamStats(team='T')
    }
    
    for timeline in timelines:
        round_num = timeline.round
        first_kill_team = None
        has_plant = False
        
        for event in timeline.events:
            # Entry tracking
            if event.event == 'ENTRY_KILL' and event.is_entry:
                team = event.team
                stats[team].entry_attempts += 1
                
                # Check if entry team won the round
                if round_results and round_results.get(round_num) == team:
                    stats[team].entry_successes += 1
                
                if first_kill_team is None:
                    first_kill_team = team
            
            # Plant tracking
            if event.event == 'PLANT':
                has_plant = True
                stats['T'].postplant_rounds += 1
                
                # Check postplant win
                if round_results and round_results.get(round_num) == 'T':
                    stats['T'].postplant_wins += 1
            
            # Defuse = CT retake success
            if event.event == 'DEFUSE':
                stats['CT'].retake_attempts += 1
                stats['CT'].retake_successes += 1
    
    return stats
