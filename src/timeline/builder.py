# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Timeline Builder
Extracts per-round event streams from parsed demo data.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .events import TimelineEvent, EventType


@dataclass
class RoundTimeline:
    """Timeline for a single round."""
    round: int
    start_tick: int
    end_tick: int
    events: List[TimelineEvent]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "round": self.round,
            "start_tick": self.start_tick,
            "end_tick": self.end_tick,
            "events": [e.to_dict() for e in sorted(self.events)]
        }


class TimelineBuilder:
    """
    Builds per-round event timelines from parsed demo data.
    
    Usage:
        builder = TimelineBuilder(parsed_demo)
        timelines = builder.build()
    """
    
    # Trade window in milliseconds (3 seconds)
    TRADE_WINDOW_MS = 3000
    
    # Tickrate (will be read from demo)
    DEFAULT_TICKRATE = 64
    
    def __init__(self, parsed_demo):
        """
        Initialize with a ParsedDemo object.
        
        Args:
            parsed_demo: ParsedDemo from src.parser
        """
        self.demo = parsed_demo
        self.tickrate = getattr(parsed_demo, 'tickrate', self.DEFAULT_TICKRATE)
        self.round_timelines: List[RoundTimeline] = []
        
    def _tick_to_ms(self, tick: int, round_start_tick: int) -> int:
        """Convert tick to milliseconds relative to round start."""
        delta_ticks = tick - round_start_tick
        return int((delta_ticks / self.tickrate) * 1000)
    
    def _extract_kills(self, round_num: int, round_start_tick: int, round_end_tick: int) -> List[TimelineEvent]:
        """Extract kill events for a round."""
        events = []
        kills = self.demo.kills
        
        if kills is None or kills.empty:
            return events
        
        # Track kills for trade detection
        recent_kills: List[Dict] = []
        
        for _, row in kills.iterrows():
            tick = int(row.get('tick', 0))
            
            # Filter to this round
            if tick < round_start_tick or tick > round_end_tick:
                continue
            
            attacker = str(row.get('attacker_name', 'Unknown'))
            victim = str(row.get('victim_name', 'Unknown'))
            attacker_team = str(row.get('attacker_team_name', 'T'))
            weapon = str(row.get('weapon', 'Unknown'))
            is_headshot = bool(row.get('headshot', False))
            
            timestamp_ms = self._tick_to_ms(tick, round_start_tick)
            
            # Check if this is a trade
            is_trade = False
            for prev_kill in recent_kills:
                if prev_kill['victim'] == attacker:
                    time_diff = timestamp_ms - prev_kill['timestamp_ms']
                    if time_diff <= self.TRADE_WINDOW_MS:
                        is_trade = True
                        break
            
            # Check if entry kill (first kill of round)
            is_entry = len(events) == 0
            
            # Create kill event
            kill_event = TimelineEvent(
                tick=tick,
                timestamp_ms=timestamp_ms,
                event=EventType.ENTRY_KILL.value if is_entry else EventType.KILL.value,
                player=attacker,
                team='CT' if 'CT' in attacker_team.upper() else 'T',
                round=round_num,
                victim=victim,
                weapon=weapon,
                is_entry=is_entry,
                is_trade=is_trade,
                is_headshot=is_headshot
            )
            events.append(kill_event)
            
            # Create death event for victim
            victim_team = str(row.get('victim_team_name', 'CT'))
            death_event = TimelineEvent(
                tick=tick,
                timestamp_ms=timestamp_ms,
                event=EventType.DEATH.value,
                player=victim,
                team='CT' if 'CT' in victim_team.upper() else 'T',
                round=round_num,
                victim=attacker  # Killed by
            )
            events.append(death_event)
            
            # Track for trade detection
            recent_kills.append({
                'tick': tick,
                'timestamp_ms': timestamp_ms,
                'victim': victim,
                'attacker': attacker
            })
            
            # If this was a trade, add TRADE event
            if is_trade:
                trade_event = TimelineEvent(
                    tick=tick,
                    timestamp_ms=timestamp_ms,
                    event=EventType.TRADE.value,
                    player=attacker,
                    team='CT' if 'CT' in attacker_team.upper() else 'T',
                    round=round_num,
                    victim=victim
                )
                events.append(trade_event)
        
        return events
    
    def _extract_bomb_events(self, round_num: int, round_start_tick: int, round_end_tick: int) -> List[TimelineEvent]:
        """Extract bomb plant/defuse events."""
        events = []
        
        # Check for plants
        if hasattr(self.demo, 'plants') and self.demo.plants is not None:
            for _, row in self.demo.plants.iterrows():
                tick = int(row.get('tick', 0))
                if tick < round_start_tick or tick > round_end_tick:
                    continue
                    
                events.append(TimelineEvent(
                    tick=tick,
                    timestamp_ms=self._tick_to_ms(tick, round_start_tick),
                    event=EventType.PLANT.value,
                    player=str(row.get('player_name', 'Unknown')),
                    team='T',
                    round=round_num
                ))
        
        # Check for defuses
        if hasattr(self.demo, 'defuses') and self.demo.defuses is not None:
            for _, row in self.demo.defuses.iterrows():
                tick = int(row.get('tick', 0))
                if tick < round_start_tick or tick > round_end_tick:
                    continue
                    
                events.append(TimelineEvent(
                    tick=tick,
                    timestamp_ms=self._tick_to_ms(tick, round_start_tick),
                    event=EventType.DEFUSE.value,
                    player=str(row.get('player_name', 'Unknown')),
                    team='CT',
                    round=round_num
                ))
        
        return events
    
    def _get_round_boundaries(self) -> List[Dict[str, int]]:
        """Get start/end ticks for each round."""
        boundaries = []
        
        if hasattr(self.demo, 'rounds') and self.demo.rounds is not None:
            rounds_df = self.demo.rounds
            for _, row in rounds_df.iterrows():
                boundaries.append({
                    'round': int(row.get('round_num', len(boundaries))),
                    'start_tick': int(row.get('freeze_end', row.get('start_tick', 0))),
                    'end_tick': int(row.get('end_tick', row.get('official_end', 0)))
                })
        else:
            # Fallback: single "round" covering entire demo
            boundaries.append({
                'round': 0,
                'start_tick': 0,
                'end_tick': getattr(self.demo, 'total_ticks', 999999)
            })
        
        return boundaries
    
    def build(self) -> List[RoundTimeline]:
        """
        Build timelines for all rounds.
        
        Returns:
            List of RoundTimeline objects
        """
        boundaries = self._get_round_boundaries()
        
        for boundary in boundaries:
            round_num = boundary['round']
            start_tick = boundary['start_tick']
            end_tick = boundary['end_tick']
            
            events: List[TimelineEvent] = []
            
            # Add round start/end markers
            events.append(TimelineEvent(
                tick=start_tick,
                timestamp_ms=0,
                event=EventType.ROUND_START.value,
                player='',
                team='',
                round=round_num
            ))
            
            # Extract all event types
            events.extend(self._extract_kills(round_num, start_tick, end_tick))
            events.extend(self._extract_bomb_events(round_num, start_tick, end_tick))
            
            # Sort by timestamp
            events.sort()
            
            self.round_timelines.append(RoundTimeline(
                round=round_num,
                start_tick=start_tick,
                end_tick=end_tick,
                events=events
            ))
        
        return self.round_timelines
    
    def attach_wpa(self, wpa_calculator) -> None:
        """
        Attach WPA deltas to kill events.
        
        Args:
            wpa_calculator: Object with compute_wpa_delta(event) method
        """
        # TODO: Integrate with existing WPA scoring
        pass
