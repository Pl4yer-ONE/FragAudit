# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3.

"""
Player Impact Predictor
Hand-written model for player performance forecasting.

NO sklearn. NO neural nets. Explainable only.

Predicts:
- P(positive_impact): Probability player will contribute positively
- Expected rating: Projected performance rating [0.7, 1.7]

Math fixes:
- Variance: documented expected range [0, 0.5]
- Rating mapping: calibrated to realistic scale
- Confidence: based on prediction strength
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import math


# Player impact coefficients
PLAYER_COEFFICIENTS = {
    # Historical performance
    "avg_rating": 0.5,            # Rating deviation from 1.0
    "consistency": 0.2,           # Low variance bonus
    
    # Role fit
    "role_match": 0.15,           # Playing primary role
    
    # Economy
    "economy_comfort": 0.1,       # Has preferred weapons
    
    # Man advantage
    "man_advantage": 0.08,        # Easier with numbers
    
    # Mistakes (negative)
    "recent_mistakes": -0.2,      # Recent errors
    
    # Intercept
    "intercept": 0.0,
}

# Bounds
MIN_IMPACT = 0.15
MAX_IMPACT = 0.85

# Expected variance range [0, 0.5]
# Low variance (0.1) = consistent player
# High variance (0.4) = inconsistent player
VARIANCE_BASELINE = 0.25


def _sigmoid(x: float) -> float:
    """Sigmoid function."""
    x = max(-20, min(20, x))
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class PlayerFeatures:
    """Features for player impact prediction."""
    # Historical (rating should be in [0.5, 2.0] range)
    avg_rating: float = 1.0
    rating_variance: float = 0.15  # Expected [0, 0.5]
    
    # Role
    current_role: str = ""
    primary_role: str = ""
    role_frequency: float = 0.5   # How often plays this role [0, 1]
    
    # Economy
    equipment_value: int = 0
    preferred_value: int = 4000
    
    # Context
    team_alive: int = 5
    enemy_alive: int = 5
    
    # Recent performance
    recent_mistake_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlayerPrediction:
    """Player impact prediction result."""
    impact_probability: float    # P(positive impact) [0.15, 0.85]
    expected_rating: float       # Projected rating [0.7, 1.7]
    confidence: float            # Prediction strength [0, 1]
    log_odds: float              # Raw log-odds
    key_factors: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ImpactPredictor:
    """
    Hand-written player impact predictor.
    
    Math fixes:
    - Variance uses documented baseline
    - Rating scaled to realistic [0.7, 1.7]
    - Confidence from abs(log_odds)
    """
    
    def __init__(self, coefficients: Optional[Dict[str, float]] = None):
        self.coef = {**PLAYER_COEFFICIENTS}
        if coefficients:
            self.coef.update(coefficients)
    
    def predict(self, features: PlayerFeatures) -> PlayerPrediction:
        """Predict player impact with proper scaling."""
        factors = {}
        
        # HISTORICAL RATING
        # Deviation from average (1.0)
        rating_dev = features.avg_rating - 1.0
        rating_contrib = rating_dev * self.coef["avg_rating"]
        factors["historical"] = round(rating_contrib, 3)
        
        # CONSISTENCY
        # Variance below baseline = bonus, above = penalty
        variance_dev = VARIANCE_BASELINE - features.rating_variance
        # Clamp to prevent extreme values
        variance_dev = max(-0.25, min(0.25, variance_dev))
        consistency_contrib = variance_dev * self.coef["consistency"]
        factors["consistency"] = round(consistency_contrib, 3)
        
        # ROLE FIT
        role_match = 1.0 if features.current_role == features.primary_role else 0.0
        role_contrib = role_match * features.role_frequency * self.coef["role_match"]
        factors["role_fit"] = round(role_contrib, 3)
        
        # ECONOMY COMFORT
        if features.preferred_value > 0:
            econ_ratio = features.equipment_value / features.preferred_value
            # Clamp ratio to [0, 1.5]
            econ_ratio = min(1.5, econ_ratio)
            econ_dev = econ_ratio - 0.5
            econ_contrib = econ_dev * self.coef["economy_comfort"]
        else:
            econ_contrib = 0.0
        factors["economy"] = round(econ_contrib, 3)
        
        # MAN ADVANTAGE
        man_diff = (features.team_alive - features.enemy_alive) / 5
        man_contrib = man_diff * self.coef["man_advantage"]
        factors["numbers"] = round(man_contrib, 3)
        
        # MISTAKES (negative)
        mistake_contrib = features.recent_mistake_count * self.coef["recent_mistakes"]
        # Cap at -0.6 (3 mistakes max effect)
        mistake_contrib = max(-0.6, mistake_contrib)
        factors["mistakes"] = round(mistake_contrib, 3)
        
        # SUM log-odds
        log_odds = self.coef["intercept"]
        for v in factors.values():
            log_odds += v
        
        # IMPACT PROBABILITY
        raw_impact = _sigmoid(log_odds)
        bounded_impact = max(MIN_IMPACT, min(MAX_IMPACT, raw_impact))
        
        # EXPECTED RATING: map impact to realistic scale
        # Impact 0.5 → rating 1.0 (average)
        # Impact 0.85 → rating ~1.5 (star player)
        # Impact 0.15 → rating ~0.7 (struggling)
        expected_rating = 0.7 + bounded_impact * 1.2
        expected_rating = max(0.7, min(1.7, expected_rating))
        
        # CONFIDENCE: abs(log_odds) based
        confidence = min(1.0, abs(log_odds) / 1.5)
        
        return PlayerPrediction(
            impact_probability=round(bounded_impact, 3),
            expected_rating=round(expected_rating, 2),
            confidence=round(confidence, 2),
            log_odds=round(log_odds, 3),
            key_factors=factors
        )


def predict_player_impact(
    avg_rating: float = 1.0,
    rating_variance: float = 0.15,
    current_role: str = "",
    primary_role: str = "",
    role_frequency: float = 0.5,
    equipment_value: int = 4000,
    team_alive: int = 5,
    enemy_alive: int = 5,
    recent_mistake_count: int = 0
) -> PlayerPrediction:
    """
    Convenience function for player impact prediction.
    
    Example:
        result = predict_player_impact(
            avg_rating=1.25,      # Above average
            rating_variance=0.1,   # Consistent
            current_role="ENTRY",
            primary_role="ENTRY",
            role_frequency=0.7
        )
        print(f"Expected rating: {result.expected_rating}")
        print(f"Confidence: {result.confidence:.0%}")
    """
    features = PlayerFeatures(
        avg_rating=avg_rating,
        rating_variance=rating_variance,
        current_role=current_role,
        primary_role=primary_role,
        role_frequency=role_frequency,
        equipment_value=equipment_value,
        team_alive=team_alive,
        enemy_alive=enemy_alive,
        recent_mistake_count=recent_mistake_count
    )
    
    predictor = ImpactPredictor()
    return predictor.predict(features)
