# CS2 Analyzer Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.9.0-orange.svg)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-26%20passing-brightgreen.svg)](tests/)

Production-grade performance analytics engine for Counter-Strike 2 demo files. Delivers accurate player ratings, role classification, cross-match comparison, and trend tracking through deep statistical analysis.

---

## Core Features

| Feature | Description |
|---------|-------------|
| **Role Classification** | Automatic detection (AWPer, Entry, Trader, Rotator, Anchor) using behavioral analysis |
| **Impact Rating** | Composite 0-100 score from kills, entries, clutches, WPA, death context |
| **Player Comparison** | Track same player across multiple demos with trend analysis |
| **Consistency Scoring** | Measure rating variance across matches |
| **Exploit Resistance** | Calibrated penalties for exit farming, stat padding, inflation |
| **Coaching Feedback** | Evidence-based mistake detection with drill recommendations |

---

## Installation

```bash
git clone https://github.com/Pl4yer-ONE/cs2-ai-coach.git
cd cs2-ai-coach

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

---

## Usage

### Single Demo Analysis
```bash
python -m src.main demo.dem --output ./output
```

### Batch Processing
```bash
python -m src.main ./demos/ --output ./output
```

### Player Comparison (Cross-Demo)
```bash
python -m src.analytics.player_tracker ./output
```

---

## Output Structure

```
output/
├── match-name/
│   ├── reports/
│   │   └── match_report_*.json
│   └── heatmaps/
│       └── map-name/*.png
└── player_comparison.json
```

---

## Rating System

### Score Bands

| Rating | Classification |
|--------|----------------|
| 95-100 | Elite |
| 85-94 | Carry |
| 70-84 | Strong |
| 50-69 | Average |
| 30-49 | Below Average |
| 15-29 | Liability |

### Calibration Rules

| Rule | Condition | Effect |
|------|-----------|--------|
| Kill Gate | raw > 105, kills < 18 | 0.90x |
| Exit Tax | exit_frags >= 8 | 0.85x |
| Low KDR Cap | KDR < 0.8 | max 75 |
| Trader Ceiling | Trader, KDR < 1.0 | max 80 |
| Rotator Ceiling | Rotator role | max 95 |
| Breakout | KDR > 1.15, KAST > 70%, kills >= 16 | +10 cap |
| Floor | Always | min 15 |

---

## Player Comparison

Track players across multiple matches:

```json
{
  "name": "REZ",
  "matches_played": 3,
  "avg_rating": 88.3,
  "form_rating": 88.3,
  "consistency": 25.1,
  "trend": "stable",
  "match_history": [
    {"map": "de_dust2", "role": "SiteAnchor", "rating": 77},
    {"map": "de_nuke", "role": "Trader", "rating": 98},
    {"map": "de_train", "role": "Rotator", "rating": 90}
  ]
}
```

| Metric | Description |
|--------|-------------|
| **avg_rating** | Mean rating across all matches |
| **form_rating** | Last 3 matches average |
| **consistency** | 100 = no variance, 0 = volatile |
| **trend** | improving, declining, stable |

---

## API Reference

### ScoreEngine

```python
from src.metrics.scoring import ScoreEngine

rating = ScoreEngine.compute_final_rating(
    scores={"raw_impact": 100},
    role="Entry",
    kdr=1.2,
    untradeable_deaths=5,
    kills=18,
    rounds_played=20,
    kast_percentage=0.7,
    exit_frags=3
)
```

### PlayerTracker

```python
from src.analytics.player_tracker import PlayerTracker

tracker = PlayerTracker()
tracker.load_directory("./outputs")
comparison = tracker.compare_players()
```

---

## Testing

```bash
python -m pytest tests/ -v
```

**26 tests covering:**
- Exit frag tax
- KDR caps
- Role ceilings
- Kill-gate logic
- Smurf detection
- Breakout rules
- Map coordinate transformations

---

## Project Structure

```
cs2-analyzer-engine/
├── src/
│   ├── main.py
│   ├── analytics/
│   │   └── player_tracker.py
│   ├── features/
│   │   └── extractor.py
│   ├── metrics/
│   │   ├── scoring.py
│   │   ├── calibration.py
│   │   └── role_classifier.py
│   └── report/
│       ├── json_reporter.py
│       └── heatmaps.py
├── tests/
├── CHANGELOG.md
├── LICENSE
└── README.md
```

---

## Requirements

- Python 3.10+
- demoparser2
- numpy
- matplotlib
- pytest

---

## License

MIT License. See [LICENSE](LICENSE).
