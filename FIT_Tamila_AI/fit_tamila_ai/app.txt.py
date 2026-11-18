import streamlit as st
import sqlite3, hashlib
from pathlib import Path
from datetime import date, datetime
import pandas as pd
import plotly.express as px

DB = Path(__file__).with_name("fit_tamila_ai.db")
st.set_page_config(page_title="FIT Tamila AI", page_icon="💪", layout="wide")

# Bilingual UI labels (English / Tamil)
LANG = st.sidebar.selectbox("Language / மொழி", ["English", "தமிழ்"])
TA = LANG == "தமிழ்"
def tr(en, ta): return ta if TA else en

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

with connect() as c:
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, name TEXT);
    CREATE TABLE IF NOT EXISTS profiles(user_id INTEGER PRIMARY KEY, dob TEXT, sex TEXT, height REAL, weight REAL,
      target_weight REAL, goal TEXT, activity TEXT, level TEXT, diet TEXT, place TEXT, steps_target INTEGER);
    CREATE TABLE IF NOT EXISTS food(user_id INTEGER, day TEXT, item TEXT, servings REAL, kcal REAL, protein REAL);
    CREATE TABLE IF NOT EXISTS progress(user_id INTEGER, day TEXT, weight REAL, steps INTEGER, water REAL, sleep REAL,
      workout INTEGER, notes TEXT, PRIMARY KEY(user_id,day));
    """)

FOODS = {
 "Idli (1 medium)":(58,2.0), "Dosa (1 medium, estimated)":(160,4.0),
 "Chapati (1 medium)":(120,3.5), "Cooked rice (1 cup)":(205,4.3),
 "Sambar (1 cup)":(100,5.0), "Rasam (1 cup)":(45,1.5),
 "Curd (100 g)":(61,3.5), "Boiled egg (1)":(78,6.3),
 "Cooked chicken (100 g)":(165,31.0), "Fish (100 g, estimated)":(160,25.0),
 "Boiled chickpeas (100 g)":(164,8.9), "Sundal (100 g, estimated)":(180,8.0),
 "Banana (1 medium)":(105,1.3), "Milk (250 ml)":(125,8.0),
 "Paneer (100 g)":(265,18.0), "Vegetable poriyal (100 g, estimated)":(90,2.5),
 "Oats (40 g dry)":(150,5.0), "Peanuts (15 g)":(85,3.8)
}
ACTIVITY = {"Sedentary":1.2,"Lightly active":1.375,"Moderately active":1.55,"Very active":1.725}
SPLIT = {
"Monday — Chest & Triceps":[("Machine chest press / push-up","Chest","3 × 8–12"),("Incline press","Chest","2–3 × 8–12"),("Triceps pushdown","Triceps","2–3 × 10–15")],
"Tuesday — Back & Biceps":[("Lat pulldown / band pulldown","Lats","3 × 8–12"),("Seated row","Back","3 × 8–12"),("Dumbbell curl","Biceps","2–3 × 10–15")],
"Wednesday — Legs & Core":[("Chair/goblet squat","Legs","3 × 8–12"),("Leg press / step-up","Legs","2–3 × 10–12"),("Dead bug","Core","2 × 8–12")],
"Thursday — Shoulders & Traps":[("Shoulder press","Shoulders","2–3 × 8–12"),("Lateral raise","Shoulders","2–3 × 12–15"),("Dumbbell shrug","Traps","2 × 10–15")],
"Friday — Full Body":[("Squat variation","Legs","2–3 × 8–12"),("Push-up / chest press","Chest","2–3 × 8–12"),("Row variation","Back","2–3 × 8–12")],
"Saturday — Cardio & Mobility":[("Brisk walk / cycle","Cardio","15–30 min"),("Gentle mobility","Mobility","5–10 min")],
"Sunday — Recovery":[("Rest or easy walk","Recovery","Comfortable pace")]
}

def password_hash(p): return hashlib.sha256(p.encode()).hexdigest()
def age(dob):
    d=date.fromisoformat(dob); t=date.today()
    return t.year-d.year-((t.month,t.day)<(d.month,d.day))
def metrics(p):
    a=age(p["dob"]); w=float(p["weight"]); h=float(p["height"])
    bmi=w/((h/100)**2)
    bmr=10*w+6.25*h-5*a+(5 if p["sex"]=="Male" else -161)
    tdee=bmr*ACTIVITY[p["activity"]]
    if p["goal"]=="Lose weight": target=tdee-min(500,max(200,tdee*.15))
    elif p["goal"]=="Gain weight / muscle": target=tdee+min(300,max(150,tdee*.08))
    else: target=tdee
    target=max(1500 if p["sex"]=="Male" else 1200,target)
    return {"age":a,"bmi":bmi,"bmr":bmr,"tdee":tdee,"target":target}

if "uid" not in st.session_state: st.session_state.uid=None
st.sidebar.title("💪 FIT Tamila AI")
st.sidebar.caption(tr("Your body. Your food. Your journey.","உங்கள் உடல். உங்கள் உணவு. உங்கள் பயணம்."))

# Authentication: separate profiles on this computer; prototype security only.
if st.session_state.uid is None:
    st.title("💪 FIT Tamila AI")
    st.subheader(tr("Tamil Nadu Fitness & Nutrition Companion","தமிழ்நாடு உடற்பயிற்சி மற்றும் உணவு வழிகாட்டி"))
    a,b=st.tabs([tr("Sign in","உள்நுழைக"),tr("Create account","கணக்கு உருவாக்கு")])
    with a:
        u=st.text_input(tr("Username","பயனர் பெயர்"),key="login_u")
        p=st.text_input(tr("Password","கடவுச்சொல்"),type="password",key="login_p")
        if st.button(tr("Sign in","உள்நுழைக")):
            with connect() as c: row=c.execute("SELECT * FROM users WHERE username=?",(u.strip(),)).fetchone()
            if row and row["password_hash"]==password_hash(p):
                st.session_state.uid=row["id"]; st.session_state.name=row["name"]; st.rerun()
            else: st.error(tr("Incorrect username or password.","பயனர் பெயர் அல்லது கடவுச்சொல் தவறு."))
    with b:
        name=st.text_input(tr("Full name","முழுப் பெயர்"),key="reg_n")
        u=st.text_input(tr("Username","பயனர் பெயர்"),key="reg_u")
        p=st.text_input(tr("Password (6+ characters)","கடவுச்சொல் (குறைந்தது 6 எழுத்துகள்)"),type="password",key="reg_p")
        if st.button(tr("Create account","கணக்கு உருவாக்கு")):
            if not name.strip() or not u.strip() or len(p)<6: st.error("Enter a name/username and a password of at least 6 characters.")
            else:
                try:
                    with connect() as c: cur=c.execute("INSERT INTO users(username,password_hash,name) VALUES(?,?,?)",(u.strip(),password_hash(p),name.strip()))
                    st.session_state.uid=cur.lastrowid; st.session_state.name=name.strip(); st.rerun()
                except sqlite3.IntegrityError: st.error("Username already exists.")
    st.info("Local prototype: accounts and records are stored in a SQLite file on this computer.")
    st.stop()

uid=st.session_state.uid
with connect() as c:
    p=c.execute("SELECT * FROM profiles WHERE user_id=?",(uid,)).fetchone()
profile=dict(p) if p else None
pages=[tr("Dashboard","முகப்பு"),tr("Profile & body analysis","சுயவிவரம் மற்றும் உடல் பகுப்பாய்வு"),
       tr("Food diary","உணவு பதிவு"),tr("Workout planner","உடற்பயிற்சி திட்டம்"),
       tr("Daily progress","தினசரி முன்னேற்றம்"),tr("AI fitness coach","AI உடற்பயிற்சி ஆலோசகர்")]
page=st.sidebar.radio(tr("Navigation","பக்கங்கள்"),pages)
if st.sidebar.button(tr("Log out","வெளியேறு")):
    st.session_state.uid=None; st.rerun()

if page==pages[1]:
    st.title(tr("Profile & body analysis","சுயவிவரம் மற்றும் உடல் பகுப்பாய்வு"))
    defaults=profile or {}
    with st.form("profile"):
        dob=st.date_input(tr("Date of birth","பிறந்த தேதி"),value=date.fromisoformat(defaults.get("dob","2000-01-01")),max_value=date.today())
        sex=st.selectbox(tr("Sex used for equation","கணக்கீட்டிற்கான பாலினம்"),["Male","Female"],index=["Male","Female"].index(defaults.get("sex","Male")))
        col1,col2=st.columns(2)
        with col1:
            height=st.number_input(tr("Height (cm)","உயரம் (செ.மீ.)"),100.0,230.0,float(defaults.get("height",170.0)),step=.5)
            weight=st.number_input(tr("Current weight (kg)","தற்போதைய எடை (கி.கி.)"),25.0,300.0,float(defaults.get("weight",70.0)),step=.1)
            target_weight=st.number_input(tr("Goal weight (kg)","இலக்கு எடை (கி.கி.)"),25.0,300.0,float(defaults.get("target_weight",65.0)),step=.1)
        with col2:
            goals=["Lose weight","Gain weight / muscle","Maintain weight"]
            goal=st.selectbox(tr("Fitness goal","உடற்பயிற்சி இலக்கு"),goals,index=goals.index(defaults.get("goal","Lose weight")))
            acts=list(ACTIVITY)
            activity=st.selectbox(tr("Activity level","செயல்பாட்டு நிலை"),acts,index=acts.index(defaults.get("activity","Lightly active")))
            levels=["Beginner","Intermediate","Advanced"]
            level=st.selectbox(tr("Experience","அனுபவம்"),levels,index=levels.index(defaults.get("level","Beginner")))
            diets=["Vegetarian","Non-vegetarian","Either"]
            diet=st.selectbox(tr("Food preference","உணவு விருப்பம்"),diets,index=diets.index(defaults.get("diet","Either")))
            places=["Gym","Home"]
            place=st.selectbox(tr("Workout location","உடற்பயிற்சி இடம்"),places,index=places.index(defaults.get("place","Gym")))
        steps_target=st.number_input(tr("Daily step target","தினசரி நடை இலக்கு"),1000,30000,int(defaults.get("steps_target",10000)),step=500)
        save=st.form_submit_button(tr("Save profile","விவரங்களைச் சேமி"),use_container_width=True)
    if save:
        if age(dob.isoformat())<18:
            st.warning("This prototype's calorie formulas are intended for adults. Please consult a qualified professional for anyone under 18.")
        with connect() as c:
            c.execute("""INSERT INTO profiles VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET dob=excluded.dob,sex=excluded.sex,height=excluded.height,
            weight=excluded.weight,target_weight=excluded.target_weight,goal=excluded.goal,activity=excluded.activity,
            level=excluded.level,diet=excluded.diet,place=excluded.place,steps_target=excluded.steps_target""",
            (uid,dob.isoformat(),sex,height,weight,target_weight,goal,activity,level,diet,place,int(steps_target)))
        st.success("Profile saved.")
        st.rerun()
    st.warning("BMI, BMR, calorie and protein values are estimates, not medical advice. Users with medical conditions, pregnancy, eating-disorder history, or special dietary needs should consult a qualified professional.")

else:
    if not profile:
        st.title("💪 FIT Tamila AI")
        st.warning(tr("Please complete your profile first.","முதலில் சுயவிவரத்தை நிரப்பவும்."))
        st.stop()
    m=metrics(profile); today=date.today().isoformat()
    with connect() as c:
        foods = pd.read_sql_query(
    "SELECT * FROM food WHERE user_id=? AND day=?",
    c,
    params=(uid, today)
)
        hist = pd.read_sql_query(
    "SELECT * FROM progress WHERE user_id=? ORDER BY day",
    c,
    params=(uid,)
)
    kcal=float(foods["kcal"].sum()) if not foods.empty else 0
    protein=float(foods["protein"].sum()) if not foods.empty else 0

    if page==pages[0]:
        st.title("💪 FIT Tamila AI")
        st.subheader(f"{tr('Welcome','வரவேற்கிறோம்')}, {st.session_state.get('name','User')}!")
        c1,c2,c3,c4=st.columns(4)
        c1.metric("BMI",f"{m['bmi']:.1f}"); c2.metric("Estimated BMR",f"{m['bmr']:.0f} kcal")
        c3.metric("Estimated TDEE",f"{m['tdee']:.0f} kcal"); c4.metric("Daily calorie target",f"{m['target']:.0f} kcal")
        st.progress(min(kcal/m["target"],1.0))
        st.write(f"**Food logged today:** {kcal:.0f} / {m['target']:.0f} kcal · **Protein logged:** {protein:.1f} g")
        if not hist.empty:
            last=hist.iloc[-1]
            a,b,d=st.columns(3); a.metric("Latest weight",f"{last['weight']:.1f} kg"); b.metric("Steps",f"{int(last['steps']):,}"); d.metric("Workout","Done" if last["workout"] else "Not marked")
        st.info("Food values are approximate. Weight changes include water and digestion—not only fat or muscle.")
    elif page==pages[2]:
        st.title("🍛 "+tr("Tamil food diary","தமிழ் உணவு பதிவு"))
        st.caption("Per-serving estimates only. Actual calories vary with size, recipe, oil, and ingredients.")
        with st.form("food_add"):
            day=st.date_input("Date",date.today())
            item=st.selectbox("Food",list(FOODS))
            servings=st.number_input("Servings",.25,20.0,1.0,step=.25)
            st.write(f"Estimated: **{FOODS[item][0]*servings:.0f} kcal** · **{FOODS[item][1]*servings:.1f} g protein**")
            add=st.form_submit_button("Add food")
        if add:
            with connect() as c: c.execute("INSERT INTO food VALUES(?,?,?,?,?,?)",(uid,day.isoformat(),item,servings,FOODS[item][0]*servings,FOODS[item][1]*servings))
            st.success("Food saved."); st.rerun()
        with connect() as c: df = pd.read_sql_query(
    "SELECT day,item,servings,kcal,protein FROM food WHERE user_id=? ORDER BY day DESC",
    c,
    params=(uid,)
)
        if not df.empty:
            st.dataframe(df,use_container_width=True,hide_index=True)
            st.metric("Total calories recorded",f"{df['kcal'].sum():.0f} kcal")
    elif page==pages[3]:
        st.title("🏋️ "+tr("Workout planner","உடற்பயிற்சி திட்டம்"))
        st.write(f"Goal: **{profile['goal']}** · Level: **{profile['level']}** · Location: **{profile['place']}**")
        day_name=date.today().strftime("%A")
        days=list(SPLIT); default=next((i for i,x in enumerate(days) if x.startswith(day_name)) ,6)
        chosen=st.selectbox("Choose day",days,index=default)
        st.dataframe(pd.DataFrame(SPLIT[chosen],columns=["Exercise","Muscle group","Suggested sets/reps"]),use_container_width=True,hide_index=True)
        st.caption("Sample plan only. Adapt to your ability and equipment. Learn technique first; stop if you feel pain, chest discomfort, or dizziness.")
        st.info("The plan is goal-aware but the sample split is not yet a clinically validated individualized prescription.")
    elif page==pages[4]:
        st.title("📈 "+tr("Daily progress","தினசரி முன்னேற்றம்"))
        old=hist[hist.day==today] if not hist.empty else pd.DataFrame()
        prev=old.iloc[0] if not old.empty else None
        with st.form("progress_form"):
            day=st.date_input("Date",date.today())
            w=st.number_input("Weight (kg)",25.0,300.0,float(prev["weight"]) if prev is not None else float(profile["weight"]),step=.1)
            steps=st.number_input("Steps",0,100000,int(prev["steps"]) if prev is not None else 0,step=500)
            water=st.number_input("Water (litres)",0.0,15.0,float(prev["water"]) if prev is not None else 0.0,step=.25)
            sleep=st.number_input("Sleep (hours)",0.0,24.0,float(prev["sleep"]) if prev is not None else 0.0,step=.5)
            workout=st.checkbox("Workout completed?",bool(prev["workout"]) if prev is not None else False)
            notes=st.text_input("Notes",str(prev["notes"]) if prev is not None else "")
            save=st.form_submit_button("Save progress")
        if save:
            with connect() as c:
                c.execute("""INSERT INTO progress VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(user_id,day) DO UPDATE SET
                weight=excluded.weight,steps=excluded.steps,water=excluded.water,sleep=excluded.sleep,workout=excluded.workout,notes=excluded.notes""",
                (uid,day.isoformat(),w,int(steps),water,sleep,int(workout),notes))
            st.success("Progress saved."); st.rerun()
        st.progress(min(steps/max(int(profile["steps_target"]),1),1.0))
        st.write(f"Step goal: {profile['steps_target']:,} · Remaining: {max(0,int(profile['steps_target'])-int(steps)):,}")
        with connect() as c: hist=pd.read_sql_query("SELECT * FROM progress WHERE user_id=? ORDER BY day",(c,uid))
        if not hist.empty:
            hist["day"]=pd.to_datetime(hist["day"])
            hist["7-day average"]=hist["weight"].rolling(7,min_periods=1).mean()
            st.plotly_chart(px.line(hist,x="day",y=["weight","7-day average"],markers=True),use_container_width=True)
            st.dataframe(hist.sort_values("day",ascending=False),use_container_width=True,hide_index=True)
    elif page==pages[5]:
        st.title("🤖 "+tr("AI fitness coach","AI உடற்பயிற்சி ஆலோசகர்"))
        st.warning("No API key was selected. This first version uses a small offline rule-based helper, NOT a live generative LLM. We will connect an actual LLM and RAG in the next step.")
        question=st.text_area("Ask about calories, Tamil food, workouts, or progress")
        if st.button("Ask FIT Tamila AI",use_container_width=True):
            q=question.lower()
            if any(x in q for x in ["idli","dosa","rice","chapati","இட்லி","தோசை","சோறு"]):
                answer="You can include familiar Tamil foods. Manage portion size and oil, and pair staples with sambar, vegetables, and a suitable protein source. Nutrition estimates vary by recipe."
            elif any(x in q for x in ["workout","exercise","chest","back","biceps","legs","shoulder"]):
                today_name=date.today().strftime("%A")
                key=next((x for x in SPLIT if x.startswith(today_name)),"Sunday — Recovery")
                answer="Today's sample plan: "+"; ".join(x[0]+" ("+x[2]+")" for x in SPLIT[key])+". Adapt it to your level and recovery."
            elif "calorie" in q:
                answer=f"Your estimated starting target is {m['target']:.0f} kcal/day. Today's food logged: {kcal:.0f} kcal. The result depends on complete, accurate entries."
            elif any(x in q for x in ["weight","progress"]):
                if hist.empty: answer="Record your weight consistently, preferably under similar conditions, and review weekly trends."
                else:
                    answer=f"Your latest saved weight is {hist.sort_values('day').iloc[-1]['weight']:.1f} kg. Compare weekly averages; daily changes can reflect water and digestion."
            else:
                answer=f"Your goal is {profile['goal']}; estimated daily target is {m['target']:.0f} kcal. Ask about Tamil meals, calories, workouts, steps, or weight trends. This offline response is not a live LLM."
            st.markdown("### Coach response"); st.write(answer)
        st.markdown("#### Recipe ideas")
        st.write("- Egg dosa with sambar (non-vegetarian preference)")
        st.write("- Chickpea sundal")
        st.write("- Pepper chicken with measured rice and vegetables")
        st.write("- Curd, fruit, and oats bowl")
        st.write("- Chapati with dal and poriyal")

st.sidebar.markdown("---")
st.sidebar.caption("FIT Tamila AI · Educational prototype")
