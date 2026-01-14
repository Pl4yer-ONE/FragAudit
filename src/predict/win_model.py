# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3.

"""
Round Win Predictor
Hand-written logistic regression for round outcome prediction.

NO sklearn. NO neural nets. Explainable coefficients only.

Features used:
- Economy differential (tanh-clamped)
- Man advantage (normalized to [-1, 1])
- Role composition (capped contribution)
- Mistake count
- Strategy type

Output: P(round_win) bounded [0.05, 0.95]
Confidence: based on prediction strength (abs log-odds)
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import math


# Explicit, explainable coefficients
# Scale: contribution to log-odds (not raw probability)
COEFFICIENTS = {
    # Economy (tanh-normalized, output in [-1, 1])
    "economy_diff": 0.8,          # Max ±0.8 log-odds from economy
    
    # Man advantage (normalized to [-1, 1])
    "man_advantage": 0.6,         # Max ±0.6 log-odds from numbers
    
    # Role quality (capped total contribution)
    "role_max": 0.15,             # Max role contribution
    
    # Mistakes (negative)
    "mistake_count": -0.10,       # Per mistake
    "high_severity": -0.15,       # Per HIGH mistake (additional)
    
    # Strategy
    "execute_strat": 0.08,        # Coordinated execute
    "rush_strat": -0.05,          # Rush = risky
    "default_strat": 0.03,        # Default = safe
    
    # Intercept (base = 50%)
    "intercept": 0.0,
}

# Bounds
MIN_PROBABILITY = 0.05
MAX_PROBABILITY = 0.95

# Scaling constants
ECONOMY_SCALE = 3000  # $3000 diff = ~76% of max economy effect (tanh saturation)
MAN_ADVANTAGE_SCALE = 5  # Max possible advantage


def _sigmoid(x: float) -> float:
    """Sigmoid function for logistic regression."""
    x = max(-20, min(20, x))
    return 1.0 / (1.0 + math.exp(-x))


def _tanh(x: float) -> float:
    """Tanh for diminishing returns scaling."""
    return math.tanh(x)


@dataclass
class RoundFeatures:
    """Features extracted for round prediction."""
    # Economy
    team_economy: int = 0
    enemy_economy: int = 0
    
    # Players alive
    team_alive: int = 5
    enemy_alive: int = 5
    
    # Role composition (counts)
    entry_count: int = 0
    support_count: int = 0
    lurk_count: int = 0
    anchor_count: int = 0
    
    # Mistakes
    mistake_count: int = 0
    high_severity_count: int = 0
    
    # Strategy
    strategy: str = ""
    
    # Side
    is_t_side: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoundPrediction:
    """Round win probability prediction."""
    probability: float           # P(win) bounded [0.05, 0.95]
    confidence: float            # Prediction strength (0-1)
    log_odds: float              # Raw log-odds before sigmoid
    dominant_factor: str         # Most influential factor
    factors: Dict[str, float]    # Individual factor contributions
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WinPredictor:
    """
    Hand-written logistic regression predictor.
    
    Math fixes applied:
    - Economy: tanh scaling for diminishing returns
    - Man advantage: normalized to [-1, 1]
    - Roles: capped total contribution
    - Confidence: based on abs(log_odds), not data presence
    """
    
    def __init__(self, coefficients: Optional[Dict[str, float]] = None):
        self.coef = {**COEFFICIENTS}
        if coefficients:
            self.coef.update(coefficients)
    
    def predict(self, features: RoundFeatures) -> RoundPrediction:
        """Predict round win probability with proper scaling."""
        factors = {}
        
        # ECONOMY: tanh scaling for diminishing returns
        # $3000 diff → tanh(1) ≈ 0.76 of max effect
        econ_diff = (features.team_economy - features.enemy_economy) / ECONOMY_SCALE
        econ_scaled = _tanh(econ_diff)  # Output in [-1, 1]
        econ_contrib = econ_scaled * self.coef["economy_diff"]
        factors["economy"] = round(econ_contrib, 3)
        
        # MAN ADVANTAGE: normalized to [-1, 1]
        man_diff = (features.team_alive - features.enemy_alive) / MAN_ADVANTAGE_SCALE
        man_contrib = man_diff * self.coef["man_advantage"]
        factors["man_advantage"] = round(man_contrib, 3)
        
        # ROLES: capped total contribution
        role_score = 0.0
        if features.entry_count > 0:
            role_score += 0.4  # Entry present
        if features.support_count > 0 or features.anchor_count > 0:
            role_score += 0.3  # Support present
        if features.lurk_count > 0:
            role_score += 0.3  # Lurk present
        # Cap at 1.0, then apply coefficient
        role_score = min(1.0, role_score)
        role_contrib = role_score * self.coef["role_max"]
        factors["roles"] = round(role_contrib, 3)
        
        # MISTAKES: linear penalty, capped
        mistake_contrib = (
            features.mistake_count * self.coef["mistake_count"] +
            features.high_severity_count * self.coef["high_severity"]
        )
        # Cap at -0.6 (6 regular mistakes max effect)
        mistake_contrib = max(-0.6, mistake_contrib)
        factors["mistakes"] = round(mistake_contrib, 3)
        
        # STRATEGY
        strat = features.strategy.upper()
        strat_contrib = 0.0
        if "EXECUTE" in strat:
            strat_contrib = self.coef["execute_strat"]
        elif "RUSH" in strat:
            strat_contrib = self.coef["rush_strat"]
        elif "DEFAULT" in strat:
            strat_contrib = self.coef["default_strat"]
        factors["strategy"] = round(strat_contrib, 3)
        
        # SUM: log-odds scale
        log_odds = self.coef["intercept"]
        for v in factors.values():
            log_odds += v
        
        # PROBABILITY: sigmoid with bounds
        raw_prob = _sigmoid(log_odds)
        bounded_prob = max(MIN_PROBABILITY, min(MAX_PROBABILITY, raw_prob))
        
        # DOMINANT FACTOR
        dominant = max(factors, key=lambda k: abs(factors[k]))
        
        # CONFIDENCE: based on prediction strength, not data presence
        # abs(log_odds) = 0 → 50% prediction → low confidence
        # abs(log_odds) = 2 → ~88% prediction → high confidence
        confidence = min(1.0, abs(log_odds) / 2.0)
        
        return RoundPrediction(
            probability=round(bounded_prob, 3),
            confidence=round(confidence, 2),
            log_odds=round(log_odds, 3),
            dominant_factor=dominant,
            factors=factors
        )


def predict_round_win(
    team_economy: int = 4000,
    enemy_economy: int = 4000,
    team_alive: int = 5,
    enemy_alive: int = 5,
    entry_count: int = 0,
    support_count: int = 0,
    mistake_count: int = 0,
    high_severity_count: int = 0,
    strategy: str = ""
) -> RoundPrediction:
    """
    Convenience function for round win prediction.
    
    Example:
        result = predict_round_win(
            team_economy=1500,   # eco
            enemy_economy=4500,  # gun round
            team_alive=5,
            enemy_alive=4,       # man advantage
        )
        print(f"Win probability: {result.probability:.0%}")
        print(f"Confidence: {result.confidence:.0%}")
        print(f"Factors: {result.factors}")
    """
    features = RoundFeatures(
        team_economy=team_economy,
        enemy_economy=enemy_economy,
        team_alive=team_alive,
        enemy_alive=enemy_alive,
        entry_count=entry_count,
        support_count=support_count,
        mistake_count=mistake_count,
        high_severity_count=high_severity_count,
        strategy=strategy
    )
    
    predictor = WinPredictor()
    return predictor.predict(features)
