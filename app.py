# app.py — LifeSync (Single‑file Streamlit App)
# Features: Login, Dashboard, Tasks+Points, Daily Progress Chart, Mood Tracker,
# AI Suggestions (rule-based), Mini Learning Quiz, Fitness Log, Local Persistence,
# Simple Leaderboard (local), and Logout. Ready for local run & GitHub deploy.

import streamlit as st
import pandas as pd
import datetime as dt
import json
import os
import random

st.set_page_config(page_title="LifeSync", page_icon="🌟", layout="wide")

# ---------------------------
# Fake user database (demo)
# ---------------------------
USERS = {
    "sameer": "1234",
    "demo": "demo"
}

# ---------------------------
# Helpers: persistence per user
# ---------------------------

def data_path(username: str) -> str:
    safe = "".join(c for c in username if c.isalnum() or c in ("_","-"))
    return f"data_{safe}.json"


def default_state(username: str):
    today = str(dt.date.today())
    return {
        "username": username,
        "points": 0,
        "tasks": [],  # {id, text, done, created}
        "progress": {},  # date -> max_points
        "mood_log": [],  # {date, mood, note}
        "fitness": [],   # {date, activity, minutes}
        "quiz_history": [],  # {date, score}
        "created_at": today,
        "updated_at": today
    }


def load_user(username: str):
    path = data_path(username)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_state(username)
    return default_state(username)


def save_user(state: dict):
    state["updated_at"] = str(dt.date.today())
    with open(data_path(state["username"]), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def bump_points(state: dict, delta: int):
    state["points"] = max(0, state.get("points", 0) + delta)
    # update daily max in progress
    today = str(dt.date.today())
    prev = state["progress"].get(today, 0)
    state["progress"][today] = max(prev, state["points"])

# ---------------------------
# Auth
# ---------------------------

def login_view():
    st.title("🔐 LifeSync Login")
    st.caption("Use demo credentials to explore: sameer/1234 or demo/demo")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in USERS and USERS[u] == p:
            st.session_state.logged_in = True
            st.session_state.username = u
            st.session_state.data = load_user(u)
            st.success("Login successful!")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")


def logout_action():
    if st.button("🔒 Logout"):
        for k in ["logged_in","username","data"]:
            if k in st.session_state:
                del st.session_state[k]
        st.experimental_rerun()

# ---------------------------
# AI Suggestions (rule-based, no external API)
# ---------------------------
MOODS = ["😊 Happy", "😓 Stressed", "😞 Sad", "😐 Neutral", "🔥 Energetic", "🧘 Calm"]


def sentiment_hint(text: str) -> str:
    text = (text or "").lower()
    neg_words = ["sad", "down", "tired", "anxious", "stress", "overwhelmed", "depressed", "cry"]
    pos_words = ["great", "good", "excited", "happy", "confident", "energized", "win"]
    score = 0
    score += sum(w in text for w in pos_words)
    score -= sum(w in text for w in neg_words)
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"


def ai_recommend(mood: str, note: str):
    # Very simple rule engine
    mood_key = (mood or "").lower()
    senti = sentiment_hint(note)
    ideas = {"tasks": [], "music": [], "learning": [], "fitness": [], "mind": []}

    if "energetic" in mood_key or senti == "positive":
        ideas["tasks"] = ["Deep work: 25 min sprint", "Clean inbox (10 emails)"]
        ideas["fitness"] = ["HIIT 15 min", "Pushups x30 + Squats x40"]
        ideas["learning"] = ["Finish 1 topic from DSA", "Watch 1 short tutorial & notes"]
        ideas["music"] = ["Focus beats playlist", "Upbeat coding mix"]
        ideas["mind"] = ["Gratitude list (3 items)"]
    elif "stressed" in mood_key or senti == "negative":
        ideas["tasks"] = ["Break tasks into tiny steps", "Do 1 smallest pending task"]
        ideas["fitness"] = ["10 min walk in fresh air"]
        ideas["learning"] = ["Micro-lesson (5 min)"]
        ideas["music"] = ["Lo-fi chill", "Nature ambience"]
        ideas["mind"] = ["4-7-8 breathing (3 rounds)", "5 min body-scan"]
    elif "sad" in mood_key:
        ideas["tasks"] = ["Text a friend", "Tidy your desk (5 min)"]
        ideas["fitness"] = ["Light stretching 8 min"]
        ideas["learning"] = ["Watch a fun explainer"]
        ideas["music"] = ["Uplifting acoustics"]
        ideas["mind"] = ["Write 1 thing you’re proud of"]
    elif "calm" in mood_key:
        ideas["tasks"] = ["Plan tomorrow (5 min)"]
        ideas["fitness"] = ["Yoga flow 10 min"]
        ideas["learning"] = ["Revise notes (10 min)"]
        ideas["music"] = ["Piano focus"]
        ideas["mind"] = ["Box breathing (2 min)"]
    else:  # neutral / default
        ideas["tasks"] = ["Top 1 priority task (25 min)"]
        ideas["fitness"] = ["Brisk walk 10 min"]
        ideas["learning"] = ["Read 3 pages"]
        ideas["music"] = ["Neutral focus playlist"]
        ideas["mind"] = ["2 min mindful pause"]

    return ideas

# ---------------------------
# UI Sections
# ---------------------------

def sidebar(state: dict):
    st.sidebar.title("🌟 LifeSync")
    st.sidebar.markdown(f"**User:** `{state['username']}`")
    st.sidebar.metric("Points", state.get("points", 0))
    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "Tasks", "Mood & AI", "Fitness", "Learning", "Leaderboard", "Settings"],
        index=0
    )
    st.sidebar.divider()
    logout_action()
    return page


# ---- Dashboard ----

def page_dashboard(state: dict):
    st.title("📊 Dashboard")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Points", state.get("points", 0))
    with c2:
        st.metric("Tasks Done", sum(1 for t in state["tasks"] if t["done"]))
    with c3:
        st.metric("Days Tracked", len(state.get("progress", {})))

    st.subheader("📈 Daily Progress")
    if state.get("progress"):
        df = (
            pd.DataFrame([
                {"date": d, "points": p} for d, p in state["progress"].items()
            ])
            .sort_values("date")
        )
        st.line_chart(df.set_index("date"))
    else:
        st.info("No progress yet — complete a task today to start your streak!")

    st.subheader("📝 Quick Add Task")
    new = st.text_input("Task text", key="quick_task")
    if st.button("Add Task") and new:
        state["tasks"].append({
            "id": random.randint(1000, 999999),
            "text": new.strip(),
            "done": False,
            "created": str(dt.date.today())
        })
        save_user(state)
        st.success("Task added!")
        st.experimental_rerun()


# ---- Tasks ----

def page_tasks(state: dict):
    st.title("✅ Tasks & Points")
    left, right = st.columns([2,1])

    with left:
        if not state["tasks"]:
            st.info("No tasks yet. Add one from Dashboard or here.")
        for t in state["tasks"]:
            cols = st.columns([0.1, 0.7, 0.2])
            with cols[0]:
                st.write("✔️" if t["done"] else "⬜")
            with cols[1]:
                st.write(f"**{t['text']}**  ")
                st.caption(f"Created: {t['created']}")
            with cols[2]:
                if not t["done"] and st.button("Complete", key=f"done_{t['id']}"):
                    t["done"] = True
                    bump_points(state, 10)
                    save_user(state)
                    st.success("+10 points")
                    st.experimental_rerun()
                if st.button("Delete", key=f"del_{t['id']}"):
                    state["tasks"] = [x for x in state["tasks"] if x["id"] != t["id"]]
                    save_user(state)
                    st.warning("Task deleted")
                    st.experimental_rerun()

    with right:
        st.subheader("Add Task")
        text = st.text_input("What to do?")
        if st.button("Add") and text:
            state["tasks"].append({
                "id": random.randint(1000, 999999),
                "text": text.strip(),
                "done": False,
                "created": str(dt.date.today())
            })
            save_user(state)
            st.success("Task added")
            st.experimental_rerun()


# ---- Mood & AI ----

def page_mood_ai(state: dict):
    st.title("🧠 Mood & AI Suggestions")
    mood = st.selectbox("How are you feeling now?", MOODS, index=3)
    note = st.text_area("Tell me a bit more (optional)")
    if st.button("Log Mood & Get Suggestions"):
        state["mood_log"].append({
            "date": str(dt.date.today()),
            "mood": mood,
            "note": note
        })
        bump_points(state, 5)  # reward check-in
        save_user(state)
        st.success("Mood logged (+5 points)")

    if st.button("Generate Suggestions"):
        ideas = ai_recommend(mood, note)
        st.subheader("🍱 Suggested Plan")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Tasks**")
            for i in ideas["tasks"]:
                st.write("•", i)
        with c2:
            st.markdown("**Fitness**")
            for i in ideas["fitness"]:
                st.write("•", i)
        with c3:
            st.markdown("**Learning**")
            for i in ideas["learning"]:
                st.write("•", i)
        st.markdown("**Music**")
        for i in ideas["music"]:
            st.write("•", i)
        st.markdown("**Mindfulness**")
        for i in ideas["mind"]:
            st.write("•", i)

    if state["mood_log"]:
        st.subheader("📜 Mood History")
        df = pd.DataFrame(state["mood_log"])  # date, mood, note
        st.dataframe(df)


# ---- Fitness ----

def page_fitness(state: dict):
    st.title("🏃 Fitness Log")
    activity = st.selectbox("Activity", ["Walk", "Run", "Cycle", "Yoga", "Strength", "Other"]) 
    minutes = st.number_input("Minutes", min_value=5, max_value=240, value=20, step=5)
    if st.button("Log Activity"):
        state["fitness"].append({
            "date": str(dt.date.today()),
            "activity": activity,
            "minutes": int(minutes)
        })
        bump_points(state, 5)
        save_user(state)
        st.success("Logged (+5 points)")

    if state["fitness"]:
        st.subheader("📅 History")
        df = pd.DataFrame(state["fitness"]).sort_values("date")
        st.dataframe(df)
        st.subheader("⏱️ Minutes per Day")
        df2 = df.groupby("date")["minutes"].sum().reset_index()
        st.bar_chart(df2.set_index("date"))


# ---- Learning (mini-quiz) ----
QUIZ = [
    {"q": "What is Big-O of binary search?", "a": ["O(n)", "O(log n)", "O(n log n)"], "c": 1},
    {"q": "Pandas is mainly used for?", "a": ["Web servers", "Data analysis", "3D rendering"], "c": 1},
    {"q": "Which creates a virtual environment?", "a": ["pip install venv", "python -m venv venv", "npm init"], "c": 1},
]


def page_learning(state: dict):
    st.title("📚 Learning — Micro Quiz")
    answers = []
    for i, item in enumerate(QUIZ, start=1):
        st.write(f"**Q{i}.** {item['q']}")
        ans = st.radio("", item["a"], key=f"quiz_{i}")
        answers.append(item["a"].index(ans))
        st.divider()
    if st.button("Submit Quiz"):
        correct = sum(1 for i, item in enumerate(QUIZ) if answers[i] == item["c"]) 
        score = int(correct / len(QUIZ) * 100)
        state["quiz_history"].append({"date": str(dt.date.today()), "score": score})
        if score >= 67:
            bump_points(state, 10)
            st.success(f"Great! Score {score}%. (+10 points)")
        else:
            st.warning(f"Score {score}%. Keep practicing!")
        save_user(state)

    if state["quiz_history"]:
        st.subheader("📈 Quiz Scores")
        df = pd.DataFrame(state["quiz_history"]).sort_values("date")
        st.line_chart(df.set_index("date"))


# ---- Leaderboard (local only) ----

def page_leaderboard(state: dict):
    st.title("🏆 Leaderboard (Local)")
    # Collect local files
    records = []
    for fname in os.listdir('.'):
        if fname.startswith('data_') and fname.endswith('.json'):
            try:
                with open(fname, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    records.append({"user": d.get("username","?"), "points": d.get("points",0)})
            except Exception:
                pass
    if records:
        df = pd.DataFrame(records).sort_values("points", ascending=False)
        st.dataframe(df)
    else:
        st.info("No local user data yet.")


# ---- Settings ----

def page_settings(state: dict):
    st.title("⚙️ Settings")
    st.write("Export or reset your local data.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Export JSON"):
            save_user(state)
            with open(data_path(state["username"]), 'r', encoding='utf-8') as f:
                st.download_button("Download data.json", f.read(), file_name=f"{state['username']}_data.json")
    with col2:
        if st.button("♻️ Reset Points (0)"):
            state["points"] = 0
            save_user(state)
            st.experimental_rerun()


# ---------------------------
# App Entrypoint
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    state = st.session_state.data
    page = sidebar(state)
    if page == "Dashboard":
        page_dashboard(state)
    elif page == "Tasks":
        page_tasks(state)
    elif page == "Mood & AI":
        page_mood_ai(state)
    elif page == "Fitness":
        page_fitness(state)
    elif page == "Learning":
        page_learning(state)
    elif page == "Leaderboard":
        page_leaderboard(state)
    elif page == "Settings":
        page_settings(state)
    save_user(state)
else:
    login_view()
