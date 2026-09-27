"""
app.py
------
Streamlit dashboard for the Bellabeat / FitBit smart-device case study.

Run:
    streamlit run app/app.py

Requires db/fitbit.db to already exist -- run `python build_db.py`
from the project root first (the app will do this automatically the
first time if the DB is missing).
"""

import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

BASE = Path(__file__).parent.parent
DB_PATH = BASE / "db" / "fitbit.db"
SQL_PATH = BASE / "sql" / "insights.sql"

st.set_page_config(page_title="Bellabeat Fitness Analytics", layout="wide", page_icon="📊")

# ---------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------
if not DB_PATH.exists():
    st.info("Building the database for the first time, this takes a few seconds...")
    subprocess.run([sys.executable, str(BASE / "build_db.py")], check=True)


@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data
def parse_sql_file():
    """Parse sql/insights.sql into {title: sql} so this tab always matches insights.sql."""
    text = SQL_PATH.read_text()
    parts = re.split(r"\n-- (\d+)\.\s*(.*?)\n", text)
    queries = {}
    for i in range(1, len(parts), 3):
        num, title, sql = parts[i], parts[i + 1], parts[i + 2]
        sql_clean = "\n".join(
            line for line in sql.splitlines() if not line.strip().startswith("--")
        ).strip().rstrip(";")
        queries[f"{num}. {title.strip()}"] = sql_clean
    return queries


conn = get_connection()
activity = pd.read_sql_query("SELECT * FROM daily_activity", conn, parse_dates=["ActivityDate"])
sleep = pd.read_sql_query("SELECT * FROM daily_sleep", conn, parse_dates=["SleepDay"])
merged = pd.read_sql_query(
    "SELECT * FROM daily_activity_sleep WHERE TotalMinutesAsleep IS NOT NULL",
    conn, parse_dates=["ActivityDate"],
)
hourly_steps = pd.read_sql_query("SELECT * FROM hourly_steps", conn, parse_dates=["ActivityHour"])

sns.set_theme(style="whitegrid", palette="viridis")
WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ---------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------
st.sidebar.header("Filters")
all_users = sorted(activity["Id"].unique())
selected_users = st.sidebar.multiselect("User ID(s)", all_users, default=all_users)

min_date, max_date = activity["ActivityDate"].min(), activity["ActivityDate"].max()
date_range = st.sidebar.date_input(
    "Date range", (min_date.date(), max_date.date()),
    min_value=min_date.date(), max_value=max_date.date(),
)

if len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
else:
    start, end = min_date, max_date

mask = (
    activity["Id"].isin(selected_users)
    & activity["ActivityDate"].between(start, end)
)
f_activity = activity[mask]
f_merged = merged[merged["Id"].isin(selected_users) & merged["ActivityDate"].between(start, end)]

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data: Fitabase / FitBit Fitness Tracker export, 33 users, "
    f"{min_date.date()} to {max_date.date()}. Source project: Bellabeat case study."
)

# ---------------------------------------------------------------
# Header + KPIs
# ---------------------------------------------------------------
st.title("📊 Bellabeat Fitness Data Analytics")
st.caption("Smart-device usage insights to guide Bellabeat's marketing strategy")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Users in view", f_activity["Id"].nunique())
k2.metric("Avg. daily steps", f"{f_activity['TotalSteps'].mean():,.0f}" if len(f_activity) else "–")
k3.metric("Avg. daily calories", f"{f_activity['Calories'].mean():,.0f}" if len(f_activity) else "–")
avg_sleep_hrs = (
    sleep[sleep["Id"].isin(selected_users) & sleep["SleepDay"].between(start, end)]["TotalMinutesAsleep"].mean() / 60
)
k4.metric("Avg. sleep (hrs)", f"{avg_sleep_hrs:.1f}" if pd.notna(avg_sleep_hrs) else "–")

tab_dash, tab_sql, tab_eda, tab_insights = st.tabs(
    ["🏠 Dashboard", "🗄️ SQL Insights", "🔬 Python EDA", "💡 Recommendations"]
)

# ---------------------------------------------------------------
# Tab 1: Dashboard (interactive, filtered)
# ---------------------------------------------------------------
with tab_dash:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Average steps by day of week")
        order = f_activity.groupby("DayOfWeek")["TotalSteps"].mean().reindex(WEEKDAY_ORDER)
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.barplot(x=order.index, y=order.values, ax=ax)
        ax.axhline(10000, color="crimson", linestyle="--", label="10,000-step benchmark")
        ax.set_ylabel("Average steps")
        ax.set_xlabel("")
        ax.legend()
        plt.xticks(rotation=30)
        st.pyplot(fig)

    with c2:
        st.subheader("Steps vs. Calories")
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.scatterplot(data=f_activity, x="TotalSteps", y="Calories", alpha=0.4, ax=ax)
        st.pyplot(fig)

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Hourly activity pattern")
        f_hourly = hourly_steps[hourly_steps["Id"].isin(selected_users)]
        hourly_avg = f_hourly.assign(Hour=f_hourly["ActivityHour"].dt.hour).groupby("Hour")["StepTotal"].mean()
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.lineplot(x=hourly_avg.index, y=hourly_avg.values, marker="o", ax=ax)
        ax.set_xlabel("Hour of day")
        ax.set_ylabel("Average steps")
        st.pyplot(fig)

    with c4:
        st.subheader("Steps over time (selected users)")
        daily = f_activity.groupby("ActivityDate")["TotalSteps"].mean()
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.lineplot(x=daily.index, y=daily.values, ax=ax)
        ax.set_ylabel("Average steps")
        ax.set_xlabel("")
        plt.xticks(rotation=30)
        st.pyplot(fig)

    st.subheader("Per-user summary (filtered)")
    per_user = (
        f_activity.groupby("Id")
        .agg(avg_steps=("TotalSteps", "mean"), avg_calories=("Calories", "mean"),
             avg_sedentary_min=("SedentaryMinutes", "mean"), days_logged=("TotalSteps", "size"))
        .round(0)
        .sort_values("avg_steps", ascending=False)
    )
    st.dataframe(per_user, use_container_width=True)

# ---------------------------------------------------------------
# Tab 2: SQL Insights (runs the actual queries from sql/insights.sql)
# ---------------------------------------------------------------
with tab_sql:
    st.subheader("SQL insight queries")
    st.caption("Every query below is read live from `sql/insights.sql` and executed against the SQLite database.")
    queries = parse_sql_file()
    choice = st.selectbox("Choose a query", list(queries.keys()))
    st.code(queries[choice], language="sql")
    result = pd.read_sql_query(queries[choice], conn)
    st.dataframe(result, use_container_width=True)

    # Quick chart for a couple of the numeric queries, when applicable
    if {"DayOfWeek", "avg_steps"}.issubset(result.columns):
        st.bar_chart(result.set_index("DayOfWeek")["avg_steps"])
    elif {"Hour", "avg_steps"}.issubset(result.columns):
        st.line_chart(result.set_index("Hour")["avg_steps"])
    elif {"activity_segment", "n_users"}.issubset(result.columns):
        st.bar_chart(result.set_index("activity_segment")["n_users"])

# ---------------------------------------------------------------
# Tab 3: Python EDA (pre-generated matplotlib/seaborn figures)
# ---------------------------------------------------------------
with tab_eda:
    st.subheader("Exploratory Data Analysis")
    st.caption("Generated by `eda/eda.py` (matplotlib + seaborn). Run that script again after changing the data.")
    fig_dir = BASE / "eda" / "figures"
    captions = {
        "01_steps_distribution.png": "Most users fall well short of the 10,000-step benchmark.",
        "02_steps_vs_calories.png": "Calories burned rises steadily with step count.",
        "03_activity_composition_by_weekday.png": "Sedentary minutes dominate every day, weekday or weekend.",
        "04_avg_steps_by_weekday.png": "Tuesday and Saturday are the most active days; Sunday the least.",
        "05_hourly_activity_pattern.png": "Activity peaks midday and again in the early evening.",
        "06_sleep_distribution.png": "A large share of nights fall short of the 7-hour CDC guideline.",
        "07_sleep_vs_sedentary.png": "More sleep is weakly associated with less sedentary time the same day.",
        "08_user_activity_segments.png": "Users split fairly evenly across activity segments.",
        "09_correlation_heatmap.png": "Steps and calories are strongly linked; sleep correlates less with daytime activity.",
    }
    cols = st.columns(2)
    for i, (fname, caption) in enumerate(captions.items()):
        path = fig_dir / fname
        if path.exists():
            with cols[i % 2]:
                st.image(str(path), caption=caption, use_container_width=True)

# ---------------------------------------------------------------
# Tab 4: Business recommendations
# ---------------------------------------------------------------
with tab_insights:
    st.subheader("What this means for Bellabeat's marketing strategy")
    st.markdown("""
1. **Most users aren't hitting 10,000 steps/day.** Only a minority qualify as "Active."
   Bellabeat's app/marketing can reframe goals around realistic, incremental targets
   (e.g. "add 1,000 steps") rather than a one-size-fits-all benchmark.

2. **Sedentary time dwarfs active time every single day**, including weekends.
   A "stand up / move" nudge feature, timed around the low-activity hours identified
   in the hourly pattern, directly addresses this.

3. **Sleep tracking has much lower adherence than activity tracking**, and logged
   sleep often falls short of the 7-hour guideline. This is a clear product/marketing
   opportunity: Bellabeat's Leaf and Time products already emphasize sleep -- these
   findings support leaning further into sleep-quality messaging and reminders.

4. **Weight logging adherence is by far the lowest** of the three tracked behaviors.
   Manual logging is friction; an opportunity exists for smarter integrations
   (e.g. smart-scale pairing) rather than relying on users to type in numbers.

5. **Activity has a clear daily rhythm** (rising through the morning, peaking midday
   and early evening). Push notifications and habit-building nudges timed to these
   windows -- rather than generic all-day reminders -- are more likely to land when
   users are already primed to move.
    """)
    st.caption(
        "Recommendations are illustrative, generated from this sample of 33 users over "
        "one month; they mirror the analysis approach used in the public Bellabeat case study."
    )
