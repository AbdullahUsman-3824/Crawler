# IIO YouTube Research Crawler

This project collects YouTube comments for the research study on
AI/deepfake-enabled financial fraud, using the
Issues--Interventions--Outcomes (IIO) codebook.

> **Current progress:** 26,422 unique raw comments collected (19,182
> top-level comments and 7,240 replies). These are raw collected
> comments, not yet the final 20,000 relevant research comments.

## 1. Project structure

``` text
Crawler/
├── config/
│   ├── codebook.json              # Final IIO codebook: 21 variables, 105 forms
│   └── search_queries.csv          # Search query bank, divided into pilot batches
├── data/
│   ├── raw/
│   │   ├── discovered_videos.json # Videos found through YouTube search
│   │   ├── discovered_videos.csv
│   │   ├── iio_comments.sqlite3   # Main comment database
│   │   └── collected_comments.csv # Export of collected comments
│   ├── processed/
│   │   ├── validated_pilot1.json  # Pilot 1 video metadata and availability
│   │   ├── validated_pilot1.csv
│   │   ├── comment_audit_sample.csv # Random sample for manual quality checking
│   │   ├── comment_audit_stats.csv  # Audit summary
│   │   ├── relevance_sample_pilot.csv # Pilot relevance-annotation sample
│   │   └── relevance_sample_stats.csv # Sample counts by video and comment type
│   └── checkpoints/
│       └── video_discovery.json   # Discovery progress; supports resuming
├── src/
│   ├── config.py                  # Project paths and environment configuration
│   ├── youtube_client.py          # Creates and tests the YouTube API client
│   ├── search_query_bank.py       # Loads queries from search_queries.csv
│   ├── video_discovery.py         # Searches YouTube and saves discovered videos
│   ├── video_validator.py         # Fetches video metadata and comment availability
│   ├── validate_discovery.py      # Runs validation for discovered videos
│   ├── comment_collector.py        # Collects top-level comments and replies into SQLite
│   ├── comment_audit.py            # Creates a sample and basic collection-quality statistics
│   └── create_relevance_sample.py  # Creates a balanced pilot sample for relevance annotation
├── .env                           # YouTube API key (never commit this file)
├── .gitignore
└── requirements.txt
```

*Some output files are created only after the corresponding step has
been run.*

## 2. Setup (one time)

Open PowerShell in the project folder:

``` powershell
cd "D:\University\8th_Semester\MarketingFundamental\Crawler"
```

Create and activate the virtual environment (if not already created):

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

``` powershell
pip install -r requirements.txt
```

Create `.env` in the project root and add your YouTube API key:

``` env
YOUTUBE_API_KEY=YOUR_API_KEY_HERE
```

Do not share or commit `.env`.

## 3. Work sequence

Run these stages in order. Commands are run from the project root.

### Step 1 --- Test YouTube API connection

Module: `src/youtube_client.py`

This checks whether the API key works.

``` powershell
python -c "from src.youtube_client import test_connection; test_connection()"
```

### Step 2 --- Discover videos

Files: - `src/search_query_bank.py` loads the selected pilot queries
from `config/search_queries.csv`. - `src/video_discovery.py` searches
YouTube, removes duplicate video IDs, and saves results/checkpoints.

Current discovery setup in `src/main.py` uses **Pilot 1**. Run:

``` powershell
python -m src.main
```

Outputs: - `data/raw/discovered_videos.json` -
`data/raw/discovered_videos.csv` -
`data/checkpoints/video_discovery.json`

The checkpoint tracks completed queries so discovery can resume. The
current pilot query bank is provisional; review relevance before
expanding to later pilot batches.

### Step 3 --- Validate discovered videos

Files: - `src/video_validator.py` fetches metadata such as view count,
reported comment count, duration, and caption availability. -
`src/validate_discovery.py` runs the validation.

``` powershell
python -m src.validate_discovery
```

Pilot 1 outputs: - `data/processed/validated_pilot1.json` -
`data/processed/validated_pilot1.csv`

The collector uses this validated CSV to decide which videos to process.
A reported comment count of zero or an inconclusive comment probe should
not automatically be interpreted as comments being disabled.

### Step 4 --- Collect comments and replies

Module: `src/comment_collector.py`

``` powershell
python -m src.comment_collector
```

Inputs: - `data/processed/validated_pilot1.csv`

Outputs: - `data/raw/iio_comments.sqlite3` --- primary database; comment
IDs are unique. - `data/raw/collected_comments.csv` --- CSV export.

The collector stores top-level comments and replies, commits progress to
SQLite, and skips videos already marked complete when rerun. If
interrupted, run the same command again. API quota exhaustion may
require waiting for quota reset before retrying.

### Step 5 --- Audit the collected comments (next step)

Module: `src/comment_audit.py`

``` powershell
python -m src.comment_audit
```

Expected outputs: - `data/processed/comment_audit_sample.csv` --- random
sample for manual review. - `data/processed/comment_audit_stats.csv` ---
basic counts and collection statistics.

Review the sample for relevance, language variety, duplicates,
empty/very short comments, and off-topic material before building the
relevance and IIO classifiers.

### Step 6 --- Create the relevance pilot sample

Module: `src/create_relevance_sample.py`

``` powershell
python -m src.create_relevance_sample
```

This script reads non-empty comments from
`data/raw/iio_comments.sqlite3` and creates a deterministic pilot sample
with seed `42`. It attempts to select four comments per video: two
top-level comments and two replies. If a video has fewer comments of one
type, the script fills the remaining slots from the other type.
For replies, it also adds `parent_comment_text` by looking up the
`parent_comment_id` in SQLite.

Outputs:

-   `data/processed/relevance_sample_pilot.csv` --- comments selected for
    relevance annotation, with blank label and reviewer columns.
-   `data/processed/relevance_sample_stats.csv` --- selected comment
    counts by video and comment type.

The pilot CSV includes fields for `relevance_label`, `context_type`,
`reason`, `evidence_text`, and `reviewer_notes`. Use these fields to
record human relevance decisions while preserving the original comment
and video IDs for traceability.

## 4. Important research notes

-   The current **26,422 comments are raw data**. Do not report them as
    26,422 relevant comments.
-   The research target is approximately **20,000 relevant comments**
    after relevance screening and quality checks.
-   The IIO codebook has 21 variables and 105 forms. Comments may
    receive multiple labels where supported by evidence.
-   Keep the original raw database unchanged. Save filtering,
    annotations, and model outputs as separate processed files/tables.
-   Preserve comment IDs and video IDs so every annotation can be traced
    back to its source.
-   Automated labels will need human review/validation. Do not treat
    model predictions as ground truth.
-   Findings describe the collected YouTube sample; they should not be
    generalized to all consumers or interpreted as causal evidence.

## 5. Current status / next action

  Stage                           Status
  ------------------------------- --------------------------
  Environment and API setup       Done
  IIO codebook and query bank     Prepared
  Pilot 1 video discovery         Done
  Pilot 1 video validation        Done
  Raw comment collection          Done --- 26,422 comments
  Comment quality audit           **Next**
  Relevance pilot sample          Prepared --- run after the quality audit
  Relevance screening             Pending
  IIO multi-label annotation      Pending
  Human validation and analysis   Pending

**Next actions:** run `python -m src.comment_audit`, review
`comment_audit_sample.csv` and its statistics, then run
`python -m src.create_relevance_sample` to prepare the pilot relevance
annotation file.


## Quick pipeline (relevance screening, IIO cues, sentiment, relationships)

Run from the project root, in this order. The raw SQLite database and `collected_comments.csv` are never modified.

| Step | Command | Output (data/processed/) |
|---|---|---|
| Relevance screening (English only, rule-based) | `python -m src.relevance_screen data/raw/collected_comments.csv annotations/relevance_pilot_v1.1.csv` | `relevance_screened.csv`, `relevance_screen_stats.csv` |
| IIO cue matching (preliminary labels) | `python -m src.iio_cues config/codebook.json data/processed/relevance_screened.csv` | `iio_annotations_long.csv`, `iio_annotations_wide.csv` |
| Sentiment and emotion (`pip install vaderSentiment`) | `python -m src.sentiment_emotion data/processed/relevance_screened.csv` | `sentiment_emotion.csv` |
| Relationships / predictive feasibility | `python -m src.predictive_models 0.5` | `predictive_feasibility.csv`, `iio_cooccurrence.csv` |
| Agreement between annotators | `python -m src.agreement annotations/relevance_pilot_v1.1.csv annotations/annotator_B_done.csv` | `annotations/disagreements.csv` |

Notes: `final_label` uses the human label when one exists, otherwise the rule-based label. IIO labels are automatic and
need human validation (see `validation_sheet_*.csv`). Predictive models run only when enough multi-dimension comments exist.
Annotation files live in `annotations/` (labels v1.1, guidelines v1.1, decisions log).
