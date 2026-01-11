"""
Scoring Engine
Normalizes various raw metrics into 0-100 scores using user-defined weighted formulas.
"""

from typing import Dict, Any, Tuple

class ScoreEngine:
    """
    Computes normalized scores (0-100) for player performance categories.
    """
    
    @staticmethod
    def _normalize(value: float, min_val: float, max_val: float) -> int:
        """Helper to clamp and normalize value to 0-100."""
        if value <= min_val: return 0
        if value >= max_val: return 100
        return int(((value - min_val) / (max_val - min_val)) * 100)

    @staticmethod
    def _get_cs_multiplier(counter_strafe: float) -> float:
        """
        Non-linear counter-strafe penalty curve.
        Lookup table with interpolation between breakpoints.
        
        | CS%  | Multiplier |
        |------|------------|
        | 95+  | 1.00       |
        | 85   | 0.92       |
        | 75   | 0.82       |
        | 65   | 0.72       |
        | <60  | 0.60       |
        """
        # Breakpoints: (cs_threshold, multiplier)
        breakpoints = [
            (95.0, 1.00),
            (85.0, 0.92),
            (75.0, 0.82),
            (65.0, 0.72),
            (60.0, 0.60),
        ]
        
        # Above highest threshold
        if counter_strafe >= breakpoints[0][0]:
            return breakpoints[0][1]
        
        # Below lowest threshold
        if counter_strafe < breakpoints[-1][0]:
            return breakpoints[-1][1]
        
        # Interpolate between breakpoints
        for i in range(len(breakpoints) - 1):
            upper_cs, upper_mult = breakpoints[i]
            lower_cs, lower_mult = breakpoints[i + 1]
            
            if lower_cs <= counter_strafe < upper_cs:
                # Linear interpolation within this band
                ratio = (counter_strafe - lower_cs) / (upper_cs - lower_cs)
                return lower_mult + ratio * (upper_mult - lower_mult)
        
        return 1.0  # Fallback

    @staticmethod
    def compute_aim_score(hs_percent: float, kpr: float, adr: float, counter_strafe: float = 80.0) -> Tuple[int, int]:
        """
        Aim Score.
        User Formula: hs_percent*0.3 + kpr*40 + adr*0.3
        
        Non-linear mechanical penalty based on counter-strafe quality.
        See _get_cs_multiplier for curve.
        
        Returns:
            Tuple of (raw_aim, effective_aim) - both 0-100
        """
        # HS input is 0.0-1.0 usually -> convert to 0-100
        hs_val = hs_percent * 100
        
        raw_score = (hs_val * 0.3) + (kpr * 40) + (adr * 0.3)
        raw_aim = int(min(100, max(0, raw_score)))
        
        # Non-linear Mechanical Penalty
        cs_mult = ScoreEngine._get_cs_multiplier(counter_strafe)
        effective_score = raw_score * cs_mult
            
        effective_aim = int(min(100, max(0, effective_score)))
        
        return (raw_aim, effective_aim)

    @staticmethod
    def compute_positioning_score(untradeable_ratio: float, trade_success: float = 0.0, survival_rate: float = 0.0) -> int:
        """
        Positioning Score.
        User Formula: 50 - (untradeable_death_ratio * 50) + trade_success * 30 + survival * 20
        """
        base = 50.0
        penalty = untradeable_ratio * 50.0
        bonus_trade = trade_success * 30.0 
        bonus_surv = survival_rate * 20.0
        
        score = base - penalty + bonus_trade + bonus_surv
        return int(min(100, max(0, score)))

    @staticmethod
    def compute_utility_score(enemies_blinded: int, util_dmg: int, flashes_thrown: int) -> int:
        """
        Utility Score.
        Formula:
        - Enemies Blinded (40%) -> Target 10
        - Utility Dmg (30%) -> Target 200
        - Usage (30%) -> Target 20
        
        Returns -1 IF no usage/data (to signal UI to hide it)
        """
        if enemies_blinded == 0 and util_dmg == 0 and flashes_thrown == 0:
            return -1 # Signal to hide
            
        s_blind = ScoreEngine._normalize(enemies_blinded, 0, 10)
        s_dmg = ScoreEngine._normalize(util_dmg, 0, 200)
        s_use = ScoreEngine._normalize(flashes_thrown, 0, 15)
        
        return int((s_blind * 0.4) + (s_dmg * 0.3) + (s_use * 0.3))
    
    @staticmethod
    def compute_impact_score(
        # Opening duels
        opening_kills_won: int,     # Opening kills in rounds team won
        opening_kills_lost: int,    # Opening kills in rounds team lost
        entry_deaths: int,          # Deaths in opening duels
        
        # Kill context
        kills_in_won_rounds: int,
        kills_in_lost_rounds: int,
        exit_frags: int,
        
        # Round-winning plays
        multikills: int, 
        clutches_1v1: int, 
        clutches_1vN: int,
        
        # Death context
        untradeable_deaths: int, 
        tradeable_deaths: int,
        
        # Stats
        total_kills: int
    ) -> int:
        """
        Impact Rating (Round-Context Aware).
        
        CORE PRINCIPLE: Kills only count if they help win rounds.
        
        Impact Bands:
        - 0-10:  AFK/Useless
        - 10-30: Low Impact / Exit Fragger
        - 30-60: Contributor
        - 60+:   Carry
        
        Formula:
        1. Kill Value (round-context weighted):
           - Kill in won round: +6
           - Kill in lost round: +1.5 (75% reduction)
           - Exit frag: -2 (padding penalty)
        
        2. Opening Picks (highest value):
           - Opening kill + round won: +10
           - Opening kill + round lost: +3
           - Entry death: -4
        
        3. Clutches (earned, no floors):
           - 1v1: +15
           - 1vN: +25
           - Multikill rounds: +5
        
        4. Trade Value:
           - Died traded: -2 (at least team got value)
           - Died untraded: -6 (pure waste)
        
        NO FLOORS. Earn every point.
        """
        impact = 0.0
        
        # 1. Kill Value (round-context)
        impact += kills_in_won_rounds * 6.0      # Full value
        impact += kills_in_lost_rounds * 1.5     # Reduced value
        impact -= exit_frags * 2.0               # Padding penalty
        
        # 2. Opening Picks (critical plays)
        impact += opening_kills_won * 10.0       # Round-winning opener
        impact += opening_kills_lost * 3.0       # Failed to convert
        impact -= entry_deaths * 4.0             # Lost opening
        
        # 3. Clutches (earned value, no free floors)
        impact += clutches_1v1 * 15.0
        impact += clutches_1vN * 25.0
        impact += multikills * 5.0
        
        # 4. Death Value
        impact -= tradeable_deaths * 2.0         # Died but traded
        impact -= untradeable_deaths * 6.0       # Died alone (waste)
        
        # Minimum: non-negative if any kills
        if total_kills > 0 and impact < 0:
            impact = max(impact, 5.0)
        
        # Clamp 0-100
        return int(min(100, max(0, impact)))

    @staticmethod
    def compute_final_rating(scores: Dict[str, int], role: str, kdr: float, untradeable_deaths: int,
                             survival_rate: float = 0.0, opening_kills: int = 0) -> int:
        """
        Compute aggregate rating with penalties.
        
        LOCKED WEIGHTS (do not change):
        - Aim: 0.35
        - Positioning: 0.25  
        - Impact: 0.40
        
        Impact Bands:
        - 0-10:  Useless - cap at 30
        - 10-30: Low Impact - cap at 45
        - 30-60: Contributor - no cap
        - 60+:   Carry - no cap
        
        Role Adjustments:
        - Entry: KDR<0.8 penalty (*0.75)
        - AWPer: Survival bonus (space denial proxy), opening kill bonus
                 KDR<0.8 penalty (*0.80) - expensive role to feed on
        
        Other Penalties:
        - Death Tax: -0.5 per untradeable death
        """
        aim = scores.get("aim") if scores.get("aim") is not None else 50
        pos = scores.get("positioning") if scores.get("positioning") is not None else 50
        imp = scores.get("impact") if scores.get("impact") is not None else 50
        
        rating = (aim * 0.35) + (pos * 0.25) + (imp * 0.40)
        
        # 1. Death Tax
        rating -= (untradeable_deaths * 0.5)
        
        # 2. Impact Band Caps (graduated, not binary)
        if imp <= 10:
            # Useless band - hard cap
            rating = min(rating, 30.0)
        elif imp <= 30:
            # Low impact band - moderate cap
            rating = min(rating, 45.0)
        # 30-60 = contributor, 60+ = carry - no cap
            
        # 3. Role-Specific Adjustments
        if role == "Entry" and kdr < 0.8:
            rating *= 0.75
        elif role == "AWPer":
            # AWPer space-denial: survival = map control
            # +5 bonus if survival > 50% (stayed alive, denied space)
            if survival_rate > 0.5:
                rating += 5.0
            # Opening picks are high-value for AWPers
            rating += opening_kills * 2.0
            # But feeding as AWP is expensive
            if kdr < 0.8:
                rating *= 0.80
            
        return int(min(70, max(0, rating)))
