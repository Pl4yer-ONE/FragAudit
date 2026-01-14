#!/bin/bash
# FragAudit Full Analysis Script
# Runs complete analysis pipeline including radar replay

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  FRAGAUDIT v3.8 - FULL ANALYSIS PIPELINE"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check for demo file argument
if [ -z "$1" ]; then
    # Default to first demo in match folder
    DEMO=$(ls match/*.dem 2>/dev/null | head -n 1)
    if [ -z "$DEMO" ]; then
        echo -e "${RED}Error: No demo file specified and none found in match/${NC}"
        echo "Usage: ./run_analysis.sh <path/to/demo.dem>"
        exit 1
    fi
    echo -e "${YELLOW}No demo specified, using: ${DEMO}${NC}"
else
    DEMO="$1"
fi

# Verify demo exists
if [ ! -f "$DEMO" ]; then
    echo -e "${RED}Error: Demo file not found: ${DEMO}${NC}"
    exit 1
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "${RED}Error: Virtual environment not found. Run: python -m venv venv${NC}"
    exit 1
fi

# Clean old output
echo -e "${CYAN}[1/5] Cleaning old output...${NC}"
rm -f reports/*.json reports/*.html reports/*.csv reports/*.mp4 2>/dev/null
rm -rf tmp_frames 2>/dev/null
echo "      Done"
echo ""

# Run tests
echo -e "${CYAN}[2/5] Running test suite...${NC}"
TEST_RESULT=$(python -m pytest tests/ -q 2>&1 | tail -n 1)
echo "      $TEST_RESULT"
echo ""

# Run main analysis with HTML report
echo -e "${CYAN}[3/5] Analyzing demo: ${DEMO}${NC}"
python main.py analyze --demo "$DEMO" --html --timeline
echo ""

# Generate radar replay
echo -e "${CYAN}[4/5] Generating radar replay...${NC}"
python main.py play --demo "$DEMO" --radar --output reports/radar_replay.mp4 2>&1 | tail -n 3
echo ""

# Show output
echo -e "${CYAN}[5/5] Output files:${NC}"
echo ""
ls -lh reports/*.json reports/*.html reports/*.csv reports/*.mp4 2>/dev/null | awk '{print "      " $9 " (" $5 ")"}'
echo ""

# Summary
echo "════════════════════════════════════════════════════════════"
echo -e "  ${GREEN}ANALYSIS COMPLETE${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "  Open HTML report:"
echo "    open reports/report_*.html"
echo ""
echo "  Play radar replay:"
echo "    open reports/radar_replay.mp4"
echo ""
