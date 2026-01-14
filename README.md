<div align="center">

<img src="docs/logo.png" alt="FragAudit" width="200"/>

# ⚔️ FRAGAUDIT

### *When the scoreboard lies, the demo doesn't.*

**Tactical Demo Analysis for CS2**

[![GPLv3](https://img.shields.io/badge/License-GPLv3-red.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-yellow.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-174%20passed-brightgreen.svg)](tests/)
[![v3.9.0](https://img.shields.io/badge/Version-3.9.0-blue.svg)](CHANGELOG.md)

---

![Radar Demo](docs/radar_preview.gif)

*Real player positions. Real mistakes. Real intel.*

</div>

---

## 🎯 WHAT IS THIS?

FragAudit rips apart CS2 demo files and exposes everything:

| Intel | What You Get |
|-------|--------------|
| 🔴 **Mistakes** | Overpeeks, failed trades, spacing errors — flagged with round and timestamp |
| 🎭 **Roles** | Entry, Lurk, Anchor, Support — detected per round, not assumed |
| 📊 **Win Probability** | Round-by-round predictions with factor breakdown |
| 🗺️ **Strategy** | Execute, Rush, Split, Default — patterns identified automatically |
| 🎬 **Radar Replay** | MP4 video with view cones, player numbers, and grenades |

**No guessing. No vibes. Just data.**

---

## 🔥 THE RADAR

<div align="center">

![Radar](docs/radar_preview.gif)

</div>

- **View cones** — See where players are looking
- **Numbered players** — CT: 1-5 | T: 6-10
- **Smoke/Flash/Molly** — All utility tracked
- **Kill markers** — Who died where
- **Boltobserv maps** — Clean radar backgrounds

```bash
python main.py analyze --demo your_match.dem --radar
```

Output: `reports/radar_*.mp4`

---

## ⚙️ INSTALL

```bash
git clone https://github.com/Pl4yer-ONE/FragAudit.git
cd FragAudit
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Verify:
```bash
python -m pytest tests/ -q
# 174 passed ✓
```

---

## 🕹️ USAGE

### Quick Analyze
```bash
python main.py analyze --demo match.dem
```

### Full Report + Radar
```bash
python main.py analyze --demo match.dem --html --radar
```

### One-Click Pipeline
```bash
./run_analysis.sh match/your-demo.dem
```

---

## 📈 PREDICTION ENGINE

```python
from src.predict import predict_round_win

result = predict_round_win(
    team_economy=1500,
    enemy_economy=4500,
    team_alive=5,
    enemy_alive=4,
    mistake_count=1
)

print(f"Win chance: {result.probability:.0%}")  # 43%
print(f"Why: {result.dominant_factor}")         # economy
```

Every prediction tells you **why**.

---

## 🏗️ BACKEND PILLARS

| Module | What It Does |
|--------|--------------|
| `mistakes/` | Detects 5 error types with severity |
| `roles/` | Classifies Entry, Lurk, Anchor, Rotator, Support |
| `wpa/` | Contextual win probability with multipliers |
| `strategy/` | Clusters Execute, Rush, Split, Default |
| `predict/` | Hand-written logistic regression (no ML libs) |
| `radar/` | Boltobserv-style replay generation |

**174 tests. No black boxes. Every coefficient explicit.**

---

## 📸 SAMPLE OUTPUT

<details>
<summary><b>📊 HTML Report</b></summary>

![Report](docs/report_overview.png)

</details>

<details>
<summary><b>👤 Player Cards</b></summary>

![Players](docs/report_players.png)

</details>

---

## 📜 CREDITS

- **Radar maps** from [boltobserv](https://github.com/boltgolt/boltobserv) (GPL-3)
- **Demo parsing** via [demoparser2](https://github.com/LaihoE/demoparser)

See [THIRDPARTY.md](THIRDPARTY.md) for full attribution.

---

## ⚖️ LICENSE

**GNU General Public License v3.0**

Open source. Copyleft. No closed forks.

---

<div align="center">

### *"Stats don't lie. But they don't explain either."*

**FragAudit explains.**

---

[![GitHub Stars](https://img.shields.io/github/stars/Pl4yer-ONE/FragAudit?style=social)](https://github.com/Pl4yer-ONE/FragAudit)

</div>
