# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Timeline Module Tests
Tests for event ordering, timestamps, and WPA validation.
"""

import pytest
from src.timeline.events import TimelineEvent, EventType
from src.timeline.builder import TimelineBuilder, RoundTimeline
from src.timeline.exporter import export_timeline_json, export_timeline_csv, export_timeline_summary


class TestTimelineEvent:
    """Tests for TimelineEvent dataclass."""
    
    def test_event_creation(self):
        """Test basic event creation."""
        event = TimelineEvent(
            tick=12345,
            timestamp_ms=3200,
            event=EventType.KILL.value,
            player="s1mple",
            team="T",
            round=5
        )
        assert event.tick == 12345
        assert event.timestamp_ms == 3200
        assert event.event == "KILL"
        assert event.player == "s1mple"
        assert event.team == "T"
        assert event.round == 5
    
    def test_event_with_metadata(self):
        """Test event with optional fields."""
        event = TimelineEvent(
            tick=12345,
            timestamp_ms=3200,
            event=EventType.KILL.value,
            player="s1mple",
            team="T",
            round=5,
            victim="zywoo",
            weapon="AK47",
            is_entry=True,
            is_headshot=True,
            wpa_delta=0.134
        )
        assert event.victim == "zywoo"
        assert event.weapon == "AK47"
        assert event.is_entry is True
        assert event.is_headshot is True
        assert event.wpa_delta == 0.134
    
    def test_event_sorting(self):
        """Test events sort by timestamp."""
        events = [
            TimelineEvent(tick=200, timestamp_ms=5000, event="KILL", player="A", team="T", round=1),
            TimelineEvent(tick=100, timestamp_ms=2000, event="KILL", player="B", team="CT", round=1),
            TimelineEvent(tick=150, timestamp_ms=3500, event="KILL", player="C", team="T", round=1),
        ]
        sorted_events = sorted(events)
        assert sorted_events[0].timestamp_ms == 2000
        assert sorted_events[1].timestamp_ms == 3500
        assert sorted_events[2].timestamp_ms == 5000
    
    def test_to_dict_excludes_none(self):
        """Test to_dict excludes None and default values."""
        event = TimelineEvent(
            tick=100,
            timestamp_ms=1000,
            event="KILL",
            player="A",
            team="T",
            round=1
        )
        d = event.to_dict()
        assert 'tick' in d
        assert 'victim' not in d  # None excluded
        assert 'is_entry' not in d  # False excluded


class TestEventType:
    """Tests for EventType enum."""
    
    def test_all_event_types_defined(self):
        """Verify all required event types exist."""
        required = [
            'KILL', 'DEATH', 'TRADE', 'ASSIST', 'DAMAGE',
            'FLASH_ASSIST', 'SMOKE_BLOCK', 'MOLLY_DAMAGE',
            'ENTRY_KILL', 'CLUTCH_START', 'CLUTCH_WIN',
            'PLANT', 'DEFUSE', 'ROUND_START', 'ROUND_END'
        ]
        for event_type in required:
            assert hasattr(EventType, event_type), f"Missing event type: {event_type}"
    
    def test_event_type_values(self):
        """Test event type string values."""
        assert EventType.KILL.value == "KILL"
        assert EventType.TRADE.value == "TRADE"


class TestRoundTimeline:
    """Tests for RoundTimeline dataclass."""
    
    def test_round_timeline_creation(self):
        """Test creating a round timeline."""
        events = [
            TimelineEvent(tick=100, timestamp_ms=1000, event="KILL", player="A", team="T", round=1),
        ]
        timeline = RoundTimeline(round=1, start_tick=0, end_tick=200, events=events)
        assert timeline.round == 1
        assert len(timeline.events) == 1
    
    def test_to_dict_sorts_events(self):
        """Test to_dict returns sorted events."""
        events = [
            TimelineEvent(tick=200, timestamp_ms=5000, event="KILL", player="A", team="T", round=1),
            TimelineEvent(tick=100, timestamp_ms=1000, event="KILL", player="B", team="CT", round=1),
        ]
        timeline = RoundTimeline(round=1, start_tick=0, end_tick=300, events=events)
        d = timeline.to_dict()
        assert d['events'][0]['timestamp_ms'] == 1000
        assert d['events'][1]['timestamp_ms'] == 5000


class TestExportSummary:
    """Tests for export_timeline_summary."""
    
    def test_summary_counts_events(self):
        """Test summary correctly counts events by type."""
        events = [
            TimelineEvent(tick=100, timestamp_ms=1000, event="KILL", player="A", team="T", round=1),
            TimelineEvent(tick=150, timestamp_ms=2000, event="DEATH", player="B", team="CT", round=1),
            TimelineEvent(tick=200, timestamp_ms=3000, event="KILL", player="C", team="T", round=1),
        ]
        timeline = RoundTimeline(round=1, start_tick=0, end_tick=300, events=events)
        
        summary = export_timeline_summary([timeline])
        assert summary['total_events'] == 3
        assert summary['rounds_count'] == 1
        assert summary['events_by_type']['KILL'] == 2
        assert summary['events_by_type']['DEATH'] == 1


class TestMonotonicTimestamps:
    """Tests to ensure timestamps are monotonically increasing within rounds."""
    
    def test_timestamps_are_monotonic(self):
        """After sorting, timestamps should be monotonically increasing."""
        events = [
            TimelineEvent(tick=300, timestamp_ms=8000, event="KILL", player="A", team="T", round=1),
            TimelineEvent(tick=100, timestamp_ms=1000, event="KILL", player="B", team="CT", round=1),
            TimelineEvent(tick=200, timestamp_ms=4000, event="KILL", player="C", team="T", round=1),
        ]
        timeline = RoundTimeline(round=1, start_tick=0, end_tick=400, events=events)
        
        sorted_events = sorted(timeline.events)
        
        for i in range(1, len(sorted_events)):
            assert sorted_events[i].timestamp_ms >= sorted_events[i-1].timestamp_ms, \
                f"Timestamps not monotonic at index {i}"
