# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Unit Tests for Strategy Classifier
Tests T-side and CT-side pattern detection.
"""

import pytest
from unittest.mock import MagicMock
import pandas as pd

from src.strategy.fingerprint import (
    StrategyType,
    StrategySignal,
    RoundStrategy,
    StrategyClassifier,
    classify_strategies,
    export_strategies_json,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_demo_rush():
    """Demo with early kill (rush)."""
    demo = MagicMock()
    demo.kills = pd.DataFrame({
        'total_rounds_played': [1],
        'tick': [500],  # Very early
        'attacker_name': ['PlayerA'],
        'attacker_team_name': ['TERRORIST'],
        'user_name': ['Enemy1'],
        'user_team_name': ['CT'],
        'user_X': [800],  # A site
        'user_Y': [0],
    })
    return demo


@pytest.fixture
def mock_demo_default():
    """Demo with late contact (default)."""
    demo = MagicMock()
    demo.kills = pd.DataFrame({
        'total_rounds_played': [1],
        'tick': [4000],  # Late (62+ seconds)
        'attacker_name': ['PlayerA'],
        'attacker_team_name': ['TERRORIST'],
        'user_name': ['Enemy1'],
        'user_team_name': ['CT'],
        'user_X': [-800],  # B site
        'user_Y': [0],
    })
    return demo


@pytest.fixture
def empty_demo():
    """Demo with no kills."""
    demo = MagicMock()
    demo.kills = pd.DataFrame()
    return demo


# ============================================================================
# StrategySignal Tests
# ============================================================================

class TestStrategySignal:
    """Tests for StrategySignal dataclass."""
    
    def test_default_values(self):
        """Signal has sensible defaults."""
        signal = StrategySignal()
        
        assert signal.first_contact_site == ""
        assert signal.time_to_first_contact == 0.0
        assert signal.utility_thrown == 0
    
    def test_to_dict(self):
        """Signal serializes correctly."""
        signal = StrategySignal(
            first_contact_site="A",
            time_to_first_contact=20.5
        )
        
        d = signal.to_dict()
        assert d['first_contact_site'] == "A"


# ============================================================================
# RoundStrategy Tests
# ============================================================================

class TestRoundStrategy:
    """Tests for RoundStrategy dataclass."""
    
    def test_creation(self):
        """Basic creation works."""
        strat = RoundStrategy(
            round=1,
            team="T",
            strategy="EXECUTE_A",
            confidence=0.8
        )
        
        assert strat.round == 1
        assert strat.strategy == "EXECUTE_A"
    
    def test_to_dict(self):
        """Serialization handles None signals."""
        strat = RoundStrategy(
            round=1,
            team="T",
            strategy="RUSH_A",
            confidence=0.75,
            signals=None
        )
        
        d = strat.to_dict()
        assert d['signals'] == {}


# ============================================================================
# StrategyClassifier Tests
# ============================================================================

class TestStrategyClassifier:
    """Tests for StrategyClassifier."""
    
    def test_empty_demo(self, empty_demo):
        """Empty demo returns low confidence strategy."""
        classifier = StrategyClassifier()
        result = classifier.classify_round(empty_demo, 1, "T")
        
        # With no data, should have low confidence
        assert result.confidence <= 0.5
    
    def test_rush_detection(self, mock_demo_rush):
        """Detects rush from early contact."""
        classifier = StrategyClassifier()
        result = classifier.classify_round(mock_demo_rush, 1, "T")
        
        # Early contact at A = RUSH_A
        assert "RUSH" in result.strategy or "EXECUTE" in result.strategy
    
    def test_default_detection(self, mock_demo_default):
        """Detects default from late contact."""
        classifier = StrategyClassifier()
        result = classifier.classify_round(mock_demo_default, 1, "T")
        
        # Late contact = DEFAULT
        assert result.strategy == StrategyType.DEFAULT_T.value
    
    def test_confidence_range(self, mock_demo_rush):
        """Confidence is between 0 and 1."""
        classifier = StrategyClassifier()
        result = classifier.classify_round(mock_demo_rush, 1, "T")
        
        assert 0.0 <= result.confidence <= 1.0
    
    def test_ct_default(self, mock_demo_rush):
        """CT defaults to DEFAULT_CT without info."""
        classifier = StrategyClassifier()
        result = classifier.classify_round(mock_demo_rush, 1, "CT")
        
        assert "CT" in result.strategy


# ============================================================================
# classify_strategies Tests
# ============================================================================

class TestClassifyStrategies:
    """Tests for classify_strategies function."""
    
    def test_empty_demo(self, empty_demo):
        """Empty demo returns empty list."""
        strategies = classify_strategies(empty_demo)
        assert strategies == []
    
    def test_returns_both_teams(self, mock_demo_rush):
        """Returns strategies for both T and CT."""
        strategies = classify_strategies(mock_demo_rush)
        
        teams = {s.team for s in strategies}
        assert "T" in teams
        assert "CT" in teams
    
    def test_returns_list(self, mock_demo_default):
        """Returns a list of RoundStrategy."""
        strategies = classify_strategies(mock_demo_default)
        
        assert isinstance(strategies, list)
        if strategies:
            assert isinstance(strategies[0], RoundStrategy)


# ============================================================================
# JSON Export Tests
# ============================================================================

class TestExportStrategiesJson:
    """Tests for JSON export."""
    
    def test_export_creates_file(self, tmp_path):
        """Export creates valid JSON file."""
        strategies = [
            RoundStrategy(round=1, team="T", strategy="EXECUTE_A", confidence=0.8),
            RoundStrategy(round=1, team="CT", strategy="DEFAULT_CT", confidence=0.7),
        ]
        
        output_path = tmp_path / "test_strats.json"
        export_strategies_json(strategies, str(output_path))
        
        assert output_path.exists()
        
        import json
        with open(output_path) as f:
            data = json.load(f)
        
        assert data['schema_version'] == "1.0"
        assert data['total_rounds'] == 1
    
    def test_export_counts_strategies(self, tmp_path):
        """Export includes strategy counts."""
        strategies = [
            RoundStrategy(round=1, team="T", strategy="EXECUTE_A", confidence=0.8),
            RoundStrategy(round=2, team="T", strategy="EXECUTE_A", confidence=0.75),
            RoundStrategy(round=3, team="T", strategy="DEFAULT_T", confidence=0.7),
        ]
        
        output_path = tmp_path / "test_counts.json"
        export_strategies_json(strategies, str(output_path))
        
        import json
        with open(output_path) as f:
            data = json.load(f)
        
        assert data['t_side_strategies']['EXECUTE_A'] == 2
        assert data['t_side_strategies']['DEFAULT_T'] == 1


# ============================================================================
# StrategyType Enum Tests
# ============================================================================

class TestStrategyTypeEnum:
    """Tests for StrategyType enum."""
    
    def test_t_side_strategies(self):
        """All T-side strategies exist."""
        expected = ['EXECUTE_A', 'EXECUTE_B', 'RUSH_A', 'RUSH_B', 'DEFAULT_T']
        
        for strat in expected:
            assert hasattr(StrategyType, strat)
    
    def test_ct_side_strategies(self):
        """All CT-side strategies exist."""
        expected = ['DEFAULT_CT', 'STACK_A', 'STACK_B', 'AGGRESSIVE_CT']
        
        for strat in expected:
            assert hasattr(StrategyType, strat)
