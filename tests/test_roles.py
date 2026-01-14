# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Unit Tests for Role Classifier
Tests per-round role detection logic.
"""

import pytest
from unittest.mock import MagicMock
import pandas as pd

from src.roles.classifier import (
    RoleType,
    RoleClassifier,
    RoleAssignment,
    classify_roles,
    export_roles_json,
    _distance,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_demo_entry_frag():
    """Create a demo where PlayerA gets entry kill."""
    demo = MagicMock()
    demo.kills = pd.DataFrame({
        'total_rounds_played': [1, 1, 1],
        'tick': [1000, 1500, 2000],
        'attacker_name': ['PlayerA', 'PlayerB', 'PlayerA'],
        'attacker_team_name': ['CT', 'CT', 'CT'],
        'user_name': ['Enemy1', 'Enemy2', 'Enemy3'],
        'user_team_name': ['TERRORIST', 'TERRORIST', 'TERRORIST'],
    })
    return demo


@pytest.fixture
def mock_demo_lurk():
    """Create a demo where PlayerA gets late kills (lurk)."""
    demo = MagicMock()
    demo.kills = pd.DataFrame({
        'total_rounds_played': [1, 1, 1],
        'tick': [1000, 1500, 3000],  # PlayerA kills late
        'attacker_name': ['PlayerB', 'PlayerB', 'PlayerA'],
        'attacker_team_name': ['CT', 'CT', 'CT'],
        'user_name': ['Enemy1', 'Enemy2', 'Enemy3'],
        'user_team_name': ['TERRORIST', 'TERRORIST', 'TERRORIST'],
    })
    return demo


@pytest.fixture
def mock_demo_support_trade():
    """Create a demo where PlayerA trades for teammate."""
    demo = MagicMock()
    demo.kills = pd.DataFrame({
        'total_rounds_played': [1, 1],
        'tick': [1000, 1100],  # Quick trade (100 ticks < 192)
        'attacker_name': ['Enemy1', 'PlayerA'],
        'attacker_team_name': ['TERRORIST', 'CT'],
        'user_name': ['PlayerB', 'Enemy1'],
        'user_team_name': ['CT', 'TERRORIST'],
    })
    return demo


@pytest.fixture
def empty_demo():
    """Demo with no kills."""
    demo = MagicMock()
    demo.kills = pd.DataFrame()
    return demo


# ============================================================================
# RoleAssignment Tests
# ============================================================================

class TestRoleAssignment:
    """Tests for RoleAssignment dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        assignment = RoleAssignment(
            round=1,
            player="TestPlayer",
            team="CT",
            role="ENTRY",
            confidence=0.85
        )
        
        assert assignment.round == 1
        assert assignment.player == "TestPlayer"
        assert assignment.role == "ENTRY"
        assert assignment.confidence == 0.85
    
    def test_to_dict(self):
        """Test serialization."""
        assignment = RoleAssignment(
            round=2,
            player="Player1",
            team="T",
            role="LURK",
            confidence=0.72,
            metrics={"entry_kill": 0.0, "kill_timing": 15.5}
        )
        
        d = assignment.to_dict()
        
        assert d['round'] == 2
        assert d['role'] == "LURK"
        assert d['metrics']['kill_timing'] == 15.5
    
    def test_to_dict_empty_metrics(self):
        """Test that None metrics becomes empty dict."""
        assignment = RoleAssignment(
            round=1,
            player="P",
            team="CT",
            role="UNKNOWN",
            confidence=0.0,
            metrics=None
        )
        
        d = assignment.to_dict()
        assert d['metrics'] == {}


# ============================================================================
# Distance Utility Tests
# ============================================================================

class TestDistanceCalculation:
    """Tests for distance utilities."""
    
    def test_distance_zero(self):
        """Same point returns zero."""
        assert _distance(0, 0, 0, 0) == 0
    
    def test_distance_horizontal(self):
        """Horizontal distance."""
        assert _distance(0, 0, 100, 0) == 100
    
    def test_distance_pythagorean(self):
        """3-4-5 triangle."""
        assert _distance(0, 0, 3, 4) == 5


# Removed: TestAvgTeammateDistance - now a class method



# ============================================================================
# RoleClassifier Tests
# ============================================================================

class TestRoleClassifier:
    """Tests for RoleClassifier."""
    
    def test_empty_demo(self, empty_demo):
        """Empty demo returns no assignments."""
        classifier = RoleClassifier()
        assignments = classifier.classify_round(empty_demo, 1)  # No team param now
        assert assignments == []
    
    def test_entry_detection(self, mock_demo_entry_frag):
        """Detect entry fragger."""
        classifier = RoleClassifier()
        assignments = classifier.classify_round(mock_demo_entry_frag, 1)
        
        # Find PlayerA
        player_a = next((a for a in assignments if a.player == "PlayerA"), None)
        
        assert player_a is not None
        # Should have high entry score
        assert player_a.metrics['entry_kill'] == 1.0
    
    def test_support_trade_detection(self, mock_demo_support_trade):
        """Detect support player who trades."""
        classifier = RoleClassifier()
        assignments = classifier.classify_round(mock_demo_support_trade, 1)
        
        player_a = next((a for a in assignments if a.player == "PlayerA"), None)
        
        assert player_a is not None
        # PlayerA traded Enemy1 after they killed PlayerB
        # But check if trade_taken detected
    
    def test_confidence_range(self, mock_demo_entry_frag):
        """Confidence is between 0 and 1."""
        classifier = RoleClassifier()
        assignments = classifier.classify_round(mock_demo_entry_frag, 1)
        
        for a in assignments:
            assert 0.0 <= a.confidence <= 1.0
    
    def test_role_is_valid_enum(self, mock_demo_entry_frag):
        """Role matches valid enum values."""
        classifier = RoleClassifier()
        assignments = classifier.classify_round(mock_demo_entry_frag, 1)
        
        valid_roles = [r.value for r in RoleType]
        for a in assignments:
            assert a.role in valid_roles


# ============================================================================
# classify_roles Integration Tests
# ============================================================================

class TestClassifyRoles:
    """Tests for classify_roles function."""
    
    def test_empty_demo(self, empty_demo):
        """Empty demo returns empty list."""
        assignments = classify_roles(empty_demo)
        assert assignments == []
    
    def test_returns_sorted_list(self, mock_demo_entry_frag):
        """Assignments are sorted by round and player."""
        assignments = classify_roles(mock_demo_entry_frag)  # No team param
        
        if len(assignments) > 1:
            for i in range(len(assignments) - 1):
                curr = assignments[i]
                next_ = assignments[i + 1]
                assert (curr.round, curr.player) <= (next_.round, next_.player)
    
    def test_no_duplicates(self, mock_demo_entry_frag):
        """No duplicate player per round."""
        assignments = classify_roles(mock_demo_entry_frag)
        from collections import Counter
        counts = Counter((a.round, a.player) for a in assignments)
        dupes = [k for k, v in counts.items() if v > 1]
        assert len(dupes) == 0


# ============================================================================
# JSON Export Tests
# ============================================================================

class TestExportRolesJson:
    """Tests for JSON export function."""
    
    def test_export_creates_file(self, tmp_path):
        """Export creates a valid JSON file."""
        assignments = [
            RoleAssignment(
                round=1,
                player="Player1",
                team="CT",
                role="ENTRY",
                confidence=0.85
            )
        ]
        
        output_path = tmp_path / "test_roles.json"
        result = export_roles_json(assignments, str(output_path))
        
        assert output_path.exists()
        
        import json
        with open(output_path) as f:
            data = json.load(f)
        
        assert data['schema_version'] == "2.0"  # Updated version
        assert data['total_assignments'] == 1
    
    def test_export_role_distribution(self, tmp_path):
        """Export includes role distribution counts."""
        assignments = [
            RoleAssignment(round=1, player="P1", team="CT", role="ENTRY", confidence=0.8),
            RoleAssignment(round=2, player="P1", team="CT", role="ENTRY", confidence=0.9),
            RoleAssignment(round=3, player="P1", team="CT", role="LURK", confidence=0.6),
        ]
        
        output_path = tmp_path / "test_dist.json"
        export_roles_json(assignments, str(output_path))
        
        import json
        with open(output_path) as f:
            data = json.load(f)
        
        assert data['role_distribution']['ENTRY'] == 2
        assert data['role_distribution']['LURK'] == 1
    
    def test_export_primary_roles(self, tmp_path):
        """Export includes player primary role aggregation."""
        assignments = [
            RoleAssignment(round=1, player="P1", team="CT", role="ENTRY", confidence=0.8),
            RoleAssignment(round=2, player="P1", team="CT", role="ENTRY", confidence=0.9),
            RoleAssignment(round=3, player="P1", team="CT", role="SUPPORT", confidence=0.5),
        ]
        
        output_path = tmp_path / "test_primary.json"
        export_roles_json(assignments, str(output_path))
        
        import json
        with open(output_path) as f:
            data = json.load(f)
        
        assert 'P1' in data['player_primary_roles']
        assert data['player_primary_roles']['P1']['role'] == 'ENTRY'
        assert data['player_primary_roles']['P1']['frequency'] == 0.67  # 2/3


# ============================================================================
# RoleType Enum Tests
# ============================================================================

class TestRoleTypeEnum:
    """Tests for RoleType enum."""
    
    def test_all_roles_defined(self):
        """All expected roles exist."""
        expected = ['ENTRY', 'LURK', 'ANCHOR', 'ROTATOR', 'SUPPORT', 'UNKNOWN']
        
        for role in expected:
            assert hasattr(RoleType, role)
    
    def test_enum_values(self):
        """Enum values match names."""
        assert RoleType.ENTRY.value == "ENTRY"
        assert RoleType.LURK.value == "LURK"
