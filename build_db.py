"""
build_db.py
-----------
Cleans the raw Fitabase (Bellabeat / FitBit) CSV exports and loads them
into a single SQLite database (db/fitbit.db) that both the SQL insights
script and the Streamlit app read from.

Run once (or whenever the raw data changes):
    python build_db.py
"""

import sqlite3
import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"
DB_PATH = BASE / "db" / "fitbit.db"


def load_daily_activity():
    df = pd.read_csv(DATA / "dailyActivity_merged.csv")
    df["ActivityDate"] = pd.to_datetime(df["ActivityDate"], format="%m/%d/%Y")

    # --- cleaning ---
    before = len(df)
    df = df.drop_duplicates()
    df = df[df["TotalSteps"] >= 0]

    # A "no-wear" day: zero steps AND zero total activity minutes.
    # We keep these rows (useful for adherence analysis) but flag them
    # instead of silently dropping data.
    df["IsNoWearDay"] = (
        (df["TotalSteps"] == 0)
        & (df["VeryActiveMinutes"] + df["FairlyActiveMinutes"] + df["LightlyActiveMinutes"] == 0)
    )

    df["DayOfWeek"] = df["ActivityDate"].dt.day_name()
    df["TotalActiveMinutes"] = (
        df["VeryActiveMinutes"] + df["FairlyActiveMinutes"] + df["LightlyActiveMinutes"]
    )

    print(f"dailyActivity: {before} -> {len(df)} rows after cleaning "
          f"({df['IsNoWearDay'].sum()} flagged no-wear days)")
    return df


def load_sleep():
    df = pd.read_csv(DATA / "sleepDay_merged.csv")
    df["SleepDay"] = pd.to_datetime(df["SleepDay"], format="%m/%d/%Y %I:%M:%S %p").dt.normalize()

    before = len(df)
    # Fitbit sometimes logs more than one sleep session in a day
    # (naps). Collapse to one row per Id/day, summing time asleep/in bed.
    df = (
        df.groupby(["Id", "SleepDay"], as_index=False)
        .agg(
            TotalSleepRecords=("TotalSleepRecords", "sum"),
            TotalMinutesAsleep=("TotalMinutesAsleep", "sum"),
            TotalTimeInBed=("TotalTimeInBed", "sum"),
        )
    )
    df["SleepEfficiencyPct"] = (
        100 * df["TotalMinutesAsleep"] / df["TotalTimeInBed"]
    ).round(1)
    df = df[df["TotalTimeInBed"] > 0]

    print(f"sleepDay: {before} -> {len(df)} rows after de-duplicating same-day sessions")
    return df


def load_weight():
    df = pd.read_csv(DATA / "weightLogInfo_merged.csv")
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y %I:%M:%S %p")
    df = df.drop(columns=["Fat"])  # >90% missing, not usable
    print(f"weightLogInfo: {len(df)} rows ({df['Id'].nunique()} users logged weight)")
    return df


def load_hourly(name, value_col):
    df = pd.read_csv(DATA / f"hourly{name}_merged.csv")
    df["ActivityHour"] = pd.to_datetime(df["ActivityHour"], format="%m/%d/%Y %I:%M:%S %p")
    df["Hour"] = df["ActivityHour"].dt.hour
    df["Date"] = df["ActivityHour"].dt.normalize()
    return df


def main():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    load_daily_activity().to_sql("daily_activity", conn, if_exists="replace", index=False)
    load_sleep().to_sql("daily_sleep", conn, if_exists="replace", index=False)
    load_weight().to_sql("weight_log", conn, if_exists="replace", index=False)
    load_hourly("Steps", "StepTotal").to_sql("hourly_steps", conn, if_exists="replace", index=False)
    load_hourly("Calories", "Calories").to_sql("hourly_calories", conn, if_exists="replace", index=False)
    load_hourly("Intensities", "TotalIntensity").to_sql("hourly_intensities", conn, if_exists="replace", index=False)

    # A convenience view joining daily activity + sleep, used heavily
    # by both the SQL insights and the Streamlit app.
    conn.execute("DROP VIEW IF EXISTS daily_activity_sleep")
    conn.execute("""
        CREATE VIEW daily_activity_sleep AS
        SELECT
            a.*,
            s.TotalMinutesAsleep,
            s.TotalTimeInBed,
            s.SleepEfficiencyPct
        FROM daily_activity a
        LEFT JOIN daily_sleep s
          ON a.Id = s.Id AND a.ActivityDate = s.SleepDay
    """)

    conn.commit()
    conn.close()
    print(f"\nDatabase written to {DB_PATH}")


if __name__ == "__main__":
    main()
