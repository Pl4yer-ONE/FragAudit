# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Timeline Exporter
Export timelines to JSON and CSV formats.
"""

import json
import csv
from typing import List, Dict, Any
from pathlib import Path

from .builder import RoundTimeline


def export_timeline_json(
    timelines: List[RoundTimeline],
    output_path: str,
    match_id: str = "",
    map_name: str = ""
) -> str:
    """
    Export timelines to JSON format.
    
    Schema (frozen):
    {
        "match_id": "string",
        "map": "string",
        "schema_version": "1.0",
        "rounds": [
            {
                "round": 0,
                "start_tick": 12345,
                "end_tick": 15678,
                "events": [...]
            }
        ]
    }
    
    Args:
        timelines: List of RoundTimeline objects
        output_path: Path to output JSON file
        match_id: Optional match identifier
        map_name: Map name
        
    Returns:
        Path to created file
    """
    output = {
        "match_id": match_id,
        "map": map_name,
        "schema_version": "1.0",
        "rounds": [t.to_dict() for t in timelines]
    }
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    return str(path)


def export_timeline_csv(
    timelines: List[RoundTimeline],
    output_path: str
) -> str:
    """
    Export timelines to flat CSV format.
    
    Columns: round, tick, timestamp_ms, event, player, team, victim, weapon, wpa_delta
    
    Args:
        timelines: List of RoundTimeline objects
        output_path: Path to output CSV file
        
    Returns:
        Path to created file
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = [
        'round', 'tick', 'timestamp_ms', 'event', 'player', 'team',
        'victim', 'weapon', 'damage', 'is_entry', 'is_trade', 
        'is_headshot', 'wpa_delta'
    ]
    
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        
        for timeline in timelines:
            for event in timeline.events:
                row = event.to_dict()
                writer.writerow(row)
    
    return str(path)


def export_timeline_summary(timelines: List[RoundTimeline]) -> Dict[str, Any]:
    """
    Generate summary statistics for timelines.
    
    Returns:
        Dict with total_events, events_by_type, rounds_count
    """
    events_by_type: Dict[str, int] = {}
    total_events = 0
    
    for timeline in timelines:
        for event in timeline.events:
            events_by_type[event.event] = events_by_type.get(event.event, 0) + 1
            total_events += 1
    
    return {
        "total_events": total_events,
        "rounds_count": len(timelines),
        "events_by_type": events_by_type
    }
