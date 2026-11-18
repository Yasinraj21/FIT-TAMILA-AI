import hashlib
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

# ============================================================
# FIT TAMILA AI — COMPLETE FITNESS MANAGEMENT SYSTEM
# Multi-user | English + Tamil | SQLite | Rule-based coach
# ============================================================

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "fit_tamila_ai.db"

st.set_page_config(page_title="FIT TAMILA AI", page_icon="💪", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
.hero {padding: 1.4rem; border-radius: 16px; background: linear-gradient(120deg,#133c35,#167d68); color:white;}
.hero h1 {color:white;}
div[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.25); padding:12px; border-radius:12px;}
</style>
""", unsafe_allow_html=True)

# --------------------------- LANGUAGE ---------------------------

TEXT = {
    "English": {
        "welcome": "Your body. Your goals. Your journey.",
        "profile": "Profile & Body Analysis", "dashboard": "Dashboard",
        "calculators": "BMI, BMR & TDEE", "goals": "Fitness Goals",
        "workouts": "Workout Planner", "nutrition": "Nutrition Planner",
        "progress": "Daily Progress", "coach": "AI Fitness Coach",
        "logout": "Log out", "name": "Full name", "age": "Age",
        "sex": "Equation setting", "height": "Height (cm)",
        "weight": "Current weight (kg)", "target": "Target weight (kg)",
        "activity": "Activity level", "goal": "Main goal", "save": "Save profile",
        "login": "Login", "register": "Create account", "username": "Username",
        "password": "Password", "confirm": "Confirm password",
    },
    "தமிழ்": {
        "welcome": "உங்கள் உடல். உங்கள் இலக்கு. உங்கள் பயணம்.",
        "profile": "சுயவிவரம் மற்றும் உடல் பகுப்பாய்வு", "dashboard": "முகப்புப் பலகை",
        "calculators": "BMI, BMR மற்றும் TDEE", "goals": "உடற்பயிற்சி இலக்குகள்",
        "workouts": "உடற்பயிற்சி திட்டம்", "nutrition": "உணவு திட்டம்",
        "progress": "தினசரி முன்னேற்றம்", "coach": "AI உடற்பயிற்சி வழிகாட்டி",
        "logout": "வெளியேறு", "name": "முழுப் பெயர்", "age": "வயது",
        "sex": "கணக்கீட்டிற்கான பாலின அமைப்பு", "height": "உயரம் (செ.மீ.)",
        "weight": "தற்போதைய எடை (கிலோ)", "target": "இலக்கு எடை (கிலோ)",
        "activity": "செயல்பாட்டு நிலை", "goal": "முக்கிய இலக்கு", "save": "சுயவிவரத்தைச் சேமி",
        "login": "உள்நுழை", "register": "கணக்கை உருவாக்கு", "username": "பயனர்பெயர்",
        "password": "கடவுச்சொல்", "confirm": "கடவுச்சொல்லை உறுதிப்படுத்து",
    },
}

# --------------------------- DATABASE ---------------------------

def connect_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with connect_db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS profiles(
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL DEFAULT '',
            age INTEGER NOT NULL DEFAULT 25,
            sex TEXT NOT NULL DEFAULT 'Male',
            height_cm REAL NOT NULL DEFAULT 170,
            current_weight REAL NOT NULL DEFAULT 70,
            target_weight REAL NOT NULL DEFAULT 65,
            activity TEXT NOT NULL DEFAULT 'Lightly active',
            goal TEXT NOT NULL DEFAULT 'Fat loss',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS progress(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entry_date TEXT NOT NULL,
            weight REAL NOT NULL,
            steps INTEGER NOT NULL DEFAULT 0,
            water_glasses INTEGER NOT NULL DEFAULT 0,
            workout_done INTEGER NOT NULL DEFAULT 0,
            calories_eaten INTEGER NOT NULL DEFAULT 0,
            protein_g REAL NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, entry_date)
        );
        CREATE TABLE IF NOT EXISTS food_entries(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entry_date TEXT NOT NULL,
            meal TEXT NOT NULL,
            food TEXT NOT NULL,
            servings REAL NOT NULL DEFAULT 1,
            calories REAL NOT NULL DEFAULT 0,
            protein_g REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS workout_entries(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entry_date TEXT NOT NULL,
            muscle_group TEXT NOT NULL,
            exercise TEXT NOT NULL,
            sets INTEGER NOT NULL DEFAULT 3,
            reps TEXT NOT NULL DEFAULT '10',
            completed INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)


init_db()

# --------------------------- CALCULATORS ---------------------------

ACTIVITY_FACTORS = {
    "Sedentary": 1.20, "Lightly active": 1.375,
    "Moderately active": 1.55, "Very active": 1.725,
    "Extra active": 1.90,
}


def calc_bmi(weight, height_cm):
    return weight / ((height_cm / 100) ** 2)


def calc_bmr(weight, height_cm, age, sex):
    # Mifflin-St Jeor estimate; sex is an equation setting.
    value = 10 * weight + 6.25 * height_cm - 5 * age
    return value + 5 if sex == "Male" else value - 161


def metrics(p):
    bmi = calc_bmi(p["current_weight"], p["height_cm"])
    bmr = calc_bmr(p["current_weight"], p["height_cm"], p["age"], p["sex"])
    tdee = bmr * ACTIVITY_FACTORS.get(p["activity"], 1.375)
    if p["goal"] == "Fat loss":
        calories = max(1200 if p["sex"] == "Female" else 1500, tdee - 300)
    elif p["goal"] == "Muscle gain":
        calories = tdee + 200
    else:
        calories = tdee
    protein = p["current_weight"] * (1.6 if p["goal"] == "Muscle gain" else 1.4)
    category = "Underweight" if bmi < 18.5 else "Healthy weight range" if bmi < 25 else "Overweight" if bmi < 30 else "Obesity range"
    return bmi, bmr, tdee, calories, protein, category


def get_profile(uid):
    with connect_db() as c:
        return c.execute("SELECT * FROM profiles WHERE user_id=?", (uid,)).fetchone()


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# --------------------------- LOGIN / REGISTER ---------------------------

def auth_page(language):
    t = TEXT[language]
    st.markdown(f'<div class="hero"><h1>💪 FIT TAMILA AI</h1><p>{t["welcome"]}</p></div>', unsafe_allow_html=True)
    login, register = st.tabs([t["login"], t["register"]])
    with login:
        with st.form("login_form"):
            username = st.text_input(t["username"]).strip()
            password = st.text_input(t["password"], type="password")
            submit = st.form_submit_button(t["login"], use_container_width=True)
        if submit:
            with connect_db() as c:
                user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            if user and user["password_hash"] == hash_password(password):
                st.session_state["uid"] = user["id"]
                st.session_state["username"] = user["username"]
                st.rerun()
            else:
                st.error("Invalid username or password.")
    with register:
        with st.form("register_form"):
            username = st.text_input(t["username"], key="new_username").strip()
            password = st.text_input(t["password"], type="password", key="new_password")
            confirm = st.text_input(t["confirm"], type="password")
            submit = st.form_submit_button(t["register"], use_container_width=True)
        if submit:
            if len(username) < 3:
                st.warning("Username must contain at least 3 characters.")
            elif len(password) < 8:
                st.warning("Use a password with at least 8 characters.")
            elif password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    with connect_db() as c:
                        cur = c.execute("INSERT INTO users(username,password_hash) VALUES(?,?)", (username, hash_password(password)))
                        uid = cur.lastrowid
                    st.session_state["uid"] = uid
                    st.session_state["username"] = username
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("That username already exists.")


# --------------------------- PROFILE ---------------------------

def profile_page(uid, language, profile):
    t = TEXT[language]
    st.header(f"👤 {t['profile']}")
    with st.form("profile_form"):
        name = st.text_input(t["name"], value=profile["full_name"] if profile else "")
        a, b = st.columns(2)
        with a:
            age = st.number_input(t["age"], 18, 100, int(profile["age"]) if profile else 25)
            sex = st.selectbox(t["sex"], ["Male", "Female"], index=["Male", "Female"].index(profile["sex"]) if profile else 0)
            height = st.number_input(t["height"], 100.0, 230.0, float(profile["height_cm"]) if profile else 170.0, 0.5)
            weight = st.number_input(t["weight"], 25.0, 300.0, float(profile["current_weight"]) if profile else 70.0, 0.1)
        with b:
            target = st.number_input(t["target"], 25.0, 300.0, float(profile["target_weight"]) if profile else 65.0, 0.1)
            activity_list = list(ACTIVITY_FACTORS)
            activity = st.selectbox(t["activity"], activity_list, index=activity_list.index(profile["activity"]) if profile else 1)
            goal_list = ["Fat loss", "Muscle gain", "Maintain weight", "General fitness"]
            goal = st.selectbox(t["goal"], goal_list, index=goal_list.index(profile["goal"]) if profile else 0)
        save = st.form_submit_button(t["save"], use_container_width=True)
    if save:
        with connect_db() as c:
            c.execute("""
            INSERT INTO profiles(user_id,full_name,age,sex,height_cm,current_weight,target_weight,activity,goal)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
            full_name=excluded.full_name,age=excluded.age,sex=excluded.sex,
            height_cm=excluded.height_cm,current_weight=excluded.current_weight,
            target_weight=excluded.target_weight,activity=excluded.activity,goal=excluded.goal,
            updated_at=CURRENT_TIMESTAMP
            """, (uid, name.strip(), int(age), sex, float(height), float(weight), float(target), activity, goal))
        st.success("Profile saved.")
        st.rerun()
    p = get_profile(uid)
    if p:
        bmi, bmr, tdee, cal, protein, cat = metrics(p)
        st.subheader("Body analysis / உடல் பகுப்பாய்வு")
        x1, x2, x3, x4 = st.columns(4)
        x1.metric("BMI", f"{bmi:.1f}", cat)
        x2.metric("BMR", f"{bmr:.0f} kcal/day")
        x3.metric("TDEE", f"{tdee:.0f} kcal/day")
        x4.metric("Protein estimate", f"{protein:.0f} g/day")


# --------------------------- DASHBOARD ---------------------------

def dashboard_page(profile, language):
    t = TEXT[language]
    st.header(f"🏠 {t['dashboard']}")
    if not profile:
        st.warning("Complete your profile first in Profile & Body Analysis.")
        return
    bmi, bmr, tdee, cal, protein, cat = metrics(profile)
    st.markdown(f'<div class="hero"><h1>வணக்கம், {profile["full_name"] or st.session_state["username"]}!</h1><p>{t["welcome"]}</p></div>', unsafe_allow_html=True)
    a, b, c, d = st.columns(4)
    a.metric("BMI", f"{bmi:.1f}", cat)
    b.metric("BMR", f"{bmr:.0f} kcal/day")
    c.metric("TDEE", f"{tdee:.0f} kcal/day")
    d.metric("Calorie target (estimate)", f"{cal:.0f} kcal/day")
    st.write(f"**Goal:** {profile['goal']} | **Target weight:** {profile['target_weight']:.1f} kg")
    st.info(f"Estimated protein starting point: {protein:.0f} g/day. Individual needs vary.")
    st.caption("BMI is a screening tool, not a diagnosis. Calorie equations are estimates.")


# --------------------------- BMI / BMR / TDEE ---------------------------

def calculator_page(profile):
    st.header("📊 BMI, BMR & TDEE Calculator")
    if not profile:
        st.warning("Save your profile first.")
        return
    bmi, bmr, tdee, cal, protein, cat = metrics(profile)
    a, b, c = st.columns(3)
    a.metric("BMI — Body Mass Index", f"{bmi:.1f}", cat)
    b.metric("BMR — Basal Metabolic Rate", f"{bmr:.0f} kcal/day")
    c.metric("TDEE — Total Daily Energy Expenditure", f"{tdee:.0f} kcal/day")
    st.subheader("What do these values mean?")
    st.markdown("""
    - **BMI (Body Mass Index):** weight relative to height; a screening tool.
    - **BMR (Basal Metabolic Rate):** estimated energy used at rest.
    - **TDEE (Total Daily Energy Expenditure):** estimated energy used in a full day, including activity.
    """)
    a, b = st.columns(2)
    a.metric("Estimated calorie starting point", f"{cal:.0f} kcal/day")
    b.metric("Protein estimate", f"{protein:.0f} g/day")
    st.caption("These are estimates, not medical prescriptions. Avoid aggressive calorie restriction.")


# --------------------------- FITNESS GOALS ---------------------------

def goals_page(profile):
    st.header("🎯 Fitness Goals")
    if not profile:
        st.warning("Save your profile first.")
        return
    diff = float(profile["current_weight"]) - float(profile["target_weight"])
    st.metric("Weight difference to target", f"{abs(diff):.1f} kg", "to lose" if diff > 0 else "to gain" if diff < 0 else "target reached")
    st.write(f"**Current goal:** {profile['goal']}")
    if diff > 0:
        st.info("For fat loss, aim for sustainable habits, balanced meals, resistance training, and a modest calorie deficit.")
    elif diff < 0:
        st.info("For weight gain, consider adequate meals, protein, progressive strength training, and recovery.")
    else:
        st.success("Your current weight matches your target. Focus on fitness, strength, and healthy routines.")


# --------------------------- WORKOUT LIBRARY ---------------------------

WORKOUTS = {
    "Chest": [
        ("Push-ups", 3, "6–12", "Keep your body straight, lower your chest under control, then push up."),
        ("Dumbbell bench press", 3, "8–12", "Lie on a bench, lower dumbbells toward chest, then press up. Use a spotter for heavy lifts."),
        ("Incline dumbbell press", 3, "8–12", "Press dumbbells from upper-chest level on an incline bench."),
        ("Chest fly", 2, "10–12", "Use light weights and avoid overstretching.")
    ],
    "Back & lats": [
        ("Lat pulldown", 3, "8–12", "Pull the bar toward your upper chest without swinging. Avoid behind-the-neck pulls."),
        ("Seated cable row", 3, "8–12", "Sit tall and pull the handle toward your torso."),
        ("One-arm dumbbell row", 3, "8–12 each side", "Support yourself on a bench and pull the dumbbell toward your hip."),
        ("Face pull", 2, "12–15", "Pull the cable toward face level with controlled movement.")
    ],
    "Shoulders & traps": [
        ("Seated shoulder press", 3, "8–12", "Press overhead without excessive lower-back arching."),
        ("Lateral raise", 3, "10–15", "Raise light dumbbells sideways to about shoulder height."),
        ("Rear-delt fly", 2, "12–15", "Hinge forward and raise weights outward."),
        ("Dumbbell shrug", 3, "10–15", "Raise shoulders toward ears, pause, then lower.")
    ],
    "Biceps": [
        ("Dumbbell curl", 3, "8–12", "Keep elbows close to sides and avoid swinging."),
        ("Hammer curl", 3, "10–12", "Keep palms facing inward during the curl."),
        ("Preacher curl", 2, "10–12", "Move comfortably and lower slowly.")
    ],
    "Triceps": [
        ("Cable triceps pushdown", 3, "10–12", "Keep elbows close to sides and extend arms down."),
        ("Overhead triceps extension", 2, "10–12", "Use manageable weight and keep elbows controlled."),
        ("Close-grip wall push-up", 2, "8–12", "Keep your body aligned and elbows comfortable.")
    ],
    "Legs & glutes": [
        ("Bodyweight squat", 3, "8–12", "Keep feet stable, brace your torso, and squat to a comfortable depth."),
        ("Leg press", 3, "10–12", "Keep your back supported and avoid forcefully locking knees."),
        ("Leg curl", 3, "10–12", "Curl smoothly and control the return."),
        ("Calf raise", 3, "12–15", "Rise onto toes, pause, and lower slowly."),
        ("Glute bridge", 3, "10–15", "Raise hips by squeezing glutes without over-arching.")
    ],
    "Abs & core": [
        ("Plank", 3, "15–40 seconds", "Keep body aligned and breathe normally."),
        ("Dead bug", 3, "8–10 each side", "Move opposite arm and leg while keeping torso controlled."),
        ("Reverse crunch", 2, "10–12", "Curl pelvis gently upward without swinging.")
    ],
    "Cardio": [
        ("Brisk walking", 1, "15–30 minutes", "Walk at a pace that raises breathing while you can still talk."),
        ("Stationary cycling", 1, "10–20 minutes", "Use comfortable resistance and pace."),
        ("Treadmill walking", 1, "10–20 minutes", "Start slowly and increase speed gradually.")
    ],
    "Full body (beginner)": [
        ("Chair or bodyweight squat", 2, "8–12", "Squat to a comfortable depth or toward a chair."),
        ("Wall push-up", 2, "8–12", "Keep your body straight and move toward the wall."),
        ("Dumbbell row", 2, "8–12 each side", "Pull a manageable dumbbell toward your hip."),
        ("Brisk walk", 1, "10–20 minutes", "Choose a comfortable pace.")
    ],
}
WEEK_SPLIT = {
    "Monday": "Chest", "Tuesday": "Back & lats", "Wednesday": "Legs & glutes",
    "Thursday": "Shoulders & traps", "Friday": "Biceps", "Saturday": "Triceps",
    "Sunday": "Recovery",
}


def workout_page(profile, uid):
    st.header("🏋️ Workout Planner")
    if not profile:
        st.warning("Save your profile first.")
        return
    level = st.selectbox("Training level", ["Beginner", "Intermediate", "Advanced"])
    day = st.selectbox("Choose day", list(WEEK_SPLIT), index=date.today().weekday())
    default_group = WEEK_SPLIT[day]
    options = list(WORKOUTS)
    group = st.selectbox("Muscle group", options, index=options.index(default_group) if default_group in options else 0)
    if group == "Full body (beginner)" or level == "Beginner":
        st.info("Start with manageable resistance. You may begin with 1–2 sets while learning technique.")
    if day == "Sunday":
        st.info("Recovery day: optional easy walk, gentle mobility, hydration, and sleep.")
    for name, sets, reps, instructions in WORKOUTS[group]:
        with st.expander(name):
            st.write(f"**Sets:** {sets} | **Repetitions/duration:** {reps}")
            st.write(f"**How to do it:** {instructions}")
            st.write("Rest as needed, often about 60–120 seconds between strength sets.")
            if st.button(f"Log {name}", key=f"log_{group}_{name}"):
                with connect_db() as c:
                    c.execute("INSERT INTO workout_entries(user_id,entry_date,muscle_group,exercise,sets,reps,completed) VALUES(?,?,?,?,?,?,1)",
                              (uid, date.today().isoformat(), group, name, sets, reps))
                st.success(f"Logged {name}.")
    st.caption("General education only. Stop if you experience sharp pain, dizziness, or unusual breathlessness.")


# --------------------------- NUTRITION PLANNER ---------------------------

FOODS = {
    "Idli (2 medium)": (140, 4), "Sambar (1 cup)": (120, 6),
    "Plain dosa (1 medium)": (170, 4), "Chapati (1 medium)": (120, 3),
    "Cooked rice (1 cup)": (205, 4), "Boiled egg (1)": (78, 6),
    "Cooked chicken (100 g)": (165, 31), "Curd (100 g)": (60, 3.5),
    "Cooked chickpeas (100 g)": (164, 8.9), "Cooked rajma (100 g)": (127, 8.7),
    "Oats (40 g dry)": (152, 5), "Banana (1 medium)": (105, 1.3),
    "Milk (250 ml)": (125, 8), "Paneer (100 g)": (265, 18),
    "Mixed vegetables (1 cup)": (80, 3), "Peanuts (20 g)": (115, 5),
}


def nutrition_page(profile, uid):
    st.header("🥗 Nutrition Planner — Tamil Nadu Foods")
    if not profile:
        st.warning("Save your profile first.")
        return
    _, _, _, target_cal, target_protein, _ = metrics(profile)
    a, b = st.columns(2)
    a.metric("Estimated calorie target", f"{target_cal:.0f} kcal/day")
    b.metric("Estimated protein starting point", f"{target_protein:.0f} g/day")
    st.caption("Food nutrition values are approximate; recipes, brands, oil, and portion sizes change the totals.")
    with st.form("food_form", clear_on_submit=True):
        meal = st.selectbox("Meal", ["Breakfast", "Lunch", "Dinner", "Snack"])
        food = st.selectbox("Food / portion", list(FOODS))
        servings = st.number_input("Number of portions", 0.25, 10.0, 1.0, 0.25)
        submit = st.form_submit_button("Add to today's food diary")
    if submit:
        kcal, protein = FOODS[food]
        with connect_db() as c:
            c.execute("INSERT INTO food_entries(user_id,entry_date,meal,food,servings,calories,protein_g) VALUES(?,?,?,?,?,?,?)",
                      (uid, date.today().isoformat(), meal, food, servings, kcal * servings, protein * servings))
        st.success("Food added.")
        st.rerun()
    with connect_db() as c:
        rows = c.execute("SELECT meal,food,servings,calories,protein_g FROM food_entries WHERE user_id=? AND entry_date=? ORDER BY id DESC",
                         (uid, date.today().isoformat())).fetchall()
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        st.dataframe(df, use_container_width=True)
        x, y = st.columns(2)
        x.metric("Recorded calories today", f"{df['calories'].sum():.0f} kcal")
        y.metric("Recorded protein today", f"{df['protein_g'].sum():.1f} g")
    else:
        st.info("No food recorded today. Add a meal above.")
    st.subheader("Simple meal ideas")
    st.markdown("""
    - **Breakfast:** idli with sambar or dosa with sambar.
    - **Lunch:** rice, dal/rajma, vegetables and curd; add eggs or chicken if preferred.
    - **Dinner:** chapati with dal or vegetables plus a protein source.
    - **Snack:** fruit, curd, milk or roasted chickpeas.
    """)


# --------------------------- DAILY PROGRESS ---------------------------

def progress_page(profile, uid):
    st.header("📈 Daily Progress")
    if not profile:
        st.warning("Save your profile first.")
        return
    today = date.today().isoformat()
    with connect_db() as c:
        existing = c.execute("SELECT * FROM progress WHERE user_id=? AND entry_date=?", (uid, today)).fetchone()
    with st.form("progress_form"):
        entry_date = st.date_input("Date", value=date.today())
        weight = st.number_input("Weight (kg)", 25.0, 300.0, float(existing["weight"]) if existing else float(profile["current_weight"]), 0.1)
        steps = st.number_input("Steps today", 0, 100000, int(existing["steps"]) if existing else 0, 500)
        water = st.number_input("Glasses of water", 0, 40, int(existing["water_glasses"]) if existing else 0)
        workout = st.checkbox("Completed workout", value=bool(existing["workout_done"]) if existing else False)
        calories = st.number_input("Calories eaten (optional)", 0, 10000, int(existing["calories_eaten"]) if existing else 0, 50)
        protein = st.number_input("Protein eaten (g, optional)", 0.0, 500.0, float(existing["protein_g"]) if existing else 0.0, 5.0)
        notes = st.text_area("Notes", value=existing["notes"] if existing else "")
        submit = st.form_submit_button("Save daily progress", use_container_width=True)
    if submit:
        with connect_db() as c:
            c.execute("""
            INSERT INTO progress(user_id,entry_date,weight,steps,water_glasses,workout_done,calories_eaten,protein_g,notes)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id,entry_date) DO UPDATE SET
            weight=excluded.weight,steps=excluded.steps,water_glasses=excluded.water_glasses,
            workout_done=excluded.workout_done,calories_eaten=excluded.calories_eaten,
            protein_g=excluded.protein_g,notes=excluded.notes
            """, (uid, entry_date.isoformat(), float(weight), int(steps), int(water), int(workout), int(calories), float(protein), notes.strip()))
            c.execute("UPDATE profiles SET current_weight=?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?", (float(weight), uid))
        st.success("Progress saved.")
        st.rerun()
    with connect_db() as c:
        rows = c.execute("SELECT entry_date,weight,steps,water_glasses,workout_done,calories_eaten,protein_g,notes FROM progress WHERE user_id=? ORDER BY entry_date", (uid,)).fetchall()
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        st.subheader("Weight trend")
        st.line_chart(df.set_index("entry_date")["weight"])
        st.dataframe(df.sort_values("entry_date", ascending=False), use_container_width=True)
        st.metric("Change from first to latest record", f"{float(df.iloc[-1]['weight']) - float(df.iloc[0]['weight']):+.1f} kg")
    else:
        st.info("No progress records yet. Save your first entry above.")


# --------------------------- RULE-BASED AI FITNESS COACH ---------------------------

def coach_page(profile):
    st.header("🤖 FIT TAMILA AI — Fitness Coach")
    st.write("This built-in coach works without an API key. It uses predefined guidance, not a generative LLM.")
    question = st.selectbox("What do you need help with?", [
        "How can I lose fat sustainably?", "How can I gain muscle?",
        "How much protein should I eat?", "How should I start exercising?",
        "What should I eat before or after a workout?",
        "How can I build a walking habit?", "How can I stay consistent?"
    ])
    if st.button("Ask FIT TAMILA AI"):
        if not profile:
            st.warning("Complete your profile first.")
            return
        _, _, tdee, cal, protein, _ = metrics(profile)
        answers = {
            "How can I lose fat sustainably?": f"Estimated maintenance is about {tdee:.0f} kcal/day and the app's illustrative starting target is {cal:.0f} kcal/day. Focus on sustainable portions, protein, vegetables, sleep and strength training. Review trends over weeks.",
            "How can I gain muscle?": f"Train consistently, progress gradually, eat enough energy and protein, and recover. Your general protein estimate is {protein:.0f} g/day; individual needs vary.",
            "How much protein should I eat?": f"A general starting estimate in this app is {protein:.0f} g/day. Sources include eggs, milk, curd, lentils, chickpeas, paneer, fish and chicken. Ask a clinician if you have kidney disease or a medically restricted diet.",
            "How should I start exercising?": "Start with comfortable walking and 2–3 light strength sessions weekly. Learn technique, increase gradually, and take recovery days.",
            "What should I eat before or after a workout?": "Before training, a familiar snack such as banana, oats or idli may suit you. After training, choose a balanced meal with protein and carbohydrates, such as eggs with dosa or chicken with rice.",
            "How can I build a walking habit?": "Start from your current step average and add a manageable amount. Short walks after meals can help. 10,000 steps is optional, not a requirement for everyone.",
            "How can I stay consistent?": "Set a small weekly target, schedule workouts, track progress, and prioritize consistency over perfection. If you miss a day, resume your routine."
        }
        st.success(answers[question])
        st.caption("Educational guidance only; not medical advice.")


# --------------------------- MAIN NAVIGATION ---------------------------

def main():
    st.sidebar.title("💪 FIT TAMILA AI")
    language = st.sidebar.selectbox("Language / மொழி", ["English", "தமிழ்"])
    st.sidebar.caption("Tamil Nadu foods • Practical fitness • Daily progress")

    if "uid" not in st.session_state:
        auth_page(language)
        return

    uid = int(st.session_state["uid"])
    profile = get_profile(uid)
    st.sidebar.write(f"👋 {st.session_state.get('username', 'User')}")
    t = TEXT[language]
    pages = [t["dashboard"], t["profile"], t["calculators"], t["goals"], t["workouts"], t["nutrition"], t["progress"], t["coach"]]
    page = st.sidebar.radio("Navigation / வழிசெலுத்தல்", pages)

    if st.sidebar.button(t["logout"], use_container_width=True):
        st.session_state.pop("uid", None)
        st.session_state.pop("username", None)
        st.rerun()

    if page == t["dashboard"]:
        dashboard_page(profile, language)
    elif page == t["profile"]:
        profile_page(uid, language, profile)
    elif page == t["calculators"]:
        calculator_page(profile)
    elif page == t["goals"]:
        goals_page(profile)
    elif page == t["workouts"]:
        workout_page(profile, uid)
    elif page == t["nutrition"]:
        nutrition_page(profile, uid)
    elif page == t["progress"]:
        progress_page(profile, uid)
    elif page == t["coach"]:
        coach_page(profile)


if __name__ == "__main__":
    main()
