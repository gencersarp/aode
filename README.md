# aode
Autonomous Opportunity Discovery Engine

## Overview

AODE is a production-grade system that **discovers, validates, and partially builds startup ideas automatically**. It operates in iterative cycles:

1. **Data Ingestion** — scrapes Reddit and GitHub Issues for real user pain points
2. **Opportunity Extraction** — clusters posts using TF-IDF + k-means (or keyword heuristics)
3. **Goodhart-Aware Scoring** — scores clusters across pain intensity, monetisation, feasibility, and competition — with explicit anti-hype and anti-generic-idea penalties
4. **Validation** — generates landing page copy, outreach messages, and a simulated interest score
5. **Auto-Build** — a multi-agent system (Planner → Engineer → Tester) produces a working Python CLI or web MVP

## Project Structure

```
aode/
├── aode/
│   ├── ingestion/          # Data scrapers (Reddit, GitHub)
│   │   ├── reddit_scraper.py
│   │   └── github_scraper.py
│   ├── extraction/         # Opportunity clustering engine
│   ├── scoring/            # Goodhart-aware scoring system
│   ├── validation/         # Landing page + outreach generator
│   ├── builder/            # Multi-agent MVP builder
│   │   ├── planner.py      # Planner Agent
│   │   ├── engineer.py     # Engineer Agent
│   │   └── tester.py       # Tester Agent
│   ├── storage/            # SQLite persistence layer
│   ├── orchestrator.py     # Main discovery loop
│   └── cli.py              # CLI entry point
├── tests/                  # Full test suite (53 tests)
├── data/                   # SQLite database (auto-created)
├── requirements.txt
└── pyproject.toml
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run one discovery cycle (uses mock data offline)
python -m aode.cli

# Run 3 cycles, validate top 5, use keyword heuristics
python -m aode.cli --cycles 3 --top-n 5 --no-sklearn
```

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--cycles` | 1 | Number of discovery cycles |
| `--top-n` | 3 | Top N opportunities to validate |
| `--no-sklearn` | off | Use keyword heuristic instead of ML clustering |
| `--n-clusters` | 8 | Number of k-means clusters |
| `--max-posts` | 200 | Max posts to fetch per cycle |

## Environment Variables (Optional)

| Variable | Purpose |
|----------|---------|
| `REDDIT_CLIENT_ID` | Reddit API client ID (uses mock data if unset) |
| `REDDIT_CLIENT_SECRET` | Reddit API client secret |
| `REDDIT_USER_AGENT` | Reddit API user agent |
| `GITHUB_TOKEN` | GitHub personal access token (uses mock data if unset) |
| `OPENAI_API_KEY` | OpenAI API key (uses heuristic builder if unset) |

## Running Tests

```bash
PYTHONPATH=. python -m pytest tests/ -v
```

## Architecture

### Scoring System (Goodhart-Aware)

Each cluster is scored on four dimensions (weighted):

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Pain intensity | 35% | Frequency and strength of complaints |
| Monetisation | 25% | Willingness-to-pay signals |
| Build feasibility | 20% | Complexity for a small team |
| Competition density | 20% | Market openness (inverted) |

**Penalties applied after raw scoring:**
- **Anti-hype penalty**: deducts up to 3 points for AI/blockchain/buzzword density
- **Anti-generic penalty**: deducts up to 2 points for vague "all-in-one platform" language

### Auto-Build Pipeline

```
PlannerAgent → EngineerAgent → TesterAgent
     ↓               ↓              ↓
  Task list    Generated code    Validation
                                  report
```

Generated MVPs include `models.py`, `core.py`, `main.py` (or `app.py`), `storage.py`, and `README.md`.

### Storage

All artefacts are persisted in SQLite (`data/aode.db`):
- `raw_posts` — scraped posts
- `opportunity_clusters` — extracted clusters
- `scored_opportunities` — scoring results
- `validations` — validation results
- `built_mvps` — generated MVP metadata
- `cycle_log` — per-cycle audit log
