# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Timeline Event Taxonomy
Frozen event types and dataclass for per-round event streams.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any


class EventType(str, Enum):
    """Frozen event taxonomy. Do not modify without versioning."""
    # Combat
    KILL = "KILL"
    DEATH = "DEATH"
    TRADE = "TRADE"
    ASSIST = "ASSIST"
    DAMAGE = "DAMAGE"
    
    # Utility
    FLASH_ASSIST = "FLASH_ASSIST"
    SMOKE_BLOCK = "SMOKE_BLOCK"
    MOLLY_DAMAGE = "MOLLY_DAMAGE"
    UTILITY_THROW = "UTILITY_THROW"
    
    # Tactical
    ENTRY_KILL = "ENTRY_KILL"
    CLUTCH_START = "CLUTCH_START"
    CLUTCH_WIN = "CLUTCH_WIN"
    
    # Objective
    PLANT = "PLANT"
    DEFUSE = "DEFUSE"
    BOMB_DROPPED = "BOMB_DROPPED"
    
    # Round
    ROUND_START = "ROUND_START"
    ROUND_END = "ROUND_END"


@dataclass
class TimelineEvent:
    """
    Single event in the round timeline.
    
    Required fields:
        tick: Game tick
        timestamp_ms: Milliseconds since round start
        event: EventType enum value
        player: Player name
        team: 'CT' or 'T'
        round: Round number (0-indexed)
    
    Optional fields:
        wpa_delta: Win Probability Added delta for this event
        victim: For KILL/DAMAGE events
        weapon: Weapon used
        damage: Damage dealt
        is_entry: First kill of round
        is_trade: Trade kill (within 3s)
        is_headshot: Headshot kill
        distance: Distance to victim (units)
    """
    tick: int
    timestamp_ms: int
    event: str  # EventType value
    player: str
    team: str
    round: int
    
    # WPA
    wpa_delta: float = 0.0
    
    # Combat metadata
    victim: Optional[str] = None
    weapon: Optional[str] = None
    damage: Optional[int] = None
    is_entry: bool = False
    is_trade: bool = False
    is_headshot: bool = False
    distance: Optional[float] = None
    
    # Utility metadata
    flashed_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != 0.0 and v is not False}
    
    def __lt__(self, other: 'TimelineEvent') -> bool:
        """Sort by timestamp."""
        return self.timestamp_ms < other.timestamp_ms
