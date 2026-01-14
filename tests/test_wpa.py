# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Unit Tests for Contextual WPA
Tests economy, man-advantage, clutch, and time multipliers.
"""

import pytest
from src.wpa.contextual_wpa import (
    EconomyType,
    WPAContext,
    WPAResult,
    ContextualWPA,
    calculate_contextual_wpa,
    DEFAULT_CONFIG,
)


# ============================================================================
# Economy Classification Tests
# ============================================================================

class TestEconomyClassification:
    """Tests for economy type detection."""
    
    def test_eco_vs_full_buy(self):
        """Low team value vs high enemy = ECO."""
        calc = ContextualWPA()
        result = calc.classify_economy(1500, 4500)
        assert result == EconomyType.ECO
    
    def test_full_buy_vs_eco(self):
        """High team value vs low enemy = ANTI_ECO."""
        calc = ContextualWPA()
        result = calc.classify_economy(4500, 1500)
        assert result == EconomyType.ANTI_ECO
    
    def test_half_buy(self):
        """Mid value = HALF_BUY."""
        calc = ContextualWPA()
        result = calc.classify_economy(2500, 2500)
        assert result == EconomyType.HALF_BUY
    
    def test_full_buy(self):
        """High value both sides = FULL_BUY."""
        calc = ContextualWPA()
        result = calc.classify_economy(4500, 4500)
        assert result == EconomyType.FULL_BUY


class TestEconomyMultipliers:
    """Tests for economy-based multipliers."""
    
    def test_eco_kill_high_value(self):
        """Eco kill should have high multiplier."""
        calc = ContextualWPA()
        mult = calc.get_economy_multiplier(EconomyType.ECO)
        assert mult == 1.6
    
    def test_anti_eco_low_value(self):
        """Anti-eco kill should have low multiplier."""
        calc = ContextualWPA()
        mult = calc.get_economy_multiplier(EconomyType.ANTI_ECO)
        assert mult == 0.6
    
    def test_full_buy_baseline(self):
        """Full buy should be baseline 1.0."""
        calc = ContextualWPA()
        mult = calc.get_economy_multiplier(EconomyType.FULL_BUY)
        assert mult == 1.0


# ============================================================================
# Man Advantage Tests
# ============================================================================

class TestManAdvantage:
    """Tests for player count advantage multipliers."""
    
    def test_5v4_advantage(self):
        """5v4 should give +15%."""
        calc = ContextualWPA()
        mult = calc.get_man_advantage_multiplier(5, 4)
        assert mult == 1.15
    
    def test_5v3_advantage(self):
        """5v3 should give +25%."""
        calc = ContextualWPA()
        mult = calc.get_man_advantage_multiplier(5, 3)
        assert mult == 1.25
    
    def test_4v5_disadvantage(self):
        """Disadvantage should have no bonus."""
        calc = ContextualWPA()
        mult = calc.get_man_advantage_multiplier(4, 5)
        assert mult == 1.0
    
    def test_even_count(self):
        """Even count should have small bonus."""
        calc = ContextualWPA()
        mult = calc.get_man_advantage_multiplier(5, 5)
        # 10 total = 4v4 or 5v5 territory
        assert mult >= 1.0


# ============================================================================
# Clutch Tests
# ============================================================================

class TestClutchMultipliers:
    """Tests for 1vX clutch situations."""
    
    def test_1v1_clutch(self):
        """1v1 should be 1.5x."""
        calc = ContextualWPA()
        mult = calc.get_clutch_multiplier(1)
        assert mult == 1.5
    
    def test_1v2_clutch(self):
        """1v2 should be 2.0x."""
        calc = ContextualWPA()
        mult = calc.get_clutch_multiplier(2)
        assert mult == 2.0
    
    def test_1v5_clutch(self):
        """1v5 should be 4.0x."""
        calc = ContextualWPA()
        mult = calc.get_clutch_multiplier(5)
        assert mult == 4.0
    
    def test_no_clutch(self):
        """Non-clutch should be 1.0."""
        calc = ContextualWPA()
        mult = calc.get_clutch_multiplier(0)
        assert mult == 1.0


# ============================================================================
# Time Multiplier Tests
# ============================================================================

class TestTimeMultipliers:
    """Tests for round time-based multipliers."""
    
    def test_early_round(self):
        """Early round (>85s left) should be lower impact."""
        calc = ContextualWPA()
        mult = calc.get_time_multiplier(100, False)
        assert mult == 0.8
    
    def test_mid_round(self):
        """Mid round should be baseline."""
        calc = ContextualWPA()
        mult = calc.get_time_multiplier(60, False)
        assert mult == 1.0
    
    def test_late_round(self):
        """Late round (<45s) should be higher."""
        calc = ContextualWPA()
        mult = calc.get_time_multiplier(30, False)
        assert mult == 1.3
    
    def test_bomb_planted(self):
        """Bomb planted should override time."""
        calc = ContextualWPA()
        mult = calc.get_time_multiplier(100, True)
        assert mult == 1.5


# ============================================================================
# Full Calculation Tests
# ============================================================================

class TestContextualWPACalculation:
    """Tests for complete WPA calculation."""
    
    def test_basic_calculation(self):
        """Basic WPA calculation should work."""
        result = calculate_contextual_wpa(
            base_wpa=0.05,
            team_equipment=4000,
            enemy_equipment=4000,
            team_alive=5,
            enemy_alive=5,
            time_remaining=60.0
        )
        
        assert result.base_wpa == 0.05
        assert result.weighted_wpa >= result.base_wpa * 0.5
        assert result.weighted_wpa <= result.base_wpa * 5.0
    
    def test_eco_round_increases_value(self):
        """Eco round kill should be worth more."""
        eco_result = calculate_contextual_wpa(
            base_wpa=0.05,
            team_equipment=1500,  # eco
            enemy_equipment=4500,
        )
        
        gun_result = calculate_contextual_wpa(
            base_wpa=0.05,
            team_equipment=4500,
            enemy_equipment=4500,
        )
        
        assert eco_result.weighted_wpa > gun_result.weighted_wpa
    
    def test_anti_eco_decreases_value(self):
        """Anti-eco kill should be worth less."""
        anti_eco = calculate_contextual_wpa(
            base_wpa=0.05,
            team_equipment=4500,
            enemy_equipment=1500,  # enemy eco
        )
        
        gun_round = calculate_contextual_wpa(
            base_wpa=0.05,
            team_equipment=4500,
            enemy_equipment=4500,
        )
        
        assert anti_eco.weighted_wpa < gun_round.weighted_wpa
    
    def test_clutch_multiplies_value(self):
        """Clutch situation should multiply value."""
        normal = calculate_contextual_wpa(
            base_wpa=0.05,
            is_clutch=False
        )
        
        clutch = calculate_contextual_wpa(
            base_wpa=0.05,
            is_clutch=True,
            clutch_vs=3
        )
        
        assert clutch.weighted_wpa > normal.weighted_wpa
    
    def test_result_has_all_fields(self):
        """Result should have all required fields."""
        result = calculate_contextual_wpa(base_wpa=0.05)
        
        assert hasattr(result, 'base_wpa')
        assert hasattr(result, 'weighted_wpa')
        assert hasattr(result, 'economy_type')
        assert hasattr(result, 'economy_mult')
        assert hasattr(result, 'man_advantage_mult')
        assert hasattr(result, 'clutch_mult')
        assert hasattr(result, 'time_mult')
        assert hasattr(result, 'total_mult')


# ============================================================================
# WPAContext Tests
# ============================================================================

class TestWPAContext:
    """Tests for WPAContext dataclass."""
    
    def test_default_values(self):
        """Context should have sensible defaults."""
        ctx = WPAContext()
        
        assert ctx.team_alive == 5
        assert ctx.enemy_alive == 5
        assert ctx.bomb_planted == False
    
    def test_to_dict(self):
        """Context should serialize to dict."""
        ctx = WPAContext(team_alive=3, enemy_alive=2)
        d = ctx.to_dict()
        
        assert d['team_alive'] == 3
        assert d['enemy_alive'] == 2


# ============================================================================
# WPAResult Tests
# ============================================================================

class TestWPAResult:
    """Tests for WPAResult dataclass."""
    
    def test_to_dict(self):
        """Result should serialize to dict."""
        result = WPAResult(
            base_wpa=0.05,
            weighted_wpa=0.08,
            economy_type="eco",
            economy_mult=1.6,
            man_advantage_mult=1.0,
            clutch_mult=1.0,
            time_mult=1.0,
            total_mult=1.6
        )
        
        d = result.to_dict()
        
        assert d['base_wpa'] == 0.05
        assert d['weighted_wpa'] == 0.08


# ============================================================================
# Config Tests
# ============================================================================

class TestConfig:
    """Tests for configuration system."""
    
    def test_default_config_exists(self):
        """Default config should have all keys."""
        required_keys = [
            'eco_kill_mult', 'anti_eco_mult', 
            '1v1_mult', '1v5_mult',
            'time_late_mult', 'time_bomb_planted_mult'
        ]
        
        for key in required_keys:
            assert key in DEFAULT_CONFIG
    
    def test_custom_config(self):
        """Custom config should override defaults."""
        custom = {"eco_kill_mult": 2.0}
        calc = ContextualWPA(config=custom)
        
        assert calc.config["eco_kill_mult"] == 2.0
        assert calc.config["anti_eco_mult"] == 0.6  # Default preserved
