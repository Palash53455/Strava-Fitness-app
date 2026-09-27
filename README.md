# Bellabeat Fitness Data Analytics (FitBit / Fitabase Case Study)

A complete, three-layer analytics project built on the public FitBit/Fitabase
smart-device dataset (33 users, 4/12/2016 - 5/12/2016), styled after the
Bellabeat "wellness technology" case study:

1. **SQL** — cleaning + insight queries (`sql/insights.sql`), run via SQLite.
2. **Python EDA** — matplotlib/seaborn charts (`eda/eda.py`).
3. **Streamlit app** — interactive dashboard that surfaces both of the above
   (`app/app.py`).

## Project structure

```
bellabeat_project/
├── data/                     raw Fitabase CSVs (daily + hourly level)
├── build_db.py                cleans the CSVs, writes db/fitbit.db
├── db/fitbit.db                SQLite database (generated)
├── sql/insights.sql            10 numbered SQL insight queries
├── run_sql_insights.py         runs every query in insights.sql, prints results
├── eda/
│   ├── eda.py                  generates all EDA charts
│   └── figures/                 saved PNG charts (generated)
├── app/app.py                  Streamlit dashboard (4 tabs)
├── requirements.txt
└── README.md
```

## Setup

```bash
cd bellabeat_project
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

## Run it

```bash
# 1. Build the cleaned SQLite database from the raw CSVs
python build_db.py

# 2. (optional) See the SQL insights printed to the terminal
python run_sql_insights.py

# 3. (optional) Regenerate the EDA charts
python eda/eda.py

# 4. Launch the dashboard
streamlit run app/app.py
```

The Streamlit app rebuilds the database automatically on first run if
`db/fitbit.db` doesn't exist yet, so step 1 is optional if you just want
to see the app.

## What's inside the app

- **Dashboard** — KPI cards + interactive charts (steps by weekday, steps vs.
  calories, hourly activity pattern, steps over time, per-user summary table),
  all filterable by user and date range from the sidebar.
- **SQL Insights** — a dropdown of the 10 queries in `sql/insights.sql`,
  each executed live against the database with its result shown as a table
  (and a quick chart where it makes sense). Editing `insights.sql` changes
  what shows up here automatically.
- **Python EDA** — the 9 pre-generated matplotlib/seaborn charts from
  `eda/eda.py`, each with a one-line takeaway.
- **Recommendations** — the marketing-strategy insights derived from the
  analysis, written up for a non-technical stakeholder (as the original
  case study brief asks for).

## Key findings (from this sample)

- Only ~7 of 33 users average 10,000+ steps/day; most fall in the
  5,000-10,000 range.
- Sedentary minutes dominate every day of the week, including weekends —
  there's no clean "weekend effect."
- Steps and calories correlate strongly (r ≈ 0.6); more steps reliably
  means more calories burned.
- Sleep-tracking adherence (24/33 users) is much higher than weight-logging
  adherence (8/33 users) — manual entry is a bigger barrier than wearing
  the device.
- Activity is concentrated from mid-morning through early evening, which is
  the natural window for reminder notifications.

## Data source

Fitabase export of FitBit Fitness Tracker Data (Bellabeat case study,
Google Data Analytics Capstone), 33 anonymized users, daily and hourly
activity/sleep/weight logs, April-May 2016.
