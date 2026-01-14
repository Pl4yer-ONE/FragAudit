# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Synergy Module Tests
Tests for duo symmetry, team metrics, and edge cases.
"""

import pytest
from src.synergy.duo import DuoStats, compute_duo_metrics, _duo_key
from src.synergy.team import TeamStats, compute_team_metrics
from src.timeline.builder import RoundTimeline
from src.timeline.events import TimelineEvent


class TestDuoStats:
    """Tests for DuoStats dataclass."""
    
    def test_duo_creation(self):
        """Test basic duo stats creation."""
        duo = DuoStats(player1="A", player2="B")
        assert duo.player1 == "A"
        assert duo.player2 == "B"
        assert duo.trade_attempts == 0
    
    def test_trade_success_rate(self):
        """Test trade success rate calculation."""
        duo = DuoStats(player1="A", player2="B", trade_attempts=10, trade_successes=7)
        assert duo.trade_success_rate == 0.7
    
    def test_trade_success_rate_zero_division(self):
        """Test trade success rate handles zero attempts."""
        duo = DuoStats(player1="A", player2="B", trade_attempts=0, trade_successes=0)
        assert duo.trade_success_rate == 0.0
    
    def test_duo_symmetry_equality(self):
        """Test (A,B) == (B,A) symmetry."""
        duo1 = DuoStats(player1="A", player2="B")
        duo2 = DuoStats(player1="B", player2="A")
        assert duo1 == duo2
    
    def test_duo_symmetry_hash(self):
        """Test symmetric hash for set/dict usage."""
        duo1 = DuoStats(player1="A", player2="B")
        duo2 = DuoStats(player1="B", player2="A")
        assert hash(duo1) == hash(duo2)
    
    def test_to_dict_includes_computed(self):
        """Test to_dict includes computed properties."""
        duo = DuoStats(
            player1="A", player2="B",
            trade_attempts=10, trade_successes=7,
            shared_rounds=20, shared_round_wins=15
        )
        d = duo.to_dict()
        assert d['trade_success_rate'] == 0.7
        assert d['shared_round_win_rate'] == 0.75


class TestDuoKey:
    """Tests for _duo_key helper."""
    
    def test_duo_key_symmetric(self):
        """Test duo key is symmetric."""
        assert _duo_key("A", "B") == _duo_key("B", "A")
    
    def test_duo_key_sorted(self):
        """Test duo key is sorted alphabetically."""
        assert _duo_key("Zywoo", "S1mple") == ("S1mple", "Zywoo")


class TestTeamStats:
    """Tests for TeamStats dataclass."""
    
    def test_team_creation(self):
        """Test basic team stats creation."""
        team = TeamStats(team="CT")
        assert team.team == "CT"
        assert team.entry_attempts == 0
    
    def test_entry_success_rate(self):
        """Test entry success rate calculation."""
        team = TeamStats(team="T", entry_attempts=10, entry_successes=6)
        assert team.entry_success_rate == 0.6
    
    def test_entry_success_rate_zero_division(self):
        """Test entry success rate handles zero division."""
        team = TeamStats(team="T", entry_attempts=0)
        assert team.entry_success_rate == 0.0
    
    def test_postplant_win_rate(self):
        """Test postplant win rate."""
        team = TeamStats(team="T", postplant_rounds=8, postplant_wins=5)
        assert team.postplant_win_rate == 0.625
