import csv
import html
import json
import os
import secrets
from datetime import datetime
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

import accounts
import chatbot
import estimates
import site_text
from logic import *

st.set_page_config(page_title="TraceFort · Know your walk-away bid", page_icon="🏛️", layout="wide",
                   initial_sidebar_state="collapsed")       # the side panel opens from the ☰ button

# ----------------------------------------------------------------------------------------------
# Look: Greek black-figure pottery: black glaze, cream parchment, one terracotta accent (a single
# terracotta line under each page title). Lexend (made for easy reading, plain zeros so money reads
# cleanly) for everything people read; Cinzel only for the wordmark and rank numerals. 18px base.
# Terracotta #A84A33 passes WCAG AA both ways: white text on it 5.7:1, as text on the cream 4.7:1.
# ----------------------------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@400;600;700&family=Cinzel:wght@700&display=swap');

:root {
  --ink: #1A1410;        /* black glaze */
  --paper: #F3E9D8;      /* parchment */
  --card: #FBF5EA;
  --wash: #E9DCC6;
  --line: #D6C4A6;
  --muted: #5C4B3B;
  --red: #A84A33;        /* terracotta (kept the old name so every rule below still points at the accent) */
  --red-dark: #7E3524;
  --space: 8px;
}
html { font-size: 18px; }
html, body, .stApp, .stApp p, .stApp label, .stApp li, .stApp input, .stApp button, .stApp textarea,
[data-testid="stMarkdownContainer"], [data-baseweb="select"] * {
  font-family: 'Lexend', 'Segoe UI', Arial, sans-serif;
}
.stApp { background: var(--paper); color: var(--ink); }
/* top: room for the fixed top bar; bottom: room for the floating Ask TraceFort button */
.block-container { padding-top: 88px; padding-bottom: calc(var(--space) * 12); max-width: 1240px; }
::selection { background: var(--red); color: #fff; }
a { color: var(--red); text-underline-offset: 3px; }
a:visited { color: var(--red-dark); }

/* hide builder chrome, incl. the Fullscreen/download toolbar Streamlit puts on the map and tables */
[data-testid="stAppDeployButton"], #MainMenu, footer, [data-testid="stElementToolbar"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }

/* ---------- top bar: ☰ + wordmark left, Sign in / Create account right. Fixed: stays put while you scroll.
   The ☰ is Streamlit's own side-panel button, restyled and pinned into the bar's left slot. ---------- */
.st-key-topbar { position: fixed; top: 0; left: 0; right: 0; z-index: 990; background: var(--paper);
                 border-bottom: 1px solid var(--line); padding: 10px 140px 10px 68px; }
/* 140px right: Streamlit Cloud draws its own Fork + GitHub buttons in the top-right corner of the page. */
/* Streamlit's header/toolbar is an invisible strip over our bar: make it click-through (it was swallowing
   clicks on Sign in / Create account), and keep only the ☰ button clickable. */
header[data-testid="stHeader"], [data-testid="stToolbar"] { background: transparent; pointer-events: none !important; }
header[data-testid="stHeader"] { z-index: 995; }
[data-testid="stExpandSidebarButton"] {
  pointer-events: auto !important; position: fixed !important; top: 10px; left: 12px; width: 46px; height: 46px;
  border: none !important; border-radius: 8px; background: transparent !important; color: var(--ink) !important;
  display: flex !important; align-items: center; justify-content: center; padding: 0 !important; }
[data-testid="stExpandSidebarButton"]:hover { background: var(--wash) !important; }
[data-testid="stExpandSidebarButton"] span { font-size: 0 !important; }          /* hide the » icon ... */
[data-testid="stExpandSidebarButton"]::before { content: "☰"; font-size: 26px; line-height: 1; }  /* ... show ☰ */
.brand { font-family: 'Cinzel', Georgia, serif; font-weight: 700; letter-spacing: .18em; font-size: 1.3rem;
         color: var(--ink); line-height: 46px; white-space: nowrap; overflow: hidden; text-overflow: clip; }
.brand span { color: var(--red); }
.st-key-topbar [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; align-items: center; gap: 8px; }
.st-key-topbar [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; flex: 1 1 auto !important; }
.st-key-topbar [data-testid="stColumn"]:not(:first-child) { flex: 0 0 auto !important; }
.st-key-topbar [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }   /* Streamlit adds -17px */
.who { font-weight: 700; white-space: nowrap; }
[data-testid="stSidebar"] .menu-who { font-weight: 700; margin: 0 0 4px; }

/* ---------- Ask TraceFort: floating button on every page ---------- */
.st-key-chat_fab { position: fixed; right: 20px; bottom: 76px; z-index: 999; width: auto !important; }
/* 76px up: Streamlit Cloud's creator badge sits in the bottom-right corner and would cover the button. */
.st-key-chat_fab button { border-radius: 99px; min-height: 54px; padding: 0 22px;
                          box-shadow: 0 6px 18px rgba(0,0,0,.25); }

/* ---------- welcome choice ---------- */
.welcome-lead { font-size: 1.1rem; margin: 0 0 14px; }

/* ---------- page title ---------- */
.masthead {
  background: var(--ink); color: #fff; padding: 24px 32px 26px; border-radius: 4px;
  border-bottom: 5px solid var(--red); margin: 10px 0 24px;
}
.masthead h1 {
  font-family: 'Lexend', Arial, sans-serif; font-weight: 700; color: #fff;
  font-size: 2.1rem; line-height: 1.2; margin: 0; padding: 0; max-width: 24ch; text-wrap: balance;
}

.summary { font-size: 1.15rem; margin: 26px 0 6px; }
.summary b { font-size: 1.3rem; }
.summary .hit { color: var(--red); }
.sample-note { color: var(--muted); font-size: .95rem; margin: 0 0 4px; }

/* ---------- home card ---------- */
.home { border: 1px solid var(--line); border-radius: 12px; padding: 22px 24px 18px; margin: 18px 0 8px; background: var(--card); }
.home-top { display: flex; gap: 18px; align-items: flex-start; }
.rank {
  font-family: 'Cinzel', Georgia, serif; font-weight: 700; flex: none;
  width: 48px; height: 48px; border-radius: 4px; background: var(--ink); color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 1.05rem; letter-spacing: .04em;
}
.home-name { flex: 1; min-width: 0; }
.addr { font-size: 1.4rem; font-weight: 700; line-height: 1.2; }
.where { color: var(--muted); font-size: .95rem; margin-top: 4px; }
.tag { display: inline-block; font-size: .72rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
       border: 1px solid #B49A78; color: var(--muted); border-radius: 4px; padding: 1px 6px; margin-right: 8px; vertical-align: 2px; }
.bid { background: var(--red); color: #fff; border-radius: 8px; padding: 12px 18px; text-align: right; flex: none; min-width: 210px; }
.bid .lbl { font-size: .8rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #F8E3D6; }
.bid .amt { font-size: 1.9rem; font-weight: 700; line-height: 1.15; font-variant-numeric: tabular-nums; }
.bid .note { font-size: .85rem; color: #F8E3D6; }
.bid.skip { background: var(--wash); color: var(--ink); border: 1px solid var(--line); }
.bid.skip .lbl, .bid.skip .note { color: var(--muted); }
.facts { margin: 16px 0 0; color: var(--ink); font-size: 1rem; }
.facts span + span::before { content: "·"; margin: 0 9px; color: #A8957C; }
.why { margin: 10px 0 0; font-size: 1.02rem; color: #3A2E24; max-width: 70ch; }
.why b { color: var(--ink); }
.nums { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 16px; border-top: 1px solid var(--line); }
.nums div { padding: 12px 12px 0 0; }
.nums div + div { padding-left: 14px; border-left: 1px solid var(--line); }
.nums .k { display: block; font-size: .78rem; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; color: var(--muted); }
.nums .v { display: block; font-size: 1.2rem; font-weight: 700; font-variant-numeric: tabular-nums; margin-top: 2px; }
.nums .v.high { color: var(--red); }
.match { display: flex; align-items: center; gap: 12px; margin-top: 16px; font-size: .95rem; color: var(--muted); }
.match .bar { flex: 1; max-width: 260px; height: 8px; background: var(--wash); border-radius: 99px; overflow: hidden; }
.match .bar i { display: block; height: 100%; background: var(--ink); }
.estimate { font-size: .85rem; color: var(--muted); margin: 12px 0 0; }

/* ---------- widgets ---------- */
.stButton > button { border-radius: 8px; min-height: 46px; font-weight: 700; padding: 0 18px; }
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--red); border: 1px solid var(--red); color: #fff; }
button[data-testid="stBaseButton-primary"]:hover, button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
  background: var(--red-dark); border-color: var(--red-dark); color: #fff; }
button[data-testid="stBaseButton-secondary"] { background: var(--card); color: var(--ink); border: 1px solid var(--ink); }
button[data-testid="stBaseButton-secondary"]:hover { background: var(--ink); color: #fff; border-color: var(--ink); }
button[data-testid="stBaseButton-tertiary"] { color: var(--red); text-decoration: underline; text-underline-offset: 3px; padding: 0; }
button:focus-visible, input:focus-visible, a:focus-visible { outline: 3px solid var(--red) !important; outline-offset: 2px; }
[data-testid="stButtonGroup"] button { min-height: 54px; padding: 0 20px; font-size: 1rem; }
.q-count { font-size: .82rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: var(--muted); margin-top: 8px; }
.q-text { font-size: 1.6rem; font-weight: 700; line-height: 1.25; margin: 6px 0 16px; text-wrap: balance; }
[data-testid="stExpander"] details { border: 1px solid var(--line); border-radius: 8px; }
[data-testid="stExpander"] summary p { font-weight: 700; }
.side-money { font-size: .95rem; color: var(--muted); margin: -6px 0 10px; }
[data-testid="stMarkdownContainer"] h3 { font-size: 1.2rem; font-weight: 700; margin: 22px 0 6px; padding: 0; }

/* ---------- footer ---------- */
.foot { color: var(--muted); font-size: .85rem; line-height: 1.6; margin-top: 6px; }

@media (max-width: 760px) {
  html { font-size: 17px; }
  .masthead { padding: 20px 20px 22px; }
  .masthead h1 { font-size: 1.6rem; }
  .home { padding: 18px 16px 14px; }
  .home-top { flex-wrap: wrap; }
  .bid { width: 100%; text-align: left; }
  .nums { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .nums div:nth-child(3) { border-left: none; padding-left: 0; }
  .brand { font-size: .95rem; letter-spacing: .08em; }
  .st-key-topbar { padding: 50px 10px 10px 64px; }      /* phones: start below Cloud's Fork/GitHub strip */
  .block-container { padding-top: 128px; }
  .st-key-topbar .stButton > button { padding: 0 10px; font-size: .82rem; min-height: 42px; }
  .st-key-top_create button p { font-size: 0 !important; }            /* phones: short label so the */
  .st-key-top_create button p::after { content: "Sign up"; font-size: .82rem; }   /* wordmark still fits */
  [data-testid="stExpandSidebarButton"] { left: 10px; top: 50px; height: 42px; width: 42px; }
  .st-key-chat_fab { right: 12px; bottom: 64px; }
}
@media (max-width: 380px) {                                   /* small phones (320-380px): keep the wordmark whole */
  .brand { font-size: .8rem; letter-spacing: .03em; }
  .st-key-topbar { padding-left: 54px; }
  .st-key-topbar [data-testid="stHorizontalBlock"] { gap: 6px; }
  .st-key-topbar .stButton > button { padding: 0 7px; }
  [data-testid="stExpandSidebarButton"] { left: 6px; }
}
</style>
""",
    unsafe_allow_html=True,
)


def money(v):
    return f"${int(round(v)):,}"


def xome_city_url(city):
    """Xome's auction list for a Texas city, e.g. Fort Worth -> https://www.xome.com/auctions/tx/fort-worth
    (checked live: Arlington lists 15 auctions, Fort Worth 44). Only the city name goes in the link."""
    slug = "-".join("".join(ch for ch in str(city).lower() if ch.isalnum() or ch == " ").split())
    return f"https://www.xome.com/auctions/tx/{slug}"


def risk_word(score):
    return "Low" if score <= 3 else "Moderate" if score <= 6 else "High"


ROMAN = {1: "I", 2: "II", 3: "III"}
ESTIMATE_NOTE = "Estimate for education. Not an appraisal, financial advice or a brokerage service."
SAMPLE_NOTE = "Sample homes for demo, built on real Zillow ZIP-code values. Addresses and auction details are made up."


# Markets: same pipeline, same Texas foreclosure rules. New market = a row here + one in generate_data.METROS.
MARKETS = {
    "dfw": {"name": "Dallas–Fort Worth", "short": "DFW", "file": "homes.csv",
            "box": (32.45, 33.30, -97.60, -96.50), "view": {"latitude": 32.82, "longitude": -97.05, "zoom": 8.9}},
    "houston": {"name": "Houston", "short": "Houston", "file": "homes_houston.csv",
                "box": (29.40, 30.20, -95.90, -94.90), "view": {"latitude": 29.78, "longitude": -95.40, "zoom": 8.9}},
}


@st.cache_data
def cached_homes(market="dfw"):
    return load_homes(Path(__file__).parent / MARKETS[market]["file"])


def masthead(title):
    st.markdown(f"<div class='masthead'><h1>{title}</h1></div>", unsafe_allow_html=True)


def reading_column():
    """Text pages read best at ~70 characters a line."""
    col, _ = st.columns([5, 2])
    return col


DEMO = {"budget": 180000, "goal": "Live in it", "risk": "Balanced", "beds": 3, "tol": TOLERANCES[1], "drive": 30,
        "work_zip": None, "market": "dfw"}
PREF_KEYS = list(DEMO)
TOKEN_COOKIE, NOTICE_COOKIE = "tracefort_token", "tracefort_notice"
ONE_YEAR = 365 * 24 * 3600


@st.cache_data
def zip_centers():
    """Texas ZIP -> (lat, lon) from the Census. A typed work ZIP is all we use: no GPS, no IP lookup."""
    with open(Path(__file__).parent / "data" / "zip_centers_tx.csv") as f:
        return {r["zip"]: (float(r["lat"]), float(r["lon"])) for r in csv.DictReader(f)}


def zip_problem(z):
    """Friendly problem with a typed ZIP, or None if we can use it."""
    if not (len(z) == 5 and z.isdigit()):
        return "A ZIP code has 5 numbers, like 76010."
    if z not in zip_centers():
        return "We don't have that ZIP. Try a nearby Texas ZIP, or skip this."
    return None


@st.cache_data
def homes_for_zip(work_zip, market="dfw"):
    """The market's homes, with drive minutes from the buyer's work ZIP instead of the nearest job center."""
    table = cached_homes(market)
    if not work_zip or work_zip not in zip_centers():
        return table
    lat0, lon0 = zip_centers()[work_zip]
    df = table.copy()
    df["drive_minutes"] = [int(round(estimates.miles(lat0, lon0, la, lo) * estimates.ROAD_FACTOR / estimates.AVG_MPH * 60))
                           for la, lo in zip(df.lat, df.lon)]
    df["job_center"] = f"your work (ZIP {work_zip})"
    return df


def my_ranked(p):
    """The buyer's homes, screened and ranked best-first (Your best homes + Ask TraceFort)."""
    return rank_homes(screen_homes(homes_for_zip(p["work_zip"], p["market"]), p["budget"], p["goal"], p["risk"], p["beds"],
                                   p["tol"], p["drive"]), p["budget"], p["goal"], p["risk"], p["drive"])


# ------------------------------------------------------------------------------------------------
# Accounts: first visit = quiz + name/PIN + agree to Terms. After that this browser is remembered
# (cookie), so people go straight to their homes. Sign out or delete the account any time.
# Cookies are written by a tiny script on the next run (Streamlit has no server-side cookie setter).
# ------------------------------------------------------------------------------------------------
def set_cookie(name, value, max_age):
    st.session_state.setdefault("cookie_ops", []).append((name, value, max_age))


ops = st.session_state.pop("cookie_ops", [])          # queued by the previous run
if ops:                                                 # names and values are ours, never user text
    script = "<script>" + "".join(f"window.parent.document.cookie = '{n}={v}; path=/; max-age={a}; SameSite=Lax';"
                                  for n, v, a in ops) + "</script>"
    st.iframe(script, height=1)



def clean_prefs(p):
    """Stored answers -> safe values for every widget (old or odd values fall back to the demo)."""
    p = p or {}
    ok = {
        "budget": isinstance(p.get("budget"), int) and 20000 <= p["budget"] <= 1000000,
        "goal": p.get("goal") in GOAL_MARGIN,
        "risk": p.get("risk") in RISK_SHIFT,
        "beds": isinstance(p.get("beds"), int) and 1 <= p["beds"] <= 5,
        "tol": p.get("tol") in TOLERANCES,
        "drive": isinstance(p.get("drive"), int) and 10 <= p["drive"] <= 45,
        "work_zip": isinstance(p.get("work_zip"), str) and p["work_zip"] in zip_centers(),
        "market": p.get("market") in MARKETS,             # accounts saved before markets existed -> DFW
    }
    return {k: (p[k] if ok[k] else DEMO[k]) for k in PREF_KEYS}


USER_KEYS = ("answers", "quiz_step", "welcome", "prefs", "chat", "pool_cash", "map_v")
USER_PREFIXES = ("w_", "q_", "chk_", "new_", "in_", "del_")   # widget values on prefs/quiz/checklist/forms


def forget_answers(keep_prefs=False):
    """Drop everything one person typed, widget values included. Streamlit keeps a widget's value under its
    key even after the dict we save is gone, so without this the next person saw (and re-saved) old answers."""
    for k in list(st.session_state):
        if (k in USER_KEYS and not (keep_prefs and k == "prefs")) or k.startswith(USER_PREFIXES):
            del st.session_state[k]


def start_session(token, name, prefs):
    # Preferences live in one plain dict, not in widget keys: Streamlit forgets a widget's value when
    # its page isn't showing, and preferences now have their own page.
    forget_answers()
    st.session_state.user = {"token": token, "name": name}
    st.session_state.prefs = clean_prefs(prefs)


def end_session(forget_device):
    token = (st.session_state.user or {}).get("token")
    if token and forget_device:
        set_cookie(TOKEN_COOKIE, "", 0)                  # forget this browser
    st.session_state.user = None
    forget_answers()


if "user" not in st.session_state:                       # new tab / app reopened
    st.session_state.user = None
    remembered = st.context.cookies.get(TOKEN_COOKIE)
    acct = accounts.from_token(remembered)
    if acct:
        start_session(remembered, acct["name"], acct["prefs"])

BUDGETS = list(range(80000, 600001, 5000))
TOL_LABEL = {TOLERANCES[0]: "Anything, I'm handy", TOLERANCES[1]: "Some, but no roof or foundation",
             TOLERANCES[2]: "Only light repairs (under $30K)"}
QUESTIONS = [  # (answer key, question, options or None for the budget slider, how to show each option, hint)
    ("goal", "What is the home for?", list(GOAL_MARGIN),
     {"Live in it": "Live in it", "Rent it": "Rent it out", "Fix and resell": "Fix it and sell it"}.get, None),
    ("budget", "What can you spend in total?", None, money,
     "Count the winning bid and the repairs together. Drag or use the arrow keys."),
    ("beds", "How many bedrooms do you need?", [1, 2, 3, 4, 5], lambda v: f"{v}+", None),
    ("work_zip", "Where do you work?", "zip", None,
     "Type your work ZIP code so drive times start from there. We keep only the ZIP, never your location."),
    ("drive", "How long a drive to work is OK?", [15, 20, 30, 45], lambda v: f"{v} min", None),
    ("tol", "How much fixing are you up for?", TOLERANCES, TOL_LABEL.get, None),
    ("risk", "How do you feel about risk?", list(RISK_SHIFT),
     {"Safe": "Play it safe", "Balanced": "Somewhere in between", "Aggressive": "I'll take chances"}.get,
     "Playing it safe keeps a bigger cushion below the home's value and hides riskier homes."),
]
PAGES = {}   # filled below; pages switch to each other through it


# ============================================ pages ===============================================

def page_start():
    """First visit: the quiz, then create an account (or look around as a guest)."""
    if st.session_state.user is not None:
        st.switch_page(PAGES["homes"])
    masthead("Find your way home.")
    if not st.session_state.get("welcome"):                 # first: guest, or sign in if you have an account
        _, mid, _ = st.columns([1, 5, 1])
        with mid, st.container(border=True):
            st.markdown("<div class='q-text'>Welcome to TraceFort</div><p class='welcome-lead'>Find foreclosure "
                        "auction homes that fit you, and the most to bid on each. Answer 7 quick questions as a "
                        "guest, or sign in if you already have an account.</p>", unsafe_allow_html=True)
            if st.button("Continue as a guest", type="primary", width="stretch"):
                st.session_state.welcome = True
                st.rerun()
            if st.button("I have an account: sign in", width="stretch"):
                st.switch_page(PAGES["sign_in"])
            if st.button("Create an account", width="stretch"):
                st.switch_page(PAGES["create"])
            if st.button("Just looking? See an example buyer", type="tertiary"):
                start_session(None, None, DEMO)
                st.switch_page(PAGES["homes"])
        return
    ans = st.session_state.setdefault("answers", {})
    step = st.session_state.setdefault("quiz_step", 0)
    total = len(QUESTIONS) + 1                              # questions + "save your answers"

    _, mid, _ = st.columns([1, 5, 1])
    with mid, st.container(border=True):
        st.progress(step / total)
        if step < len(QUESTIONS):
            key, question, options, fmt, hint = QUESTIONS[step]
            st.markdown(f"<div class='q-count'>Question {step + 1} of {len(QUESTIONS)}</div>"
                        f"<div class='q-text'>{question}</div>", unsafe_allow_html=True)
            if options == "zip":                            # typed answer: a form sends it with the click
                with st.form("zip_form", border=False):
                    typed = st.text_input("Work ZIP code", value=ans.get(key) or "", max_chars=5, placeholder="76010")
                    go = st.form_submit_button("Next", type="primary", width="stretch")
                st.caption(hint)
                if go:
                    z = typed.strip()
                    problem = zip_problem(z) if z else "Type your work ZIP code, or skip this question."
                    if problem:
                        st.error(problem)
                    else:
                        ans[key] = z
                        st.session_state.quiz_step += 1
                        st.rerun()
                b1, b2 = st.columns(2)
                if b1.button("Back", width="stretch"):
                    st.session_state.quiz_step -= 1
                    st.rerun()
                if b2.button("Skip this question", width="stretch"):
                    ans[key] = None
                    st.session_state.quiz_step += 1
                    st.rerun()
                return
            if options is None:
                current = min(BUDGETS, key=lambda b: abs(b - ans.get(key, DEMO["budget"])))
                val = st.select_slider(question, BUDGETS, value=current, format_func=money, key=f"q_{key}",
                                       label_visibility="collapsed")
            else:
                default = ans.get(key) if ans.get(key) in options else None
                val = st.segmented_control(question, options, format_func=fmt, default=default, key=f"q_{key}",
                                           label_visibility="collapsed")
            if hint:
                st.caption(hint)
            back, nxt = st.columns(2)
            if back.button("Back", width="stretch"):
                if val is not None:
                    ans[key] = val
                if step == 0:
                    st.session_state.welcome = False        # back to the guest / sign-in choice
                else:
                    st.session_state.quiz_step -= 1
                st.rerun()
            if nxt.button("Next", type="primary", disabled=val is None, width="stretch"):
                ans[key] = val
                st.session_state.quiz_step += 1
                st.rerun()
            if val is None:
                st.caption("Pick one to continue.")
        else:
            st.markdown("<div class='q-count'>Last step</div><div class='q-text'>See your homes</div>",
                        unsafe_allow_html=True)
            if st.button("See my homes as a guest", type="primary", width="stretch",
                         help="Nothing is saved. Create an account any time from the menu to keep your answers."):
                start_session(None, None, ans)
                st.switch_page(PAGES["homes"])
            with st.expander("Or save your answers: create an account"):
                account_form(ans, then="homes")
            if st.button("Back", width="stretch"):
                st.session_state.quiz_step -= 1
                st.rerun()


def account_form(prefs, then):
    """Name + PIN + agreement. Errors show right under the button, where people are looking."""
    st.caption("Make an account once and we'll remember you on this device. No email, no ID.")
    st.page_link(PAGES["terms"], label="Read the Terms of Use")
    st.page_link(PAGES["privacy"], label="Read the Privacy Policy")
    with st.form("create_account", border=False):          # a form sends every field together
        name = st.text_input("What should we call you?", max_chars=40, key="new_name")
        pin = st.text_input("Pick a 4-digit PIN", type="password", max_chars=4, key="new_pin",
                            help="Only needed if you sign out and want to come back. Don't reuse your bank PIN.")
        agreed = st.checkbox("I'm 18 or older, and I agree to the Terms of Use and Privacy Policy.", key="new_agree")
        create = st.form_submit_button("Create my account", type="primary", width="stretch")
    if create:
        prefs = clean_prefs(prefs)
        try:
            token = accounts.create(name, pin, prefs, agreed=agreed)
        except ValueError as err:
            st.error(str(err))
        else:
            start_session(token, name.strip(), prefs)
            set_cookie(TOKEN_COOKIE, token, ONE_YEAR)
            if then == "prefs":
                st.session_state.flash = "Your account is ready. Now tell us what you're looking for."
            st.switch_page(PAGES[then])


def page_create():
    """The top-bar "Create account" button: a real form, no quiz required."""
    user = st.session_state.user
    if user is not None and user["token"]:
        st.switch_page(PAGES["homes"])
    masthead("Create your account")
    answers = st.session_state.get("answers") or (st.session_state.get("prefs") if user else None)
    _, mid, _ = st.columns([1, 5, 1])
    with mid, st.container(border=True):
        if answers:
            st.markdown("<div class='q-count'>We'll save the answers you already gave</div>", unsafe_allow_html=True)
        account_form(answers or DEMO, then="homes" if answers else "prefs")
        if st.button("Already have an account? Sign in", type="tertiary"):
            st.switch_page(PAGES["sign_in"])


def page_sign_in():
    if st.session_state.user is not None and st.session_state.user["token"]:
        st.switch_page(PAGES["homes"])
    masthead("Sign in")
    _, mid, _ = st.columns([1, 5, 1])
    with mid, st.container(border=True):
        st.markdown("<div class='q-count'>Welcome back</div>", unsafe_allow_html=True)
        with st.form("sign_in", border=False):             # a form sends every field together
            name = st.text_input("Your first name", key="in_name")
            pin = st.text_input("Your 4-digit PIN", type="password", max_chars=4, key="in_pin")
            go = st.form_submit_button("Sign in", type="primary", width="stretch")
        if go:
            token = accounts.sign_in(name, pin)
            if token:
                acct = accounts.from_token(token)
                start_session(token, acct["name"], acct["prefs"])
                set_cookie(TOKEN_COOKIE, token, ONE_YEAR)
                st.switch_page(PAGES["homes"])
            wait = accounts.lock_remaining(name)
            if wait:
                st.error(f"Too many wrong tries. To keep accounts safe, sign-in for this name is paused for "
                         f"{(wait + 59) // 60} more minute(s).")
            else:
                st.error("That name and PIN don't match. Check them and try again. "
                         "After 5 wrong tries, sign-in pauses for 15 minutes.")
        if st.button("New here? Create an account", type="tertiary"):
            st.switch_page(PAGES["create"])


def need_user():
    """Pages for people who've started; anyone else goes to the quiz."""
    if st.session_state.user is None:
        st.switch_page(PAGES["start"])
    return st.session_state.prefs


def home_card(pos, home):
    addr = html.escape(str(home.neighborhood))
    where = [html.escape(str(home.city))]
    if getattr(home, "zip", None):
        where[0] += f", TX {html.escape(str(home.zip))}"
    if getattr(home, "auction_date", None):
        d = pd.Timestamp(home.auction_date)
        where.append(f"Auction {d:%a %b} {d.day}, {d.year}")   # no %-d: breaks on Windows

    if home.viable:
        bid = (f"<div class='bid'><div class='lbl'>Walk-away bid</div><div class='amt'>{money(home.walk_away)}</div>"
               f"<div class='note'>Stop bidding here</div></div>")
    else:
        bid = (f"<div class='bid skip'><div class='lbl'>Skip this one</div><div class='amt'>{money(home.walk_away)}</div>"
               f"<div class='note'>Your limit is under the {money(home.opening_bid)} opening bid</div></div>")

    facts = [f"{int(home.beds)} beds", f"{home.baths:g} baths", f"{int(home.sqft):,} sq ft"]
    if getattr(home, "year_built", None):
        facts.append(f"built {int(home.year_built)}")
    job = getattr(home, "job_center", None)
    facts.append(f"{int(home.drive_minutes)} min drive" + (f" to {html.escape(str(job))}" if isinstance(job, str) else ""))
    store_mi = getattr(home, "store_miles", None)
    if store_mi is not None and pd.notna(store_mi) and store_mi <= 3:
        facts.append(f"{store_mi:.1f} mi to {html.escape(str(home.store_name))}")

    room = int(home.est_value - home.repair_cost - home.opening_bid)
    why = (f"Opens at <b>{money(home.opening_bid)}</b>. Worth about <b>{money(home.est_value)}</b> once fixed. "
           f"After <b>{money(home.repair_cost)}</b> in repairs that leaves about <b>{money(room)}</b> of room.")
    if home.viable:
        why += (f" Win at {money(home.walk_away)} and you'd also pay about <b>{money(auction_fees(home.walk_away))}</b> "
                "in auction fee and closing costs; your walk-away bid already leaves room for that.")
    rw = risk_word(home.risk_score)

    st.markdown(
        f"""
<div class="home">
  <div class="home-top">
    <div class="rank" role="img" aria-label="Rank {pos}">{ROMAN.get(pos, pos)}</div>
    <div class="home-name"><div class="addr">{addr}</div>
      <div class="where"><span class="tag">Sample home</span>{' · '.join(where)}</div></div>
    {bid}
  </div>
  <div class="facts">{''.join(f'<span>{f}</span>' for f in facts)}</div>
  <p class="why">{why}</p>
  <div class="nums">
    <div><span class="k">Opening bid</span><span class="v">{money(home.opening_bid)}</span></div>
    <div><span class="k">Worth once fixed</span><span class="v">{money(home.est_value)}</span></div>
    <div><span class="k">Repairs</span><span class="v">{money(home.repair_cost)}</span></div>
    <div><span class="k">Risk</span><span class="v{' high' if rw == 'High' else ''}">{rw} · {int(home.risk_score)}/10</span></div>
  </div>
  <div class="match"><span>Match {int(home.score)}%</span><div class="bar"><i style="width:{int(home.score)}%"></i></div></div>
  <p class="estimate">{ESTIMATE_NOTE}</p>
</div>
""",
        unsafe_allow_html=True,
    )
    # One click to where bidding happens, so buyers don't hunt for it on another site. Opens in a new tab, so
    # this card (walk-away bid + checklist) stays open here. Sample homes have no real listing page, so they
    # open real auctions in the same city; a real listing_url (when we have one) goes straight to that home.
    url = getattr(home, "listing_url", None)
    if isinstance(url, str) and url.startswith("https://"):
        st.link_button("Open this listing on Xome", url, icon=":material/open_in_new:", type="primary")
    else:
        st.link_button(f"See auctions in {home.city} on Xome", xome_city_url(home.city),
                       icon=":material/open_in_new:", type="primary",
                       help="Opens Xome in a new tab. This home is a sample, so you'll see real auctions in the same "
                            "city. Keep this page open to check each one against your walk-away bid and checklist.")
    with st.expander("Ready to bid? Your checklist"):
        steps = bid_checklist(home)
        if getattr(home, "occupied", 0):
            steps.append("Someone may still live here: plan time and money for them to move out")
            steps.append("Only a court eviction can make them leave. Never change the locks or shut off utilities. "
                         "Renters usually get at least 90 days' notice (free help: TexasLawHelp.org)")
        if getattr(home, "interior_inspected", 1) == 0:
            steps.append("Nobody has seen the inside: keep extra cash for surprises")
        for step_no, step_text in enumerate(steps):
            st.checkbox(step_text, key=f"chk_{home.listing_id}_{step_no}")


# Opens on the whole metro, tilted, and can't zoom out past it. Each home is a 3D column as tall as its
# walk-away bid. Click a column to zoom into that home.
# ponytail: deck.gl can't hard-lock panning at the edges; the zoom-out cap keeps it metro-sized.
MIN_ZOOM, CLOSE_ZOOM = 8.4, 14.5
TILT, TURN = 45, -20                                       # map pitch and bearing in degrees
# Column radius (meters) and height (meters per $1,000 of bid) for the metro view and the street view.
# The best 3 are drawn BEST_WIDER times wider so the other homes never hide them.
# ponytail: deck.gl columns have no pixel min/max, so manual scroll-zoom makes them thick or thin; a
# zoom-aware size needs a custom deck.gl layer.
COLUMN = {"metro": (550, 60), "street": (22, 2.5)}
BEST_WIDER = 2


def homes_map(homes, market):
    m = MARKETS[market]
    s, n, w, e = m["box"]                              # south, north, west, east
    pts = homes[homes.lat.between(s, n) & homes.lon.between(w, e)].copy()
    if pts.empty:
        return
    top = pts.index < 3                                    # ranked_homes is sorted best-first
    pts["rank"] = [ROMAN.get(i + 1, "") for i in pts.index]
    pts["bid_txt"] = [money(v) if ok else "skip" for v, ok in zip(pts.walk_away, pts.viable)]
    pts["height"] = [v / 1000 if ok else 5 for v, ok in zip(pts.walk_away, pts.viable)]  # $k; skipped = short stub
    pts = pts[["lat", "lon", "neighborhood", "city", "rank", "bid_txt", "height"]]

    st.session_state.setdefault("map_v", 0)
    key = f"map_{market}_{st.session_state.map_v}"     # new market = fresh map, no leftover selection
    chosen = ((st.session_state.get(key) or {}).get("selection") or {}).get("objects") or {}
    picked = chosen.get("best") or chosen.get("homes") or []     # one layer for the best 3, one for the rest
    if picked:
        p = picked[0]
        view = pdk.ViewState(latitude=p["lat"], longitude=p["lon"], zoom=CLOSE_ZOOM, min_zoom=MIN_ZOOM, max_zoom=17,
                             pitch=TILT, bearing=TURN)
        radius, per_k = COLUMN["street"]
        st.markdown(f"<p class='summary'><b>{html.escape(p['neighborhood'])}</b>, {html.escape(p['city'])}</p>",
                    unsafe_allow_html=True)
    else:
        view = pdk.ViewState(**m["view"], min_zoom=MIN_ZOOM, max_zoom=17, pitch=TILT, bearing=TURN)
        radius, per_k = COLUMN["metro"]
        st.markdown("<p class='summary'><b>Where they are</b></p>", unsafe_allow_html=True)
    best = pts[pts["rank"] != ""].assign(
        top=lambda d: d.height * per_k * 1.12,                                   # numeral floats above its column
        nudge=lambda d: d["rank"].map({"I": [-24, 0], "II": [24, 0], "III": [0, -28]}))  # nearby homes' labels fan out
    column = dict(get_position="[lon, lat]", get_elevation="height", elevation_scale=per_k, disk_resolution=24,
                  extruded=True, pickable=True, auto_highlight=True)

    deck = pdk.Deck(
        map_style="light",
        initial_view_state=view,
        layers=[
            pdk.Layer("ColumnLayer", id="homes", data=pts[pts["rank"] == ""], radius=radius,
                      get_fill_color=[92, 75, 59, 150], **column),                  # other homes: thin, see-through
            pdk.Layer("ColumnLayer", id="best", data=best, radius=radius * BEST_WIDER,
                      get_fill_color=[168, 74, 51, 250], **column),                 # best 3: wide terracotta
            pdk.Layer("TextLayer", id="ranks", data=best, get_position="[lon, lat, top]", get_text="rank",
                      get_color=[26, 20, 16], get_size=18, font_weight=700, get_pixel_offset="nudge", background=True,
                      get_background_color=[251, 245, 234, 235], background_padding=[6, 2, 6, 2],
                      parameters={"depthCompare": "always"}),                       # never hidden behind a column
        ],
        tooltip={"html": "<b>{neighborhood}</b><br/>{city} · walk-away {bid_txt}<br/><i>Click to zoom in</i>",
                 "style": {"backgroundColor": "#1A1410", "color": "#FBF5EA", "fontSize": "14px"}},
    )
    st.pydeck_chart(deck, on_select="rerun", selection_mode="single-object", key=key, height=440,
                    alt=f"3D map of {m['name']} with {len(pts)} sample homes as columns; taller columns have a higher "
                        "walk-away bid. The best three are the cards listed above.")
    st.caption("Wide terracotta: your best 3. Thin brown: other homes that fit. Taller column = higher walk-away bid. "
               "Click a column to zoom in. To tilt or turn the map, right-click and drag (or Ctrl + drag); "
               "on a phone, use two fingers. The cards above list the same homes.")
    if picked and st.button(f"Back to all of {m['short']}"):
        st.session_state.map_v += 1                        # new key = selection cleared
        st.rerun()


def page_homes():
    prefs = need_user()
    name = html.escape(st.session_state.user["name"] or "")
    masthead(f"{name + ', here' if name else 'Here'} are your best homes.")
    ranked = my_ranked(prefs)
    st.markdown(f"<p class='sample-note'>{SAMPLE_NOTE}</p>", unsafe_allow_html=True)
    checked = f"{len(cached_homes(prefs['market'])):,}</b> homes in {MARKETS[prefs['market']]['name']}"
    if ranked.empty:
        st.markdown(f"<p class='summary'>We checked <b>{checked} and none fit these settings yet.</p>",
                    unsafe_allow_html=True)
        st.info("Try a higher budget, fewer bedrooms, a longer drive, or more repair tolerance.")
        st.page_link(PAGES["prefs"], label="Change my preferences")
        return
    viable = int(ranked["viable"].sum())
    st.markdown(f"<p class='summary'>We checked <b>{checked}. <b class='hit'>{viable}</b> fit your "
                f"budget and needs. Here are your best {min(3, len(ranked))}.</p>", unsafe_allow_html=True)
    top_three = ranked.head(3)
    for pos, home in enumerate(top_three.itertuples(), start=1):
        home_card(pos, home)
    if len(top_three) < 3:
        st.info(f"Only {len(top_three)} home(s) fit. Loosen a preference to see more.")
    if {"lat", "lon"} <= set(ranked.columns):
        homes_map(ranked, prefs["market"])


def page_investor():
    prefs = need_user()
    masthead("Investor mode")
    st.write("Have money for more than one home? Enter your total capital. We plan every home as a fix-and-resell, "
             f"keep the average risk at your level ({prefs['risk']}), put no more than half your money into one home, "
             "and pick the set that earns the most after every cost.")
    pool_cash = st.number_input("Total capital ($)", min_value=50000, max_value=2000000, value=300000, step=10000,
                                key="pool_cash")
    flip = "Fix and resell"                       # investing = flipping, whatever the buyer's own goal is
    wide = rank_homes(screen_homes(homes_for_zip(prefs["work_zip"], prefs["market"]), int(pool_cash), flip, prefs["risk"], 1, TOLERANCES[0], 60),
                      int(pool_cash), flip, prefs["risk"], 60)
    plan = plan_portfolio(wide, int(pool_cash), prefs["risk"])
    if plan.empty:
        st.warning("No profitable set of homes fits this capital and risk level. Try more capital or a higher risk level.")
        return
    st.markdown(f"<p class='summary'>Buy <b>{len(plan)}</b> home(s), use <b>{money(plan.capital.sum())}</b>, "
                f"expected profit <b class='hit'>{money(plan.profit.sum())}</b>.</p>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame({
        "Home": plan.neighborhood, "City": plan.city, "Your bid": plan.bid.map(money),
        "Repairs": plan.repair_cost.map(money), "Cash used": plan.capital.map(money),
        "Expected profit": plan.profit.map(money), "Risk": plan.risk_score.map(lambda r: f"{int(r)}/10"),
    }), hide_index=True, width="stretch")
    st.caption("Your bid = about 10% over the opening bid, never above the walk-away bid. Cash used = bid + Xome "
               "buyer's premium (5% or $2,500) + ~2% closing + repairs. Profit is after those and ~10% for selling "
               f"and holding the home. {ESTIMATE_NOTE} {SAMPLE_NOTE}")


def page_prefs():
    prefs = need_user()
    masthead("My preferences")
    col = reading_column()
    with col:
        st.write("Change anything here and your homes update right away."
                 + (" We save it to your account." if st.session_state.user["token"] else ""))
        for k in PREF_KEYS:                       # Streamlit drops widget state when you leave a page: refill it
            st.session_state.setdefault(f"w_{k}", prefs[k] if k != "work_zip" else (prefs[k] or ""))
        new = {
            "market": st.selectbox("Where are you buying?", list(MARKETS), key="w_market",
                                   format_func=lambda k: MARKETS[k]["name"],
                                   help="Texas metros only for now: our walk-away bid follows Texas foreclosure rules."),
            "budget": st.number_input("Total budget, repairs included ($)", min_value=20000, max_value=1000000,
                                      step=5000, key="w_budget",
                                      help="Everything you can spend: the winning bid plus fixing the house."),
        }
        st.markdown(f"<div class='side-money'>{money(new['budget'])}</div>", unsafe_allow_html=True)
        new["goal"] = st.selectbox("What's the home for?", list(GOAL_MARGIN), key="w_goal",
                                   help="Investors keep a bigger cushion, so their walk-away bid is lower.")
        new["risk"] = st.selectbox("How much risk is OK?", list(RISK_SHIFT), key="w_risk",
                                   help="Safe keeps a bigger cushion and hides risky homes.")
        new["beds"] = st.slider("Bedrooms, at least", 1, 5, key="w_beds")
        typed_zip = st.text_input("Work ZIP code (optional)", max_chars=5, key="w_work_zip", placeholder="76010",
                                  help="Drive times start from here. We keep only the ZIP, never your location.")
        new["work_zip"] = prefs["work_zip"]
        if typed_zip.strip() and zip_problem(typed_zip.strip()):
            st.error(zip_problem(typed_zip.strip()))
        else:
            new["work_zip"] = typed_zip.strip() or None
        new["drive"] = st.slider("Longest drive to work (minutes)", 10, 45, key="w_drive")
        new["tol"] = st.selectbox("Repairs you can handle", TOLERANCES, key="w_tol")
        new = clean_prefs({k: int(v) if k in ("budget", "beds", "drive") else v for k, v in new.items()})
        if new != prefs:
            st.session_state.prefs = new
            if st.session_state.user["token"]:
                accounts.save_prefs(st.session_state.user["token"], new)
            st.toast("Preferences saved")
        st.page_link(PAGES["homes"], label="See my homes")


def page_account():
    need_user()
    user = st.session_state.user
    masthead("Account")
    col = reading_column()
    with col:
        if not user["token"]:
            st.write("You're browsing as a guest, so your answers aren't saved.")
            if st.button("Create an account to save them", type="primary"):
                st.switch_page(PAGES["create"])                    # keeps the guest's answers
            if st.button("Start over"):
                end_session(forget_device=False)
                st.switch_page(PAGES["start"])
            return

        st.markdown(f"### {html.escape(user['name'])}")
        st.write("We remember you on this device, so you don't need to sign in each time.")
        if st.button("Sign out"):
            accounts.sign_out(user["token"])
            end_session(forget_device=True)
            st.switch_page(PAGES["sign_in"])

        st.markdown("### Your data")
        data = accounts.export(user["token"]) or {}
        st.download_button("Download my data", json.dumps(data, indent=2), file_name="tracefort-my-data.json",
                           mime="application/json", help="Your name, preferences and when you agreed to the Terms.")

        st.markdown("### Delete my account")
        st.write("This permanently deletes your name, PIN and preferences, and signs you out everywhere. "
                 "It can't be undone.")
        sure = st.checkbox("I understand, delete my account", key="del_sure")
        if st.button("Delete my account", type="primary", disabled=not sure):
            accounts.delete_account(user["token"])
            end_session(forget_device=True)
            st.session_state.flash = "Your account and answers were deleted."
            st.switch_page(PAGES["start"])


def text_page(title, body):
    def render():
        masthead(title)
        with reading_column():
            st.markdown(body)
    return render


def page_contact():
    masthead("Contact")
    with reading_column():
        st.write("Questions, a problem using TraceFort, or something hard to use? Send us a note. "
                 "Only the TraceFort team reads these, in a PIN-protected inbox. "
                 "For bidding, deposits or a specific auction, contact Xome directly.")
        with st.form("contact", clear_on_submit=True):
            who = st.text_input("Your first name (optional)", max_chars=40)
            msg = st.text_area("Your message", max_chars=2000, height=160)
            sent = st.form_submit_button("Send message", type="primary")
        if sent:
            if len(msg.strip()) < 5:
                st.error("Write a few words so we know how to help.")
            else:
                accounts.save_message(who, msg)
                st.success("Thanks, we got your message.")


def admin_pin():
    """Team inbox PIN from .streamlit/secrets.toml (admin_pin = "...") or the TRACEFORT_ADMIN_PIN env var."""
    try:
        return str(st.secrets["admin_pin"])
    except Exception:                                   # no secrets file, or no key in it
        return os.environ.get("TRACEFORT_ADMIN_PIN", "")


def page_inbox():
    masthead("Team inbox")
    with reading_column():
        if not admin_pin():
            st.warning("The inbox is locked until a team PIN is set in .streamlit/secrets.toml (admin_pin).")
            return
        if not st.session_state.get("admin_ok"):
            st.write("For the TraceFort team only.")
            with st.form("inbox_pin", border=False):
                pin = st.text_input("Team PIN", type="password")
                go = st.form_submit_button("Open inbox", type="primary")
            if go:
                if accounts.attempt("__admin__", secrets.compare_digest(pin.encode(), admin_pin().encode())):
                    st.session_state.admin_ok = True
                    st.rerun()
                wait = accounts.lock_remaining("__admin__")
                st.error(f"Too many wrong tries. The inbox is paused for {(wait + 59) // 60} more minute(s)."
                         if wait else "That PIN isn't right.")
            return
        msgs = accounts.list_messages()
        top, lock = st.columns([4, 1], vertical_alignment="center")
        top.write(f"**{len(msgs)}** message(s), newest first.")
        if lock.button("Lock inbox"):
            st.session_state.pop("admin_ok", None)
            st.rerun()
        for m in msgs:
            with st.container(border=True):
                when = datetime.fromtimestamp(m["at"]).strftime("%b %d, %Y %I:%M %p")
                st.caption(f"{when} · {m['name'] or 'No name given'}")
                st.text(m["message"])                    # st.text: shown exactly as typed, never as HTML
                if st.button("Delete", key=f"del_msg_{m['id']}"):
                    accounts.delete_message(m["id"])
                    st.rerun()


CHAT_STARTERS = ["I'm new to this. Where do I start?", "What is a foreclosure auction?",
                 "What's a walk-away bid?", "Why is home #1 my best match?",
                 "How do I use this site?", "Are there extra fees at auction?"]


def anthropic_key():
    """Claude API key from .streamlit/secrets.toml (anthropic_api_key = "...") or ANTHROPIC_API_KEY."""
    try:
        return str(st.secrets["anthropic_api_key"])
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")


@st.dialog("Ask TraceFort", width="large")
def chat_window():
    """The helper opens over whatever page you're on (floating button), so it's part of the site, not a menu page.
    st.rerun(scope="fragment") redraws only this window, so it stays open between questions."""
    key = anthropic_key()
    st.caption("Answers come from Claude, an AI made by Anthropic, using your preferences and your top 3 sample "
               "homes. It can make mistakes. Estimates for education only, not financial advice. "
               "Don't share personal details. Chats aren't saved after you leave.")
    if not key:
        st.info("AI answers are off on this computer, so you'll get quick built-in answers.")

    prefs = st.session_state.get("prefs") if st.session_state.user else None
    top, count = [], 0
    if prefs:
        ranked = my_ranked(prefs)
        top = list(ranked.head(3).itertuples())
        count = int(ranked["viable"].sum()) if not ranked.empty else 0

    chat = st.session_state.setdefault("chat", [])
    thread = st.container()                              # messages go here, so the type box stays below them
    with thread:
        for m in chat:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])               # Markdown only: HTML in a reply is shown as text

    asked = None
    if not chat:
        starters = st.container()
        starters.write("Try one of these, or type your own question below.")
        cols = starters.columns(2)
        for i, starter in enumerate(CHAT_STARTERS):
            if cols[i % 2].button(starter, key=f"starter_{i}", width="stretch"):
                asked = starter
    used = sum(m["role"] == "user" for m in chat)
    full = used >= chatbot.MAX_USER_MESSAGES
    typed = st.chat_input("Ask about auctions or your homes", max_chars=chatbot.MAX_CHARS, disabled=full)
    if full:
        st.caption("That's the chat limit for this visit. Clear the chat to start a new one.")
    asked = asked or typed
    if asked:
        chat.append({"role": "user", "content": asked})
        with thread:
            with st.chat_message("user"):
                st.markdown(asked)
            with st.chat_message("assistant"):
                client = chatbot.make_client(key) if key else None
                if client:
                    reply = st.write_stream(chatbot.stream_reply(client, chat,
                                                                 chatbot.context_block(prefs, top, count)))
                else:
                    reply = chatbot.offline_answer(asked, top)
                    st.markdown(reply)
        chat.append({"role": "assistant", "content": reply if isinstance(reply, str) else "".join(map(str, reply))})
        st.rerun(scope="fragment")                       # starter buttons go away; the window stays open
    if chat and st.button("Clear chat", type="tertiary"):
        st.session_state.chat = []
        st.rerun(scope="fragment")


def chat_button():
    with st.container(key="chat_fab"):
        if st.button("Ask TraceFort", icon=":material/chat:", type="primary", key="open_chat",
                     help="Questions about auctions, your homes or this site"):
            chat_window()


def cookie_notice():
    """Shown until the visitor closes it; closing sets a 1-year cookie so it stays closed."""
    if st.context.cookies.get(NOTICE_COOKIE) == "ok" or st.session_state.get("notice_closed"):
        return
    with st.container(border=True):
        text, ok = st.columns([5, 1], vertical_alignment="center")
        with text:
            st.markdown("We use a few small cookies to keep you signed in and protect forms. No ads. "
                        "Our free host, Streamlit, also sets its own analytics cookies.")
            st.page_link(PAGES["cookies"], label="Read the Cookie Policy")
        if ok.button("Got it", key="cookie_ok", type="primary", width="stretch"):
            st.session_state.notice_closed = True
            set_cookie(NOTICE_COOKIE, "ok", ONE_YEAR)
            st.rerun()


# ======================================= site frame ===============================================

def top_bar():
    """☰ (side panel) + wordmark left; Sign in / Create account right (or "Hi, name" + Account).
    One row on phones too: CSS stops the columns from stacking, and the bar is fixed so it stays put."""
    user = st.session_state.user
    signed_in = user is not None and user["token"]
    with st.container(key="topbar"):
        cols = st.columns([6, 1, 1], vertical_alignment="center")
        cols[0].markdown("<div class='brand' role='img' aria-label='TraceFort'>TRACE<span>FORT</span></div>",
                         unsafe_allow_html=True)
        if not signed_in:
            if cols[1].button("Sign in", key="top_sign_in"):
                st.switch_page(PAGES["sign_in"])
            if cols[2].button("Create account", key="top_create", type="primary"):
                st.switch_page(PAGES["create"])                        # a real form; guests keep their answers
        else:
            cols[1].markdown(f"<div class='who'>Hi, {html.escape(user['name'])}</div>", unsafe_allow_html=True)
            if cols[2].button("Account", key="top_account"):
                st.switch_page(PAGES["account"])


def side_menu():
    """What the ☰ button opens."""
    user = st.session_state.user
    with st.sidebar:
        st.markdown("<div class='brand'>TRACE<span>FORT</span></div>", unsafe_allow_html=True)
        if user is None:                                        # brand new visitor
            st.page_link(PAGES["start"], label="Start here (guest)", icon=":material/explore:")
            st.page_link(PAGES["sign_in"], label="Sign in", icon=":material/login:")
            st.page_link(PAGES["create"], label="Create account", icon=":material/person_add:")
        else:
            who = html.escape(user["name"]) if user["token"] else "Guest"
            st.markdown(f"<p class='menu-who'>Hi, {who}</p>", unsafe_allow_html=True)
            for key, icon in (("homes", "home"), ("investor", "query_stats"), ("prefs", "tune"),
                              ("account", "person")):
                st.page_link(PAGES[key], icon=f":material/{icon}:")
            if not user["token"]:                               # guests can save or switch to their account
                st.page_link(PAGES["create"], label="Create account to save", icon=":material/person_add:")
                st.page_link(PAGES["sign_in"], label="Sign in", icon=":material/login:")
        st.divider()
        for key in ("about", "how", "contact"):
            st.page_link(PAGES[key])
        st.divider()
        for key in ("terms", "privacy", "cookies", "access"):
            st.page_link(PAGES[key])


def site_footer():
    st.divider()
    rows = [[("about", "About"), ("how", "How it works"), ("contact", "Contact")],
            [("terms", "Terms of Use"), ("privacy", "Privacy Policy"), ("cookies", "Cookie Policy"),
             ("access", "Accessibility")]]
    for row in rows:                                    # two short rows so no label gets cut off
        for col, (key, label) in zip(st.columns(4), row):
            col.page_link(PAGES[key], label=label)
    st.markdown(
        "<div class='foot'>Built by <a href='https://github.com/SHRAMRAI' target='_blank'>Shramika Rai</a>, "
        "<a href='https://github.com/gyawaliprajita50' target='_blank'>Prajita Gyawali</a> and "
        "<a href='https://github.com/forbidynaliew' target='_blank'>Prashna Pandey</a> · "
        "<a href='https://github.com/SHRAMRAI/TraceFort' target='_blank'>Code on GitHub</a><br>"
        "© 2026 TraceFort, a student project from HackUTA 2026. "
        "Built for the Xome challenge; not affiliated with or endorsed by Xome. "
        f"{ESTIMATE_NOTE}<br>Home values: Zillow Home Value Index. "
        "Map data © OpenStreetMap contributors, map tiles © CARTO. Homes shown are samples.</div>",
        unsafe_allow_html=True,
    )


signed_in = st.session_state.user is not None
shown = lambda flag: "visible" if flag else "hidden"
PAGES.update({
    "start": st.Page(page_start, title="Start here", url_path="start", default=not signed_in,
                     visibility=shown(not signed_in)),
    "sign_in": st.Page(page_sign_in, title="Sign in", url_path="sign-in",
                       visibility=shown(not signed_in or not st.session_state.user["token"])),
    "create": st.Page(page_create, title="Create account", url_path="create-account",
                      visibility=shown(not signed_in or not st.session_state.user["token"])),
    "homes": st.Page(page_homes, title="Your best homes", url_path="homes", default=signed_in,
                     visibility=shown(signed_in)),
    "investor": st.Page(page_investor, title="Investor mode", url_path="investor", visibility=shown(signed_in)),
    "prefs": st.Page(page_prefs, title="My preferences", url_path="preferences", visibility=shown(signed_in)),
    "account": st.Page(page_account, title="Account", url_path="account", visibility=shown(signed_in)),
    "about": st.Page(text_page("About TraceFort", site_text.ABOUT), title="About", url_path="about"),
    "how": st.Page(text_page("How it works", site_text.HOW), title="How it works", url_path="how-it-works"),
    "contact": st.Page(page_contact, title="Contact", url_path="contact"),
    "terms": st.Page(text_page("Terms of Use", site_text.TERMS), title="Terms of Use", url_path="terms"),
    "privacy": st.Page(text_page("Privacy Policy", site_text.PRIVACY), title="Privacy Policy", url_path="privacy"),
    "cookies": st.Page(text_page("Cookie Policy", site_text.COOKIES), title="Cookie Policy", url_path="cookies"),
    "access": st.Page(text_page("Accessibility", site_text.ACCESSIBILITY), title="Accessibility",
                      url_path="accessibility"),
    "inbox": st.Page(page_inbox, title="Team inbox", url_path="inbox", visibility="hidden"),   # team only: /inbox
})
nav = st.navigation({
    ("Your account" if signed_in else "Get started"): [PAGES[k] for k in ("start", "sign_in", "create", "homes",
                                                                          "investor", "prefs", "account")],
    "TraceFort": [PAGES[k] for k in ("about", "how", "contact", "inbox")],
    "Legal": [PAGES[k] for k in ("terms", "privacy", "cookies", "access")],
}, position="hidden")                                    # pages are reached from the ☰ side panel and footer
top_bar()
side_menu()
if st.session_state.get("last_page") != nav.url_path:   # picked a page: on phones, close the side panel
    st.session_state.last_page = nav.url_path            # (desktop keeps it open beside the page)
    st.iframe(f"<!-- {html.escape(nav.url_path or 'home')} --><script>const d = window.parent.document; "   # unique per page,
              "if (window.parent.innerWidth < 768) "                                     # or Streamlit reuses the frame
              "d.querySelector('[data-testid=stSidebarCollapseButton] button, button[data-testid=stSidebarCollapseButton]')"
              "?.click();</script>", height=1)
cookie_notice()
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))
nav.run()
site_footer()
chat_button()
