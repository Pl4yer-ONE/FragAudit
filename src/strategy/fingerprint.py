# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Strategy Fingerprint Classifier
Detects team strategies per round based on behavioral signals.

T-Side Strategies:
- EXECUTE_A/B: Fast site hit with utility
- SPLIT_A/B: Multi-angle attack
- DEFAULT: Map control, late hit
- RUSH: No utility fast hit
- FAKE: Misdirection

CT-Side Strategies:
- DEFAULT_2_1_2: Standard 2A-1M-2B
- STACK_A/B: Heavy site presence
- AGGRESSIVE: Early control/push

Detection based on:
- First contact location and timing
- Utility usage count/location
- Player positions at key times
- Bomb plant site
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Set
from enum import Enum


class StrategyType(Enum):
    """Round strategy taxonomy."""
    # T-Side
    EXECUTE_A = "EXECUTE_A"
    EXECUTE_B = "EXECUTE_B"
    SPLIT_A = "SPLIT_A"
    SPLIT_B = "SPLIT_B"
    DEFAULT_T = "DEFAULT_T"
    RUSH_A = "RUSH_A"
    RUSH_B = "RUSH_B"
    FAKE = "FAKE"
    
    # CT-Side
    DEFAULT_CT = "DEFAULT_CT"
    STACK_A = "STACK_A"
    STACK_B = "STACK_B"
    AGGRESSIVE_CT = "AGGRESSIVE_CT"
    
    # Unknown
    UNKNOWN = "UNKNOWN"


@dataclass
class StrategySignal:
    """
    Behavioral signals extracted from a round.
    """
    first_contact_site: str = ""  # A, B, MID
    time_to_first_contact: float = 0.0  # Seconds
    utility_thrown: int = 0
    utility_a: int = 0
    utility_b: int = 0
    utility_mid: int = 0
    bomb_plant_site: str = ""  # A or B (empty if no plant)
    deaths_before_plant: int = 0
    early_deaths: int = 0  # Deaths in first 20s
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoundStrategy:
    """
    Detected strategy for a team in a round.
    """
    round: int
    team: str  # T or CT
    strategy: str
    confidence: float
    signals: Optional[StrategySignal] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d['signals'] is None:
            d['signals'] = {}
        return d


class StrategyClassifier:
    """
    Classifies team strategies per round.
    """
    
    # Timing thresholds (seconds)
    RUSH_THRESHOLD = 15  # Contact < 15s = rush
    FAST_THRESHOLD = 25  # Contact < 25s = fast execute
    DEFAULT_THRESHOLD = 40  # Contact > 40s = default/slow
    
    def __init__(self):
        pass
    
    def extract_signals(
        self, 
        parsed_demo, 
        round_num: int,
        team: str
    ) -> StrategySignal:
        """
        Extract behavioral signals from a round for one team.
        """
        signal = StrategySignal()
        
        kills = parsed_demo.kills
        if kills is None or kills.empty:
            return signal
        
        # Get round kills
        round_col = 'total_rounds_played' if 'total_rounds_played' in kills.columns else 'round_num'
        if round_col not in kills.columns:
            return signal
        
        round_kills = kills[kills[round_col] == round_num].sort_values('tick')
        
        if round_kills.empty:
            return signal
        
        # Find first contact (first kill in round)
        if len(round_kills) > 0:
            first_kill = round_kills.iloc[0]
            tick = int(first_kill.get('tick', 0))
            
            # Convert tick to seconds (assuming 64 tick)
            # Round start is approximated
            signal.time_to_first_contact = round(tick / 64 % 115, 1)
            
            # Determine site from position
            kill_x = float(first_kill.get('user_X', first_kill.get('victim_X', 0)) or 0)
            kill_y = float(first_kill.get('user_Y', first_kill.get('victim_Y', 0)) or 0)
            
            # Simple site detection (map-specific, simplified)
            signal.first_contact_site = self._detect_site_from_pos(kill_x, kill_y)
        
        # Count deaths
        team_upper = team.upper()
        for _, kill in round_kills.iterrows():
            victim_team = str(kill.get('user_team_name', kill.get('victim_team_name', '')))
            tick = int(kill.get('tick', 0))
            time_s = (tick / 64) % 115
            
            if team_upper in victim_team.upper():
                if time_s < 20:
                    signal.early_deaths += 1
        
        return signal
    
    def _detect_site_from_pos(self, x: float, y: float) -> str:
        """
        Simplified site detection from position.
        This is map-agnostic - real implementation would use map data.
        """
        # Very simplified heuristic
        # Positive X typically = A on many maps
        # This should be replaced with proper map callout data
        if x > 500:
            return "A"
        elif x < -500:
            return "B"
        else:
            return "MID"
    
    def classify_round(
        self, 
        parsed_demo, 
        round_num: int,
        team: str = "T"
    ) -> RoundStrategy:
        """
        Classify strategy for a specific round and team.
        """
        signals = self.extract_signals(parsed_demo, round_num, team)
        
        strategy, confidence = self._classify_from_signals(signals, team)
        
        return RoundStrategy(
            round=round_num,
            team=team,
            strategy=strategy.value,
            confidence=confidence,
            signals=signals
        )
    
    def _classify_from_signals(
        self, 
        signals: StrategySignal,
        team: str
    ) -> tuple:
        """
        Classify strategy from extracted signals.
        Returns (StrategyType, confidence).
        """
        team = team.upper()
        
        if team == "T":
            return self._classify_t_side(signals)
        else:
            return self._classify_ct_side(signals)
    
    def _classify_t_side(self, signals: StrategySignal) -> tuple:
        """Classify T-side strategy."""
        time = signals.time_to_first_contact
        site = signals.first_contact_site
        
        # Rush: Very fast contact
        if time < self.RUSH_THRESHOLD:
            if site == "A":
                return StrategyType.RUSH_A, 0.8
            elif site == "B":
                return StrategyType.RUSH_B, 0.8
            else:
                return StrategyType.RUSH_A, 0.5  # Default to A
        
        # Fast execute
        if time < self.FAST_THRESHOLD:
            if site == "A":
                return StrategyType.EXECUTE_A, 0.75
            elif site == "B":
                return StrategyType.EXECUTE_B, 0.75
            else:
                return StrategyType.EXECUTE_A, 0.5
        
        # Default/slow round
        if time >= self.DEFAULT_THRESHOLD:
            return StrategyType.DEFAULT_T, 0.7
        
        # Mid-tempo, could be split or default
        if signals.early_deaths > 1:
            # Lost players early = likely failed default
            return StrategyType.DEFAULT_T, 0.6
        
        # Execute at normal tempo
        if site == "A":
            return StrategyType.EXECUTE_A, 0.6
        elif site == "B":
            return StrategyType.EXECUTE_B, 0.6
        
        return StrategyType.UNKNOWN, 0.3
    
    def _classify_ct_side(self, signals: StrategySignal) -> tuple:
        """Classify CT-side strategy."""
        # CT classification is harder without position data
        # Simplified version based on early deaths
        
        if signals.early_deaths > 1:
            # Lost players early = likely aggressive
            return StrategyType.AGGRESSIVE_CT, 0.6
        
        # Default CT setup
        return StrategyType.DEFAULT_CT, 0.7


def classify_strategies(parsed_demo) -> List[RoundStrategy]:
    """
    Classify strategies for all rounds and both teams.
    """
    classifier = StrategyClassifier()
    strategies = []
    
    kills = parsed_demo.kills
    if kills is None or kills.empty:
        return strategies
    
    round_col = 'total_rounds_played' if 'total_rounds_played' in kills.columns else 'round_num'
    if round_col not in kills.columns:
        return strategies
    
    round_nums = sorted(kills[round_col].unique())
    
    for round_num in round_nums:
        # Classify both teams
        t_strat = classifier.classify_round(parsed_demo, int(round_num), "T")
        ct_strat = classifier.classify_round(parsed_demo, int(round_num), "CT")
        
        strategies.append(t_strat)
        strategies.append(ct_strat)
    
    return strategies


def export_strategies_json(strategies: List[RoundStrategy], output_path: str) -> str:
    """Export strategies to JSON file."""
    import json
    from pathlib import Path
    
    # Aggregate by strategy type
    t_strats = {}
    ct_strats = {}
    
    for s in strategies:
        if s.team == "T":
            t_strats[s.strategy] = t_strats.get(s.strategy, 0) + 1
        else:
            ct_strats[s.strategy] = ct_strats.get(s.strategy, 0) + 1
    
    output = {
        "schema_version": "1.0",
        "total_rounds": len(strategies) // 2,
        "t_side_strategies": t_strats,
        "ct_side_strategies": ct_strats,
        "strategies": [s.to_dict() for s in strategies]
    }
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    return str(path)
