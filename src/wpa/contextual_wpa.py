# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Contextual WPA Engine
Win Probability Added with situational context weighting.

Context factors:
- Economy: eco vs gun vs anti-eco
- Man-advantage: 5v4, 5v3, etc.
- Clutch pressure: 1vX situations
- Time decay: late round is higher impact

This transforms flat WPA into meaningful impact scores.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Tuple
from enum import Enum
import math


class EconomyType(Enum):
    """Round economy classification."""
    FULL_BUY = "full_buy"      # $4000+ avg equipment
    HALF_BUY = "half_buy"      # $2000-4000 avg
    ECO = "eco"                # $0-2000 avg (force/eco)
    ANTI_ECO = "anti_eco"      # Team has guns vs eco opponent


# Default multipliers - can be overridden via config
DEFAULT_CONFIG = {
    # Economy multipliers (how valuable is a kill in this economy)
    "eco_kill_mult": 1.6,       # Killing during our eco = high value
    "half_buy_mult": 1.2,
    "full_buy_mult": 1.0,
    "anti_eco_mult": 0.6,       # Expected kills, lower impact
    
    # Man advantage multipliers
    "5v4_mult": 1.15,
    "5v3_mult": 1.25,
    "4v3_mult": 1.20,
    "4v4_mult": 1.05,
    "3v3_mult": 1.10,
    
    # Clutch multipliers (1vX)
    "1v1_mult": 1.5,
    "1v2_mult": 2.0,
    "1v3_mult": 2.5,
    "1v4_mult": 3.0,
    "1v5_mult": 4.0,
    
    # Time multipliers (based on % of round remaining)
    "time_early_mult": 0.8,     # First 30s
    "time_mid_mult": 1.0,       # 30-60s
    "time_late_mult": 1.3,      # Last 45s
    "time_bomb_planted_mult": 1.5,  # After plant
}


@dataclass
class WPAContext:
    """
    Context for a specific moment in a round.
    """
    # Economy
    team_equipment_value: int = 0
    enemy_equipment_value: int = 0
    
    # Man count
    team_alive: int = 5
    enemy_alive: int = 5
    
    # Time
    round_time_remaining: float = 115.0  # Seconds
    bomb_planted: bool = False
    
    # Clutch
    is_clutch: bool = False
    clutch_vs: int = 0  # 1vX where X is this value
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WPAResult:
    """
    Result of contextual WPA calculation.
    """
    base_wpa: float
    weighted_wpa: float
    economy_type: str
    economy_mult: float
    man_advantage_mult: float
    clutch_mult: float
    time_mult: float
    total_mult: float
    context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


class ContextualWPA:
    """
    Calculates context-weighted Win Probability Added.
    """
    
    def __init__(self, config: Optional[Dict[str, float]] = None):
        self.config = {**DEFAULT_CONFIG}
        if config:
            self.config.update(config)
    
    def classify_economy(
        self, 
        team_value: int, 
        enemy_value: int
    ) -> EconomyType:
        """
        Classify economy state.
        
        Args:
            team_value: Average equipment value for team
            enemy_value: Average equipment value for enemy
        """
        # Thresholds (per player average)
        ECO_THRESHOLD = 2000
        HALF_THRESHOLD = 3500
        
        team_is_eco = team_value < ECO_THRESHOLD
        enemy_is_eco = enemy_value < ECO_THRESHOLD
        
        if team_is_eco and not enemy_is_eco:
            return EconomyType.ECO
        elif not team_is_eco and enemy_is_eco:
            return EconomyType.ANTI_ECO
        elif team_value < HALF_THRESHOLD:
            return EconomyType.HALF_BUY
        else:
            return EconomyType.FULL_BUY
    
    def get_economy_multiplier(self, economy: EconomyType) -> float:
        """Get multiplier based on economy state."""
        mapping = {
            EconomyType.ECO: self.config["eco_kill_mult"],
            EconomyType.HALF_BUY: self.config["half_buy_mult"],
            EconomyType.FULL_BUY: self.config["full_buy_mult"],
            EconomyType.ANTI_ECO: self.config["anti_eco_mult"],
        }
        return mapping.get(economy, 1.0)
    
    def get_man_advantage_multiplier(
        self, 
        team_alive: int, 
        enemy_alive: int
    ) -> float:
        """Get multiplier based on player count."""
        diff = team_alive - enemy_alive
        
        if diff >= 2:
            return self.config.get("5v3_mult", 1.25)
        elif diff == 1:
            return self.config.get("5v4_mult", 1.15)
        elif diff == 0:
            total = team_alive + enemy_alive
            if total <= 6:
                return self.config.get("3v3_mult", 1.10)
            else:
                return self.config.get("4v4_mult", 1.05)
        else:
            # Disadvantage - no bonus
            return 1.0
    
    def get_clutch_multiplier(self, clutch_vs: int) -> float:
        """Get multiplier for 1vX clutch situations."""
        if clutch_vs <= 0:
            return 1.0
        
        key = f"1v{min(clutch_vs, 5)}_mult"
        return self.config.get(key, 1.0 + (clutch_vs * 0.5))
    
    def get_time_multiplier(
        self, 
        time_remaining: float, 
        bomb_planted: bool
    ) -> float:
        """Get multiplier based on round time."""
        if bomb_planted:
            return self.config["time_bomb_planted_mult"]
        
        # Standard round is 115 seconds
        if time_remaining > 85:  # First 30s
            return self.config["time_early_mult"]
        elif time_remaining > 45:  # Mid round
            return self.config["time_mid_mult"]
        else:  # Last 45s
            return self.config["time_late_mult"]
    
    def calculate(
        self, 
        base_wpa: float, 
        context: WPAContext
    ) -> WPAResult:
        """
        Calculate contextual WPA from base WPA and situational context.
        
        Args:
            base_wpa: Raw WPA value (e.g., 0.05 for a standard kill)
            context: Situational context
            
        Returns:
            WPAResult with weighted WPA
        """
        # Classify economy
        economy = self.classify_economy(
            context.team_equipment_value,
            context.enemy_equipment_value
        )
        
        # Get multipliers
        econ_mult = self.get_economy_multiplier(economy)
        man_mult = self.get_man_advantage_multiplier(
            context.team_alive, 
            context.enemy_alive
        )
        clutch_mult = self.get_clutch_multiplier(
            context.clutch_vs if context.is_clutch else 0
        )
        time_mult = self.get_time_multiplier(
            context.round_time_remaining,
            context.bomb_planted
        )
        
        # Combined multiplier
        total_mult = econ_mult * man_mult * clutch_mult * time_mult
        
        # Weighted WPA
        weighted_wpa = base_wpa * total_mult
        
        return WPAResult(
            base_wpa=round(base_wpa, 4),
            weighted_wpa=round(weighted_wpa, 4),
            economy_type=economy.value,
            economy_mult=round(econ_mult, 2),
            man_advantage_mult=round(man_mult, 2),
            clutch_mult=round(clutch_mult, 2),
            time_mult=round(time_mult, 2),
            total_mult=round(total_mult, 3),
            context=context.to_dict()
        )


def calculate_contextual_wpa(
    base_wpa: float,
    team_equipment: int = 4000,
    enemy_equipment: int = 4000,
    team_alive: int = 5,
    enemy_alive: int = 5,
    time_remaining: float = 60.0,
    bomb_planted: bool = False,
    is_clutch: bool = False,
    clutch_vs: int = 0
) -> WPAResult:
    """
    Convenience function to calculate contextual WPA.
    
    Example:
        result = calculate_contextual_wpa(
            base_wpa=0.05,
            team_equipment=1500,  # eco
            enemy_equipment=4500,  # gun round
            team_alive=5,
            enemy_alive=4,
            time_remaining=30
        )
        print(result.weighted_wpa)  # Higher than 0.05
    """
    context = WPAContext(
        team_equipment_value=team_equipment,
        enemy_equipment_value=enemy_equipment,
        team_alive=team_alive,
        enemy_alive=enemy_alive,
        round_time_remaining=time_remaining,
        bomb_planted=bomb_planted,
        is_clutch=is_clutch,
        clutch_vs=clutch_vs
    )
    
    calculator = ContextualWPA()
    return calculator.calculate(base_wpa, context)


def export_wpa_config(output_path: str) -> str:
    """Export default WPA config to JSON file."""
    import json
    from pathlib import Path
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    
    return str(path)
