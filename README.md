<div align="center">

# 🎯 FragAudit

### *Where every frag gets audited.*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.9.0-orange.svg)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-26%20passing-brightgreen.svg)](tests/)

**Production-grade CS2 demo analysis engine.**  
*Accurate ratings. Real insights. Zero fluff.*

---

[Installation](#installation) • [Usage](#usage) • [Rating System](#rating-system) • [API](#api-reference) • [License](#license)

</div>

---

## What is FragAudit?

FragAudit is a forensic analysis engine for Counter-Strike 2 demos. It dissects every kill, death, and round to produce **accurate, exploit-resistant player ratings**.

No magic numbers. No inflated stats. Just **audited performance**.

---

## Features

| Feature | Description |
|---------|-------------|
| **Role Detection** | AWPer, Entry, Trader, Rotator, Anchor — detected from behavior |
| **Impact Rating** | 0-100 score from kills, entries, clutches, WPA |
| **Player Tracking** | Compare same player across multiple demos |
| **Trend Analysis** | Improving, declining, or stable performance |
| **Consistency Score** | How stable is their rating match-to-match? |
| **Exploit Resistance** | Exit farming, stat padding, inflation — all penalized |

---

## Installation

```bash
git clone https://github.com/Pl4yer-ONE/FragAudit.git
cd FragAudit

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

---

## Usage

### Analyze Demo
```bash
python -m src.main demo.dem --output ./output
```

### Batch Process
```bash
python -m src.main ./demos/ --output ./output
```

### Player Comparison
```bash
python -m src.analytics.player_tracker ./output
```

---

## Rating System

### Score Bands

| Rating | Meaning |
|--------|---------|
| 95-100 | Elite |
| 85-94 | Carry |
| 70-84 | Strong |
| 50-69 | Average |
| 30-49 | Below Average |
| 15-29 | Liability |

### Anti-Exploit Rules

| Rule | Trigger | Penalty |
|------|---------|---------|
| Kill Gate | raw > 105, kills < 18 | 0.90x |
| Exit Tax | exits >= 8 | 0.85x |
| KDR Cap | KDR < 0.8 | max 75 |
| Trader Ceiling | Trader, KDR < 1.0 | max 80 |
| Rotator Ceiling | Rotator role | max 95 |
| Floor | Always | min 15 |

---

## Player Tracking

Track performance across matches:

```json
{
  "name": "REZ",
  "matches_played": 3,
  "avg_rating": 88.3,
  "form_rating": 88.3,
  "consistency": 25.1,
  "trend": "stable"
}
```

---

## API Reference

### ScoreEngine
```python
from src.metrics.scoring import ScoreEngine

rating = ScoreEngine.compute_final_rating(
    scores={"raw_impact": 100},
    role="Entry",
    kdr=1.2,
    kills=18,
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

26 tests covering calibration, caps, and edge cases.

---

## License

MIT License. See [LICENSE](LICENSE).

---

<div align="center">

**FragAudit** — *Where every frag gets audited.*

</div>
