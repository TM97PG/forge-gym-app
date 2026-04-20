from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any
from urllib.parse import quote

from flask import Flask, flash, jsonify, redirect, render_template, render_template_string, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
SEED_FILE = DATA_DIR / "seed.json"
RESEARCH_FILE = DATA_DIR / "research_sources.json"
FOODS_FILE = DATA_DIR / "foods.json"
DB_PATH_ENV = os.environ.get("FORGE_DB_PATH", "").strip()
DB_FILE = Path(DB_PATH_ENV) if DB_PATH_ENV else DATA_DIR / "forge.sqlite3"

app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder=str(TEMPLATES_DIR))
app.secret_key = os.environ.get("FORGE_SECRET_KEY", "forge-secret-2026")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FORGE_COOKIE_SECURE", "0") == "1"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

DEFAULT_ADMIN_USERNAME = os.environ.get("FORGE_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("FORGE_ADMIN_PASSWORD", "telemontdaljam1")
DEFAULT_MITAR_USERNAME = os.environ.get("FORGE_MITAR_USERNAME", "mitar")
DEFAULT_MITAR_PASSWORD = os.environ.get("FORGE_MITAR_PASSWORD", "telemont97daljam")
MIN_PASSWORD_LENGTH = 8
TRIAL_DAYS = 15


COACHES = {
    "strength": {
        "name": "Vera Iron",
        "role": "Strength Coach",
        "tone": "Build top-end force with clean reps and clear progression.",
        "accent": "orange",
    },
    "hypertrophy": {
        "name": "Noah Mass",
        "role": "Hypertrophy Coach",
        "tone": "Drive volume, tension and pump without junk fatigue.",
        "accent": "gold",
    },
    "conditioning": {
        "name": "Mila Engine",
        "role": "Conditioning Coach",
        "tone": "Keep output high, recover fast and protect the joints.",
        "accent": "red",
    },
    "mobility": {
        "name": "Tara Flow",
        "role": "Recovery Coach",
        "tone": "Restore range, unlock positions and keep you fresh for the next block.",
        "accent": "sand",
    },
}

LANGUAGES = {
    "me": {
        "code": "me",
        "flag": "CG",
        "name": "CG",
        "folders": "Folderi",
        "plans": "Planovi",
        "calendar": "Kalendar",
        "users": "Korisnici",
        "logout": "Izlaz",
        "hero_kicker": "Adaptivni atletski sistem",
        "hero_text": "Licna gym aplikacija sa posebnim korisnickim profilom, trenerima, dnevnim zadacima i kalendarom koji se prilagodjava cilju osobe.",
        "mobile_center": "Mobilni kontrolni centar",
        "profile_title": "Tvoji podaci",
        "plans_title": "Izaberi svoj plan",
        "assistant_title": "Personalni trener",
        "mission_title": "Sta je danas bitno",
        "wellness_title": "Wellness",
        "planner_title": "Sedmicni raspored",
        "calendar_title": "Licni kalendar",
        "coaches_title": "Tvoj coaching tim",
        "today_title": "Danasnji plan",
        "nutrition_title": "Ishrana danas",
        "chat_title": "AI trener",
        "checkin_title": "Dnevni check-in",
        "shopping_title": "Shopping lista",
        "progress_title": "Trend napretka",
        "pricing_title": "Planovi i pristup",
        "legal_terms": "Uslovi koriscenja",
        "legal_privacy": "Privatnost",
    },
    "en": {
        "code": "en",
        "flag": "EN",
        "name": "EN",
        "folders": "Folders",
        "plans": "Plans",
        "calendar": "Calendar",
        "users": "Users",
        "logout": "Logout",
        "hero_kicker": "Adaptive athlete system",
        "hero_text": "Personal gym app with separate user data, personal coaches, daily tasks and a calendar that adapts to the athlete goal.",
        "mobile_center": "Mobile control center",
        "profile_title": "Your data",
        "plans_title": "Choose your plan",
        "assistant_title": "Personal coach",
        "mission_title": "What matters today",
        "wellness_title": "Wellness",
        "planner_title": "Weekly layout",
        "calendar_title": "Personal calendar",
        "coaches_title": "Your coaching team",
        "today_title": "Today's plan",
        "nutrition_title": "Nutrition today",
        "chat_title": "AI trainer",
        "checkin_title": "Daily check-in",
        "shopping_title": "Shopping list",
        "progress_title": "Progress trends",
        "pricing_title": "Plans and access",
        "legal_terms": "Terms",
        "legal_privacy": "Privacy",
    },
}

SUBSCRIPTION_PLANS = [
    {"key": "starter", "name": "Starter", "price": "0 EUR", "detail": f"Free full-access trial for the first {TRIAL_DAYS} days."},
    {"key": "pro", "name": "Pro", "price": "19 EUR", "detail": "AI coach, adaptive calendar and detailed nutrition."},
    {"key": "elite", "name": "Elite", "price": "49 EUR", "detail": "Full premium coaching flow, admin tools and launch-grade insights."},
]

COMMERCIAL_OFFERS = [
    {"title": "By sessions weekly", "price": "14-29 EUR", "detail": "Charge more as the user unlocks 3, 4 or 6 guided sessions per week."},
    {"title": "By coach access", "price": "19-39 EUR", "detail": "One coach lane for Starter, full coaching squad and AI trainer for higher tiers."},
    {"title": "By goal system", "price": "24-49 EUR", "detail": "Bodybuilding, cut, muscle gain and performance can each be premium guided programs."},
    {"title": "By accountability", "price": "9-19 EUR", "detail": "Daily check-ins, weekly reviews and stricter coaching feedback can be an add-on layer."},
]

DISCOUNT_CODES = {
    "FORGE10": {"percent": 10, "label": "Launch 10%"},
    "PRO20": {"percent": 20, "label": "Pro offer 20%"},
    "ELITE25": {"percent": 25, "label": "Elite offer 25%"},
}

EXERCISE_TECHNIQUE_GUIDES = {
    "Back squat": {
        "source_label": "ACE Squat fundamentals",
        "source_url": "https://www.acefitness.org/resources/everyone/exercise-library/135/bodyweight-squat/",
        "cues": [
            "Brace the core before the descent.",
            "Keep chest up while hips move back.",
            "Drive evenly through the floor on the way up.",
        ],
    },
    "Bench press": {
        "source_label": "ACE Chest Press",
        "source_url": "https://www.acefitness.org/resources/everyone/exercise-library/19/chest-press/",
        "cues": [
            "Pull shoulders down and back into the bench.",
            "Lower under control to mid chest.",
            "Press up without losing wrist position or arching hard.",
        ],
    },
    "Romanian deadlift": {
        "source_label": "ACE Romanian Deadlift",
        "source_url": "https://www.acefitness.org/continuing-education/certified/may-2025/8865/the-ace-do-it-better-series-the-romanian-deadlift/",
        "cues": [
            "Push hips back first and keep a long spine.",
            "Lower until hamstrings load, not until the back rounds.",
            "Drive feet into the floor and finish with the hips.",
        ],
    },
    "Lat pulldown or pull-up": {
        "source_label": "ACE Seated Lat Pulldown",
        "source_url": "https://www.acefitness.org/resources/everyone/exercise-library/158/seated-lat-pulldown/",
        "cues": [
            "Set shoulders down and back before pulling.",
            "Drive elbows down toward the torso.",
            "Return under control without shrugging up early.",
        ],
    },
    "Chest supported row": {
        "source_label": "ACE Seated Row",
        "source_url": "https://www.acefitness.org/resources/everyone/exercise-library/48/seated-row/",
        "cues": [
            "Stay tall through the chest and keep a flat torso.",
            "Pull elbows back close to the rib cage.",
            "Pause briefly, then extend the arms without rounding forward.",
        ],
    },
    "Incline dumbbell press": {
        "source_label": "ACE Chest Press",
        "source_url": "https://www.acefitness.org/resources/everyone/exercise-library/19/chest-press/",
        "cues": [
            "Pack the shoulders before the first rep.",
            "Lower with control and keep forearms stacked.",
            "Press to full extension without losing bench contact.",
        ],
    },
    "Cable lateral raise": {
        "source_label": "ACE Lateral Raise",
        "source_url": "https://www.acefitness.org/resources/everyone/exercise-library/26/lateral-raise/",
        "cues": [
            "Brace the torso and keep shoulders down.",
            "Raise arms out and slightly forward, not straight behind the body.",
            "Stop around shoulder height and lower smoothly.",
        ],
    },
    "Goblet squat": {
        "source_label": "ACE Squat fundamentals",
        "source_url": "https://www.acefitness.org/resources/everyone/exercise-library/135/bodyweight-squat/",
        "cues": [
            "Hold the weight close and stay tall through the chest.",
            "Sit between the hips with the core braced.",
            "Drive out of the bottom through the whole foot.",
        ],
    },
    "Hip thrust": {
        "source_label": "ACE glute bridge / hip extension progression",
        "source_url": "https://www.acefitness.org/resources/pros/expert-articles/7963/what-is-the-difference-between-romanian-deadlift-vs-deadlift/",
        "cues": [
            "Keep ribs down before the thrust.",
            "Drive through heels and fully extend the hips.",
            "Pause at lockout without overextending the lower back.",
        ],
    },
}


def plan_price_map() -> dict[str, int]:
    return {"starter": 0, "pro": 19, "elite": 49}


def resolve_discount_code(code: str) -> dict[str, Any]:
    normalized = str(code or "").strip().upper()
    if not normalized:
        return {"code": "", "percent": 0, "label": "No discount"}
    item = DISCOUNT_CODES.get(normalized)
    if not item:
        return {"code": normalized, "percent": 0, "label": "Invalid code"}
    return {"code": normalized, "percent": int(item["percent"]), "label": str(item["label"])}


def valid_subscription_tier(value: str, default: str = "starter") -> str:
    allowed = {item["key"] for item in SUBSCRIPTION_PLANS}
    return value if value in allowed else default


INLINE_LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Forge Login</title>
  <style>
    :root { --bg:#060606; --panel:#111315; --line:rgba(255,255,255,.08); --text:#f6efdf; --muted:#c4b39d; --accent:#ff8b39; --accent2:#ffc14d; --glass:rgba(255,255,255,.045); }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; display:grid; place-items:center; padding:12px; color:var(--text); font-family:Arial,Helvetica,sans-serif; background:radial-gradient(circle at top left, rgba(255,139,57,.22), transparent 28%), radial-gradient(circle at bottom right, rgba(255,193,77,.14), transparent 24%), linear-gradient(180deg,#050505,#111); }
    .card { width:min(1080px,100%); background:linear-gradient(180deg, rgba(22,22,24,.96), rgba(14,14,15,.96)); border:1px solid var(--line); border-radius:32px; padding:28px; box-shadow:0 30px 80px rgba(0,0,0,.45); position:relative; overflow:hidden; }
    .card:before { content:""; position:absolute; inset:0; background:linear-gradient(125deg, transparent 0 35%, rgba(255,255,255,.04) 50%, transparent 65%); pointer-events:none; }
    .eyebrow,.mini { text-transform:uppercase; letter-spacing:.14em; font-size:11px; color:var(--muted); font-weight:700; }
    .pill { display:inline-flex; padding:10px 12px; border-radius:999px; background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-weight:800; font-size:11px; letter-spacing:.12em; text-transform:uppercase; }
    h1 { margin:12px 0 8px; font-size:44px; line-height:.96; font-family:Georgia,serif; }
    p { color:#eadbc8; line-height:1.7; }
    .grid { display:grid; gap:12px; grid-template-columns:repeat(3,minmax(0,1fr)); margin:22px 0; }
    .feature,.flash,.login-side { padding:14px; border-radius:20px; background:var(--glass); border:1px solid var(--line); }
    .feature strong,.login-side strong { display:block; margin-top:8px; font-size:18px; }
    form { display:grid; gap:12px; margin-top:14px; }
    label { display:grid; gap:8px; font-size:14px; color:var(--muted); }
    input,button { min-height:54px; border-radius:16px; border:1px solid var(--line); }
    input { width:100%; padding:12px 14px; background:rgba(255,255,255,.05); color:var(--text); }
    button { background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-weight:800; cursor:pointer; }
    .stack,.login-shell-grid,.pricing-login,.hero-gallery { display:grid; gap:10px; margin:14px 0; }
    .login-shell-grid { grid-template-columns:1.1fr .9fr; align-items:start; }
    .hero-gallery { grid-template-columns:1.1fr .9fr; margin-top:18px; }
    .hero-photo { min-height:210px; border-radius:24px; border:1px solid var(--line); background-size:cover; background-position:center; position:relative; overflow:hidden; }
    .hero-photo:after { content:""; position:absolute; inset:0; background:linear-gradient(180deg, rgba(0,0,0,.05), rgba(0,0,0,.55)); }
    .hero-photo strong,.hero-photo span { position:relative; z-index:1; display:block; padding:16px 16px 0; }
    .brand-row { display:flex; align-items:center; justify-content:space-between; gap:16px; }
    .logo-mark { width:58px; height:58px; border-radius:18px; display:grid; place-items:center; color:#17110a; background:linear-gradient(135deg,var(--accent),var(--accent2)); box-shadow:0 14px 28px rgba(255,139,57,.24); overflow:hidden; }
    .logo-mark svg { width:36px; height:36px; display:block; }
    .pricing-login { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .offer { padding:14px; border-radius:20px; background:rgba(255,255,255,.04); border:1px solid var(--line); }
    .offer strong { display:block; margin:8px 0 6px; font-size:18px; }
    .offer .price { display:inline-flex; margin-top:4px; padding:6px 10px; border-radius:999px; background:rgba(255,255,255,.06); font-size:12px; font-weight:800; }
    @media (max-width: 900px) { .grid,.login-shell-grid,.hero-gallery,.pricing-login { grid-template-columns:1fr; } h1 { font-size:36px; } .card { padding:20px; border-radius:26px; } }
  </style>
</head>
<body>
  <main class="card">
    <div class="brand-row">
      <div style="display:flex;align-items:center;gap:14px;">
        <div class="logo-mark">
          <svg viewBox="0 0 64 64" aria-hidden="true" fill="none">
            <path d="M18 50V14h29v8H28v8h16v8H28v12H18Z" fill="#17110A"/>
            <path d="M43 14h7l-7 7V14Z" fill="#17110A" opacity=".65"/>
          </svg>
        </div>
        <div>
    <div class="pill">APP.PY ONLY BUILD V59</div>
          <div class="eyebrow" style="margin-top:10px;">Forge Athlete OS</div>
        </div>
      </div>
      <div class="mini">Premium gym performance system</div>
    </div>
    <h1>Secure athlete login V59</h1>
    <p>Uloguj se, otvori svoj plan i nastavi tacno tamo gdje si stao.</p>
    <div class="hero-gallery">
      <article class="hero-photo" style="background-image:url('https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=1200&q=80');">
        <strong>Elite gym atmosphere</strong>
        <span>Strength, physique and performance in one polished flow.</span>
      </article>
      <article class="hero-photo" style="background-image:url('https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=1200&q=80');">
        <strong>Personal coaching UX</strong>
        <span>Built to feel like a private trainer, not just a tracker.</span>
      </article>
    </div>
    <div class="grid">
      <article class="feature"><div class="mini">Profile</div><strong>Custom athlete data</strong><p>Ime, prezime, visina, kilaza, godine i cilj po korisniku.</p></article>
      <article class="feature"><div class="mini">Training</div><strong>3 predloga plana</strong><p>Biranje vise predlozenih treninga prema cilju korisnika.</p></article>
      <article class="feature"><div class="mini">Calendar</div><strong>Plan po danima</strong><p>Izabrani plan ide direktno u korisnicki kalendar.</p></article>
    </div>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
      <div class="stack">
        {% for message in messages %}
        <div class="flash">{{ message }}</div>
        {% endfor %}
      </div>
      {% endif %}
    {% endwith %}
    <div class="login-shell-grid">
      <form method="post">
        <label>Username <input type="text" name="username" placeholder="Username" required></label>
        <label>Password <input type="password" name="password" placeholder="Password" required></label>
        <button type="submit">Udji u Forge</button>
        <a href="/register" style="display:inline-flex;justify-content:center;align-items:center;min-height:52px;border-radius:16px;border:1px solid var(--line);text-decoration:none;color:var(--text);background:rgba(255,255,255,.04);font-weight:700;">Napravi nalog</a>
      </form>
      <div class="login-side">
        <div class="mini">Private access</div>
        <strong>Mobile athlete login</strong>
        <p>Cist ulaz, odvojeni nalozi i zasebni planovi za svakog korisnika.</p>
        <div class="mini" style="margin-top:16px;">Monetization ideas</div>
        <div class="pricing-login">
          {% for item in commercial_offers %}
          <article class="offer">
            <div class="price">{{ item.price }}</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
          </article>
          {% endfor %}
        </div>
      </div>
    </div>
  </main>
</body>
</html>
"""


INLINE_REGISTER_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Forge Registration</title>
  <style>
    :root { --bg:#060606; --panel:#111315; --line:rgba(255,255,255,.08); --text:#f6efdf; --muted:#c4b39d; --accent:#ff8b39; --accent2:#ffc14d; --glass:rgba(255,255,255,.045); }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; display:grid; place-items:center; padding:12px; color:var(--text); font-family:Arial,Helvetica,sans-serif; background:radial-gradient(circle at top left, rgba(255,139,57,.22), transparent 28%), radial-gradient(circle at bottom right, rgba(255,193,77,.14), transparent 24%), linear-gradient(180deg,#050505,#111); }
    .card { width:min(760px,100%); background:linear-gradient(180deg, rgba(22,22,24,.96), rgba(14,14,15,.96)); border:1px solid var(--line); border-radius:32px; padding:28px; box-shadow:0 30px 80px rgba(0,0,0,.45); }
    .mini { text-transform:uppercase; letter-spacing:.14em; font-size:11px; color:var(--muted); font-weight:700; }
    .pill { display:inline-flex; padding:10px 12px; border-radius:999px; background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-weight:800; font-size:11px; letter-spacing:.12em; text-transform:uppercase; }
    h1 { margin:12px 0 8px; font-size:42px; line-height:.96; font-family:Georgia,serif; }
    p { color:#eadbc8; line-height:1.7; }
    .grid,.plan-grid { display:grid; gap:12px; grid-template-columns:repeat(2,minmax(0,1fr)); margin-top:18px; }
    label { display:grid; gap:8px; font-size:14px; color:var(--muted); }
    input,select,button { width:100%; min-height:52px; border-radius:16px; border:1px solid var(--line); font:inherit; }
    input,select { padding:12px 14px; background:rgba(255,255,255,.05); color:var(--text); }
    button { background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-weight:800; cursor:pointer; }
    .full { grid-column:1 / -1; }
    .flash,.plan-card { margin:14px 0; padding:14px; border-radius:18px; background:var(--glass); border:1px solid var(--line); }
    .plan-card strong { display:block; margin:8px 0 6px; font-size:18px; }
    @media (max-width: 760px) { .grid,.plan-grid { grid-template-columns:1fr; } .card { padding:20px; } h1 { font-size:34px; } }
  </style>
</head>
<body data-view-mode="{{ payload.view_mode }}">
  <main class="card">
    <div class="pill">Forge registration</div>
    <div class="mini" style="margin-top:14px;">Create your athlete account</div>
    <h1>Napravi svoj nalog</h1>
    <p>Korisnik moze sam da napravi nalog, pa ga Forge odmah vodi na onboarding da unese svoje adaptive filtere i ciljeve.</p>
    <div class="plan-grid">
      {% for plan in subscription_plans %}
      <article class="plan-card">
        <div class="mini">{{ plan.price }}</div>
        <strong>{{ plan.name }}</strong>
        <p>{{ plan.detail }}</p>
      </article>
      {% endfor %}
    </div>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}
        <div class="flash">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="post" class="grid">
      <label>Ime i prezime<input type="text" name="full_name" required></label>
      <label>Username<input type="text" name="username" required></label>
      <label>Password<input type="password" name="password" required></label>
      <label>Pol
        <select name="gender">
          <option value="male">Musko</option>
          <option value="female">Zensko</option>
        </select>
      </label>
      <label>Godine<input type="number" name="age" value="25" min="13" max="100"></label>
      <label>Visina cm<input type="number" step="0.1" name="height_cm" value="180"></label>
      <label>Kilaza kg<input type="number" step="0.1" name="weight_kg" value="80"></label>
      <label>Cilj
        <select name="goal">
          <option value="performance">Performance</option>
          <option value="muscle">Muscle</option>
          <option value="cut">Cut</option>
        </select>
      </label>
      <label>Paket
        <select name="subscription_tier">
          {% for plan in subscription_plans %}
          <option value="{{ plan.key }}">{{ plan.name }} - {{ plan.price }}</option>
          {% endfor %}
        </select>
      </label>
      <button class="full" type="submit">Kreiraj nalog</button>
      <a class="full" href="/login" style="display:inline-flex;justify-content:center;align-items:center;min-height:52px;border-radius:16px;border:1px solid var(--line);text-decoration:none;color:var(--text);background:rgba(255,255,255,.04);font-weight:700;">Nazad na login</a>
    </form>
  </main>
</body>
</html>
"""


INLINE_DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Forge Dashboard</title>
  <style>
    :root { --bg:#060505; --panel:rgba(15,14,16,.94); --panel-soft:rgba(24,20,18,.86); --line:rgba(255,255,255,.08); --text:#fbf4e8; --muted:#cbb79d; --orange:#f48b38; --gold:#f2c15a; --red:#d65d5d; --green:#59cf82; --teal:#46c7c7; --blue:#6aa8ff; --plum:#42261c; }
    * { box-sizing:border-box; } html { scroll-behavior:smooth; }
    body { margin:0; color:var(--text); background:
      radial-gradient(circle at top left, rgba(244,139,56,.18), transparent 24%),
      radial-gradient(circle at right 18%, rgba(242,193,90,.15), transparent 20%),
      radial-gradient(circle at bottom right, rgba(70,199,199,.08), transparent 26%),
      linear-gradient(180deg,#060505,#0d0d0f 50%,#070707); font-family:Arial,Helvetica,sans-serif; }
    .shell { width:min(1280px, calc(100vw - 24px)); margin:0 auto; padding:18px 0 118px; }
    .topbar,.hero,.panel,.option,.flash { background:var(--panel); border:1px solid var(--line); border-radius:26px; box-shadow:0 28px 90px rgba(0,0,0,.42); }
    .topbar { display:grid; grid-template-columns:1fr auto; gap:12px; align-items:center; padding:16px 18px; position:sticky; top:10px; z-index:4; backdrop-filter:blur(18px); margin-bottom:14px; background:linear-gradient(180deg, rgba(18,16,18,.96), rgba(14,13,15,.92)); }
    .toplinks { display:grid; grid-auto-flow:column; gap:10px; align-items:start; }
    .toplinks a,.logout,.pill,.tag { display:inline-flex; align-items:center; justify-content:center; padding:10px 12px; border-radius:999px; text-decoration:none; color:inherit; font-size:11px; text-transform:uppercase; letter-spacing:.12em; font-weight:800; }
    .pill,.logout { color:#17110a; background:linear-gradient(135deg,var(--orange),var(--gold)); }
    .toplinks a,.tag { border:1px solid var(--line); background:rgba(255,255,255,.05); }
    .hero { padding:34px; background:
      radial-gradient(circle at top right, rgba(242,193,90,.18), transparent 24%),
      radial-gradient(circle at left 8%, rgba(244,139,56,.24), transparent 30%),
      linear-gradient(140deg, rgba(93,42,24,.58), rgba(14,14,15,.96) 36%, rgba(122,75,29,.24)); }
    .mini { text-transform:uppercase; letter-spacing:.14em; font-size:11px; color:var(--muted); font-weight:800; }
    h1,h2,h3 { margin:0; font-family:Georgia,serif; line-height:.96; }
    h1 { font-size:clamp(38px, 7vw, 76px); }
    h2 { font-size:clamp(26px, 4vw, 42px); }
    .hero-head,.hero-user,.split,.section-head,.head-row { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; flex-wrap:wrap; }
    .hero p,.option p,.metric-note,.log p,.admin-note { color:#eadbc8; line-height:1.65; }
    .hero-kpis,.grid3,.grid4,.option-grid,.calendar-grid,.users-grid,.quickbar,.suggestion-grid,.meal-grid,.mission-grid,.folder-grid,.filter-grid,.planner-grid,.pr-grid,.today-kpis,.session-grid { display:grid; gap:14px; }
    .hero-kpis { grid-template-columns:repeat(4,minmax(0,1fr)); margin-top:18px; }
    .today-kpis { grid-template-columns:repeat(4,minmax(0,1fr)); margin-top:16px; }
    .session-grid { grid-template-columns:.95fr 1.05fr; margin-top:16px; }
    .grid3 { grid-template-columns:repeat(3,minmax(0,1fr)); }
    .grid4 { grid-template-columns:repeat(4,minmax(0,1fr)); }
    .quickbar { grid-template-columns:repeat(4,minmax(0,1fr)); margin-top:16px; }
    .quickbar a { padding:14px; border-radius:18px; text-decoration:none; text-align:center; background:rgba(255,255,255,.05); border:1px solid var(--line); font-size:12px; text-transform:uppercase; letter-spacing:.08em; font-weight:800; }
    .kpi,.option,.log,.user-card,.flash { padding:18px; }
    .kpi,.option,.log,.user-card { border-radius:22px; background:linear-gradient(180deg, rgba(26,24,25,.98), rgba(18,18,20,.98)); border:1px solid rgba(255,255,255,.06); }
    .kpi strong,.user-card strong,.option strong { display:block; margin-top:8px; font-size:24px; }
    .page { display:grid; grid-template-columns:1.08fr .92fr; gap:18px; margin-top:18px; }
    .span { grid-column:1 / -1; }
    .panel { padding:24px; }
    .section-head { margin-bottom:14px; }
    form { display:grid; gap:12px; }
    .form2 { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .full { grid-column:1 / -1; }
    label { display:grid; gap:8px; color:var(--muted); font-size:14px; }
    input,select,textarea,button { width:100%; min-height:52px; border-radius:16px; border:1px solid var(--line); font:inherit; }
    input,select,textarea { padding:12px 14px; background:rgba(255,255,255,.05); color:var(--text); }
    textarea { min-height:110px; resize:vertical; }
    button { background:linear-gradient(135deg,var(--orange),var(--gold)); color:#18110b; font-weight:800; cursor:pointer; }
    .panel-grid { display:grid; gap:16px; grid-template-columns:1.05fr .95fr; }
    .option-grid { margin-top:16px; }
    .option { background:linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02)), linear-gradient(135deg, rgba(241,90,36,.12), rgba(18,18,19,.96)); }
    .option ul,.list { margin:12px 0 0; padding-left:18px; display:grid; gap:8px; }
    .next,.notice { margin-top:14px; padding:16px; border-radius:18px; }
    .next { background:rgba(78,186,114,.12); border:1px solid rgba(78,186,114,.18); }
    .notice { background:rgba(255,176,0,.08); border:1px solid rgba(255,176,0,.18); }
    .logs { display:grid; gap:12px; max-height:780px; overflow:auto; }
    .users-grid,.meal-grid,.folder-grid,.planner-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .mission-grid { grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:16px; }
    .filter-grid { grid-template-columns:repeat(4,minmax(0,1fr)); margin-top:16px; }
    .achievement-grid { display:grid; gap:14px; grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:16px; }
    .pr-grid { grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:16px; }
    .coach-grid,.today-grid,.lang-switch,.calendar-lane,.trend-grid,.chat-grid,.pricing-grid { display:grid; gap:14px; }
    .coach-grid { grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:16px; }
    .today-grid { grid-template-columns:1.1fr .9fr; margin-top:16px; }
    .calendar-lane { grid-template-columns:repeat(2,minmax(0,1fr)); margin-top:16px; }
    .trend-grid { grid-template-columns:repeat(4,minmax(0,1fr)); margin-top:16px; }
    .chat-grid { grid-template-columns:1fr 1fr; margin-top:16px; }
    .pricing-grid { grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:16px; }
    .lang-switch { grid-auto-flow:column; gap:8px; justify-content:end; }
    .lang-chip { display:inline-flex; align-items:center; gap:8px; padding:10px 12px; border-radius:999px; border:1px solid var(--line); text-decoration:none; color:inherit; background:rgba(255,255,255,.04); font-size:11px; font-weight:800; letter-spacing:.08em; }
    .lang-chip.active { background:linear-gradient(135deg,var(--orange),var(--gold)); color:#17110a; }
    .chat-stack { display:grid; gap:10px; max-height:320px; overflow:auto; margin-top:16px; }
    .bubble { padding:14px; border-radius:18px; border:1px solid var(--line); }
    .bubble.user { background:rgba(255,255,255,.06); }
    .bubble.coach { background:rgba(241,90,36,.08); }
    .flash-stack { display:grid; gap:10px; margin-bottom:14px; }
    .top-nav-links { display:flex; flex-wrap:wrap; gap:10px; justify-content:flex-end; }
    .top-nav-links a { display:inline-flex; align-items:center; justify-content:center; padding:10px 12px; border-radius:999px; text-decoration:none; color:inherit; font-size:11px; text-transform:uppercase; letter-spacing:.12em; font-weight:800; border:1px solid var(--line); background:rgba(255,255,255,.05); }
    .account-rail { display:flex; gap:10px; flex-wrap:wrap; margin-top:18px; }
    .account-chip { display:inline-flex; align-items:center; justify-content:center; padding:12px 14px; border-radius:18px; text-decoration:none; color:var(--text); background:rgba(255,255,255,.06); border:1px solid var(--line); font-size:12px; font-weight:800; letter-spacing:.06em; }
    .account-chip.primary { background:linear-gradient(135deg,var(--orange),var(--gold)); color:#17110a; }
    .utility-rail { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; margin-top:14px; }
    .utility-card { padding:14px 16px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.045); text-decoration:none; color:var(--text); }
    .utility-card strong { display:block; margin-top:8px; font-size:18px; }
.practical-shell { display:grid; gap:16px; margin-top:16px; }
.mission-shell { display:grid; grid-template-columns:1.15fr .85fr; gap:16px; margin-top:16px; }
.mission-lead { padding:22px; border-radius:26px; border:1px solid rgba(255,255,255,.08); background:linear-gradient(145deg, rgba(241,90,36,.18), rgba(255,255,255,.045) 44%, rgba(255,176,0,.14)); }
.mission-lead strong { display:block; margin-top:10px; font-size:34px; line-height:1.02; }
.mission-lead p { margin:10px 0 0; color:#eadbc8; line-height:1.6; }
.mission-notes { display:grid; gap:10px; margin-top:16px; }
.mission-note { padding:12px 14px; border-radius:16px; border:1px solid var(--line); background:rgba(255,255,255,.045); }
.signal-stack { display:grid; gap:12px; }
.signal-card { padding:16px; border-radius:22px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.025)); }
.signal-card strong { display:block; margin-top:8px; font-size:20px; }
.signal-card.progress { border-color:rgba(255,176,0,.22); }
.signal-card.warning { border-color:rgba(255,106,106,.22); }
.signal-card.action { border-color:rgba(241,90,36,.22); }
.signal-card.nutrition { border-color:rgba(89,193,115,.2); }
.quick-capture-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:16px; }
.capture-card { padding:15px 16px; border-radius:20px; border:1px solid var(--line); background:rgba(255,255,255,.045); text-decoration:none; color:var(--text); display:grid; gap:8px; }
.capture-card strong { font-size:19px; }
.snapshot-strip { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:16px; }
.snapshot-card { padding:16px; border-radius:20px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.025)); }
.snapshot-card strong { display:block; margin-top:8px; font-size:24px; }
.fast-lane-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }
.lane-card { padding:16px; border-radius:22px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.03)); text-decoration:none; color:var(--text); display:grid; gap:8px; }
.lane-card strong { font-size:20px; line-height:1.08; }
.lane-card.primary { background:linear-gradient(145deg, rgba(241,90,36,.2), rgba(255,255,255,.05) 44%, rgba(255,176,0,.14)); border-color:rgba(241,90,36,.24); }
.lane-card.train { border-color:rgba(255,176,0,.16); }
.lane-card.fuel { border-color:rgba(89,193,115,.18); }
.lane-card.track { border-color:rgba(112,150,255,.2); }
.tactical-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:16px; }
.tactical-card { padding:16px; border-radius:22px; border:1px solid var(--line); background:rgba(255,255,255,.045); text-decoration:none; color:var(--text); display:grid; gap:8px; }
.tactical-card strong { font-size:21px; line-height:1.08; }
.tactical-card .tag { width:max-content; }
.agenda-board { padding:18px; border-radius:24px; border:1px solid rgba(255,255,255,.08); background:linear-gradient(160deg, rgba(255,255,255,.05), rgba(255,255,255,.025)); }
.agenda-grid { display:grid; gap:10px; margin-top:14px; }
.agenda-row { display:grid; grid-template-columns:88px 1fr auto; gap:12px; align-items:start; padding:14px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
.agenda-time { font-size:18px; font-weight:900; letter-spacing:.04em; color:#f7efdf; }
.agenda-row strong { display:block; font-size:18px; }
.agenda-state { display:inline-flex; align-items:center; justify-content:center; padding:8px 10px; border-radius:999px; font-size:11px; font-weight:900; letter-spacing:.08em; text-transform:uppercase; border:1px solid var(--line); background:rgba(255,255,255,.05); }
.agenda-state.now { background:rgba(241,90,36,.16); border-color:rgba(241,90,36,.28); }
.agenda-state.done { background:rgba(78,186,114,.16); border-color:rgba(78,186,114,.26); }
.agenda-state.up-next { background:rgba(255,176,0,.12); border-color:rgba(255,176,0,.22); }
.folder-menu { display:flex; gap:10px; overflow:auto; padding:10px 2px 2px; margin-top:14px; scrollbar-width:none; }
.folder-menu::-webkit-scrollbar { display:none; }
.folder-menu a { white-space:nowrap; text-decoration:none; color:var(--text); padding:12px 14px; border-radius:16px; border:1px solid var(--line); background:rgba(255,255,255,.05); font-size:12px; font-weight:800; letter-spacing:.05em; }
.view-mode { display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }
.view-mode a { text-decoration:none; color:var(--text); padding:10px 12px; border-radius:14px; border:1px solid var(--line); background:rgba(255,255,255,.04); font-size:12px; font-weight:800; letter-spacing:.06em; }
.view-mode a.active { background:linear-gradient(135deg,var(--orange),var(--gold)); color:#17110a; }
.one-screen-home { margin-top:18px; display:grid; gap:16px; }
.one-screen-grid { display:grid; grid-template-columns:1.2fr .8fr; gap:16px; }
    .home-primary { padding:26px; border-radius:28px; border:1px solid rgba(255,255,255,.08); background:linear-gradient(155deg, rgba(244,139,56,.18), rgba(255,255,255,.05) 46%, rgba(242,193,90,.11)); }
.home-primary strong { display:block; margin-top:10px; font-size:34px; line-height:1.02; }
.home-primary p { margin:12px 0 0; color:#eadbc8; line-height:1.6; }
.home-stat-strip { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:16px; }
.home-stat { padding:16px; border-radius:20px; border:1px solid var(--line); background:rgba(255,255,255,.05); }
.home-stat strong { display:block; margin-top:8px; font-size:24px; }
.guided-day-shell { display:grid; gap:12px; }
    .guided-step { padding:16px; border-radius:20px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.03)); }
.guided-step strong { display:block; margin-top:8px; font-size:20px; }
.guided-step.now { border-color:rgba(255,176,0,.28); background:rgba(255,176,0,.08); }
.guided-step.done { opacity:.7; }
.mode-board { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
    .mode-card { padding:16px; border-radius:20px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02)); }
.mode-card.active { border-color:rgba(241,90,36,.34); background:rgba(241,90,36,.1); }
.mode-card strong { display:block; margin-top:8px; font-size:20px; }
.command-center { margin-top:18px; display:grid; gap:16px; }
.command-head { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap; }
.command-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }
.command-card { text-decoration:none; color:var(--text); padding:18px; border-radius:22px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.03)); display:grid; gap:8px; }
.command-card strong { font-size:18px; }
.command-card .tag { width:max-content; }
.hero-stage { display:grid; grid-template-columns:1.18fr .82fr; gap:16px; margin-top:20px; }
.hero-banner { padding:22px; border-radius:24px; border:1px solid rgba(255,255,255,.08); background:linear-gradient(160deg, rgba(255,255,255,.06), rgba(255,255,255,.02)); }
.hero-banner strong { display:block; margin-top:10px; font-size:32px; line-height:1.02; }
.hero-banner p { margin:10px 0 0; color:#eadbc8; }
.hero-actions { display:flex; gap:10px; flex-wrap:wrap; margin-top:16px; }
.hero-actions a { text-decoration:none; color:inherit; }
.delight-shell { margin-top:18px; display:grid; gap:16px; }
.delight-main { display:grid; grid-template-columns:1.05fr .95fr; gap:16px; }
.delight-lead { padding:22px; border-radius:26px; border:1px solid rgba(255,255,255,.08); background:linear-gradient(155deg, rgba(241,90,36,.18), rgba(255,255,255,.05) 42%, rgba(255,176,0,.12)); }
.delight-lead strong { display:block; margin-top:8px; font-size:34px; line-height:1.02; }
.delight-lead p { margin:12px 0 0; color:#eadbc8; line-height:1.6; }
.delight-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:16px; }
.delight-card { padding:16px; border-radius:22px; border:1px solid var(--line); background:rgba(255,255,255,.05); }
.delight-card strong { display:block; margin-top:8px; font-size:22px; line-height:1.1; }
.widget-rail { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }
.widget-chip { padding:16px; border-radius:22px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02)); text-decoration:none; color:var(--text); display:grid; gap:8px; }
.widget-chip strong { font-size:18px; }
.widget-chip .tag { width:max-content; }
.dock-row { display:flex; gap:10px; overflow:auto; padding-bottom:4px; scrollbar-width:none; }
.dock-row::-webkit-scrollbar { display:none; }
.dock-row a { text-decoration:none; color:var(--text); min-width:148px; padding:14px 16px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
.dock-row strong { display:block; margin-top:8px; font-size:16px; }
.workspace-home { display:grid; gap:16px; margin-top:18px; }
.workspace-shell { display:grid; grid-template-columns:1.12fr .88fr; gap:16px; }
.workspace-lead { padding:24px; border-radius:28px; border:1px solid rgba(255,255,255,.08); background:linear-gradient(150deg, rgba(244,139,56,.16), rgba(255,255,255,.04) 46%, rgba(106,168,255,.08)); }
.workspace-lead strong { display:block; margin-top:10px; font-size:36px; line-height:1.02; }
.workspace-lead p { margin:12px 0 0; color:#eadbc8; line-height:1.6; }
.workspace-stack { display:grid; gap:12px; }
.workspace-note { padding:16px; border-radius:20px; border:1px solid var(--line); background:rgba(255,255,255,.05); }
.workspace-note strong { display:block; margin-top:8px; font-size:20px; }
.room-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }
.room-card { padding:18px; border-radius:22px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.025)); text-decoration:none; color:var(--text); display:grid; gap:8px; }
.room-card strong { font-size:21px; line-height:1.08; }
.room-card .tag { width:max-content; }
.today-plan-shell { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
.plan-stack { display:grid; gap:10px; margin-top:14px; }
.plan-step { padding:14px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.045); }
.plan-step strong { display:block; margin-top:6px; font-size:18px; }
.task-stack { display:grid; gap:10px; }
.task-card { padding:14px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.045); }
.task-card strong { display:block; margin-top:6px; font-size:18px; }
.command-strip { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:16px; }
.command-pill { padding:14px 16px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.045); text-decoration:none; color:var(--text); display:grid; gap:8px; }
.command-pill strong { font-size:18px; line-height:1.08; }
.priority-shell { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:16px; }
.priority-card { padding:16px; border-radius:20px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.03)); }
.priority-card strong { display:block; margin-top:8px; font-size:22px; line-height:1.08; }
.launchpad { display:grid; grid-template-columns:1.05fr .95fr; gap:16px; margin-top:18px; }
.action-main { padding:20px; border-radius:24px; border:1px solid rgba(255,255,255,.08); background:linear-gradient(150deg, rgba(241,90,36,.18), rgba(255,255,255,.04) 44%, rgba(255,176,0,.12)); }
.action-main strong { display:block; margin-top:8px; font-size:30px; line-height:1.02; }
.action-main p { margin:12px 0 0; color:#eadbc8; line-height:1.55; }
.action-row { display:flex; gap:10px; flex-wrap:wrap; margin-top:16px; }
.flow-grid { display:grid; gap:12px; }
.flow-card { padding:16px; border-radius:20px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
.flow-card.done { opacity:.72; }
.flow-card strong { display:block; margin-top:8px; font-size:20px; }
.flow-status { display:inline-flex; padding:8px 12px; border-radius:999px; font-size:11px; font-weight:900; letter-spacing:.08em; text-transform:uppercase; }
.flow-status.now { background:rgba(241,90,36,.16); border:1px solid rgba(241,90,36,.3); }
.flow-status.ready { background:rgba(255,176,0,.14); border:1px solid rgba(255,176,0,.25); }
.flow-status.done { background:rgba(78,186,114,.16); border:1px solid rgba(78,186,114,.28); }
.panel-collapsible { padding:0; overflow:hidden; }
.panel-collapsible[open] { padding:0; }
.panel-summary { list-style:none; cursor:pointer; padding:18px 20px; display:flex; align-items:center; justify-content:space-between; gap:10px; }
.panel-summary::-webkit-details-marker { display:none; }
.panel-summary strong { font-size:20px; }
.panel-summary .mini { margin-bottom:6px; }
.panel-summary .tag { flex-shrink:0; }
.panel-body { padding:0 20px 20px; }
.minimal-only { display:none; }
body[data-view-mode="simple"] .pro-heavy { display:none !important; }
body[data-view-mode="simple"] .minimal-only { display:block; }
.focus-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:16px; }
.focus-card { padding:16px; border-radius:20px; border:1px solid var(--line); background:rgba(255,255,255,.035); }
.focus-card strong { display:block; margin-top:8px; font-size:20px; }
.coach-day-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:18px; }
.coach-step { padding:16px; border-radius:20px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
.coach-step strong { display:block; margin-top:8px; font-size:20px; }
.coach-step.done { opacity:.65; }
.coach-step .notice { margin-top:10px; }
    .summary-strip { display:grid; grid-template-columns:1.1fr .9fr; gap:16px; margin-top:18px; }
    .summary-card { padding:18px; border-radius:22px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .task-meter { height:10px; width:100%; border-radius:999px; background:rgba(255,255,255,.06); overflow:hidden; margin-top:12px; }
    .task-meter span { display:block; height:100%; background:linear-gradient(135deg,var(--orange),var(--gold)); }
    .today-badge { display:inline-flex; padding:8px 12px; border-radius:999px; background:rgba(78,186,114,.14); border:1px solid rgba(78,186,114,.24); font-size:12px; font-weight:800; }
    .queue-list { display:grid; gap:10px; margin-top:14px; }
    .queue-row { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; padding:12px 14px; border-radius:16px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .queue-row.done { opacity:.62; }
.player-card { padding:20px; border-radius:26px; border:1px solid var(--line); background:linear-gradient(160deg, rgba(255,176,0,.1), rgba(255,255,255,.03) 45%, rgba(241,90,36,.1)); position:relative; overflow:hidden; }
.player-top { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
.player-screen { margin-top:16px; padding:24px; border-radius:24px; background:rgba(0,0,0,.22); border:1px solid rgba(255,255,255,.06); text-align:center; }
.player-time { font-size:clamp(42px, 8vw, 74px); font-family:Georgia,serif; line-height:1; margin:12px 0; letter-spacing:.04em; }
.player-controls { display:flex; justify-content:center; gap:12px; margin-top:16px; flex-wrap:wrap; }
.player-btn { min-width:64px; min-height:64px; border-radius:999px; border:1px solid var(--line); background:rgba(255,255,255,.06); color:var(--text); font-size:18px; font-weight:900; display:inline-flex; align-items:center; justify-content:center; }
.player-btn.primary { background:linear-gradient(135deg,var(--orange),var(--gold)); color:#17110a; }
.player-btn.ghost { background:rgba(255,255,255,.04); }
.player-meta { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:16px; }
.player-meta .log { padding:14px; text-align:center; }
.player-start { display:flex; justify-content:center; margin-top:18px; }
.player-start button { min-height:76px; min-width:min(100%, 320px); border-radius:999px; font-size:20px; letter-spacing:.08em; text-transform:uppercase; }
.player-live-hint { margin-top:14px; font-size:13px; color:var(--muted); }
.player-strip { display:flex; gap:10px; flex-wrap:wrap; justify-content:center; margin-top:14px; }
.player-strip .tag { background:rgba(255,255,255,.08); }
.player-overlay { position:fixed; inset:0; z-index:120; background:radial-gradient(circle at top, rgba(241,90,36,.22), transparent 26%), linear-gradient(180deg, rgba(8,8,8,.98), rgba(12,12,14,.98)); padding:max(16px, env(safe-area-inset-top)) 16px max(20px, env(safe-area-inset-bottom)); display:none; flex-direction:column; gap:14px; }
.player-overlay.open { display:flex; }
.player-overlay-top { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.player-overlay-top .mini { margin-bottom:4px; }
.player-close { min-width:52px; min-height:52px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.06); color:var(--text); font-size:24px; font-weight:900; }
.player-overlay-screen { border-radius:28px; border:1px solid rgba(255,255,255,.08); background:linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02)); padding:22px; text-align:center; }
.player-overlay-timer { font-size:clamp(62px, 15vw, 108px); font-family:Georgia,serif; line-height:1; margin:10px 0 6px; }
.player-overlay-title { font-size:clamp(30px, 7vw, 54px); line-height:.95; margin:8px 0; }
.player-overlay-subtitle { color:var(--muted); margin:8px 0 0; }
.player-overlay-grid { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:12px; }
.player-overlay-card { padding:16px; border-radius:20px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
.player-overlay-card strong { display:block; margin-top:8px; font-size:20px; }
.player-overlay-actions { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:12px; }
.player-overlay-actions .player-btn { width:100%; min-height:60px; border-radius:20px; }
.player-overlay-nav { display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; }
.player-overlay-nav .player-btn { width:100%; min-height:56px; border-radius:18px; }
.player-overlay-checkpoints { display:grid; gap:10px; }
.player-overlay-checkpoint { display:flex; align-items:center; justify-content:space-between; gap:10px; padding:12px 14px; border-radius:16px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
.player-overlay-checkpoint.done { opacity:.6; }
.player-overlay-footer { margin-top:auto; display:grid; gap:12px; }
.swipe-note { text-align:center; color:var(--muted); font-size:13px; }
.overlay-progress { height:10px; border-radius:999px; background:rgba(255,255,255,.08); overflow:hidden; }
.overlay-progress span { display:block; height:100%; background:linear-gradient(135deg,var(--orange),var(--gold)); }
    .preset-row { display:flex; gap:10px; flex-wrap:wrap; justify-content:center; margin-top:14px; }
    .preset-row button { min-height:42px; min-width:110px; border-radius:999px; background:rgba(255,255,255,.05); color:var(--text); }
    .bottom { position:fixed; left:12px; right:12px; bottom:12px; display:none; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; padding:10px; background:rgba(15,15,16,.92); border:1px solid var(--line); border-radius:22px; backdrop-filter:blur(18px); }
    .bottom a { padding:12px 8px; text-decoration:none; text-align:center; border-radius:14px; font-size:12px; color:var(--muted); font-weight:800; }
    .bottom a:first-child { background:linear-gradient(135deg,var(--orange),var(--gold)); color:#17110a; }
    @media (max-width: 980px) { .page,.panel-grid,.hero-kpis,.grid3,.grid4,.users-grid,.quickbar,.meal-grid,.mission-grid,.achievement-grid,.folder-grid,.filter-grid,.planner-grid,.pr-grid,.coach-grid,.today-grid,.calendar-lane,.trend-grid,.chat-grid,.pricing-grid,.today-kpis,.summary-strip,.session-grid,.launchpad,.focus-grid,.coach-day-grid,.hero-stage,.delight-main,.delight-grid,.widget-rail,.one-screen-grid,.home-stat-strip,.mode-board,.fast-lane-grid,.utility-rail,.snapshot-strip,.tactical-grid,.quick-capture-grid,.mission-shell,.workspace-shell,.today-plan-shell,.room-grid,.command-strip,.priority-shell { grid-template-columns:1fr 1fr; } .topbar { grid-template-columns:1fr; } .top-nav-links { justify-content:flex-start; } .agenda-row { grid-template-columns:88px 1fr; } .agenda-row .agenda-state { grid-column:2; width:max-content; } }
@media (max-width: 760px) { .shell { width:min(100vw - 14px,100%); } .page,.panel-grid,.hero-kpis,.grid3,.grid4,.users-grid,.quickbar,.form2,.meal-grid,.mission-grid,.achievement-grid,.folder-grid,.filter-grid,.planner-grid,.pr-grid,.coach-grid,.today-grid,.calendar-lane,.trend-grid,.chat-grid,.pricing-grid,.today-kpis,.summary-strip,.session-grid,.player-meta,.player-overlay-grid,.player-overlay-actions,.command-grid,.launchpad,.focus-grid,.coach-day-grid,.hero-stage,.delight-main,.delight-grid,.widget-rail,.one-screen-grid,.home-stat-strip,.mode-board,.fast-lane-grid,.utility-rail,.snapshot-strip,.tactical-grid,.quick-capture-grid,.mission-shell,.workspace-shell,.today-plan-shell,.room-grid,.command-strip,.priority-shell { grid-template-columns:1fr; } .hero,.panel,.workspace-lead { padding:18px; } .bottom { display:grid; bottom:max(12px, env(safe-area-inset-bottom)); } .lang-switch { justify-content:start; grid-auto-flow:row; } .folder-menu { margin-top:12px; padding-bottom:4px; } .player-overlay { padding:calc(10px + env(safe-area-inset-top)) 12px calc(18px + env(safe-area-inset-bottom)); } .player-overlay-screen { padding:18px; } .player-overlay-title { font-size:34px; } .dock-row a { min-width:132px; } .panel-summary { padding:16px 18px; } .panel-body { padding:0 18px 18px; } .agenda-row { grid-template-columns:1fr; } }
  </style>
</head>
<body data-view-mode="{{ payload.view_mode }}">
  <div class="shell">
    <div class="topbar">
      <div>
        <div class="mini">Forge athlete OS</div>
<strong style="display:block;margin-top:6px;font-size:20px;">APP.PY ONLY BUILD V59</strong>
      </div>
      <div class="toplinks">
        <div class="lang-switch">
          {% for item in payload.languages %}
          <a class="lang-chip {% if item.code == payload.lang %}active{% endif %}" href="/set-language?lang={{ item.code }}&next=/dashboard">{{ item.flag }} {{ item.name }}</a>
          {% endfor %}
        </div>
        <div class="top-nav-links">
          <a href="#folders">Hub {{ payload.ui.folders }}</a>
          <a href="/hub/program">Coach {{ payload.ui.plans }}</a>
          <a href="/hub/calendar">Daily {{ payload.ui.calendar }}</a>
          <a href="/hub/profile">Profile</a>
          <a class="logout" href="/logout">{{ payload.ui.logout }}</a>
        </div>
      </div>
    </div>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
      <div class="flash-stack">
        {% for message in messages %}
        <div class="flash">{{ message }}</div>
        {% endfor %}
      </div>
      {% endif %}
    {% endwith %}

    <section class="hero">
      <div class="hero-head">
        <div>
          <div class="mini">{{ payload.ui.hero_kicker }}</div>
          <h1>Forge</h1>
          <p>Home keeps only the essentials. Open the right room, finish the block, move on.</p>
        </div>
<div class="pill">Dashboard V59</div>
      </div>
      <div class="hero-user" style="margin-top:18px;">
        <div>
          <div class="mini">Athlete</div>
          <h3 style="margin-top:8px;">{{ payload.user.full_name }}</h3>
          <p>@{{ payload.user.username }} - {{ payload.user.age }} yrs - {{ payload.user.height_cm }} cm - {{ payload.user.weight_kg }} kg</p>
        </div>
        <div>
          <div class="mini">Goal</div>
          <h3 style="margin-top:8px;">{{ payload.user.goal|title }}</h3>
          <p>{{ payload.user.experience_level|title }} lane.</p>
        </div>
      </div>
      <div class="account-rail">
        <a class="account-chip primary" href="/hub/train">Open train</a>
        <a class="account-chip" href="/hub/profile">Profile</a>
        <a class="account-chip" href="/hub/calendar">Calendar</a>
        <a class="account-chip" href="/logout">Logout</a>
      </div>
      <div class="utility-rail">
        {% for item in payload.profile_tools %}
        <a class="utility-card" href="{{ item.anchor }}">
          <div class="mini">Account</div>
          <strong>{{ item.title }}</strong>
          <p style="margin-top:8px;">{{ item.detail }}</p>
        </a>
        {% endfor %}
      </div>
      <section class="practical-shell" id="folders" style="margin-top:16px;">
        <article class="agenda-board">
          <div class="mini">Focus folders</div>
          <strong style="display:block;margin-top:8px;font-size:28px;">One room for one job.</strong>
          <p style="margin-top:10px;">Use a dedicated room for training, food, progress, coaching, profile or planning. No clutter on home.</p>
          <div class="fast-lane-grid">
            {% for item in payload.workspace_hub %}
            <a class="lane-card {% if loop.first %}primary{% else %}soft{% endif %}" href="{{ item.anchor }}">
              <div class="mini">{{ item.title }}</div>
              <strong>{{ item.detail }}</strong>
              <p>{{ item.metric }}</p>
              <div class="tag">Open room</div>
            </a>
            {% endfor %}
          </div>
        </article>
      </section>
      <section class="workspace-home">
        <div class="command-strip">
          {% for item in payload.command_strip %}
          <a class="command-pill" href="{{ item.anchor }}">
            <div class="mini">{{ item.kicker }}</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
          </a>
          {% endfor %}
        </div>
        <div class="priority-shell">
          {% for item in payload.priority_stack %}
          <article class="priority-card">
            <div class="mini">{{ item.kicker }}</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
            <div class="tag">{{ item.meta }}</div>
          </article>
          {% endfor %}
        </div>
        <div class="workspace-shell">
          <article class="workspace-lead">
            <div class="mini">Daily workspace</div>
            <strong>{{ payload.home_hub.headline }}</strong>
            <p>{{ payload.home_hub.detail }}</p>
            <div class="hero-actions">
              <a class="pill" href="{{ payload.home_hub.primary.anchor }}">{{ payload.home_hub.primary.label }}</a>
              <a class="tag" href="{{ payload.home_hub.secondary.anchor }}">{{ payload.home_hub.secondary.label }}</a>
            </div>
            <div class="plan-stack">
              {% for item in payload.home_hub.stats %}
              <article class="plan-step">
                <div class="mini">{{ item.label }}</div>
                <strong>{{ item.value }}</strong>
                <p style="margin-top:8px;">{{ item.detail }}</p>
              </article>
              {% endfor %}
            </div>
          </article>
          <div class="workspace-stack">
            <article class="workspace-note">
              <div class="mini">Next move</div>
              <strong>{{ payload.single_next_action.title }}</strong>
              <p>{{ payload.single_next_action.detail }}</p>
              <div class="hero-actions">
                <a class="pill" href="{{ payload.single_next_action.anchor }}">{{ payload.single_next_action.cta }}</a>
                <div class="tag">{{ payload.single_next_action.tag }}</div>
              </div>
            </article>
            <div class="task-stack">
              {% for item in payload.daily_tasks %}
              <article class="task-card">
                <div class="mini">{{ item.kicker }}</div>
                <strong>{{ item.title }}</strong>
                <p>{{ item.detail }}</p>
              </article>
              {% endfor %}
            </div>
          </div>
        </div>
        <div class="room-grid" id="folders">
          {% for item in payload.workspace_hub %}
          <a class="room-card" href="{{ item.anchor }}">
            <div class="mini">{{ item.title }}</div>
            <strong>{{ item.detail }}</strong>
            <p>{{ item.metric }}</p>
            <div class="tag">Open room</div>
          </a>
          {% endfor %}
        </div>
        <div class="today-plan-shell">
          <article class="agenda-board">
            <div class="mini">Today agenda</div>
            <strong style="display:block;margin-top:8px;font-size:28px;">Move through the day in order.</strong>
            <p style="margin-top:10px;">Open one block at a time. Finish it. The next step is already prepared.</p>
            <div class="agenda-grid">
              {% for item in payload.today_agenda %}
              <a class="agenda-row" href="{{ item.anchor }}" style="text-decoration:none;color:inherit;">
                <div class="agenda-time">{{ item.time }}</div>
                <div>
                  <strong>{{ item.title }}</strong>
                  <p style="margin-top:6px;">{{ item.detail }}</p>
                </div>
                <div class="agenda-state {{ item.state|replace(' ', '-') }}">{{ item.state }}</div>
              </a>
              {% endfor %}
            </div>
          </article>
          <article class="agenda-board">
            <div class="mini">Focused actions</div>
            <strong style="display:block;margin-top:8px;font-size:28px;">Only the useful tools.</strong>
            <p style="margin-top:10px;">Training, fuel, progress and coach stay close. Extra detail lives inside each room.</p>
            <div class="fast-lane-grid" style="margin-top:14px;">
              {% for item in payload.fast_lane %}
              <a class="lane-card {{ item.emphasis }}" href="{{ item.anchor }}">
                <div class="mini">{{ item.kicker }}</div>
                <strong>{{ item.title }}</strong>
                <p>{{ item.detail }}</p>
                <div class="tag">{{ item.metric }}</div>
              </a>
              {% endfor %}
            </div>
          </article>
        </div>
      </section>
      {% if payload.view_mode == 'pro' %}
      <section class="mission-shell">
        <article class="mission-lead">
          <div class="mini">Mission control</div>
          <strong>{{ payload.mission_control.headline }}</strong>
          <p>{{ payload.mission_control.subline }}</p>
          <div class="mission-notes">
            <div class="mission-note"><div class="mini">Focus</div><strong style="font-size:18px;">{{ payload.mission_control.focus_signal }}</strong></div>
            <div class="mission-note"><div class="mini">Coach signal</div><strong style="font-size:18px;">{{ payload.mission_control.coach_signal }}</strong></div>
            <div class="mission-note"><div class="mini">Nutrition signal</div><strong style="font-size:18px;">{{ payload.mission_control.nutrition_signal }}</strong></div>
          </div>
        </article>
        <div class="signal-stack">
          {% for item in payload.signal_stack %}
          <article class="signal-card {{ item.level }}">
            <div class="mini">Signal</div>
            <strong>{{ item.title }}</strong>
            <p style="margin-top:8px;">{{ item.detail }}</p>
          </article>
          {% endfor %}
        </div>
      </section>
      <div class="quick-capture-grid">
        {% for item in payload.quick_capture %}
        <a class="capture-card" href="{{ item.anchor }}">
          <div class="mini">Quick action</div>
          <strong>{{ item.title }}</strong>
          <p>{{ item.detail }}</p>
          <div class="tag">{{ item.tag }}</div>
        </a>
        {% endfor %}
      </div>
      <section class="practical-shell">
        <div class="snapshot-strip">
          {% for item in payload.today_snapshot %}
          <article class="snapshot-card">
            <div class="mini">{{ item.label }}</div>
            <strong>{{ item.value }}</strong>
            <p style="margin-top:8px;">{{ item.detail }}</p>
          </article>
          {% endfor %}
        </div>
        <div class="fast-lane-grid">
          {% for item in payload.fast_lane %}
          <a class="lane-card {{ item.emphasis }}" href="{{ item.anchor }}">
            <div class="mini">{{ item.kicker }}</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
            <div class="tag">{{ item.metric }}</div>
          </a>
          {% endfor %}
        </div>
        <article class="agenda-board">
          <div class="mini">Today agenda</div>
          <strong style="display:block;margin-top:8px;font-size:28px;">Today's run sheet</strong>
          <p style="margin-top:10px;">Move through the day in order. Open the next block, close it, continue.</p>
          <div class="agenda-grid">
            {% for item in payload.today_agenda %}
            <a class="agenda-row" href="{{ item.anchor }}" style="text-decoration:none;color:inherit;">
              <div class="agenda-time">{{ item.time }}</div>
              <div>
                <strong>{{ item.title }}</strong>
                <p style="margin-top:6px;">{{ item.detail }}</p>
              </div>
              <div class="agenda-state {{ item.state|replace(' ', '-') }}">{{ item.state }}</div>
            </a>
            {% endfor %}
          </div>
        </article>
        <div class="tactical-grid">
          {% for item in payload.tactical_cards %}
          <a class="tactical-card" href="{{ item.anchor }}">
            <div class="mini">{{ item.kicker }}</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
            <div class="tag">{{ item.cta }}</div>
          </a>
          {% endfor %}
        </div>
      </section>
      <section class="one-screen-home">
        <div class="one-screen-grid">
          <article class="home-primary">
            <div class="mini">Today plan</div>
            <strong>{{ payload.home_hub.headline }}</strong>
            <p>{{ payload.home_hub.detail }}</p>
            <div class="hero-actions">
              <a class="pill" href="{{ payload.home_hub.primary.anchor }}">{{ payload.home_hub.primary.label }}</a>
              <a class="tag" href="{{ payload.home_hub.secondary.anchor }}">{{ payload.home_hub.secondary.label }}</a>
            </div>
            <div class="home-stat-strip">
              {% for item in payload.home_hub.stats %}
              <article class="home-stat">
                <div class="mini">{{ item.label }}</div>
                <strong>{{ item.value }}</strong>
                <p style="margin-top:8px;">{{ item.detail }}</p>
              </article>
              {% endfor %}
            </div>
          </article>
          <div class="guided-day-shell">
            {% for item in payload.guided_day_flow %}
            <article class="guided-step {{ item.state }}">
              <div class="mini">{{ item.kicker }}</div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.detail }}</p>
              <div style="margin-top:12px;"><a href="{{ item.anchor }}" style="color:#f7efdf;font-weight:800;text-decoration:none;">{{ item.cta }}</a></div>
            </article>
            {% endfor %}
          </div>
        </div>
        <div class="mode-board">
          {% for item in payload.mode_blueprint %}
          <article class="mode-card {% if item.active %}active{% endif %}">
            <div class="mini">{{ item.kicker }}</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
            <div style="margin-top:12px;"><a href="{{ item.anchor }}" style="color:#f7efdf;font-weight:800;text-decoration:none;">{{ item.cta }}</a></div>
          </article>
          {% endfor %}
        </div>
      </section>
      {% if payload.view_mode == 'pro' %}
      <div class="hero-kpis">
        <article class="kpi"><span class="mini">Sessions</span><strong>{{ payload.stats.weekly_sessions }}</strong></article>
        <article class="kpi"><span class="mini">Volume</span><strong>{{ payload.stats.weekly_volume }}</strong></article>
        <article class="kpi"><span class="mini">Minutes</span><strong>{{ payload.stats.weekly_minutes }}</strong></article>
        <article class="kpi"><span class="mini">Calories</span><strong>{{ payload.assistant.targets.calories }}</strong></article>
      </div>
      <div class="mission-grid">
        <article class="kpi"><span class="mini">Recovery score</span><strong>{{ payload.scores.recovery_score }}/10</strong></article>
        <article class="kpi"><span class="mini">Transformation</span><strong>{{ payload.scores.transformation_score }}/10</strong></article>
        <article class="kpi"><span class="mini">Consistency</span><strong>{{ payload.scores.consistency_score }}%</strong></article>
      </div>
      <div class="hero-stage">
        <article class="hero-banner">
          <div class="mini">Today</div>
          <strong>{{ payload.delight_board.headline }}</strong>
          <p>{{ payload.delight_board.subline }}</p>
          <div class="hero-actions">
            <a class="pill" href="{{ payload.delight_board.primary_cta.anchor }}">{{ payload.delight_board.primary_cta.label }}</a>
            <a class="tag" href="{{ payload.delight_board.secondary_cta.anchor }}">{{ payload.delight_board.secondary_cta.label }}</a>
          </div>
        </article>
        <div class="widget-rail">
          {% for item in payload.delight_board.widgets %}
          <a href="{{ item.anchor }}" class="widget-chip">
            <div class="mini">{{ item.title }}</div>
            <strong>{{ item.detail }}</strong>
            <div class="tag">{{ item.metric }}</div>
          </a>
          {% endfor %}
        </div>
      </div>
      <div class="quickbar">
        <a href="#folders">Open {{ payload.ui.folders }}</a>
        <a href="/hub/program">View {{ payload.ui.plans }}</a>
          <a href="/daily-checkin">Daily check-in</a>
          <a href="/hub/profile">Edit profile</a>
      </div>
      <div class="filter-grid">
        {% for item in payload.adaptive_filters %}
        <article class="kpi">
          <span class="mini">{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
        {% endfor %}
      </div>
      {% endif %}
      <div class="view-mode">
        <a href="/set-view-mode?mode=simple" class="{% if payload.view_mode == 'simple' %}active{% endif %}">Simple</a>
        <a href="/set-view-mode?mode=pro" class="{% if payload.view_mode == 'pro' %}active{% endif %}">Pro</a>
        <a href="/workout-mode">Workout only</a>
        <a href="/nutrition-mode">Nutrition only</a>
        <a href="/weekly-reset">Weekly reset</a>
      </div>
      <nav class="folder-menu" aria-label="Section menu">
        {% for item in payload.section_menu %}
        <a href="{{ item.anchor }}">{{ item.title }}</a>
        {% endfor %}
      </nav>
      <section class="command-center">
        <div class="command-head">
          <div>
            <div class="mini">Easy mode</div>
            <strong style="font-size:26px;">{{ payload.easy_mode.headline }}</strong>
            <p style="margin-top:8px;">{{ payload.easy_mode.detail }}</p>
          </div>
          <div class="tag">{{ payload.easy_mode.primary_tag }}</div>
        </div>
        <div class="command-grid">
          {% for item in payload.easy_mode.primary_actions %}
          <a href="{{ item.anchor }}" class="command-card">
            <div class="mini">{{ item.kicker }}</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
            <div class="tag">{{ item.tag }}</div>
          </a>
          {% endfor %}
        </div>
        <div class="dock-row">
          {% for item in payload.quick_dock %}
          <a href="{{ item.anchor }}">
            <div class="mini">{{ item.kicker }}</div>
            <strong>{{ item.title }}</strong>
            <p style="margin-top:6px;">{{ item.detail }}</p>
          </a>
          {% endfor %}
        </div>
      </section>
      {% endif %}
      {% if payload.view_mode == 'pro' %}
      <section class="delight-shell">
        <div class="delight-main">
          <article class="delight-lead">
            <div class="mini">Control center</div>
            <strong>Today's control panel</strong>
            <p>Open the right room fast and keep the day moving.</p>
          </article>
          <div class="planner-grid">
            {% for item in payload.operating_board %}
            <article class="option">
              <div class="mini">Now</div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.detail }}</p>
              <div class="notice" style="margin-top:10px;">{{ item.note }}</div>
            </article>
            {% endfor %}
          </div>
        </div>
        <div class="delight-grid">
          {% for item in payload.customer_delight.cards %}
          <article class="delight-card">
            <div class="mini">{{ item.kicker }}</div>
            <strong>{{ item.title }}</strong>
            <p style="margin-top:12px;">{{ item.detail }}</p>
            <div class="notice">{{ item.tag }}</div>
          </article>
          {% endfor %}
        </div>
        <div class="widget-rail">
          {% for item in payload.workspace_hub %}
          <a href="{{ item.anchor }}" class="widget-chip">
            <div class="mini">Workspace</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
            <div class="tag">{{ item.metric }}</div>
          </a>
          {% endfor %}
        </div>
      </section>
      {% endif %}
      <section class="launchpad">
        <article class="action-main">
          <div class="mini">Do this now</div>
          <strong>{{ payload.single_next_action.title }}</strong>
          <p>{{ payload.single_next_action.detail }}</p>
          <div class="action-row">
            <a href="{{ payload.single_next_action.anchor }}" class="pill">{{ payload.single_next_action.cta }}</a>
            <div class="tag">{{ payload.single_next_action.tag }}</div>
          </div>
          <div class="focus-grid">
            {% for item in payload.focus_cards %}
            <article class="focus-card">
              <div class="mini">{{ item.kicker }}</div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.detail }}</p>
            </article>
            {% endfor %}
          </div>
        </article>
        <div class="flow-grid">
          {% for item in payload.day_flow %}
          <article class="flow-card {% if item.state == 'done' %}done{% endif %}">
            <div class="flow-status {{ item.state }}">{{ item.state_label }}</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
            <div style="margin-top:12px;"><a href="{{ item.anchor }}" style="color:#f7efdf;font-weight:800;text-decoration:none;">{{ item.cta }}</a></div>
          </article>
          {% endfor %}
        </div>
      </section>
      {% if payload.view_mode == 'pro' %}
      <section class="summary-strip" style="margin-top:18px;">
        <article class="summary-card">
          <div class="mini">{{ payload.recomposition_home.headline }}</div>
          <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.recomposition_home.cards[0].value if payload.recomposition_home.cards else "Ready" }}</strong>
          <p style="margin-top:12px;">{{ payload.recomposition_home.checkpoint }}</p>
          <ul class="list" style="margin-top:10px;">
            {% for item in payload.recomposition_home.cards %}
            <li><strong>{{ item.label }}</strong> - {{ item.value }}</li>
            {% endfor %}
          </ul>
        </article>
        <article class="summary-card">
          <div class="mini">{{ payload.weekly_adaptive_block.headline }}</div>
          <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.weekly_adaptive_block.mode }}</strong>
          <p style="margin-top:12px;">{{ payload.weekly_adaptive_block.week_label }} - {{ payload.weekly_adaptive_block.focus }}</p>
          <ul class="list" style="margin-top:10px;">
            {% for item in payload.weekly_adaptive_block.changes %}
            <li>{{ item }}</li>
            {% endfor %}
          </ul>
          <div class="next">{{ payload.weekly_adaptive_block.coach_call }}</div>
        </article>
      </section>
      {% endif %}
      <section class="coach-day-grid">
        {% for item in payload.coach_day_flow %}
        <article class="coach-step {% if item.done %}done{% endif %}">
          <div class="mini">{{ item.kicker }}</div>
          <strong>{{ item.title }}</strong>
          <p>{{ item.detail }}</p>
          <div class="notice">{{ item.prescription }}</div>
          <p style="margin-top:10px;">{{ item.cue }}</p>
          <div style="margin-top:12px;"><a href="{{ item.anchor }}" style="color:#f7efdf;font-weight:800;text-decoration:none;">{{ item.cta }}</a></div>
        </article>
        {% endfor %}
      </section>
      {% if payload.view_mode == 'pro' %}
      <div class="summary-strip" style="margin-top:18px;">
        <article class="summary-card">
          <div class="mini">Coach</div>
          <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.coach_briefing.coach }}</strong>
          <p style="margin-top:12px;">{{ payload.coach_briefing.opening }}</p>
          <p>{{ payload.coach_briefing.summary }}</p>
          <div class="next">{{ payload.coach_briefing.next_step }}</div>
        </article>
        <article class="summary-card">
          <div class="mini">Today</div>
          <strong style="display:block;margin-top:8px;font-size:24px;">Simple flow</strong>
          <ul class="list" style="margin-top:12px;">
            {% for item in payload.reminder_center %}
            <li><strong>{{ item.time }}</strong> - {{ item.title }} - {{ item.detail }}</li>
            {% endfor %}
          </ul>
          <div style="margin-top:14px;"><a href="/daily-checkin" style="color:#f7efdf;font-weight:800;text-decoration:none;">Open daily check-in</a></div>
        </article>
      </div>
      {% endif %}
    </section>

    <section class="panel span" id="folders">
      <div class="section-head">
        <div><div class="mini">{{ payload.ui.folders }}</div><h2>{{ payload.ui.mobile_center }}</h2></div>
      </div>
      <div class="folder-grid">
        {% for item in payload.folder_cards %}
        <a href="{{ item.anchor }}" class="option" style="text-decoration:none;">
          <div class="mini">{{ item.kicker }}</div>
          <strong>{{ item.title }}</strong>
          <p>{{ item.detail }}</p>
          <div class="notice" style="margin-top:10px;">{{ item.metric }}</div>
        </a>
        {% endfor %}
      </div>
    </section>

      <section class="panel span">
        <div class="section-head">
          <div><div class="mini">Home</div><h2>Use one widget and move on</h2></div>
        </div>
        <div class="summary-strip" style="margin-top:0;">
          {% for item in payload.dashboard_core_widgets %}
          <article class="summary-card">
            <div class="mini">{{ item.kicker }}</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">{{ item.title }}</strong>
            <p style="margin-top:12px;">{{ item.detail }}</p>
            <div class="actions">
              <a href="{{ item.anchor }}" class="pill">Open</a>
              <div class="notice">{{ item.metric }}</div>
            </div>
          </article>
          {% endfor %}
        </div>
      </section>

    {% if payload.show_full_dashboard %}
    <main class="page">
      <section class="panel span" id="profile">
        <div class="section-head">
          <div><div class="mini">Athlete profile</div><h2>{{ payload.ui.profile_title }}</h2></div>
        </div>
        <div class="grid4">
          <article class="kpi"><span class="mini">Full name</span><strong>{{ payload.user.full_name }}</strong></article>
          <article class="kpi"><span class="mini">Gender</span><strong>{{ payload.user.gender|title }}</strong></article>
          <article class="kpi"><span class="mini">Age</span><strong>{{ payload.user.age }}</strong></article>
          <article class="kpi"><span class="mini">Height / Weight</span><strong>{{ payload.user.height_cm }} / {{ payload.user.weight_kg }}</strong></article>
          <article class="kpi"><span class="mini">Goal</span><strong>{{ payload.user.goal|title }}</strong></article>
          <article class="kpi"><span class="mini">Equipment</span><strong>{{ payload.user.equipment_access|title }}</strong></article>
          <article class="kpi"><span class="mini">Fatigue</span><strong>{{ payload.user.fatigue_state|title }}</strong></article>
          <article class="kpi"><span class="mini">Cycle mode</span><strong>{{ payload.user.cycle_phase|title }}</strong></article>
        </div>
        <div class="panel-grid" style="margin-top:16px;">
          <form method="post" action="/profile/update" class="form2">
            <label>Ime i prezime<input type="text" name="full_name" value="{{ payload.user.full_name }}" required></label>
            <label>Pol
              <select name="gender">
                <option value="male" {% if payload.user.gender == 'male' %}selected{% endif %}>Musko</option>
                <option value="female" {% if payload.user.gender == 'female' %}selected{% endif %}>Zensko</option>
              </select>
            </label>
            <label>Godine<input type="number" name="age" value="{{ payload.user.age }}" min="13" max="100"></label>
            <label>Visina cm<input type="number" step="0.1" name="height_cm" value="{{ payload.user.height_cm }}"></label>
            <label>Kilaza kg<input type="number" step="0.1" name="weight_kg" value="{{ payload.user.weight_kg }}"></label>
            <label>Cilj
              <select name="goal">
                <option value="performance" {% if payload.user.goal == 'performance' %}selected{% endif %}>Performance</option>
                <option value="muscle" {% if payload.user.goal == 'muscle' %}selected{% endif %}>Muscle</option>
                <option value="cut" {% if payload.user.goal == 'cut' %}selected{% endif %}>Cut</option>
              </select>
            </label>
            <label>Iskustvo
              <select name="experience_level">
                <option value="beginner" {% if payload.user.experience_level == 'beginner' %}selected{% endif %}>Beginner</option>
                <option value="intermediate" {% if payload.user.experience_level == 'intermediate' %}selected{% endif %}>Intermediate</option>
                <option value="advanced" {% if payload.user.experience_level == 'advanced' %}selected{% endif %}>Advanced</option>
              </select>
            </label>
            <label>Oprema
              <select name="equipment_access">
                <option value="full gym" {% if payload.user.equipment_access == 'full gym' %}selected{% endif %}>Full gym</option>
                <option value="home" {% if payload.user.equipment_access == 'home' %}selected{% endif %}>Home</option>
                <option value="hotel" {% if payload.user.equipment_access == 'hotel' %}selected{% endif %}>Hotel</option>
              </select>
            </label>
            <label>Umor
              <select name="fatigue_state">
                <option value="steady" {% if payload.user.fatigue_state == 'steady' %}selected{% endif %}>Steady</option>
                <option value="high" {% if payload.user.fatigue_state == 'high' %}selected{% endif %}>High</option>
                <option value="drained" {% if payload.user.fatigue_state == 'drained' %}selected{% endif %}>Drained</option>
              </select>
            </label>
            <label>Cycle mode
              <select name="cycle_phase">
                <option value="neutral" {% if payload.user.cycle_phase == 'neutral' %}selected{% endif %}>Neutral</option>
                <option value="performance" {% if payload.user.cycle_phase == 'performance' %}selected{% endif %}>Performance</option>
                <option value="recovery" {% if payload.user.cycle_phase == 'recovery' %}selected{% endif %}>Recovery</option>
                <option value="late_cycle" {% if payload.user.cycle_phase == 'late_cycle' %}selected{% endif %}>Late cycle</option>
              </select>
            </label>
            <button class="full" type="submit">Sacuvaj profil</button>
          </form>
          <div>
            <div class="mini">Achievements</div>
            <div class="achievement-grid">
              {% for item in payload.achievements %}
              <article class="option">
                <strong>{{ item.title }}</strong>
                <div class="notice">{{ item.value }}</div>
                <p>{{ item.detail }}</p>
              </article>
              {% endfor %}
            </div>
          </div>
        </div>
      </section>

      <section class="panel span" id="plans">
        <div class="section-head">
          <div><div class="mini">Suggested training</div><h2>{{ payload.ui.plans_title }}</h2></div>
        </div>
        <div class="summary-strip" style="margin-bottom:16px;">
          <article class="summary-card">
            <div class="mini">Active package</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.active_package.title }}</strong>
            <p style="margin-top:12px;">{{ payload.active_package.summary }}</p>
            <div class="notice">{{ payload.active_package.focus }} - {{ payload.active_package.days }} days</div>
            <p style="margin-top:10px;">Latest work: {{ payload.active_package.latest_work }}</p>
            <div class="next">Next calendar block: {{ payload.active_package.next_calendar }}</div>
          </article>
          <article class="summary-card">
            <div class="mini">Package filters</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">Coach package library</strong>
            <div class="quickbar" style="margin-top:14px;">
              {% for item in payload.package_filters %}
              <span class="tag">{{ item.label }}</span>
              {% endfor %}
            </div>
            <p style="margin-top:12px;">Each package already has fixed workout days and pre-written exercise lists. User chooses, coach leads.</p>
          </article>
        </div>
        <div class="planner-grid" style="margin-bottom:16px;">
          {% for item in payload.program_board %}
          <article class="option">
            <div class="mini">{{ item.day }} - {{ item.focus }}</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.prescription }}</p>
            <ul class="list" style="margin-top:10px;">
              {% for exercise in item.top_exercises %}
              <li>{{ exercise }}</li>
              {% endfor %}
            </ul>
          </article>
          {% endfor %}
        </div>
        <div class="option-grid">
          {% for option in payload.assistant.suggestions %}
          <article class="option">
            <div class="head-row">
              <div>
                <div class="mini">{{ option.coach_role }}</div>
                <strong>{{ option.title }}</strong>
              </div>
              <div class="tag">{{ option.days }} days</div>
            </div>
            <div class="notice" style="margin-top:12px;">Focus: {{ option.focus }}</div>
            <p>{{ option.summary }}</p>
            <ul class="list">
              {% for bullet in option.blocks %}
              <li>{{ bullet }}</li>
              {% endfor %}
            </ul>
            <div class="stack" style="margin-top:14px;">
              {% for session in option.sessions %}
              <article class="log">
                <div class="mini">{{ session.day }} - {{ session.prescription }}</div>
                <strong style="display:block;margin-top:6px;">{{ session.title }}</strong>
                <ul class="list" style="margin-top:10px;">
                  {% for exercise in session.exercises %}
                  <li>{{ exercise }}</li>
                  {% endfor %}
                </ul>
              </article>
              {% endfor %}
            </div>
            <div class="notice">Nutrition: {{ option.nutrition }}</div>
            <form method="post" action="/plan/select" style="margin-top:14px;">
              <input type="hidden" name="title" value="{{ option.title }}">
              <input type="hidden" name="coach_key" value="{{ option.coach_key }}">
              <input type="hidden" name="details" value="{{ option.focus }} - {{ option.summary }}">
              <button type="submit">Izaberi ovaj plan</button>
            </form>
          </article>
          {% endfor %}
        </div>
      </section>

      <section class="panel span" id="today-plan">
        <div class="section-head">
          <div><div class="mini">Today</div><h2>{{ payload.ui.today_title }}</h2></div>
        </div>
        <div class="today-kpis">
          <article class="kpi">
            <span class="mini">Day status</span>
            <strong>{{ payload.today_blueprint.status_label }}</strong>
          </article>
          <article class="kpi">
            <span class="mini">Session time</span>
            <strong>{{ payload.today_blueprint.duration }}</strong>
          </article>
          <article class="kpi">
            <span class="mini">Progress today</span>
            <strong>{{ payload.today_progress.done_items }}/{{ payload.today_progress.total_items }}</strong>
          </article>
          <article class="kpi">
            <span class="mini">Meals today</span>
            <strong>{{ payload.today_progress.meal_done }}/{{ payload.today_progress.meal_total }}</strong>
          </article>
        </div>
        <div class="summary-strip">
          <article class="summary-card">
            <div class="mini">Completion</div>
            <strong style="display:block;margin-top:8px;font-size:28px;">{{ payload.today_progress.completion_percent }}%</strong>
            <div class="task-meter"><span style="width:{{ payload.today_progress.completion_percent }}%;"></span></div>
            <p style="margin-top:12px;">Exercises finished: {{ payload.today_progress.exercise_done }}/{{ payload.today_progress.exercise_total }}. Meals completed: {{ payload.today_progress.meal_done }}/{{ payload.today_progress.meal_total }}.</p>
          </article>
          <article class="summary-card">
            <div class="mini">Coach focus</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.today_blueprint.title }}</strong>
            <p style="margin-top:12px;">{{ payload.today_blueprint.focus_line }}</p>
            <div class="today-badge" style="margin-top:8px;">Coach {{ payload.today_blueprint.coach_name }}</div>
          </article>
        </div>
        <div class="planner-grid" style="margin-top:16px;">
          {% for item in payload.notifications %}
          <article class="option">
            <div class="mini">{{ item.level }}</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
          </article>
          {% endfor %}
        </div>
        <div class="planner-grid" style="margin-top:16px;">
          {% for item in payload.daily_tasks %}
          <article class="option">
            <div class="mini">Daily task</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
            <div class="notice" style="margin-top:10px;">{{ item.state }}</div>
          </article>
          {% endfor %}
        </div>
        <div class="minimal-only">
          <div class="summary-card" style="margin-top:16px;">
            <div class="mini">Simple mode</div>
            <strong style="display:block;margin-top:8px;font-size:22px;">{{ payload.today_blueprint.title }}</strong>
            <p style="margin-top:10px;">{{ payload.coach_briefing.next_step }}</p>
            <div class="quickbar" style="margin-top:14px;">
              <a href="/workout-mode">Open workout</a>
              <a href="/nutrition-mode">Open nutrition</a>
              <a href="/daily-checkin">Check-in</a>
            </div>
          </div>
        </div>
        <div class="session-grid pro-heavy">
          <article class="player-card" id="workout-player" data-rest="{{ payload.live_session.rest_timer }}">
            <div class="player-top">
              <div>
                <div class="mini">{{ payload.live_session.title }}</div>
                <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.live_session.next_move }}</strong>
              </div>
              <div class="tag">{% if payload.live_session.mode == "training" %}Workout live{% else %}Recovery live{% endif %}</div>
            </div>
            <div class="player-screen">
              <div class="mini">Rest timer</div>
              <div class="player-time" id="player-timer">00:00</div>
              <div class="mini" style="margin-top:10px;">Session timer</div>
              <div class="player-time" id="session-timer" style="font-size:34px;">00:00</div>
              <p id="player-status">{{ payload.live_session.coach_prompt }}</p>
              <div class="player-start">
                <button type="button" class="player-btn primary" id="player-start-main" aria-label="Start workout">Start workout</button>
              </div>
              <div class="player-controls">
                <button type="button" class="player-btn primary" id="player-start-session" aria-label="Start session timer">Start session</button>
                <button type="button" class="player-btn" id="player-stop-session" aria-label="Stop session timer">Stop session</button>
              </div>
              <div class="player-controls">
                <button type="button" class="player-btn primary" id="player-play" aria-label="Play workout">Play</button>
                <button type="button" class="player-btn" id="player-pause" aria-label="Pause workout">Pause</button>
                <button type="button" class="player-btn" id="player-reset" aria-label="Reset timer">Reset</button>
              </div>
              <div class="preset-row">
                {% for preset in payload.live_session.rest_presets %}
                <button type="button" class="preset-btn" data-seconds="{{ preset.seconds }}">{{ preset.label }} {{ preset.seconds }}s</button>
                {% endfor %}
              </div>
              <div class="player-strip">
                <div class="tag">Live player</div>
                <div class="tag">Swipe steps</div>
                <div class="tag">One tap set finish</div>
                <div class="tag">{{ payload.voice_coach.mode_label }}</div>
              </div>
              <div class="player-live-hint">Open fullscreen mode and run the whole workout from the center player without scrolling.</div>
            </div>
            <div class="player-meta">
              <article class="log">
                <div class="mini">Current focus</div>
                <strong style="font-size:20px;">{{ payload.today_blueprint.status_label }}</strong>
              </article>
              <article class="log">
                <div class="mini">Session length</div>
                <strong style="font-size:20px;">{{ payload.today_blueprint.duration }}</strong>
              </article>
              <article class="log">
                <div class="mini">Coach lane</div>
                <strong style="font-size:20px;">{{ payload.today_blueprint.coach_name }}</strong>
              </article>
            </div>
            <div class="queue-list" style="margin-top:16px;">
              <div class="queue-row">
                <div>
                  <div class="mini">Technique mode</div>
                  <strong style="font-size:18px;margin-top:6px;">How to do the next movement</strong>
                  <ul class="list" style="margin-top:10px;">
                    {% for tip in payload.live_session.technique %}
                    <li>{{ tip }}</li>
                    {% endfor %}
                  </ul>
                  {% if payload.live_session.technique_source_url %}
                  <p style="margin-top:12px;"><a href="{{ payload.live_session.technique_source_url }}" target="_blank" rel="noreferrer" style="color:#f7efdf;">Source: {{ payload.live_session.technique_source_label }}</a></p>
                  {% endif %}
                </div>
              </div>
            </div>
          </article>
          <article class="option">
            <div class="mini">Live queue</div>
            <strong>{% if payload.live_session.mode == "training" %}Workout order{% else %}Recovery order{% endif %}</strong>
            {% if payload.live_session.queue %}
            <div class="queue-list">
              {% for item in payload.live_session.queue %}
              <div class="queue-row {% if item.done %}done{% endif %}" data-queue-index="{{ loop.index0 }}" data-item-key="{{ item.item_key }}">
                <div>
                  {% if item.machine_image %}
                  <img src="{{ item.machine_image }}" alt="{{ item.machine_label }}" style="width:100%;max-width:220px;border-radius:18px;border:1px solid rgba(255,255,255,.08);display:block;margin-bottom:12px;background:#111;">
                  {% endif %}
                  <div class="mini">{{ item.machine_label }} - {{ item.machine_focus }}</div>
                  <strong style="font-size:18px;margin-top:0;">{{ item.name }}</strong>
                  <p style="margin-top:6px;">{{ item.detail }}</p>
                  <div class="notice" style="margin-top:10px;">Auto-weight: {{ item.weight_suggestion }}</div>
                  {% if item.checkpoints %}
                  <div class="queue-list" style="margin-top:10px;">
                    {% for checkpoint in item.checkpoints %}
                    <form method="post" action="/today/check">
                      <input type="hidden" name="item_type" value="set">
                      <input type="hidden" name="item_key" value="{{ checkpoint.item_key }}">
                      <button type="submit" style="min-height:44px;">{% if checkpoint.done %}{{ checkpoint.label }} done{% else %}Mark {{ checkpoint.label }}{% endif %}</button>
                    </form>
                    {% endfor %}
                  </div>
                  {% endif %}
                </div>
                <div class="tag">{% if item.done %}Done{% else %}Next{% endif %}</div>
              </div>
              {% endfor %}
            </div>
            {% else %}
            <div class="queue-list">
              <div class="queue-row">
                <div>
                  <strong style="font-size:18px;margin-top:0;">Recovery walk</strong>
                  <p style="margin-top:6px;">Easy movement, breathing and early sleep.</p>
                </div>
                <div class="tag">Recovery</div>
              </div>
            </div>
            {% endif %}
            <div class="queue-list" style="margin-top:16px;">
              <div class="queue-row">
                <div>
                  <div class="mini">Rest presets</div>
                  <strong style="font-size:18px;margin-top:6px;">Choose the right pace</strong>
                  <ul class="list" style="margin-top:10px;">
                    {% for preset in payload.live_session.rest_presets %}
                    <li>{{ preset.label }} - {{ preset.seconds }} sec - {{ preset.use }}</li>
                    {% endfor %}
                  </ul>
                </div>
              </div>
            </div>
            <div class="queue-list" style="margin-top:16px;">
              <div class="queue-row">
                <div>
                  <div class="mini">Smart progression</div>
                  <strong style="font-size:18px;margin-top:6px;">What to do with the load today</strong>
                  <ul class="list" style="margin-top:10px;">
                    {% for item in payload.live_session.progression %}
                    <li><strong>{{ item.name }}</strong> - {{ item.recommendation }}</li>
                    {% endfor %}
                  </ul>
                </div>
              </div>
            </div>
          </article>
        </div>
        <div class="player-overlay" id="player-overlay" aria-hidden="true">
          <div class="player-overlay-top">
            <div>
              <div class="mini">Gym pro mode</div>
              <strong style="font-size:24px;">{{ payload.live_session.title }}</strong>
            </div>
            <button type="button" class="player-close" id="player-close" aria-label="Close workout mode">×</button>
          </div>
          <div class="player-overlay-screen">
            <div class="mini" id="overlay-step-label">Current block</div>
            <div class="player-overlay-title" id="overlay-step-title">{{ payload.live_session.next_move }}</div>
            <p class="player-overlay-subtitle" id="overlay-step-detail">{{ payload.live_session.coach_prompt }}</p>
            <div class="player-overlay-timer" id="overlay-timer">00:00</div>
            <div class="overlay-progress"><span id="overlay-progress-bar" style="width:0%;"></span></div>
          </div>
          <div class="player-overlay-grid">
            <article class="player-overlay-card">
              <div class="mini">Auto-weight</div>
              <strong id="overlay-weight">{{ payload.live_session.queue[0].weight_suggestion if payload.live_session.queue else "Use control and quality." }}</strong>
              <p id="overlay-rest">{{ payload.live_session.rest_timer }}</p>
            </article>
            <article class="player-overlay-card">
              <div class="mini">Technique</div>
              <strong id="overlay-technique-head">{{ payload.live_session.technique[0] if payload.live_session.technique else "Stay clean under load." }}</strong>
              <p id="overlay-technique-tail">{{ payload.live_session.technique[1] if payload.live_session.technique|length > 1 else payload.live_session.coach_prompt }}</p>
            </article>
          </div>
          <div id="overlay-machine-card" class="player-overlay-card" style="margin-top:12px;">
            {% if payload.live_session.queue and payload.live_session.queue[0].machine_image %}
            <img id="overlay-machine-image" src="{{ payload.live_session.queue[0].machine_image }}" alt="{{ payload.live_session.queue[0].machine_label }}" style="width:100%;border-radius:18px;border:1px solid rgba(255,255,255,.08);display:block;background:#111;">
            {% else %}
            <div id="overlay-machine-image" style="display:none;"></div>
            {% endif %}
            <strong id="overlay-machine-label" style="display:block;margin-top:12px;">{{ payload.live_session.queue[0].machine_label if payload.live_session.queue else "Training station" }}</strong>
            <p id="overlay-machine-focus">{{ payload.live_session.queue[0].machine_focus if payload.live_session.queue else "Follow the live coaching lane." }}</p>
          </div>
          <div class="player-strip">
            <div class="tag" id="overlay-voice-state">{{ payload.voice_coach.mode_label }}</div>
            <div class="tag">{{ payload.voice_coach.session_type|title }} cues</div>
          </div>
          <div class="player-overlay-checkpoints" id="overlay-checkpoints"></div>
          <div class="player-overlay-footer">
            <div class="player-overlay-actions">
              <button type="button" class="player-btn primary" id="overlay-complete-step">Complete current set</button>
              <button type="button" class="player-btn ghost" id="overlay-open-source">Technique source</button>
            </div>
            <div class="player-overlay-actions">
              <button type="button" class="player-btn primary" id="overlay-voice-cue">Voice cue</button>
              <button type="button" class="player-btn ghost" id="overlay-voice-toggle">Auto voice on</button>
            </div>
            <div class="player-overlay-actions">
              <button type="button" class="player-btn primary" id="overlay-play">Play</button>
              <button type="button" class="player-btn" id="overlay-pause">Pause</button>
              <button type="button" class="player-btn" id="overlay-reset">Reset</button>
              <button type="button" class="player-btn ghost" id="overlay-preset-cycle">Next preset</button>
            </div>
            <div class="player-overlay-nav">
              <button type="button" class="player-btn" id="overlay-prev">Prev</button>
              <button type="button" class="player-btn ghost" id="overlay-exit">Exit</button>
              <button type="button" class="player-btn" id="overlay-next">Next</button>
            </div>
            <div class="swipe-note">Swipe left or right on the workout screen to move between exercises while the timer stays live.</div>
          </div>
        </div>
        <div class="summary-strip">
          <article class="summary-card">
            <div class="mini">Session finish</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.live_session.completion_title }}</strong>
            <p style="margin-top:12px;">{{ payload.live_session.completion_note }}</p>
          </article>
          <article class="summary-card">
            <div class="mini">Weekly coach review</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.weekly_review.score }} / 100</strong>
            <p style="margin-top:12px;">{{ payload.weekly_review.headline }}</p>
            <ul class="list" style="margin-top:10px;">
              {% for point in payload.weekly_review.points %}
              <li>{{ point }}</li>
              {% endfor %}
            </ul>
            <div class="notice">{{ payload.weekly_review.adjustment }}</div>
            <div class="next">{{ payload.weekly_review.next_week_adjustment }}</div>
          </article>
        </div>
        <div class="trend-grid" style="margin-top:16px;">
          {% for item in payload.session_analytics.tiles %}
          <article class="kpi">
            <span class="mini">{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.detail }}</p>
          </article>
          {% endfor %}
        </div>
        <div class="today-grid">
          <article class="option">
            <div class="head-row">
              <div>
                <div class="mini">{{ payload.today_blueprint.coach_role }} - {{ payload.today_blueprint.status_label }}</div>
                <strong>{{ payload.today_blueprint.title }}</strong>
              </div>
              <div class="tag">{{ payload.today_blueprint.duration }}</div>
            </div>
            <p>Coach: {{ payload.today_blueprint.coach_name }}</p>
            <div class="notice">{{ payload.today_blueprint.warmup }}</div>
            <p>{{ payload.today_blueprint.focus_line }}</p>
            {% if payload.today_blueprint.day_type == "training" %}
            <div class="stack" style="margin-top:14px;">
              {% for item in payload.today_blueprint.exercises %}
              <article class="log">
                <div class="mini">Step {{ item.order }} - {{ item.block }} - {{ item.duration }}</div>
                {% if item.machine_image %}
                <img src="{{ item.machine_image }}" alt="{{ item.machine_label }}" style="width:100%;max-width:240px;border-radius:18px;border:1px solid rgba(255,255,255,.08);display:block;margin:10px 0;background:#111;">
                {% endif %}
                <strong style="display:block;margin-top:6px;">{{ item.name }}</strong>
                <div class="notice" style="margin-top:10px;">{{ item.machine_label }} - {{ item.machine_focus }}</div>
                <p>{{ item.sets }} sets - {{ item.reps }} reps - rest {{ item.rest }}</p>
                <p>{{ item.note }}</p>
                <form method="post" action="/today/check" style="margin-top:10px;">
                  <input type="hidden" name="item_type" value="exercise">
                  <input type="hidden" name="item_key" value="{{ item.item_key }}">
                  <button type="submit">{% if item.item_key in payload.completed_today %}Completed{% else %}Mark exercise done{% endif %}</button>
                </form>
              </article>
              {% endfor %}
            </div>
            {% else %}
            <ul class="list">
              {% for item in payload.today_blueprint.rest_day_actions %}
              <li>{{ item }}</li>
              {% endfor %}
            </ul>
            {% endif %}
            <div class="next">Latest athlete note: {{ payload.today_blueprint.latest_note }}</div>
          </article>
          <article class="option">
            <div class="mini">{{ payload.ui.nutrition_title }}</div>
            <strong>{% if payload.today_blueprint.day_type == "training" %}Coach meal structure{% else %}Recovery nutrition{% endif %}</strong>
            <div class="stack" style="margin-top:14px;">
              {% for item in payload.today_blueprint.nutrition %}
              <article class="log">
                <div class="mini">{{ item.time }} - {{ item.title }}</div>
                <strong style="display:block;margin-top:6px;">{{ item.meal }}</strong>
                <p>{{ item.purpose }}</p>
                <form method="post" action="/today/check" style="margin-top:10px;">
                  <input type="hidden" name="item_type" value="meal">
                  <input type="hidden" name="item_key" value="{{ item.item_key }}">
                  <button type="submit">{% if item.item_key in payload.completed_today %}Completed{% else %}Mark meal done{% endif %}</button>
                </form>
              </article>
              {% endfor %}
            </div>
          </article>
        </div>
        <div class="panel-grid" style="margin-top:16px;">
          {% for item in payload.exercise_mastery %}
          <article class="log">
            <div class="mini">Exercise mastery</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">{{ item.name }}</strong>
            <ul class="list" style="margin-top:12px;">
              <li><strong>Setup:</strong> {{ item.setup }}</li>
              <li><strong>Execution:</strong> {{ item.execution }}</li>
              <li><strong>Avoid:</strong> {{ item.mistake }}</li>
              <li><strong>Swap:</strong> {{ item.swap }}</li>
            </ul>
          </article>
          {% endfor %}
        </div>
      </section>

      <details class="panel panel-collapsible pro-heavy" id="assistant" open>
        <summary class="panel-summary">
          <div><div class="mini">Assistant</div><strong>{{ payload.ui.assistant_title }}</strong></div>
          <div class="tag">Coach</div>
        </summary>
        <div class="panel-body">
        <div class="notice">{{ payload.ui.coaches_title }}</div>
        <div class="coach-grid">
          {% for coach in payload.personal_trainers %}
          <article class="option">
            <div class="mini">{{ coach.lead }}</div>
            <strong>{{ coach.name }}</strong>
            <div class="notice">{{ coach.role }}</div>
            <p>{{ coach.duty }}</p>
            <p>{{ coach.tone }}</p>
          </article>
          {% endfor %}
        </div>
        <div class="next">{{ payload.assistant.headline }}</div>
        <div class="grid3">
          <article class="kpi"><span class="mini">Protein</span><strong>{{ payload.assistant.targets.protein }}g</strong></article>
          <article class="kpi"><span class="mini">Carbs</span><strong>{{ payload.assistant.targets.carbs }}g</strong></article>
          <article class="kpi"><span class="mini">Fats</span><strong>{{ payload.assistant.targets.fats }}g</strong></article>
        </div>
        <div class="panel-grid" style="margin-top:16px;">
          <article class="log">
            <div class="mini">{{ payload.periodization_engine.headline }}</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.periodization_engine.block_name }}</strong>
            <p style="margin-top:10px;">{{ payload.periodization_engine.week_label }} - {{ payload.periodization_engine.phase_signal }}</p>
            <div class="notice">{{ payload.periodization_engine.today_fit }}</div>
            <p style="margin-top:10px;">{{ payload.periodization_engine.week_focus }}</p>
            <div class="next">{{ payload.periodization_engine.coach_call }} Up next: {{ payload.periodization_engine.up_next }}</div>
          </article>
          <article class="log">
            <div class="mini">{{ payload.adaptive_training_engine.headline }}</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.adaptive_training_engine.readiness }}</strong>
            <p style="margin-top:10px;">{{ payload.adaptive_training_engine.today_rule }}</p>
            <div class="notice">{{ payload.adaptive_training_engine.volume_anchor }}</div>
            <ul class="list" style="margin-top:12px;">
              {% for item in payload.adaptive_training_engine.session_order %}
              <li>{{ item }}</li>
              {% endfor %}
            </ul>
            <div class="next">{{ payload.adaptive_training_engine.next_week }}</div>
          </article>
          <article class="log">
            <div class="mini">Smart substitutions</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.adaptive_training_engine.recent_focus }}</strong>
            <ul class="list" style="margin-top:12px;">
              {% for item in payload.adaptive_training_engine.substitutions %}
              <li>{{ item }}</li>
              {% endfor %}
            </ul>
          </article>
        </div>
        <div class="panel-grid" style="margin-top:16px;">
          <div class="log">
            <div class="mini">Training logic</div>
            <ul class="list">
              {% for item in payload.assistant.training_summary %}
              <li>{{ item }}</li>
              {% endfor %}
            </ul>
          </div>
          <div class="log">
            <div class="mini">Nutrition logic</div>
            <ul class="list">
              {% for item in payload.assistant.nutrition_summary %}
              <li>{{ item }}</li>
              {% endfor %}
            </ul>
          </div>
        </div>
        <div class="next">{{ payload.assistant.next_action }}</div>
        </div>
      </details>

      <details class="panel panel-collapsible" id="mission">
        <summary class="panel-summary">
          <div><div class="mini">Daily mission</div><strong>{{ payload.ui.mission_title }}</strong></div>
          <div class="tag">Meals</div>
        </summary>
        <div class="panel-body">
        <div class="log">
          <ul class="list">
            {% for item in payload.daily_mission %}
            <li>{{ item }}</li>
            {% endfor %}
          </ul>
        </div>
        <div class="panel-grid" style="margin-top:16px;">
          <article class="log">
            <div class="mini">{{ payload.nutrition_intelligence.headline }}</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.nutrition_intelligence.next_meal_title }}</strong>
            <p style="margin-top:10px;">{{ payload.nutrition_intelligence.next_meal_detail }}</p>
            <div class="notice">{{ payload.nutrition_intelligence.next_meal_purpose }}</div>
            <ul class="list" style="margin-top:12px;">
              <li>Calories left: {{ payload.nutrition_intelligence.calories_left }}</li>
              <li>Protein left: {{ payload.nutrition_intelligence.protein_left }}g</li>
              <li>Carbs left: {{ payload.nutrition_intelligence.carbs_left }}g</li>
              <li>Fats left: {{ payload.nutrition_intelligence.fats_left }}g</li>
            </ul>
          </article>
          <article class="log">
            <div class="mini">Smart swaps and prep</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">Keep food simple</strong>
            <ul class="list" style="margin-top:12px;">
              {% for item in payload.nutrition_intelligence.smart_swaps %}
              <li>{{ item }}</li>
              {% endfor %}
            </ul>
            <div class="notice" style="margin-top:12px;">Prep</div>
            <ul class="list" style="margin-top:10px;">
              {% for item in payload.nutrition_intelligence.prep_steps %}
              <li>{{ item }}</li>
              {% endfor %}
            </ul>
          </article>
        </div>
        <div class="meal-grid" style="margin-top:16px;">
          {% for meal in payload.meal_suggestions %}
          <article class="option">
            <div class="mini">{{ meal.time }}</div>
            <strong>{{ meal.title }}</strong>
            <p>{{ meal.details }}</p>
            <div class="notice">{{ meal.macro }}</div>
          </article>
          {% endfor %}
        </div>
        <form method="post" action="/log-meal" class="form2" style="margin-top:16px;">
          <label>Meal type
            <select name="meal_type">
              <option value="breakfast">Breakfast</option>
              <option value="lunch">Lunch</option>
              <option value="pre-workout">Pre-workout</option>
              <option value="post-workout">Post-workout</option>
              <option value="dinner">Dinner</option>
            </select>
          </label>
          <label>Food name<input type="text" name="food_name" placeholder="Chicken and rice"></label>
          <label>Grams<input type="number" step="0.1" name="grams" value="150"></label>
          <label>Calories<input type="number" step="0.1" name="calories" value="450"></label>
          <label>Protein<input type="number" step="0.1" name="protein" value="35"></label>
          <label>Carbs<input type="number" step="0.1" name="carbs" value="40"></label>
          <label>Fats<input type="number" step="0.1" name="fats" value="12"></label>
          <label>Goal tag<input type="text" name="goal_tag" value="{{ payload.user.goal }}"></label>
          <label class="full">Notes<input type="text" name="notes" placeholder="Quick meal note"></label>
          <input type="hidden" name="logged_at" value="{{ today }}T12:00">
          <button class="full" type="submit">Log meal from dashboard</button>
        </form>
        </div>
      </details>

      <details class="panel span panel-collapsible pro-heavy" id="progress">
        <summary class="panel-summary">
          <div><div class="mini">Progress</div><strong>{{ payload.ui.progress_title }}</strong></div>
          <div class="tag">Trends</div>
        </summary>
        <div class="panel-body">
        <div class="trend-grid">
          {% for item in payload.progress_trends %}
          <article class="kpi">
            <span class="mini">{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.detail }}</p>
          </article>
          {% endfor %}
        </div>
        <div class="trend-grid" style="margin-top:16px;">
          {% for item in payload.recomposition_dashboard.tiles %}
          <article class="kpi">
            <span class="mini">{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.detail }}</p>
          </article>
          {% endfor %}
        </div>
        <div class="panel-grid" style="margin-top:16px;">
          <article class="log">
            <div class="mini">{{ payload.progress_system.headline }}</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">{{ payload.progress_system.recomposition_score }}/100</strong>
            <p style="margin-top:10px;">Adherence score: {{ payload.progress_system.adherence_score }}/100</p>
            <ul class="list" style="margin-top:12px;">
              {% for item in payload.progress_system.wins %}
              <li>{{ item }}</li>
              {% endfor %}
            </ul>
          </article>
          <article class="log">
            <div class="mini">Watchouts</div>
            <strong style="display:block;margin-top:8px;font-size:24px;">Next checkpoint</strong>
            <ul class="list" style="margin-top:12px;">
              {% for item in payload.progress_system.watchouts %}
              <li>{{ item }}</li>
              {% endfor %}
            </ul>
            <div class="next">{{ payload.progress_system.next_checkpoint }}</div>
          </article>
        </div>
        </div>
      </details>

      <details class="panel span panel-collapsible pro-heavy" id="market">
        <summary class="panel-summary">
          <div><div class="mini">Launch</div><strong>{{ payload.ui.pricing_title }}</strong></div>
          <div class="tag">{{ payload.user.subscription_tier|title }}</div>
        </summary>
        <div class="panel-body">
        <div class="log" style="margin-bottom:16px;">
          <strong>Aktivni paket: {{ payload.user.subscription_tier|title }}</strong>
          <p>Status: {{ payload.user.billing_status|title }}{% if payload.user.gift_package %} - Gift access{% endif %}</p>
          <p>{% if payload.user.discount_code %}Discount code: {{ payload.user.discount_code }} ({{ payload.user.discount_percent }}%){% else %}Discount code jos nije iskoriscen.{% endif %}</p>
          <p>Trial: {{ payload.access.status_label }}</p>
          <p>Preporuceni paket: {{ payload.access.recommended_tier|title }}</p>
        </div>
        <div class="pricing-grid">
          {% for plan in payload.subscription_plans %}
          <article class="option">
            <div class="mini">{{ plan.price }}</div>
            <strong>{{ plan.name }}</strong>
            <p>{{ plan.detail }}</p>
            {% if plan.key == "starter" %}
            <div class="notice">Starter je ukljucen automatski kao full trial tokom prvih {{ payload.access.days_left if payload.access.trial_active else 0 }} dana.</div>
            {% else %}
            <form method="post" action="/subscribe" style="margin-top:14px;">
              <input type="hidden" name="subscription_tier" value="{{ plan.key }}">
              <label>Discount code<input type="text" name="discount_code" placeholder="FORGE10"></label>
              <button type="submit">Aktiviraj {{ plan.name }}</button>
            </form>
            {% endif %}
          </article>
          {% endfor %}
        </div>
        <div class="planner-grid">
          {% for item in payload.market_flags %}
          <article class="option">
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
          </article>
          {% endfor %}
        </div>
        <div class="pricing-grid">
          {% for item in payload.commercial_offers %}
          <article class="option">
            <div class="mini">{{ item.price }}</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
          </article>
          {% endfor %}
        </div>
        </div>
      </details>

      <details class="panel panel-collapsible pro-heavy" id="wellness">
        <summary class="panel-summary">
          <div><div class="mini">{{ payload.ui.wellness_title }}</div><strong>{{ payload.wellness_panel.title }}</strong></div>
          <div class="tag">Recovery</div>
        </summary>
        <div class="panel-body">
        <div class="log">
          <p>{{ payload.wellness_panel.tone }}</p>
          <ul class="list">
            {% for item in payload.wellness_panel.points %}
            <li>{{ item }}</li>
            {% endfor %}
          </ul>
        </div>
      </section>

      <section class="panel span" id="planner">
        <div class="section-head">
          <div><div class="mini">Weekly planner</div><h2>{{ payload.ui.planner_title }}</h2></div>
        </div>
        <div class="planner-grid">
          {% for item in payload.weekly_planner %}
          <article class="option">
            <div class="mini">{{ item.day_label }} - {{ item.date }}</div>
            <strong>{{ item.title }}</strong>
            <div class="notice">{{ item.type }}</div>
            <p>{{ item.details }}</p>
          </article>
          {% endfor %}
        </div>
        </div>
      </details>

      <section class="panel span" id="ai-trainer">
        <div class="section-head">
          <div><div class="mini">AI</div><h2>{{ payload.ui.chat_title }}</h2></div>
        </div>
        <div class="log" style="margin-bottom:16px;">
          <strong>{{ payload.ai_concierge.name }}</strong>
          <p>{{ payload.ai_concierge.greeting }}</p>
        </div>
        <div class="chat-grid">
          <div>
            {% if payload.ai_concierge.enabled %}
            <form method="post" action="/assistant/chat">
              <label>Poruka treneru<textarea name="message" placeholder="Na primjer: sta da radim danas ako sam umoran?"></textarea></label>
              <button type="submit">Posalji AI treneru</button>
            </form>
            {% else %}
            <div class="log">
              <strong>Elite AI trener</strong>
              <p>Puni personalni AI chat je dostupan u Elite paketu ili tokom trial perioda.</p>
            </div>
            {% endif %}
            <div class="chat-stack">
              {% for item in payload.coach_messages %}
              <article class="bubble {% if item.sender == 'user' %}user{% else %}coach{% endif %}">
                <div class="mini">{{ item.sender }} - {{ item.created_at }}</div>
                <p>{{ item.message }}</p>
              </article>
              {% endfor %}
            </div>
          </div>
          <div>
            <div class="notice">Coach memory</div>
            <form method="post" action="/coach-memory">
              <label>Save a personal note for the AI coach<textarea name="memory_text" placeholder="Example: my shoulder gets irritated on heavy overhead work, or I prefer morning training."></textarea></label>
              <button type="submit">Save to coach memory</button>
            </form>
            <div class="chat-stack">
              {% for item in payload.coach_memory %}
              <article class="bubble user">
                <div class="mini">{{ item.memory_type }} - {{ item.created_at }}</div>
                <p>{{ item.memory_text }}</p>
              </article>
              {% endfor %}
            </div>
            <div class="notice">{{ payload.ui.checkin_title }}</div>
            <form method="post" action="/checkin/daily" class="form2">
              <label>Mood
                <select name="mood">
                  <option value="locked in">Locked in</option>
                  <option value="steady">Steady</option>
                  <option value="tired">Tired</option>
                  <option value="flat">Flat</option>
                </select>
              </label>
              <label>Energy<input type="number" name="energy_score" value="7" min="1" max="10"></label>
              <label>Soreness<input type="number" name="soreness_score" value="4" min="1" max="10"></label>
              <label>Motivation<input type="number" name="motivation_score" value="7" min="1" max="10"></label>
              <label class="full">Note<textarea name="note" placeholder="Kako se osjecas, sta te boli i kako si spavao?"></textarea></label>
              <button class="full" type="submit">Sacuvaj daily check-in</button>
            </form>
            <div class="chat-stack">
              {% for item in payload.checkins %}
              <article class="bubble coach">
                <div class="mini">{{ item.checkin_date }} - mood {{ item.mood }}</div>
                <p>Energy {{ item.energy_score }}/10 - soreness {{ item.soreness_score }}/10 - motivation {{ item.motivation_score }}/10</p>
                <p>{{ item.note }}</p>
              </article>
              {% endfor %}
            </div>
          </div>
        </div>
      </section>

      <section class="panel span" id="pr-tracker">
        <div class="section-head">
          <div><div class="mini">PR tracker</div><h2>Best lifts by exercise</h2></div>
        </div>
        <div class="pr-grid">
          {% for item in payload.pr_tracker %}
          <article class="option">
            <div class="mini">{{ item.category }}</div>
            <strong>{{ item.exercise_name }}</strong>
            <div class="notice">{{ item.weight_kg }} kg - {{ item.reps_text }}</div>
            <p>{{ item.logged_at }}</p>
          </article>
          {% endfor %}
        </div>
      </section>

      <section class="panel" id="calendar">
        <div class="section-head">
          <div><div class="mini">{{ payload.ui.calendar }}</div><h2>{{ payload.ui.calendar_title }}</h2></div>
        </div>
        <div class="section-head" style="margin-top:16px;">
          <div><div class="mini">Nutrition</div><h2>{{ payload.ui.shopping_title }}</h2></div>
        </div>
        <div class="planner-grid">
          {% for item in payload.shopping_list %}
          <article class="option">
            <div class="mini">Shop</div>
            <strong>{{ item.name }}</strong>
            <p>{{ item.reason }}</p>
          </article>
          {% endfor %}
        </div>
        <div class="calendar-lane">
          {% for day in payload.personal_calendar %}
          <article class="option">
            <div class="mini">{{ day.day_label }} - {{ day.date }}</div>
            <strong>Coach day flow</strong>
            <ul class="list">
              {% for slot in day.slots %}
              <li><strong>{{ slot.time }}</strong> - {{ slot.title }} - {{ slot.detail }}</li>
              {% endfor %}
            </ul>
          </article>
          {% endfor %}
        </div>
        <div class="panel-grid">
          <form method="post" action="/calendar/add" class="form2">
            <label>Date<input type="date" name="event_date" value="{{ today }}"></label>
            <label>Type
              <select name="event_type"><option value="training">Training</option><option value="nutrition">Nutrition</option><option value="recovery">Recovery</option><option value="checkin">Check-in</option></select>
            </label>
            <label class="full">Title<input type="text" name="title" placeholder="Upper strength day"></label>
            <label>Coach
              <select name="coach_key"><option value="strength">Strength</option><option value="hypertrophy">Hypertrophy</option><option value="conditioning">Conditioning</option><option value="mobility">Recovery</option></select>
            </label>
            <label class="full">Details<textarea name="details" placeholder="What is planned for that day"></textarea></label>
            <button class="full" type="submit">Dodaj u kalendar</button>
          </form>
          <div class="logs">
            {% for item in payload.calendar %}
            <article class="log">
              <div class="mini">{{ item.event_date }} - {{ item.event_type }}</div>
              <strong style="display:block;margin-top:8px;font-size:22px;">{{ item.title }}</strong>
              <p>{{ item.details }}</p>
            </article>
            {% endfor %}
          </div>
        </div>
      </section>

      {% if payload.user.role == "admin" %}
      <section class="panel span" id="admin">
        <div class="section-head">
          <div><div class="mini">Admin</div><h2>Create separate user accounts</h2></div>
        </div>
        <div class="trend-grid">
          <article class="kpi"><span class="mini">Users</span><strong>{{ payload.business.total_users }}</strong></article>
          <article class="kpi"><span class="mini">Members</span><strong>{{ payload.business.total_members }}</strong></article>
          <article class="kpi"><span class="mini">Paid</span><strong>{{ payload.business.active_paid_users }}</strong></article>
          <article class="kpi"><span class="mini">Gifted</span><strong>{{ payload.business.gifted_users }}</strong></article>
          <article class="kpi"><span class="mini">MRR</span><strong>{{ payload.business.mrr }} EUR</strong></article>
        </div>
        <div class="panel-grid">
          <form method="post" action="/admin/users" class="form2">
            <label>Ime i prezime<input type="text" name="full_name" required></label>
            <label>Username<input type="text" name="username" required></label>
            <label>Password<input type="text" name="password" required></label>
            <label>Pol
              <select name="gender">
                <option value="male">Musko</option>
                <option value="female">Zensko</option>
              </select>
            </label>
            <label>Cycle mode
              <select name="cycle_phase">
                <option value="neutral">Neutral</option>
                <option value="performance">Performance</option>
                <option value="recovery">Recovery</option>
                <option value="late_cycle">Late cycle</option>
              </select>
            </label>
            <label>Oprema
              <select name="equipment_access">
                <option value="full gym">Full gym</option>
                <option value="home">Home</option>
                <option value="hotel">Hotel</option>
              </select>
            </label>
            <label>Umor
              <select name="fatigue_state">
                <option value="steady">Steady</option>
                <option value="high">High</option>
                <option value="drained">Drained</option>
              </select>
            </label>
            <label>Goal
              <select name="goal"><option value="performance">Performance</option><option value="muscle">Muscle</option><option value="cut">Cut</option></select>
            </label>
            <label>Subscription
              <select name="subscription_tier"><option value="starter">Starter</option><option value="pro">Pro</option><option value="elite">Elite</option></select>
            </label>
            <label>Years<input type="number" name="age" value="28"></label>
            <label>Height cm<input type="number" step="0.1" name="height_cm" value="180"></label>
            <label>Weight kg<input type="number" step="0.1" name="weight_kg" value="80"></label>
            <label>Experience
              <select name="experience_level"><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select>
            </label>
            <label class="full">Role
              <select name="role"><option value="member">Member</option><option value="admin">Admin</option></select>
            </label>
            <button class="full" type="submit">Create user</button>
          </form>
          <form method="post" action="/admin/gift-package" class="form2" style="margin-bottom:14px;">
            <label>Korisnik
              <select name="user_id">
                {% for user in payload.users if user.role != "admin" %}
                <option value="{{ user.id }}">{{ user.full_name }} (@{{ user.username }})</option>
                {% endfor %}
              </select>
            </label>
            <label>Gift paket
              <select name="subscription_tier">
                {% for plan in payload.subscription_plans if plan.key != "starter" %}
                <option value="{{ plan.key }}">{{ plan.name }}</option>
                {% endfor %}
              </select>
            </label>
            <label class="full">Napomena<input type="text" name="gift_note" placeholder="Founder gift, launch partner..."></label>
            <button class="full" type="submit">Dodijeli gift paket</button>
          </form>
          <div class="users-grid">
            {% for user in payload.users %}
            <article class="user-card">
              <div class="mini">{{ user.role }} - {{ user.billing_status|title }}</div>
              <strong>{{ user.full_name }}</strong>
              <p>Gift: {{ "Yes" if user.gift_package else "No" }}{% if user.gifted_by %} - by {{ user.gifted_by }}{% endif %}</p>
              <p>Discount: {% if user.discount_code %}{{ user.discount_code }} ({{ user.discount_percent }}%){% else %}None{% endif %}</p>
              <p>@{{ user.username }} - {{ user.subscription_tier|title }} - {{ user.gender|title }} - {{ user.age }} yrs - {{ user.height_cm }} cm - {{ user.weight_kg }} kg - {{ user.goal }}</p>
            </article>
            {% endfor %}
          </div>
        </div>
      </section>
      {% endif %}
      <section class="panel span" id="legal">
        <div class="section-head">
          <div><div class="mini">Legal</div><h2>Launch footer</h2></div>
        </div>
        <div class="quickbar">
          <a href="/terms">{{ payload.ui.legal_terms }}</a>
          <a href="/privacy">{{ payload.ui.legal_privacy }}</a>
          <a href="/app-version">Build</a>
          <a href="/health">Health</a>
        </div>
      </section>
    </main>
    {% endif %}

    <nav class="bottom">
      <a href="#today-plan">Today</a>
      <a href="#plans">Plans</a>
      <a href="#mission">Meals</a>
      <a href="#ai-trainer">Coach</a>
      <a href="#profile">Profile</a>
    </nav>
  </div>
  <script id="live-session-json" type="application/json">{{ payload.live_session|tojson }}</script>
  <script id="voice-coach-json" type="application/json">{{ payload.voice_coach|tojson }}</script>
  <script>
    (function () {
      const player = document.getElementById("workout-player");
      if (!player) return;
      const timerNode = document.getElementById("player-timer");
      const sessionTimerNode = document.getElementById("session-timer");
      const statusNode = document.getElementById("player-status");
      const playBtn = document.getElementById("player-play");
      const pauseBtn = document.getElementById("player-pause");
      const resetBtn = document.getElementById("player-reset");
      const mainStartBtn = document.getElementById("player-start-main");
      const startSessionBtn = document.getElementById("player-start-session");
      const stopSessionBtn = document.getElementById("player-stop-session");
      const presetButtons = document.querySelectorAll(".preset-btn");
      const overlay = document.getElementById("player-overlay");
      const overlayCloseBtn = document.getElementById("player-close");
      const overlayExitBtn = document.getElementById("overlay-exit");
      const overlayTimer = document.getElementById("overlay-timer");
      const overlayStepLabel = document.getElementById("overlay-step-label");
      const overlayStepTitle = document.getElementById("overlay-step-title");
      const overlayStepDetail = document.getElementById("overlay-step-detail");
      const overlayWeight = document.getElementById("overlay-weight");
      const overlayRest = document.getElementById("overlay-rest");
      const overlayMachineImage = document.getElementById("overlay-machine-image");
      const overlayMachineLabel = document.getElementById("overlay-machine-label");
      const overlayMachineFocus = document.getElementById("overlay-machine-focus");
      const overlayTechniqueHead = document.getElementById("overlay-technique-head");
      const overlayTechniqueTail = document.getElementById("overlay-technique-tail");
      const overlayCheckpoints = document.getElementById("overlay-checkpoints");
      const overlayProgressBar = document.getElementById("overlay-progress-bar");
      const overlayCompleteBtn = document.getElementById("overlay-complete-step");
      const overlaySourceBtn = document.getElementById("overlay-open-source");
      const overlayVoiceBtn = document.getElementById("overlay-voice-cue");
      const overlayVoiceToggleBtn = document.getElementById("overlay-voice-toggle");
      const overlayVoiceState = document.getElementById("overlay-voice-state");
      const overlayPlayBtn = document.getElementById("overlay-play");
      const overlayPauseBtn = document.getElementById("overlay-pause");
      const overlayResetBtn = document.getElementById("overlay-reset");
      const overlayPresetBtn = document.getElementById("overlay-preset-cycle");
      const overlayPrevBtn = document.getElementById("overlay-prev");
      const overlayNextBtn = document.getElementById("overlay-next");
      const sessionScript = document.getElementById("live-session-json");
      const voiceScript = document.getElementById("voice-coach-json");
      const sessionData = sessionScript ? JSON.parse(sessionScript.textContent || "{}") : {};
      const voiceCoach = voiceScript ? JSON.parse(voiceScript.textContent || "{}") : {};

      function parseRest(value) {
        const text = String(value || "").toLowerCase();
        const match = text.match(/(\\d+)/);
        return match ? Number(match[1]) : 60;
      }

      const defaultSeconds = parseRest(player.dataset.rest);
      let currentPreset = defaultSeconds;
      let secondsLeft = defaultSeconds;
      let intervalId = null;
      let sessionSeconds = 0;
      let sessionIntervalId = null;
      let queue = Array.isArray(sessionData.queue) ? sessionData.queue : [];
      let activeIndex = Math.max(0, queue.findIndex(function (item) { return !item.done; }));
      if (activeIndex < 0) activeIndex = 0;
      let touchStartX = 0;
      let touchEndX = 0;
      let autoVoiceEnabled = !!voiceCoach.auto_enabled;
      let lastSpokenKey = "";

      function updateVoiceStateLabel(message) {
        if (overlayVoiceState) overlayVoiceState.textContent = message;
        if (overlayVoiceToggleBtn) overlayVoiceToggleBtn.textContent = autoVoiceEnabled ? "Auto voice on" : "Auto voice off";
      }

      function buildVoiceCue(item) {
        if (!item) {
          return "Workout complete. Great job. Hydrate, cool down and log your recovery.";
        }
        const technique = Array.isArray(sessionData.technique) ? sessionData.technique : [];
        const checkpointSummary = Array.isArray(item.checkpoints) && item.checkpoints.length
          ? item.checkpoints.filter(function (checkpoint) { return !checkpoint.done; }).map(function (checkpoint) { return checkpoint.label; }).join(", ")
          : "Complete the movement cleanly.";
        return [
          voiceCoach.opening || "Coach cue ready.",
          "Current move: " + item.name + ".",
          item.detail || "",
          "Weight suggestion: " + (item.weight_suggestion || "Use a clean working load.") + ".",
          technique[0] || "Stay braced and move with control.",
          "Next checkpoints: " + checkpointSummary + ".",
        ].filter(Boolean).join(" ");
      }

      function speakVoiceCue(force) {
        if (!("speechSynthesis" in window)) {
          updateVoiceStateLabel("Voice not supported");
          return;
        }
        const item = queue[activeIndex] || null;
        const voiceKey = item && item.item_key ? item.item_key : "session-finish";
        if (!force && (!autoVoiceEnabled || voiceKey === lastSpokenKey)) return;
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(buildVoiceCue(item));
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.lang = "en-US";
        window.speechSynthesis.speak(utterance);
        lastSpokenKey = voiceKey;
        updateVoiceStateLabel(autoVoiceEnabled ? "Voice cue live" : "Voice cue played");
      }

      function renderTime() {
        const mins = String(Math.floor(secondsLeft / 60)).padStart(2, "0");
        const secs = String(secondsLeft % 60).padStart(2, "0");
        timerNode.textContent = mins + ":" + secs;
        if (overlayTimer) overlayTimer.textContent = mins + ":" + secs;
      }

      function renderSessionTime() {
        if (!sessionTimerNode) return;
        const mins = String(Math.floor(sessionSeconds / 60)).padStart(2, "0");
        const secs = String(sessionSeconds % 60).padStart(2, "0");
        sessionTimerNode.textContent = mins + ":" + secs;
      }

      function startSessionTimer() {
        if (sessionIntervalId) return;
        sessionIntervalId = window.setInterval(function () {
          sessionSeconds += 1;
          renderSessionTime();
        }, 1000);
      }

      function stopSessionTimer() {
        if (!sessionIntervalId) return;
        window.clearInterval(sessionIntervalId);
        sessionIntervalId = null;
      }

      function startTimer() {
        if (intervalId) return;
        statusNode.textContent = "Workout in progress. Follow the current block, then use the timer between sets.";
        if (overlayStepDetail) overlayStepDetail.textContent = "Workout is live. Stay on the current movement, then use the rest timer before the next set.";
        intervalId = window.setInterval(function () {
          if (secondsLeft > 0) {
            secondsLeft -= 1;
            renderTime();
            return;
          }
          window.clearInterval(intervalId);
          intervalId = null;
          statusNode.textContent = "Rest block finished. Move to the next set or next exercise.";
          if (overlayStepDetail) overlayStepDetail.textContent = "Rest finished. Hit complete for the next set or swipe to the next movement.";
        }, 1000);
      }

      function pauseTimer() {
        if (intervalId) {
          window.clearInterval(intervalId);
          intervalId = null;
        }
        statusNode.textContent = "Timer paused. Resume when you are ready.";
        if (overlayStepDetail) overlayStepDetail.textContent = "Timer paused. Reset or resume when you are ready to continue.";
      }

      function resetTimer() {
        if (intervalId) {
          window.clearInterval(intervalId);
          intervalId = null;
        }
        secondsLeft = currentPreset;
        renderTime();
        statusNode.textContent = "Timer reset. Press play to begin the next rest block.";
        if (overlayStepDetail) overlayStepDetail.textContent = "Timer reset. Start the next rest block when the current set is finished.";
      }

      function openOverlay() {
        if (!overlay) return;
        overlay.classList.add("open");
        overlay.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
      }

      function closeOverlay() {
        if (!overlay) return;
        overlay.classList.remove("open");
        overlay.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
      }

      function renderCheckpoints(item) {
        if (!overlayCheckpoints) return;
        overlayCheckpoints.innerHTML = "";
        if (!item) {
          overlayCheckpoints.innerHTML = '<div class="player-overlay-checkpoint"><div><strong>Workout complete</strong><p>No pending steps left in this queue.</p></div></div>';
          return;
        }
        if (Array.isArray(item.checkpoints) && item.checkpoints.length) {
          item.checkpoints.forEach(function (checkpoint) {
            const row = document.createElement("div");
            row.className = "player-overlay-checkpoint" + (checkpoint.done ? " done" : "");
            row.innerHTML = "<div><strong>" + checkpoint.label + "</strong><p>" + (checkpoint.done ? "Completed" : "Pending") + "</p></div><div class=\"tag\">" + (checkpoint.done ? "Done" : "Next") + "</div>";
            overlayCheckpoints.appendChild(row);
          });
          return;
        }
        const row = document.createElement("div");
        row.className = "player-overlay-checkpoint" + (item.done ? " done" : "");
        row.innerHTML = "<div><strong>" + item.name + "</strong><p>" + (item.done ? "Marked complete" : "Use one tap to finish this movement.") + "</p></div><div class=\"tag\">" + (item.done ? "Done" : "Live") + "</div>";
        overlayCheckpoints.appendChild(row);
      }

      function renderOverlay() {
        if (!overlay) return;
        const total = queue.length || 1;
        const item = queue[activeIndex] || null;
        const completedCount = queue.filter(function (entry) { return entry.done; }).length;
        if (!item) {
          overlayStepLabel.textContent = "Session finish";
          overlayStepTitle.textContent = sessionData.completion_title || "Workout complete";
          overlayStepDetail.textContent = sessionData.completion_note || "Session is complete.";
          overlayWeight.textContent = "No next load";
          overlayRest.textContent = "Cooldown";
          if (overlayMachineImage) overlayMachineImage.style.display = "none";
          if (overlayMachineLabel) overlayMachineLabel.textContent = "Session complete";
          if (overlayMachineFocus) overlayMachineFocus.textContent = "Recovery and food are next.";
          overlayTechniqueHead.textContent = (sessionData.technique || [])[0] || "Great work.";
          overlayTechniqueTail.textContent = (sessionData.technique || [])[1] || "Hydrate and log the session.";
          overlayProgressBar.style.width = "100%";
          renderCheckpoints(null);
          return;
        }
        overlayStepLabel.textContent = "Exercise " + (activeIndex + 1) + " / " + total;
        overlayStepTitle.textContent = item.name;
        overlayStepDetail.textContent = item.detail;
        overlayWeight.textContent = item.weight_suggestion || "Use stable working weight.";
        overlayRest.textContent = "Rest preset: " + currentPreset + " sec";
        if (overlayMachineImage) {
          if (item.machine_image) {
            overlayMachineImage.src = item.machine_image;
            overlayMachineImage.style.display = "block";
          } else {
            overlayMachineImage.style.display = "none";
          }
        }
        if (overlayMachineLabel) overlayMachineLabel.textContent = item.machine_label || "Training station";
        if (overlayMachineFocus) overlayMachineFocus.textContent = item.machine_focus || "Main station";
        overlayTechniqueHead.textContent = (sessionData.technique || [])[0] || "Keep setup tight and move with control.";
        overlayTechniqueTail.textContent = (sessionData.technique || [])[1] || statusNode.textContent;
        overlayProgressBar.style.width = String(Math.round((completedCount / total) * 100)) + "%";
        renderCheckpoints(item);
        if (overlay.classList.contains("open")) {
          speakVoiceCue(false);
        }
      }

      function updateQueueRowUI(itemKey) {
        if (!itemKey) return;
        const row = document.querySelector('[data-item-key="' + itemKey + '"]');
        if (row) {
          row.classList.add("done");
          const tag = row.querySelector(".tag");
          if (tag) tag.textContent = "Done";
        }
      }

      function syncQueueCompletion(item) {
        if (!item) return;
        const allCheckpointsDone = Array.isArray(item.checkpoints) && item.checkpoints.length
          ? item.checkpoints.every(function (checkpoint) { return checkpoint.done; })
          : true;
        if (allCheckpointsDone) {
          item.done = true;
          updateQueueRowUI(item.item_key);
        }
      }

      function nextPendingIndex() {
        const idx = queue.findIndex(function (entry) { return !entry.done; });
        return idx === -1 ? queue.length : idx;
      }

      function moveToIndex(index) {
        if (!queue.length) {
          activeIndex = 0;
          renderOverlay();
          return;
        }
        activeIndex = Math.max(0, Math.min(index, queue.length - 1));
        renderOverlay();
      }

      function nextItem() {
        if (!queue.length) return;
        moveToIndex(Math.min(activeIndex + 1, queue.length - 1));
      }

      function prevItem() {
        if (!queue.length) return;
        moveToIndex(Math.max(activeIndex - 1, 0));
      }

      function completeCurrentStep() {
        const item = queue[activeIndex];
        if (!item) return;
        let payload = null;
        let completedWholeMovement = false;
        if (Array.isArray(item.checkpoints) && item.checkpoints.length) {
          const nextCheckpoint = item.checkpoints.find(function (checkpoint) { return !checkpoint.done; });
          if (nextCheckpoint) {
            payload = { item_type: "set", item_key: nextCheckpoint.item_key };
            nextCheckpoint.done = true;
          }
        }
        if (!payload && !item.done && item.item_key) {
          payload = { item_type: "exercise", item_key: item.item_key };
          item.done = true;
        }
        if (!payload) {
          nextItem();
          return;
        }
        syncQueueCompletion(item);
        completedWholeMovement = !!item.done;
        renderOverlay();
        fetch("/today/check", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"
          },
          body: new URLSearchParams(payload)
        }).then(function () {
          syncQueueCompletion(item);
          const pending = nextPendingIndex();
          if (completedWholeMovement && pending < queue.length && pending !== activeIndex) {
            activeIndex = pending;
            secondsLeft = currentPreset;
            renderTime();
            statusNode.textContent = "Next movement loaded automatically. Start when ready.";
          } else if (pending < queue.length && pending !== activeIndex) {
            activeIndex = pending;
          }
          renderOverlay();
        }).catch(function () {
          statusNode.textContent = "Step saved locally. Refresh if the network drops.";
        });
      }

      function cyclePreset() {
        if (!sessionData.rest_presets || !sessionData.rest_presets.length) return;
        const currentIdx = sessionData.rest_presets.findIndex(function (preset) { return Number(preset.seconds) === currentPreset; });
        const nextIdx = currentIdx === -1 ? 0 : (currentIdx + 1) % sessionData.rest_presets.length;
        currentPreset = Number(sessionData.rest_presets[nextIdx].seconds || defaultSeconds);
        secondsLeft = currentPreset;
        renderTime();
        renderOverlay();
      }

      function openTechniqueSource() {
        if (sessionData.technique_source_url) {
          window.open(sessionData.technique_source_url, "_blank", "noopener");
        }
      }

      function toggleAutoVoice() {
        autoVoiceEnabled = !autoVoiceEnabled;
        lastSpokenKey = "";
        updateVoiceStateLabel(autoVoiceEnabled ? "Voice cue live" : "Voice manual");
        if (autoVoiceEnabled && overlay.classList.contains("open")) {
          speakVoiceCue(true);
        }
      }

      function handleTouchStart(event) {
        touchStartX = event.changedTouches[0].screenX;
      }

      function handleTouchEnd(event) {
        touchEndX = event.changedTouches[0].screenX;
        const diff = touchEndX - touchStartX;
        if (Math.abs(diff) < 40) return;
        if (diff < 0) nextItem();
        if (diff > 0) prevItem();
      }

      renderTime();
      renderSessionTime();
      playBtn.addEventListener("click", startTimer);
      pauseBtn.addEventListener("click", pauseTimer);
      resetBtn.addEventListener("click", resetTimer);
      if (startSessionBtn) startSessionBtn.addEventListener("click", startSessionTimer);
      if (stopSessionBtn) stopSessionBtn.addEventListener("click", stopSessionTimer);
      if (overlayPlayBtn) overlayPlayBtn.addEventListener("click", startTimer);
      if (overlayPauseBtn) overlayPauseBtn.addEventListener("click", pauseTimer);
      if (overlayResetBtn) overlayResetBtn.addEventListener("click", resetTimer);
      if (overlayPresetBtn) overlayPresetBtn.addEventListener("click", cyclePreset);
      if (overlaySourceBtn) overlaySourceBtn.addEventListener("click", openTechniqueSource);
      if (overlayVoiceBtn) overlayVoiceBtn.addEventListener("click", function () { speakVoiceCue(true); });
      if (overlayVoiceToggleBtn) overlayVoiceToggleBtn.addEventListener("click", toggleAutoVoice);
      if (overlayCompleteBtn) overlayCompleteBtn.addEventListener("click", completeCurrentStep);
      if (overlayPrevBtn) overlayPrevBtn.addEventListener("click", prevItem);
      if (overlayNextBtn) overlayNextBtn.addEventListener("click", nextItem);
      if (overlayCloseBtn) overlayCloseBtn.addEventListener("click", closeOverlay);
      if (overlayExitBtn) overlayExitBtn.addEventListener("click", closeOverlay);
      if (mainStartBtn) {
        mainStartBtn.addEventListener("click", function () {
          statusNode.textContent = "Workout started. Follow the next movement and use the player between sets.";
          openOverlay();
          renderOverlay();
          startSessionTimer();
          speakVoiceCue(true);
          startTimer();
        });
      }
      presetButtons.forEach(function (button) {
        button.addEventListener("click", function () {
          currentPreset = Number(button.dataset.seconds || defaultSeconds);
          secondsLeft = currentPreset;
          renderTime();
          statusNode.textContent = "Preset selected. Press play to run that rest block.";
          renderOverlay();
        });
      });
      if (overlay) {
        overlay.addEventListener("touchstart", handleTouchStart, { passive: true });
        overlay.addEventListener("touchend", handleTouchEnd, { passive: true });
      }
      document.querySelectorAll(".queue-row[data-queue-index]").forEach(function (row) {
        row.addEventListener("click", function () {
          const index = Number(row.dataset.queueIndex || "0");
          moveToIndex(index);
          openOverlay();
        });
      });
      updateVoiceStateLabel(autoVoiceEnabled ? "Voice cue ready" : "Voice manual");
      renderOverlay();
    })();
  </script>
</body>
</html>
"""


INLINE_ONBOARDING_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Forge Onboarding</title>
  <style>
    :root { --bg:#050505; --panel:#121315; --line:rgba(255,255,255,.08); --text:#f6efdf; --muted:#c7b59f; --accent:#ff8b39; --accent2:#ffc14d; }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; display:grid; place-items:center; padding:20px; color:var(--text); font-family:Arial,Helvetica,sans-serif; background:radial-gradient(circle at top left, rgba(255,139,57,.18), transparent 24%), linear-gradient(180deg,#050505,#101112); }
    .card { width:min(760px,100%); padding:28px; border-radius:28px; background:linear-gradient(180deg, rgba(22,22,24,.96), rgba(14,14,15,.96)); border:1px solid var(--line); box-shadow:0 30px 80px rgba(0,0,0,.45); }
    .mini { text-transform:uppercase; letter-spacing:.14em; font-size:11px; color:var(--muted); font-weight:800; }
    .pill { display:inline-flex; padding:10px 12px; border-radius:999px; background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-size:11px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
    h1 { margin:12px 0 8px; font-size:42px; line-height:.96; font-family:Georgia,serif; }
    p { color:#eadbc8; line-height:1.7; }
    form { display:grid; gap:12px; margin-top:18px; grid-template-columns:repeat(2,minmax(0,1fr)); }
    label { display:grid; gap:8px; color:var(--muted); font-size:14px; }
    input,select,button { width:100%; min-height:52px; border-radius:16px; border:1px solid var(--line); font:inherit; }
    input,select { padding:12px 14px; background:rgba(255,255,255,.05); color:var(--text); }
    button { background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-weight:800; cursor:pointer; }
    .full { grid-column:1 / -1; }
    .grid { display:grid; gap:12px; grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:18px; }
    .tile { padding:14px; border-radius:18px; background:rgba(255,255,255,.04); border:1px solid var(--line); }
    .tile strong { display:block; margin-top:8px; font-size:18px; }
    .section-kicker { margin-top:18px; padding:12px 14px; border-radius:16px; background:rgba(255,255,255,.05); border:1px solid var(--line); }
    details { grid-column:1 / -1; border:1px solid var(--line); border-radius:18px; background:rgba(255,255,255,.04); }
    summary { list-style:none; cursor:pointer; padding:16px; display:flex; align-items:center; justify-content:space-between; gap:12px; }
    summary::-webkit-details-marker { display:none; }
    .advanced-grid { padding:0 16px 16px; display:grid; gap:12px; grid-template-columns:repeat(2,minmax(0,1fr)); }
    @media (max-width: 760px) { form,.grid,.advanced-grid { grid-template-columns:1fr; } .card { padding:20px; } h1 { font-size:34px; } }
  </style>
</head>
<body>
  <main class="card">
    <div class="pill">First login setup</div>
    <div class="mini" style="margin-top:14px;">Forge athlete profile</div>
    <h1>Popuni svoj profil</h1>
    <p>Unesi ime, godine, visinu, kilazu i cilj. Na osnovu toga Forge ti daje predloge treninga, ishrane i kalendar plana.</p>
    <div class="grid">
      <article class="tile"><div class="mini">Goal</div><strong>Personalized training</strong><p>Dobijas vise planova za performance, muscle ili cut cilj.</p></article>
      <article class="tile"><div class="mini">Nutrition</div><strong>Macro targets</strong><p>Kalorije i makroi se racunaju po tvom profilu.</p></article>
      <article class="tile"><div class="mini">Calendar</div><strong>Planned routine</strong><p>Izabrani plan i preporuke ulaze u tvoj kalendar.</p></article>
    </div>
    <div class="section-kicker">
      <div class="mini">Essentials first</div>
      <strong style="display:block;margin-top:8px;font-size:20px;">Prvo unesi samo ono sto je potrebno za start.</strong>
      <p style="margin-top:8px;">Ime, cilj, body podaci i iskustvo su dovoljni da aplikacija odmah slozi prvi kvalitetan plan. Napredne filtere mozes otvoriti ispod.</p>
    </div>
    <form method="post">
      <label>Ime i prezime<input type="text" name="full_name" value="{{ user.full_name }}" required></label>
      <label class="full">Cilj
        <select name="goal">
          <option value="performance" {% if user.goal == 'performance' %}selected{% endif %}>Performance</option>
          <option value="muscle" {% if user.goal == 'muscle' %}selected{% endif %}>Muscle</option>
          <option value="cut" {% if user.goal == 'cut' %}selected{% endif %}>Cut</option>
        </select>
      </label>
      <label>Godine<input type="number" name="age" value="{{ user.age }}" min="13" max="100" required></label>
      <label>Visina cm<input type="number" step="0.1" name="height_cm" value="{{ user.height_cm }}" required></label>
      <label>Kilaza kg<input type="number" step="0.1" name="weight_kg" value="{{ user.weight_kg }}" required></label>
      <label>Pol
        <select name="gender">
          <option value="male" {% if user.gender == 'male' %}selected{% endif %}>Musko</option>
          <option value="female" {% if user.gender == 'female' %}selected{% endif %}>Zensko</option>
        </select>
      </label>
      <label class="full">Iskustvo
        <select name="experience_level">
          <option value="beginner" {% if user.experience_level == 'beginner' %}selected{% endif %}>Beginner</option>
          <option value="intermediate" {% if user.experience_level == 'intermediate' %}selected{% endif %}>Intermediate</option>
          <option value="advanced" {% if user.experience_level == 'advanced' %}selected{% endif %}>Advanced</option>
        </select>
      </label>
      <details>
        <summary>
          <div>
            <div class="mini">Advanced setup</div>
            <strong>Oprema, umor i cycle mode</strong>
          </div>
          <div class="pill" style="padding:8px 10px;">Optional</div>
        </summary>
        <div class="advanced-grid">
      <label>Oprema
        <select name="equipment_access">
          <option value="full gym" {% if user.equipment_access == 'full gym' %}selected{% endif %}>Full gym</option>
          <option value="home" {% if user.equipment_access == 'home' %}selected{% endif %}>Home</option>
          <option value="hotel" {% if user.equipment_access == 'hotel' %}selected{% endif %}>Hotel</option>
        </select>
      </label>
      <label>Umor
        <select name="fatigue_state">
          <option value="steady" {% if user.fatigue_state == 'steady' %}selected{% endif %}>Steady</option>
          <option value="high" {% if user.fatigue_state == 'high' %}selected{% endif %}>High</option>
          <option value="drained" {% if user.fatigue_state == 'drained' %}selected{% endif %}>Drained</option>
        </select>
      </label>
      <label>Cycle mode
        <select name="cycle_phase">
          <option value="neutral" {% if user.cycle_phase == 'neutral' %}selected{% endif %}>Neutral</option>
          <option value="performance" {% if user.cycle_phase == 'performance' %}selected{% endif %}>Performance</option>
          <option value="recovery" {% if user.cycle_phase == 'recovery' %}selected{% endif %}>Recovery</option>
          <option value="late_cycle" {% if user.cycle_phase == 'late_cycle' %}selected{% endif %}>Late cycle</option>
        </select>
      </label>
        </div>
      </details>
      <button class="full" type="submit">Sacuvaj profil i nastavi</button>
    </form>
  </main>
</body>
</html>
"""


INLINE_WORKOUT_ONLY_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Forge Workout Mode</title>
  <style>
    :root { --bg:#040404; --panel:#111214; --line:rgba(255,255,255,.09); --text:#fbf4e8; --muted:#ccb99f; --accent:#ff7a1a; --accent2:#ffd15a; --green:#59cf82; --blue:#72a8ff; }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; color:var(--text); font-family:Arial,Helvetica,sans-serif; background:radial-gradient(circle at top, rgba(255,122,26,.18), transparent 24%), radial-gradient(circle at bottom right, rgba(114,168,255,.10), transparent 24%), linear-gradient(180deg,#040404,#111214); }
    .shell { width:min(760px,100%); margin:0 auto; padding:calc(16px + env(safe-area-inset-top)) 16px calc(24px + env(safe-area-inset-bottom)); display:grid; gap:16px; }
    .card { padding:20px; border-radius:28px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(22,22,24,.98), rgba(14,14,15,.98)); box-shadow:0 26px 80px rgba(0,0,0,.42); }
    .mini { text-transform:uppercase; letter-spacing:.14em; font-size:11px; color:var(--muted); font-weight:800; }
    .pill { display:inline-flex; padding:10px 12px; border-radius:999px; background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-size:11px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
    .top { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
    .player-time { font-size:clamp(64px, 18vw, 118px); font-family:Georgia,serif; line-height:1; margin:12px 0; text-align:center; }
    .screen { text-align:center; padding:22px; border-radius:24px; border:1px solid var(--line); background:linear-gradient(160deg, rgba(255,122,26,.12), rgba(255,255,255,.04) 55%, rgba(114,168,255,.08)); }
    .actions,.navs { display:grid; gap:12px; }
    .actions { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .navs { grid-template-columns:repeat(3,minmax(0,1fr)); }
    button,a.btn { min-height:58px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.06); color:var(--text); font:inherit; font-weight:800; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; }
    button.primary,a.btn.primary { background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; }
    .list { display:grid; gap:10px; }
    .row { padding:14px; border-radius:20px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .row.done { opacity:.6; }
    .hero-grid,.metrics,.session-board { display:grid; gap:12px; }
    .hero-grid { grid-template-columns:1.08fr .92fr; }
    .metrics { grid-template-columns:repeat(3,minmax(0,1fr)); }
    .metric { padding:14px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .metric strong { display:block; margin-top:6px; font-size:22px; }
    .session-board { grid-template-columns:1fr 1fr; }
    .session-chip { padding:12px 14px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .session-chip strong { display:block; margin-top:6px; font-size:18px; }
    .next-up { margin-top:12px; padding:14px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .next-up strong { display:block; margin-top:8px; font-size:20px; }
    .machine-preview { width:100%; border-radius:22px; border:1px solid var(--line); background:#0d0d0e; display:block; }
    .active-row { outline:2px solid rgba(255,209,90,.75); background:linear-gradient(180deg, rgba(255,122,26,.12), rgba(255,255,255,.04)); }
    .set-grid { display:grid; gap:8px; margin-top:12px; }
    .set-pill { display:flex; justify-content:space-between; align-items:center; gap:10px; padding:10px 12px; border-radius:14px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .set-pill.done { opacity:.58; background:rgba(89,207,130,.12); }
    .sticky-actions { position:sticky; bottom:calc(10px + env(safe-area-inset-bottom)); display:grid; gap:12px; }
    .sticky-actions .card { padding:14px; border-radius:24px; backdrop-filter:blur(14px); background:rgba(15,16,18,.94); }
    @media (max-width: 760px) { .actions,.navs,.hero-grid,.metrics,.session-board { grid-template-columns:1fr; } .player-time { font-size:82px; } }
  </style>
</head>
<body>
  <main class="shell">
    <section class="card">
      <div class="top">
        <div>
          <div class="pill">Workout only mode</div>
          <div class="mini" style="margin-top:12px;">{{ payload.user.full_name }}</div>
        </div>
        <a href="/dashboard#today-plan" class="btn">Back to dashboard</a>
      </div>
      <div class="hero-grid" style="margin-top:16px;">
        <div class="screen">
          <div class="mini">{{ payload.live_session.title }}</div>
          <h1 id="wo-title" style="font-family:Georgia,serif;font-size:42px;line-height:.96;">{{ payload.live_session.next_move }}</h1>
          <div class="player-time" id="wo-timer">00:00</div>
          <div class="mini">Session timer</div>
          <div class="player-time" id="wo-session" style="font-size:44px;">00:00</div>
          <p id="wo-status">{{ payload.live_session.coach_prompt }}</p>
        </div>
        <div class="card" style="padding:18px;">
          {% if payload.live_session.queue and payload.live_session.queue[0].machine_image %}
          <img id="wo-machine-image" class="machine-preview" src="{{ payload.live_session.queue[0].machine_image }}" alt="{{ payload.live_session.queue[0].machine_label }}">
          {% else %}
          <div id="wo-machine-image" class="machine-preview" style="display:none;"></div>
          {% endif %}
          <div class="session-board" style="margin-top:12px;">
            <div class="session-chip">
              <div class="mini">Station</div>
              <strong id="wo-machine-label">{{ payload.live_session.queue[0].machine_label if payload.live_session.queue else "Training station" }}</strong>
            </div>
            <div class="session-chip">
              <div class="mini">Focus</div>
              <strong id="wo-machine-focus">{{ payload.live_session.queue[0].machine_focus if payload.live_session.queue else payload.today_blueprint.status_label }}</strong>
            </div>
            <div class="session-chip">
              <div class="mini">Auto-weight</div>
              <strong id="wo-weight">{{ payload.live_session.queue[0].weight_suggestion if payload.live_session.queue else "Use control and quality." }}</strong>
            </div>
            <div class="session-chip">
              <div class="mini">Rest preset</div>
              <strong id="wo-preset-label">{{ payload.live_session.rest_presets[0].seconds if payload.live_session.rest_presets else 60 }} sec</strong>
            </div>
          </div>
          <div class="next-up">
            <div class="mini">Next up</div>
            <strong id="wo-next-up">{{ payload.live_session.queue[1].name if payload.live_session.queue|length > 1 else payload.live_session.next_move }}</strong>
            <p id="wo-next-detail">{{ payload.live_session.queue[1].detail if payload.live_session.queue|length > 1 else payload.live_session.coach_prompt }}</p>
          </div>
          <div class="session-board" style="margin-top:12px;">
            <div class="session-chip">
              <div class="mini">{{ payload.train_os_pro.headline }}</div>
              <strong>{{ payload.train_os_pro.next_move }}</strong>
              <p style="margin-top:8px;color:var(--muted);">{{ payload.train_os_pro.voice_line }}</p>
            </div>
            <div class="session-chip">
              <div class="mini">{{ payload.train_os_pro.voice_label }}</div>
              <strong>Finish clean</strong>
              <p style="margin-top:8px;color:var(--muted);">{{ payload.train_os_pro.finish_stack[0] if payload.train_os_pro.finish_stack else "Close the working sets before moving on." }}</p>
            </div>
          </div>
        </div>
      </div>
      <div class="metrics">
        <article class="metric"><div class="mini">Workout status</div><strong id="wo-progress-main">{{ payload.today_progress.completion_percent }}%</strong></article>
        <article class="metric"><div class="mini">Sets closed</div><strong id="wo-sets-done">0</strong></article>
        <article class="metric"><div class="mini">Exercise queue</div><strong id="wo-queue-progress">{{ payload.live_session.queue|length }}</strong></article>
      </div>
      <div class="sticky-actions">
        <div class="card">
          <div class="actions">
            <button class="primary" type="button" id="wo-start">Start</button>
            <button type="button" id="wo-complete">Complete current set</button>
            <button type="button" id="wo-pause">Pause</button>
            <button type="button" id="wo-reset">Reset</button>
          </div>
          <div class="navs" style="margin-top:12px;">
            <button type="button" id="wo-prev">Prev</button>
            <button type="button" id="wo-preset">Next preset</button>
            <button type="button" id="wo-next">Next</button>
          </div>
        </div>
      </div>
    </section>
    <section class="card">
      <div class="grid" style="margin-bottom:16px;">
        <article class="row">
          <div class="mini">Autoplay lane</div>
          <strong>Next movements</strong>
          <ul class="list">{% for item in payload.train_os_pro.autoplay_lane %}<li><strong>{{ item.name }}</strong> - {{ item.detail }} - {{ item.station }} - {{ item.load }}</li>{% endfor %}</ul>
        </article>
        <article class="row">
          <div class="mini">Cue stack</div>
          <strong>Execution reminders</strong>
          <ul class="list">{% for item in payload.train_os_pro.cue_stack %}<li><strong>{{ item.name }}</strong> - {{ item.execution }} - Avoid {{ item.mistake }}</li>{% endfor %}</ul>
        </article>
      </div>
      <div class="top">
        <div>
          <div class="mini">Live queue</div>
          <strong style="display:block;margin-top:8px;font-size:24px;">Follow the session step by step</strong>
        </div>
        <div class="pill">Evidence on</div>
      </div>
      <div class="list">
        {% for item in payload.live_session.queue %}
        <div class="row {% if item.done %}done{% endif %}" data-wo-index="{{ loop.index0 }}" data-item-key="{{ item.item_key }}">
          <strong>{{ item.name }}</strong>
          <div class="mini" style="margin-top:8px;">{{ item.machine_label }} - {{ item.machine_focus }}</div>
          <p>{{ item.detail }}</p>
          <div>Auto-weight: {{ item.weight_suggestion }}</div>
          {% if item.checkpoints %}
          <div class="set-grid">
            {% for checkpoint in item.checkpoints %}
            <div class="set-pill {% if checkpoint.done %}done{% endif %}">
              <span>{{ checkpoint.label }}</span>
              <strong>{% if checkpoint.done %}Done{% else %}Live{% endif %}</strong>
            </div>
            {% endfor %}
          </div>
          {% endif %}
        </div>
        {% endfor %}
      </div>
    </section>
    <section class="card">
      <div class="top">
        <div>
          <div class="mini">Session board</div>
          <strong style="display:block;margin-top:8px;font-size:24px;">Live workout summary</strong>
        </div>
        <div class="pill">{{ payload.session_analytics.completion_score }}% complete</div>
      </div>
      <div class="metrics" style="margin-top:16px;">
        <article class="metric"><div class="mini">Volume</div><strong>{{ payload.session_analytics.total_volume }}</strong></article>
        <article class="metric"><div class="mini">Calories</div><strong>{{ payload.session_analytics.estimated_calories }}</strong></article>
        <article class="metric"><div class="mini">Average RPE</div><strong>{{ payload.session_analytics.average_rpe }}</strong></article>
      </div>
      <div class="list" style="margin-top:16px;">
        <div class="row">
          <div class="mini">Coach call</div>
          <strong>{{ payload.session_analytics.next_session_call }}</strong>
          <p>{{ payload.session_analytics.summary }}</p>
        </div>
      </div>
    </section>
  </main>
  <script id="wo-data" type="application/json">{{ payload.live_session|tojson }}</script>
  <script>
    (function () {
      const data = JSON.parse(document.getElementById("wo-data").textContent || "{}");
      const timerNode = document.getElementById("wo-timer");
      const sessionNode = document.getElementById("wo-session");
      const statusNode = document.getElementById("wo-status");
      const titleNode = document.getElementById("wo-title");
      const machineImage = document.getElementById("wo-machine-image");
      const machineLabel = document.getElementById("wo-machine-label");
      const machineFocus = document.getElementById("wo-machine-focus");
      const weightNode = document.getElementById("wo-weight");
      const presetLabel = document.getElementById("wo-preset-label");
      const nextUpNode = document.getElementById("wo-next-up");
      const nextDetailNode = document.getElementById("wo-next-detail");
      const progressMain = document.getElementById("wo-progress-main");
      const setsDoneNode = document.getElementById("wo-sets-done");
      const queueProgressNode = document.getElementById("wo-queue-progress");
      const rows = Array.from(document.querySelectorAll("[data-wo-index]"));
      const presets = data.rest_presets || [];
      let currentPreset = presets.length ? Number(presets[0].seconds || 60) : 60;
      let secondsLeft = currentPreset;
      let intervalId = null;
      let sessionIntervalId = null;
      let sessionSeconds = 0;
      let queue = Array.isArray(data.queue) ? data.queue : [];
      let activeIndex = Math.max(0, queue.findIndex(item => !item.done));
      if (activeIndex < 0) activeIndex = 0;
      function renderTime() {
        const mins = String(Math.floor(secondsLeft / 60)).padStart(2, "0");
        const secs = String(secondsLeft % 60).padStart(2, "0");
        timerNode.textContent = mins + ":" + secs;
      }
      function renderSessionTime() {
        const mins = String(Math.floor(sessionSeconds / 60)).padStart(2, "0");
        const secs = String(sessionSeconds % 60).padStart(2, "0");
        sessionNode.textContent = mins + ":" + secs;
      }
      function startSession() {
        if (sessionIntervalId) return;
        sessionIntervalId = setInterval(function () {
          sessionSeconds += 1;
          renderSessionTime();
        }, 1000);
      }
      function renderState() {
        rows.forEach((row, idx) => {
          row.classList.toggle("active-row", idx === activeIndex);
        });
        const item = queue[activeIndex];
        const completedExercises = queue.filter(entry => entry.done).length;
        const totalSets = queue.reduce((sum, entry) => sum + ((entry.checkpoints || []).length || 1), 0);
        const closedSets = queue.reduce((sum, entry) => sum + ((entry.checkpoints || []).filter(point => point.done).length || (entry.done ? 1 : 0)), 0);
        progressMain.textContent = totalSets ? Math.round((closedSets / totalSets) * 100) + "%" : "0%";
        setsDoneNode.textContent = String(closedSets);
        queueProgressNode.textContent = completedExercises + "/" + queue.length;
        if (!item) {
          titleNode.textContent = data.completion_title || "Workout complete";
          statusNode.textContent = data.completion_note || "Session complete.";
          machineLabel.textContent = "Session complete";
          machineFocus.textContent = "Recovery and nutrition next.";
          weightNode.textContent = "No next load";
          if (nextUpNode) nextUpNode.textContent = "Session complete";
          if (nextDetailNode) nextDetailNode.textContent = "Open recovery, food and the weekly review.";
          return;
        }
        titleNode.textContent = item.name;
        statusNode.textContent = item.name + " | " + item.detail;
        machineLabel.textContent = item.machine_label || "Training station";
        machineFocus.textContent = item.machine_focus || "Main station";
        weightNode.textContent = item.weight_suggestion || "Use stable working weight.";
        const nextItem = queue[activeIndex + 1];
        if (nextUpNode) nextUpNode.textContent = nextItem ? nextItem.name : "Finish session";
        if (nextDetailNode) nextDetailNode.textContent = nextItem ? nextItem.detail : "Close the last block, then move to recovery and food.";
        if (machineImage) {
          if (item.machine_image) {
            machineImage.src = item.machine_image;
            machineImage.style.display = "block";
          } else {
            machineImage.style.display = "none";
          }
        }
      }
      function start() {
        if (intervalId) return;
        startSession();
        intervalId = setInterval(function () {
          if (secondsLeft > 0) {
            secondsLeft -= 1;
            renderTime();
            return;
          }
          clearInterval(intervalId);
          intervalId = null;
          statusNode.textContent = "Rest finished. Move to the next set.";
        }, 1000);
      }
      function pause() { if (intervalId) { clearInterval(intervalId); intervalId = null; } }
      function reset() { pause(); secondsLeft = currentPreset; renderTime(); renderState(); }
      function move(delta) {
        if (!queue.length) return;
        activeIndex = Math.max(0, Math.min(activeIndex + delta, queue.length - 1));
        renderState();
      }
      function cyclePreset() {
        if (!presets.length) return;
        const currentIndex = presets.findIndex(item => Number(item.seconds) === currentPreset);
        const nextIndex = currentIndex === -1 ? 0 : (currentIndex + 1) % presets.length;
        currentPreset = Number(presets[nextIndex].seconds || 60);
        secondsLeft = currentPreset;
        presetLabel.textContent = currentPreset + " sec";
        renderTime();
      }
      function complete() {
        const item = queue[activeIndex];
        if (!item) return;
        let payload = null;
        if (item.checkpoints && item.checkpoints.length) {
          const nextCheckpoint = item.checkpoints.find(point => !point.done);
          if (nextCheckpoint) {
            nextCheckpoint.done = true;
            payload = { item_type: "set", item_key: nextCheckpoint.item_key };
          }
          if (item.checkpoints.every(point => point.done)) item.done = true;
        } else if (!item.done) {
          item.done = true;
          payload = { item_type: "exercise", item_key: item.item_key };
        }
        rows[activeIndex]?.classList.add("done");
        const setPills = rows[activeIndex] ? Array.from(rows[activeIndex].querySelectorAll(".set-pill")) : [];
        if (setPills.length) {
          const nextUndone = setPills.find(pill => !pill.classList.contains("done"));
          if (nextUndone) {
            nextUndone.classList.add("done");
            const strong = nextUndone.querySelector("strong");
            if (strong) strong.textContent = "Done";
          }
        }
        const nextPending = queue.findIndex(entry => !entry.done);
        if (nextPending !== -1) activeIndex = nextPending;
        if (item.done && queue[activeIndex]) {
          const nextRest = parseInt(String(queue[activeIndex].detail || '').match(/rest\\s+(\\d+)/i)?.[1] || currentPreset, 10);
          if (!Number.isNaN(nextRest) && nextRest > 0) {
            currentPreset = nextRest;
            secondsLeft = currentPreset;
            presetLabel.textContent = currentPreset + " sec";
            renderTime();
          }
        }
        renderState();
        if (!payload) return;
        fetch("/today/check", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8", "X-Requested-With": "XMLHttpRequest" },
          body: new URLSearchParams(payload)
        });
      }
      document.getElementById("wo-start").addEventListener("click", start);
      document.getElementById("wo-pause").addEventListener("click", pause);
      document.getElementById("wo-reset").addEventListener("click", reset);
      document.getElementById("wo-prev").addEventListener("click", () => move(-1));
      document.getElementById("wo-next").addEventListener("click", () => move(1));
      document.getElementById("wo-preset").addEventListener("click", cyclePreset);
      document.getElementById("wo-complete").addEventListener("click", complete);
      renderTime();
      renderSessionTime();
      presetLabel.textContent = currentPreset + " sec";
      renderState();
    })();
  </script>
</body>
</html>
"""


INLINE_FOCUS_HUB_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Forge Focus Hub</title>
  <style>
    :root { --bg:#050505; --panel:#111214; --panel-soft:rgba(24,20,18,.86); --line:rgba(255,255,255,.09); --text:#fbf4e8; --muted:#ccb99f; --accent:#f48b38; --accent2:#f2c15a; }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; color:var(--text); font-family:Arial,Helvetica,sans-serif; background:radial-gradient(circle at top, rgba(244,139,56,.18), transparent 24%), linear-gradient(180deg,#050505,#101214); }
    .shell { width:min(920px,100%); margin:0 auto; padding:calc(16px + env(safe-area-inset-top)) 16px calc(24px + env(safe-area-inset-bottom)); display:grid; gap:16px; }
    .card { padding:20px; border-radius:28px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(22,22,24,.98), rgba(14,14,15,.98)); box-shadow:0 26px 80px rgba(0,0,0,.42); }
    .mini { text-transform:uppercase; letter-spacing:.14em; font-size:11px; color:var(--muted); font-weight:800; }
    .pill,.btn-primary { display:inline-flex; align-items:center; justify-content:center; padding:10px 12px; border-radius:999px; background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-size:11px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; text-decoration:none; }
    .top { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; flex-wrap:wrap; }
    .grid,.summary,.trainer-grid { display:grid; gap:12px; }
    .grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .summary { grid-template-columns:repeat(3,minmax(0,1fr)); }
    .trainer-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .tile { padding:16px; border-radius:20px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .tile strong { display:block; margin-top:8px; font-size:22px; }
    .list { display:grid; gap:10px; margin-top:12px; }
    .row { padding:14px; border-radius:18px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.03)); }
    .row strong { display:block; margin-bottom:8px; }
    .actions { display:flex; gap:10px; flex-wrap:wrap; margin-top:12px; }
    .actions a { text-decoration:none; color:inherit; }
    .muted { color:#e7d9c8; line-height:1.6; }
    .account-tools { display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }
    .account-tools a { text-decoration:none; color:var(--text); padding:10px 12px; border-radius:16px; border:1px solid var(--line); background:rgba(255,255,255,.05); font-size:12px; font-weight:800; }
    .account-tools a.primary { background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#17110a; }
    .hub-strip { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }
    .hub-kpi { padding:16px; border-radius:20px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .hub-kpi strong { display:block; margin-top:8px; font-size:24px; }
    @media (max-width: 760px) { .grid,.summary,.trainer-grid { grid-template-columns:1fr; } }
    @media (max-width: 760px) { .hub-strip { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <main class="shell">
    <section class="card">
      <div class="top">
        <div>
          <div class="pill">{{ hub_title }}</div>
          <div class="mini" style="margin-top:12px;">{{ payload.user.full_name }}</div>
          <h1 style="margin:10px 0 0;font-family:Georgia,serif;font-size:42px;line-height:.96;">{{ hub_heading }}</h1>
          <p class="muted">{{ hub_copy }}</p>
        </div>
        <div class="actions">
          <a href="/dashboard" class="btn-primary">Back home</a>
          <a href="/workout-mode" class="btn-primary">Workout mode</a>
        </div>
      </div>
      <div class="account-tools">
        <a class="primary" href="/hub/profile">Open profile</a>
        <a href="/hub/calendar">Calendar</a>
        <a href="/logout">Logout</a>
      </div>
    </section>

    {% if hub_key == "train" %}
    <section class="card">
      <div class="summary">
        <article class="tile"><div class="mini">Train OS</div><strong>{{ payload.train_os.primary_call }}</strong><p class="muted">{{ payload.train_os.primary_detail }}</p></article>
        <article class="tile"><div class="mini">Station</div><strong>{{ payload.train_os.station }}</strong><p class="muted">{{ payload.train_os.station_focus }}</p></article>
        <article class="tile"><div class="mini">Autoplay</div><strong>{{ payload.train_os.next_up }}</strong><p class="muted">{{ payload.train_os.autoplay_note }}</p></article>
      </div>
      <div class="row" style="margin-top:16px;">
        <div class="mini">{{ payload.train_os_pro.headline }}</div>
        <strong>{{ payload.train_os_pro.next_move }}</strong>
        <p class="muted">{{ payload.train_os_pro.voice_line }}</p>
        <div class="mini" style="margin-top:10px;">{{ payload.train_os_pro.voice_label }}</div>
      </div>
      <div class="hub-strip">
        <article class="hub-kpi"><div class="mini">Today</div><strong>{{ payload.today_blueprint.status_label }}</strong><p class="muted">{{ payload.train_room.detail }}</p></article>
        <article class="hub-kpi"><div class="mini">Progress</div><strong>{{ payload.today_progress.completion_percent }}%</strong><p class="muted">{{ payload.today_progress.done_items }}/{{ payload.today_progress.total_items }} blocks closed.</p></article>
        <article class="hub-kpi"><div class="mini">Coach</div><strong>{{ payload.today_blueprint.coach_name }}</strong><p class="muted">{{ payload.single_next_action.tag }}</p></article>
      </div>
      <div class="grid" style="margin-top:16px;">
        <article class="row">
          <div class="mini">Current block</div>
          <strong>{{ payload.train_room.current_name }}</strong>
          <p class="muted">{{ payload.train_room.current_detail }}</p>
          <div class="mini" style="margin-top:8px;">{{ payload.train_room.current_prescription }}</div>
          <div class="actions">
            <a href="/workout-mode" class="btn-primary">Open live player</a>
            <a href="/hub/program" class="btn-primary">Open program</a>
          </div>
        </article>
        <article class="row">
          {% if payload.train_room.current_machine_image %}
          <img src="{{ payload.train_room.current_machine_image }}" alt="{{ payload.train_room.current_machine }}" style="width:100%;max-width:260px;border-radius:18px;border:1px solid rgba(255,255,255,.08);display:block;margin-bottom:12px;background:#111;">
          {% endif %}
          <div class="mini">{{ payload.train_room.current_machine }}</div>
          <strong>{{ payload.train_room.current_machine_focus }}</strong>
          <p class="muted">Auto-weight: {{ payload.train_room.current_weight }}</p>
          <div class="mini" style="margin-top:8px;">Next up · {{ payload.train_room.next_name }}</div>
        </article>
      </div>
      <div class="grid" style="margin-top:16px;">
        {% for item in payload.train_room.queue_preview %}
        <article class="row">
          <div class="mini">{{ item.machine_label }}</div>
          <strong>{{ item.name }}</strong>
          <p class="muted">{{ item.detail }}</p>
          <div class="mini" style="margin-top:8px;">Auto-weight</div>
          <strong style="font-size:18px;">{{ item.weight_suggestion }}</strong>
        </article>
        {% endfor %}
      </div>
      <div class="grid" style="margin-top:16px;">
        <article class="row">
          <strong>Autoplay lane</strong>
          <ul class="list">{% for item in payload.train_os_pro.autoplay_lane %}<li><strong>{{ item.name }}</strong> - {{ item.detail }} - {{ item.station }} - {{ item.load }}</li>{% endfor %}</ul>
        </article>
        <article class="row">
          <strong>Execution board</strong>
          <ul class="list">{% for item in payload.train_os.summary_tiles %}<li><strong>{{ item.label }}</strong> - {{ item.value }} - {{ item.detail }}</li>{% endfor %}</ul>
          <div class="mini" style="margin-top:10px;">{{ payload.train_os.completion_note }}</div>
        </article>
        <article class="row">
          <strong>Session board</strong>
          <ul class="list">{% for item in payload.train_room.session_tiles %}<li><strong>{{ item.label }}</strong> - {{ item.value }} - {{ item.detail }}</li>{% endfor %}</ul>
        </article>
        <article class="row">
          <strong>Technique notes</strong>
          <ul class="list">{% for item in payload.train_room.mastery_preview %}<li><strong>{{ item.name }}</strong> - {{ item.execution }}</li>{% endfor %}</ul>
          <div class="mini" style="margin-top:10px;">{{ payload.voice_coach.mode_label }}</div>
        </article>
        <article class="row">
          <strong>Cue stack</strong>
          <ul class="list">{% for item in payload.train_os_pro.cue_stack %}<li><strong>{{ item.name }}</strong> - {{ item.execution }} - Avoid: {{ item.mistake }}</li>{% endfor %}</ul>
        </article>
        <article class="row">
          <strong>Finish sequence</strong>
          <ul class="list">{% for item in payload.train_os_pro.finish_stack %}<li>{{ item }}</li>{% endfor %}</ul>
        </article>
      </div>
    </section>
    {% elif hub_key == "program" %}
    <section class="card">
      <div class="hub-strip">
        <article class="hub-kpi"><div class="mini">Current block</div><strong>{{ payload.periodization_engine.week_label }}</strong><p class="muted">{{ payload.periodization_engine.block_name }}</p></article>
        <article class="hub-kpi"><div class="mini">Coach signal</div><strong>{{ payload.periodization_engine.phase_signal }}</strong><p class="muted">{{ payload.periodization_engine.coach_call }}</p></article>
        <article class="hub-kpi"><div class="mini">Focus this week</div><strong>{{ payload.periodization_engine.week_focus }}</strong><p class="muted">{{ payload.periodization_engine.today_fit }}</p></article>
      </div>
      <div class="summary">
        <article class="tile"><div class="mini">Active package</div><strong>{{ payload.active_package.title }}</strong><p class="muted">{{ payload.active_package.summary }}</p></article>
        <article class="tile"><div class="mini">Focus</div><strong>{{ payload.active_package.focus }}</strong><p class="muted">{{ payload.active_package.days }} training days.</p></article>
        <article class="tile"><div class="mini">Next block</div><strong>{{ payload.active_package.next_calendar }}</strong><p class="muted">{{ payload.periodization_engine.block_name }}</p></article>
      </div>
      <div class="grid" style="margin-top:16px;">
        {% for item in payload.program_board %}
        <article class="row">
          <div class="mini">{{ item.day }}</div>
          <strong>{{ item.title }}</strong>
          <p class="muted">{{ item.prescription }}</p>
          <ul class="list">
            {% for exercise in item.top_exercises %}
            <li>{{ exercise }}</li>
            {% endfor %}
          </ul>
        </article>
        {% endfor %}
      </div>
      <div class="grid" style="margin-top:16px;">
        {% for item in payload.program_builder %}
        <article class="row">
          <div class="mini">{{ item.week }} - {{ item.phase }}</div>
          <strong>{{ item.focus }}</strong>
          <p class="muted">{{ item.coach_call }}</p>
          <div class="mini" style="margin-top:8px;">{{ item.session_title }} - {{ item.session_prescription }}</div>
          <ul class="list">{% for exercise in item.top_exercises %}<li>{{ exercise }}</li>{% endfor %}</ul>
        </article>
        {% endfor %}
      </div>
    </section>
    {% elif hub_key == "fuel" %}
    <section class="card">
      <div class="mini">{{ payload.fuel_room.headline }}</div>
      <div class="summary" style="margin-top:16px;">
        <article class="tile"><div class="mini">Fuel OS</div><strong>{{ payload.fuel_os.eat_now }}</strong><p class="muted">{{ payload.fuel_os.eat_now_detail }}</p></article>
        <article class="tile"><div class="mini">Macro call</div><strong>{{ payload.fuel_os.macro_call }}</strong><p class="muted">Stay aligned instead of improvising meals.</p></article>
        <article class="tile"><div class="mini">Prep stack</div><strong>{{ payload.fuel_os.prep_stack[0] if payload.fuel_os.prep_stack else 'Prep food now' }}</strong><p class="muted">{{ payload.fuel_os.prep_stack[1] if payload.fuel_os.prep_stack|length > 1 else 'Keep the next day easy.' }}</p></article>
      </div>
      <div class="hub-strip" style="margin-top:16px;">
        <article class="hub-kpi"><div class="mini">Eat now</div><strong>{{ payload.fuel_room.next_meal }}</strong><p class="muted">{{ payload.fuel_room.next_detail }}</p></article>
        <article class="hub-kpi"><div class="mini">Prep call</div><strong>{{ payload.fuel_room.prep_call[0] if payload.fuel_room.prep_call else 'Prep core foods' }}</strong><p class="muted">{{ payload.fuel_room.prep_call[1] if payload.fuel_room.prep_call|length > 1 else 'Stay ahead of the week.' }}</p></article>
        <article class="hub-kpi"><div class="mini">Macro lane</div><strong>{{ payload.fuel_room.protein_left }}g protein left</strong><p class="muted">{{ payload.fuel_room.calories_left }} kcal left today.</p></article>
      </div>
      <div class="summary">
        <article class="tile"><div class="mini">Next meal</div><strong>{{ payload.fuel_room.next_meal }}</strong><p class="muted">{{ payload.fuel_room.next_detail }}</p></article>
        <article class="tile"><div class="mini">Protein left</div><strong>{{ payload.fuel_room.protein_left }}g</strong><p class="muted">Keep fuel aligned.</p></article>
        <article class="tile"><div class="mini">Calories left</div><strong>{{ payload.fuel_room.calories_left }}</strong><p class="muted">{{ payload.nutrition_intelligence.day_type|title }} day.</p></article>
      </div>
      <div class="grid" style="margin-top:16px;">
        <article class="row">
          <strong>Smart swaps</strong>
          <ul class="list">{% for item in payload.fuel_room.smart_swaps %}<li>{{ item }}</li>{% endfor %}</ul>
        </article>
        <article class="row">
          <strong>Shopping list</strong>
          <ul class="list">{% for item in payload.fuel_room.shopping_preview %}<li>{{ item.name }} - {{ item.reason }}</li>{% endfor %}</ul>
        </article>
      </div>
      <div class="grid" style="margin-top:16px;">
        {% for item in payload.fuel_room.weekly_plan %}
        <article class="row">
          <div class="mini">{{ item.day }}</div>
          <strong>{{ item.theme }}</strong>
          <p class="muted">{{ item.rule }}</p>
          <ul class="list">{% for meal in item.meals %}<li>{{ meal }}</li>{% endfor %}</ul>
        </article>
        {% endfor %}
      </div>
      <div class="grid" style="margin-top:16px;">
        <article class="row">
          <strong>3-day fuel lane</strong>
          <ul class="list">
            {% for item in payload.fuel_os_pro.three_day_plan %}
            <li><strong>{{ item.day }}</strong> - {{ item.theme }} - {{ item.rule }}</li>
            {% endfor %}
          </ul>
        </article>
        <article class="row">
          <strong>Replacement stack</strong>
          <ul class="list">{% for item in payload.fuel_os_pro.replacement_stack %}<li>{{ item }}</li>{% endfor %}</ul>
          <div class="mini" style="margin-top:10px;">{{ payload.fuel_os_pro.next_macro_move }}</div>
        </article>
      </div>
    </section>
    {% elif hub_key == "coach" %}
    <section class="card">
      <div class="summary">
        <article class="tile"><div class="mini">AI concierge</div><strong>{{ payload.ai_concierge.name }}</strong><p class="muted">{{ payload.ai_concierge.greeting }}</p></article>
        <article class="tile"><div class="mini">Current mission</div><strong>{{ payload.coach_briefing.coach }}</strong><p class="muted">{{ payload.coach_briefing.next_step }}</p></article>
        <article class="tile"><div class="mini">Coach lane</div><strong>{{ payload.assistant.coach_role }}</strong><p class="muted">{{ payload.assistant.headline }}</p></article>
      </div>
      <div class="row" style="margin-top:16px;">
        <div class="mini">{{ payload.coach_memory_pro.headline }}</div>
        <strong>{{ payload.coach_memory_pro.stagnation_flag }}</strong>
        <p class="muted">{{ payload.coach_memory_pro.latest_focus }} · {{ payload.coach_memory_pro.energy_lane }}</p>
        <ul class="list">{% for item in payload.coach_memory_pro.notes %}<li>{{ item }}</li>{% endfor %}</ul>
      </div>
      <div class="trainer-grid" style="margin-top:16px;">
        {% for item in payload.personal_trainers %}
        <article class="row"><div class="mini">{{ item.lead }}</div><strong>{{ item.name }}</strong><p class="muted">{{ item.duty }}</p><div class="mini">{{ item.role }}</div></article>
        {% endfor %}
      </div>
    </section>
    {% elif hub_key == "track" %}
    <section class="card">
      <div class="mini">{{ payload.track_room.headline }}</div>
      <div class="summary" style="margin-top:16px;">
        <article class="tile"><div class="mini">Track OS</div><strong>{{ payload.track_os.trajectory }}</strong><p class="muted">{{ payload.track_os.trajectory_detail }}</p></article>
        <article class="tile"><div class="mini">Recomp</div><strong>{{ payload.track_os.recomp }}/100</strong><p class="muted">{{ payload.track_os.adherence }}% adherence</p></article>
        <article class="tile"><div class="mini">Focus</div><strong>{{ payload.track_os.wins[0] if payload.track_os.wins else 'Hold consistency' }}</strong><p class="muted">{{ payload.track_os.watchouts[0] if payload.track_os.watchouts else 'Keep weekly review honest.' }}</p></article>
      </div>
      <div class="hub-strip" style="margin-top:16px;">
        <article class="hub-kpi"><div class="mini">Recomp</div><strong>{{ payload.track_room.recomp }}/100</strong><p class="muted">{{ payload.track_room.checkpoint }}</p></article>
        <article class="hub-kpi"><div class="mini">Adherence</div><strong>{{ payload.track_room.adherence }}%</strong><p class="muted">{{ payload.weekly_review.headline }}</p></article>
        <article class="hub-kpi"><div class="mini">Next checkpoint</div><strong>{{ payload.track_room.checkpoint }}</strong><p class="muted">{{ payload.track_room.review }}</p></article>
      </div>
      <div class="summary">
        {% for item in payload.track_room.tiles %}
        <article class="tile"><div class="mini">{{ item.label }}</div><strong>{{ item.value }}</strong><p class="muted">{{ item.detail }}</p></article>
        {% endfor %}
      </div>
      <div class="grid" style="margin-top:16px;">
        <article class="row"><strong>Wins</strong><ul class="list">{% for item in payload.track_room.wins %}<li>{{ item }}</li>{% endfor %}</ul></article>
        <article class="row"><strong>Watchouts</strong><ul class="list">{% for item in payload.track_room.watchouts %}<li>{{ item }}</li>{% endfor %}</ul></article>
      </div>
      <div class="grid" style="margin-top:16px;">
        <article class="row"><strong>Trend lines</strong><ul class="list">{% for item in payload.track_room.trends %}<li><strong>{{ item.label }}</strong> - {{ item.value }} - {{ item.detail }}</li>{% endfor %}</ul></article>
        <article class="row"><strong>Coach review</strong><ul class="list"><li>{{ payload.track_room.review }}</li><li>{{ payload.track_room.checkpoint }}</li></ul></article>
      </div>
      <div class="summary" style="margin-top:16px;">
        <article class="tile"><div class="mini">Transformation mode</div><strong>{{ payload.transformation_mode.review_call }}</strong><p class="muted">{{ payload.transformation_mode.checkpoint }}</p></article>
        <article class="tile"><div class="mini">Latest body data</div><strong>{{ payload.transformation_mode.latest_weight }} kg</strong><p class="muted">Waist {{ payload.transformation_mode.latest_waist }} cm · {{ payload.transformation_mode.photo_count }} progress photos.</p></article>
        <article class="tile"><div class="mini">Recomp score</div><strong>{{ payload.transformation_mode.score }}/10</strong><p class="muted">{{ payload.transformation_mode.headline }}</p></article>
      </div>
      <div class="row" style="margin-top:16px;">
        <div class="mini">{{ payload.transformation_shell.headline }}</div>
        <strong>{{ payload.transformation_shell.hero }}</strong>
        <p class="muted">{{ payload.transformation_shell.checkpoint }}</p>
        <div class="mini" style="margin-top:10px;">{{ payload.transformation_shell.latest_photo_label }}</div>
      </div>
      <div class="grid" style="margin-top:16px;">
        <article class="row"><strong>Transformation tiles</strong><ul class="list">{% for item in payload.transformation_mode.tiles %}<li><strong>{{ item.label }}</strong> - {{ item.value }} - {{ item.detail }}</li>{% endfor %}</ul></article>
        <article class="row"><strong>Transformation trends</strong><ul class="list">{% for item in payload.transformation_mode.trends %}<li><strong>{{ item.label }}</strong> - {{ item.value }} - {{ item.detail }}</li>{% endfor %}</ul></article>
      </div>
      <div class="grid" style="margin-top:16px;">
        <article class="row"><strong>Track review tiles</strong><ul class="list">{% for item in payload.transformation_shell.review_tiles %}<li><strong>{{ item.label }}</strong> - {{ item.value }} - {{ item.detail }}</li>{% endfor %}</ul></article>
        <article class="row"><strong>Trend stack</strong><ul class="list">{% for item in payload.transformation_shell.trend_stack %}<li><strong>{{ item.label }}</strong> - {{ item.value }} - {{ item.detail }}</li>{% endfor %}</ul></article>
      </div>
    </section>
    {% elif hub_key == "profile" %}
    <section class="card">
      <div class="summary">
        <article class="tile"><div class="mini">Full name</div><strong>{{ payload.user.full_name }}</strong><p class="muted">{{ payload.user.goal|title }} - {{ payload.user.experience_level|title }}</p></article>
        <article class="tile"><div class="mini">Body</div><strong>{{ payload.user.height_cm }} cm / {{ payload.user.weight_kg }} kg</strong><p class="muted">Age {{ payload.user.age }}</p></article>
        <article class="tile"><div class="mini">Equipment</div><strong>{{ payload.user.equipment_access|title }}</strong><p class="muted">{{ payload.user.fatigue_state|title }} fatigue</p></article>
      </div>
      <div class="account-tools">
        <a class="primary" href="/dashboard">Back home</a>
        <a href="/hub/calendar">Open calendar</a>
        <a href="/logout">Logout</a>
      </div>
      <div class="grid" style="margin-top:16px;">
        {% for item in payload.achievements %}
        <article class="row"><div class="mini">{{ item.title }}</div><strong>{{ item.value }}</strong><p class="muted">{{ item.detail }}</p></article>
        {% endfor %}
      </div>
      {% if payload.user.role == 'admin' %}
      <div class="summary" style="margin-top:16px;">
        {% for item in payload.admin_growth.tiles %}
        <article class="tile"><div class="mini">{{ item.label }}</div><strong>{{ item.value }}</strong><p class="muted">{{ item.detail }}</p></article>
        {% endfor %}
      </div>
      <div class="row" style="margin-top:16px;">
        <div class="mini">Growth overview</div>
        <strong>{{ payload.admin_growth.headline }}</strong>
        <p class="muted">{{ payload.admin_growth.summary }}</p>
      </div>
      <div class="summary" style="margin-top:16px;">
        {% for item in payload.admin_conversion.tiles %}
        <article class="tile"><div class="mini">{{ item.label }}</div><strong>{{ item.value }}</strong><p class="muted">{{ item.detail }}</p></article>
        {% endfor %}
      </div>
      <div class="row" style="margin-top:16px;">
        <div class="mini">Conversion cockpit</div>
        <strong>Trial to paid overview</strong>
        <p class="muted">{{ payload.admin_conversion.summary }}</p>
      </div>
      <div class="summary" style="margin-top:16px;">
        {% for item in payload.admin_revenue.tiles %}
        <article class="tile"><div class="mini">{{ item.label }}</div><strong>{{ item.value }}</strong><p class="muted">{{ item.detail }}</p></article>
        {% endfor %}
      </div>
      <div class="row" style="margin-top:16px;">
        <div class="mini">{{ payload.admin_revenue.headline }}</div>
        <strong>Revenue and retention signal</strong>
        <p class="muted">{{ payload.admin_revenue.summary }}</p>
      </div>
      {% endif %}
    </section>
    {% elif hub_key == "calendar" %}
    <section class="card">
      <div class="grid">
        {% for day in payload.personal_calendar %}
        <article class="row">
          <div class="mini">{{ day.day_label }} - {{ day.date }}</div>
          <strong>Daily flow</strong>
          <ul class="list">{% for slot in day.slots %}<li><strong>{{ slot.time }}</strong> - {{ slot.title }} - {{ slot.detail }}</li>{% endfor %}</ul>
        </article>
        {% endfor %}
      </div>
    </section>
    {% endif %}
  </main>
</body>
</html>
"""


INLINE_DAILY_CHECKIN_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Forge Daily Check-in</title>
  <style>
    :root { --bg:#050505; --panel:#121315; --line:rgba(255,255,255,.08); --text:#f6efdf; --muted:#c7b59f; --accent:#ff8b39; --accent2:#ffc14d; }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; color:var(--text); font-family:Arial,Helvetica,sans-serif; background:radial-gradient(circle at top left, rgba(255,139,57,.18), transparent 24%), linear-gradient(180deg,#050505,#101112); }
    .shell { width:min(720px,100%); margin:0 auto; padding:calc(16px + env(safe-area-inset-top)) 16px calc(24px + env(safe-area-inset-bottom)); display:grid; gap:16px; }
    .card { padding:22px; border-radius:26px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(22,22,24,.96), rgba(14,14,15,.96)); }
    .mini { text-transform:uppercase; letter-spacing:.14em; font-size:11px; color:var(--muted); font-weight:800; }
    .pill { display:inline-flex; padding:10px 12px; border-radius:999px; background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-size:11px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
    h1 { margin:10px 0 6px; font-size:40px; line-height:.96; font-family:Georgia,serif; }
    .grid { display:grid; gap:12px; grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:14px; }
    label { display:grid; gap:8px; color:var(--muted); }
    input,select,textarea,button,a.btn { width:100%; min-height:52px; border-radius:16px; border:1px solid var(--line); font:inherit; }
    input,select,textarea { padding:12px 14px; background:rgba(255,255,255,.05); color:var(--text); }
    button,a.btn { background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-weight:800; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; }
    textarea { min-height:108px; resize:vertical; }
    .actions { display:grid; gap:12px; grid-template-columns:1fr 1fr; margin-top:16px; }
    @media (max-width: 760px) { .grid,.actions { grid-template-columns:1fr; } h1 { font-size:34px; } }
  </style>
</head>
<body>
  <main class="shell">
    <section class="card">
      <div class="pill">Daily check-in wizard</div>
      <div class="mini" style="margin-top:14px;">{{ payload.user.full_name }}</div>
      <h1>How are you today?</h1>
      <p>One quick check-in makes the workout, meals and coach recommendations smarter for the rest of the day.</p>
      <form method="post" action="/checkin/daily" class="grid">
        <label>Mood
          <select name="mood">
            <option value="steady">Steady</option>
            <option value="good">Good</option>
            <option value="flat">Flat</option>
            <option value="tired">Tired</option>
          </select>
        </label>
        <label>Energy 1-10<input type="number" min="1" max="10" name="energy_score" value="7"></label>
        <label>Soreness 1-10<input type="number" min="1" max="10" name="soreness_score" value="4"></label>
        <label class="full">Motivation 1-10<input type="number" min="1" max="10" name="motivation_score" value="7"></label>
        <label class="full">Short note<textarea name="note" placeholder="Sleep, stress, pain, schedule, anything important for today's plan."></textarea></label>
        <div class="actions" style="grid-column:1 / -1;">
          <button type="submit">Save check-in</button>
          <a href="/dashboard" class="btn">Skip to dashboard</a>
        </div>
      </form>
    </section>
  </main>
</body>
</html>
"""


INLINE_NUTRITION_ONLY_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Forge Nutrition Mode</title>
  <style>
    :root { --bg:#050505; --panel:#121315; --line:rgba(255,255,255,.08); --text:#f6efdf; --muted:#c7b59f; --accent:#ff8b39; --accent2:#ffc14d; }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; color:var(--text); font-family:Arial,Helvetica,sans-serif; background:radial-gradient(circle at top, rgba(255,139,57,.16), transparent 24%), linear-gradient(180deg,#050505,#111214); }
    .shell { width:min(760px,100%); margin:0 auto; padding:calc(16px + env(safe-area-inset-top)) 16px calc(24px + env(safe-area-inset-bottom)); display:grid; gap:16px; }
    .card { padding:20px; border-radius:24px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(22,22,24,.96), rgba(14,14,15,.96)); }
    .mini { text-transform:uppercase; letter-spacing:.14em; font-size:11px; color:var(--muted); font-weight:800; }
    .pill { display:inline-flex; padding:10px 12px; border-radius:999px; background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-size:11px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
    .stack { display:grid; gap:12px; margin-top:16px; }
    .meal { padding:16px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .meal strong { display:block; margin-top:6px; font-size:20px; }
    a,button { text-decoration:none; color:var(--text); }
    form { display:grid; gap:12px; margin-top:14px; }
    input,select,button { width:100%; min-height:50px; border-radius:16px; border:1px solid var(--line); font:inherit; }
    input,select { padding:12px 14px; background:rgba(255,255,255,.05); color:var(--text); }
    button { background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-weight:800; cursor:pointer; }
  </style>
</head>
<body>
  <main class="shell">
    <section class="card">
      <div class="pill">Nutrition only mode</div>
      <div class="mini" style="margin-top:12px;">{{ payload.user.full_name }}</div>
      <h1 style="font-family:Georgia,serif;font-size:40px;line-height:.96;margin:10px 0 6px;">Meals for today</h1>
      <p style="color:#eadbc8;">Open only the food structure, log meals fast, close the day clean.</p>
      <div class="stack">
        {% for item in payload.today_blueprint.nutrition %}
        <article class="meal">
          <div class="mini">{{ item.time }} · {{ item.title }}</div>
          <strong>{{ item.meal }}</strong>
          <p>{{ item.purpose }}</p>
          <form method="post" action="/today/check">
            <input type="hidden" name="item_type" value="meal">
            <input type="hidden" name="item_key" value="{{ item.item_key }}">
            <button type="submit">{% if item.item_key in payload.completed_today %}Meal completed{% else %}Mark meal done{% endif %}</button>
          </form>
        </article>
        {% endfor %}
      </div>
    </section>
    <section class="card">
      <div class="mini">Quick meal log</div>
      <form method="post" action="/log-meal">
        <select name="meal_type"><option value="breakfast">Breakfast</option><option value="lunch">Lunch</option><option value="pre-workout">Pre-workout</option><option value="post-workout">Post-workout</option><option value="dinner">Dinner</option></select>
        <input type="text" name="food_name" placeholder="Chicken and rice">
        <input type="number" step="0.1" name="grams" value="150" placeholder="Grams">
        <input type="number" step="0.1" name="calories" value="450" placeholder="Calories">
        <input type="number" step="0.1" name="protein" value="35" placeholder="Protein">
        <input type="number" step="0.1" name="carbs" value="40" placeholder="Carbs">
        <input type="number" step="0.1" name="fats" value="12" placeholder="Fats">
        <input type="hidden" name="goal_tag" value="{{ payload.user.goal }}">
        <input type="hidden" name="logged_at" value="{{ today }}T12:00">
        <button type="submit">Log meal</button>
      </form>
      <div style="margin-top:14px;"><a href="/dashboard#mission" style="color:#f7efdf;font-weight:800;">Back to dashboard</a></div>
    </section>
  </main>
</body>
</html>
"""


INLINE_WEEKLY_RESET_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Forge Weekly Reset</title>
  <style>
    :root { --bg:#050505; --panel:#121315; --line:rgba(255,255,255,.08); --text:#f6efdf; --muted:#c7b59f; --accent:#ff8b39; --accent2:#ffc14d; }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; color:var(--text); font-family:Arial,Helvetica,sans-serif; background:radial-gradient(circle at top, rgba(255,139,57,.16), transparent 24%), linear-gradient(180deg,#050505,#111214); }
    .shell { width:min(760px,100%); margin:0 auto; padding:calc(16px + env(safe-area-inset-top)) 16px calc(24px + env(safe-area-inset-bottom)); display:grid; gap:16px; }
    .card { padding:22px; border-radius:26px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(22,22,24,.96), rgba(14,14,15,.96)); }
    .mini { text-transform:uppercase; letter-spacing:.14em; font-size:11px; color:var(--muted); font-weight:800; }
    .pill { display:inline-flex; padding:10px 12px; border-radius:999px; background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#16110b; font-size:11px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
    .grid { display:grid; gap:12px; grid-template-columns:repeat(2,minmax(0,1fr)); }
    .box { padding:16px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .box strong { display:block; margin-top:8px; font-size:22px; }
    ul { margin:10px 0 0; padding-left:18px; }
    a { color:#f7efdf; font-weight:800; text-decoration:none; }
    @media (max-width: 760px) { .grid { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <main class="shell">
    <section class="card">
      <div class="pill">Weekly reset</div>
      <div class="mini" style="margin-top:12px;">{{ payload.user.full_name }}</div>
      <h1 style="font-family:Georgia,serif;font-size:40px;line-height:.96;margin:10px 0 6px;">Prepare next week</h1>
      <p style="color:#eadbc8;">Review the score, follow the coach adjustment, and start the new week.</p>
      <div class="grid">
        <article class="box">
          <div class="mini">Weekly score</div>
          <strong>{{ payload.weekly_review.score }}/100</strong>
          <p>{{ payload.weekly_review.headline }}</p>
        </article>
        <article class="box">
          <div class="mini">Next week</div>
          <strong>Coach adjustment</strong>
          <p>{{ payload.weekly_review.next_week_adjustment }}</p>
        </article>
      </div>
      <div class="grid" style="margin-top:12px;">
        <article class="box">
          <div class="mini">Reset checklist</div>
          <ul>
            <li>Open workout player and confirm first training day.</li>
            <li>Open nutrition mode and prepare food structure.</li>
            <li>Run a daily check-in on the first day of the week.</li>
          </ul>
        </article>
        <article class="box">
          <div class="mini">Quick links</div>
          <ul>
            <li><a href="/workout-mode">Open workout only</a></li>
            <li><a href="/nutrition-mode">Open nutrition only</a></li>
            <li><a href="/daily-checkin">Open daily check-in</a></li>
          </ul>
        </article>
      </div>
    </section>
  </main>
</body>
</html>
"""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                subscription_tier TEXT NOT NULL DEFAULT 'starter',
                billing_status TEXT NOT NULL DEFAULT 'inactive',
                gift_package INTEGER NOT NULL DEFAULT 0,
                gifted_by TEXT NOT NULL DEFAULT '',
                discount_code TEXT NOT NULL DEFAULT '',
                discount_percent INTEGER NOT NULL DEFAULT 0,
                trial_started_at TEXT NOT NULL DEFAULT '',
                trial_ends_at TEXT NOT NULL DEFAULT '',
                gender TEXT NOT NULL DEFAULT 'male',
                cycle_phase TEXT NOT NULL DEFAULT 'neutral',
                equipment_access TEXT NOT NULL DEFAULT 'full gym',
                fatigue_state TEXT NOT NULL DEFAULT 'steady',
                age INTEGER NOT NULL DEFAULT 28,
                height_cm REAL NOT NULL DEFAULT 180,
                weight_kg REAL NOT NULL DEFAULT 80,
                goal TEXT NOT NULL DEFAULT 'performance',
                experience_level TEXT NOT NULL DEFAULT 'intermediate',
                profile_completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workout_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                workout_date TEXT NOT NULL,
                coach_key TEXT NOT NULL,
                focus TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                volume_load INTEGER NOT NULL,
                energy_score INTEGER NOT NULL,
                effort_score INTEGER NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS body_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                metric_date TEXT NOT NULL,
                body_weight REAL NOT NULL,
                body_fat REAL NOT NULL,
                chest REAL NOT NULL,
                waist REAL NOT NULL,
                arm REAL NOT NULL,
                thigh REAL NOT NULL,
                sleep_hours REAL NOT NULL,
                steps INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS meal_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                logged_at TEXT NOT NULL,
                meal_type TEXT NOT NULL,
                food_name TEXT NOT NULL,
                grams REAL NOT NULL,
                calories REAL NOT NULL,
                protein REAL NOT NULL,
                carbs REAL NOT NULL,
                fats REAL NOT NULL,
                goal_tag TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS exercise_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                logged_at TEXT NOT NULL,
                exercise_name TEXT NOT NULL,
                category TEXT NOT NULL,
                muscle_group TEXT NOT NULL,
                sets_count INTEGER NOT NULL,
                reps_text TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                rpe REAL NOT NULL,
                coach_key TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS progress_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                photo_date TEXT NOT NULL,
                pose TEXT NOT NULL,
                mood TEXT NOT NULL,
                lighting_score INTEGER NOT NULL,
                visual_score INTEGER NOT NULL,
                photo_url TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                event_date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                coach_key TEXT NOT NULL DEFAULT 'strength',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                checkin_date TEXT NOT NULL,
                mood TEXT NOT NULL DEFAULT 'steady',
                energy_score INTEGER NOT NULL DEFAULT 7,
                soreness_score INTEGER NOT NULL DEFAULT 4,
                motivation_score INTEGER NOT NULL DEFAULT 7,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS coach_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_plan_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                check_date TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_key TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS coach_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                memory_type TEXT NOT NULL DEFAULT 'preference',
                memory_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        ensure_column(db, "workout_logs", "user_id", "user_id INTEGER NOT NULL DEFAULT 1")
        ensure_column(db, "users", "gender", "gender TEXT NOT NULL DEFAULT 'male'")
        ensure_column(db, "users", "cycle_phase", "cycle_phase TEXT NOT NULL DEFAULT 'neutral'")
        ensure_column(db, "users", "equipment_access", "equipment_access TEXT NOT NULL DEFAULT 'full gym'")
        ensure_column(db, "users", "fatigue_state", "fatigue_state TEXT NOT NULL DEFAULT 'steady'")
        ensure_column(db, "users", "profile_completed", "profile_completed INTEGER NOT NULL DEFAULT 0")
        ensure_column(db, "users", "subscription_tier", "subscription_tier TEXT NOT NULL DEFAULT 'starter'")
        ensure_column(db, "users", "billing_status", "billing_status TEXT NOT NULL DEFAULT 'inactive'")
        ensure_column(db, "users", "gift_package", "gift_package INTEGER NOT NULL DEFAULT 0")
        ensure_column(db, "users", "gifted_by", "gifted_by TEXT NOT NULL DEFAULT ''")
        ensure_column(db, "users", "discount_code", "discount_code TEXT NOT NULL DEFAULT ''")
        ensure_column(db, "users", "discount_percent", "discount_percent INTEGER NOT NULL DEFAULT 0")
        ensure_column(db, "users", "trial_started_at", "trial_started_at TEXT NOT NULL DEFAULT ''")
        ensure_column(db, "users", "trial_ends_at", "trial_ends_at TEXT NOT NULL DEFAULT ''")
        ensure_column(db, "daily_plan_checks", "user_id", "user_id INTEGER NOT NULL DEFAULT 1")
        ensure_column(db, "body_metrics", "user_id", "user_id INTEGER NOT NULL DEFAULT 1")
        ensure_column(db, "meal_logs", "user_id", "user_id INTEGER NOT NULL DEFAULT 1")
        ensure_column(db, "exercise_logs", "user_id", "user_id INTEGER NOT NULL DEFAULT 1")
        ensure_column(db, "progress_photos", "user_id", "user_id INTEGER NOT NULL DEFAULT 1")
        ensure_column(db, "calendar_events", "user_id", "user_id INTEGER NOT NULL DEFAULT 1")
        ensure_column(db, "coach_memory", "user_id", "user_id INTEGER NOT NULL DEFAULT 1")
        ensure_column(db, "body_metrics", "form_score", "form_score INTEGER NOT NULL DEFAULT 7")
        ensure_column(db, "body_metrics", "checkin_note", "checkin_note TEXT NOT NULL DEFAULT ''")

        admin_exists = db.execute("SELECT id FROM users WHERE username = ?", (DEFAULT_ADMIN_USERNAME,)).fetchone()
        if not admin_exists:
            db.execute(
                """
                INSERT INTO users (
                    username, password_hash, full_name, role, subscription_tier, billing_status, profile_completed, age, height_cm, weight_kg, goal, experience_level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    DEFAULT_ADMIN_USERNAME,
                    generate_password_hash(DEFAULT_ADMIN_PASSWORD),
                    "Forge Admin",
                    "admin",
                    "elite",
                    "paid",
                    1,
                    30,
                    180,
                    84,
                    "performance",
                    "advanced",
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )
        else:
            db.execute(
                """
                UPDATE users
                SET password_hash = ?, role = 'admin', subscription_tier = 'elite', billing_status = 'paid', profile_completed = 1
                WHERE username = ?
                """,
                (generate_password_hash(DEFAULT_ADMIN_PASSWORD), DEFAULT_ADMIN_USERNAME),
            )

        mitar_exists = db.execute("SELECT id FROM users WHERE username = ?", (DEFAULT_MITAR_USERNAME,)).fetchone()
        if not mitar_exists:
            db.execute(
                """
                INSERT INTO users (
                    username, password_hash, full_name, role, subscription_tier, billing_status, profile_completed, age, height_cm, weight_kg, goal, experience_level, gender, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    DEFAULT_MITAR_USERNAME,
                    generate_password_hash(DEFAULT_MITAR_PASSWORD),
                    "Mitar",
                    "member",
                    "elite",
                    "paid",
                    1,
                    28,
                    182,
                    85,
                    "muscle",
                    "advanced",
                    "male",
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )
        else:
            db.execute(
                """
                UPDATE users
                SET password_hash = ?, subscription_tier = 'elite', billing_status = 'paid', profile_completed = 1, full_name = 'Mitar'
                WHERE username = ?
                """,
                (generate_password_hash(DEFAULT_MITAR_PASSWORD), DEFAULT_MITAR_USERNAME),
            )

        demo_exists = db.execute("SELECT id FROM users WHERE username = 'lenovo'").fetchone()
        if not demo_exists:
            db.execute(
                """
                INSERT INTO users (
                    username, password_hash, full_name, role, age, height_cm, weight_kg, goal, experience_level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "lenovo",
                    generate_password_hash("forge1234"),
                    "Lenovo Athlete",
                    "member",
                    27,
                    183,
                    86.1,
                    "performance",
                    "intermediate",
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )

        demo_user = db.execute("SELECT id FROM users WHERE username = 'lenovo'").fetchone()
        demo_user_id = int(demo_user["id"])
        db.execute("UPDATE users SET profile_completed = 1 WHERE username IN (?, ?, 'lenovo')", (DEFAULT_ADMIN_USERNAME, DEFAULT_MITAR_USERNAME))

        existing_logs = db.execute("SELECT COUNT(*) AS count FROM workout_logs WHERE user_id = ?", (demo_user_id,)).fetchone()["count"]
        existing_metrics = db.execute("SELECT COUNT(*) AS count FROM body_metrics WHERE user_id = ?", (demo_user_id,)).fetchone()["count"]
        existing_meals = db.execute("SELECT COUNT(*) AS count FROM meal_logs WHERE user_id = ?", (demo_user_id,)).fetchone()["count"]
        existing_exercises = db.execute("SELECT COUNT(*) AS count FROM exercise_logs WHERE user_id = ?", (demo_user_id,)).fetchone()["count"]
        existing_photos = db.execute("SELECT COUNT(*) AS count FROM progress_photos WHERE user_id = ?", (demo_user_id,)).fetchone()["count"]
        existing_calendar = db.execute("SELECT COUNT(*) AS count FROM calendar_events WHERE user_id = ?", (demo_user_id,)).fetchone()["count"]

        if not existing_logs:
            seed_logs = [
                ("2026-04-07", "strength", "Upper strength", 72, 14200, 8, 9, "Bench moved well. Added one back-off set."),
                ("2026-04-08", "mobility", "Recovery flow", 34, 0, 7, 5, "Low stress day. Hips opened up."),
                ("2026-04-09", "conditioning", "Engine intervals", 46, 3200, 8, 8, "Bike intervals and sled pushes."),
                ("2026-04-10", "hypertrophy", "Push hypertrophy", 81, 16850, 7, 9, "Great chest pump. Shoulders stable."),
                ("2026-04-11", "strength", "Lower power", 78, 18120, 9, 9, "Squat day. Fast bar speed on top sets."),
            ]
            for row in seed_logs:
                db.execute(
                    """
                    INSERT INTO workout_logs (
                        user_id, workout_date, coach_key, focus, duration_minutes, volume_load,
                        energy_score, effort_score, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (demo_user_id, *row, datetime.utcnow().isoformat(timespec="seconds")),
                )

        if not existing_metrics:
            seed_metrics = [
                ("2026-04-05", 87.4, 14.2, 108.0, 84.0, 39.5, 60.0, 7.7, 10220, 7, "Solid look. Midsection tighter than last week."),
                ("2026-04-08", 87.0, 14.0, 108.4, 83.5, 39.8, 60.4, 8.1, 11410, 8, "Fuller upper body and better recovery."),
                ("2026-04-11", 86.7, 13.8, 108.9, 83.0, 40.1, 60.8, 7.9, 11880, 8, "Lean look with strong training pop."),
            ]
            for row in seed_metrics:
                db.execute(
                    """
                    INSERT INTO body_metrics (
                        user_id, metric_date, body_weight, body_fat, chest, waist, arm, thigh,
                        sleep_hours, steps, form_score, checkin_note, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (demo_user_id, *row, datetime.utcnow().isoformat(timespec="seconds")),
                )

        if not existing_meals:
            seed_meals = [
                ("2026-04-12T08:00:00", "breakfast", "Greek yogurt", 250, 165, 24, 10, 5, "muscle", "Fast protein start."),
                ("2026-04-12T08:00:00", "breakfast", "Oats", 80, 311, 13, 53, 6, "performance", "Pre-lift carbs."),
                ("2026-04-12T13:30:00", "lunch", "Chicken breast", 220, 363, 68, 0, 8, "cut", "Lean protein anchor."),
                ("2026-04-12T13:30:00", "lunch", "Rice cooked", 280, 364, 7, 79, 1, "performance", "Main carb serving."),
                ("2026-04-12T19:30:00", "dinner", "Salmon", 180, 371, 40, 0, 23, "recovery", "Omega-3 support."),
            ]
            for row in seed_meals:
                db.execute(
                    """
                    INSERT INTO meal_logs (
                        user_id, logged_at, meal_type, food_name, grams, calories, protein, carbs,
                        fats, goal_tag, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (demo_user_id, *row, datetime.utcnow().isoformat(timespec="seconds")),
                )

        if not existing_exercises:
            seed_exercises = [
                ("2026-04-11T18:10:00", "Back squat", "strength", "legs", 5, "5,5,5,5,5", 140, 8.5, "strength", "Fast concentric drive."),
                ("2026-04-11T18:42:00", "Romanian deadlift", "strength", "posterior chain", 4, "8,8,8,8", 110, 8.0, "strength", "Hamstrings loaded well."),
                ("2026-04-10T19:15:00", "Incline dumbbell press", "hypertrophy", "chest", 4, "10,10,9,8", 36, 9.0, "hypertrophy", "Big upper chest pump."),
                ("2026-04-09T17:50:00", "Echo bike intervals", "conditioning", "engine", 10, "10x:20/40", 0, 8.0, "conditioning", "Breathing under control."),
            ]
            for row in seed_exercises:
                db.execute(
                    """
                    INSERT INTO exercise_logs (
                        user_id, logged_at, exercise_name, category, muscle_group, sets_count, reps_text,
                        weight_kg, rpe, coach_key, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (demo_user_id, *row, datetime.utcnow().isoformat(timespec="seconds")),
                )

        if not existing_photos:
            seed_photos = [
                ("2026-04-05", "Front", "Sharp", 8, 7, "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=900&q=80", "Waist looking tighter."),
                ("2026-04-08", "Back", "Full", 7, 8, "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=900&q=80", "Lats and shoulders showing more fullness."),
                ("2026-04-11", "Side", "Lean", 8, 8, "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=900&q=80", "Midsection leaner and posture better."),
            ]
            for row in seed_photos:
                db.execute(
                    """
                    INSERT INTO progress_photos (
                        user_id, photo_date, pose, mood, lighting_score, visual_score, photo_url, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (demo_user_id, *row, datetime.utcnow().isoformat(timespec="seconds")),
                )

        if not existing_calendar:
            for row in [
                ("2026-04-14", "training", "Upper strength day", "Heavy bench, pull-ups and rows.", "strength"),
                ("2026-04-15", "nutrition", "High-carb refill", "Push carbs around the session and keep fats lower.", "hypertrophy"),
                ("2026-04-16", "recovery", "Mobility and sleep focus", "Light walk, stretch and 8h sleep target.", "mobility"),
            ]:
                db.execute(
                    """
                    INSERT INTO calendar_events (
                        user_id, event_date, event_type, title, details, coach_key, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (demo_user_id, *row, datetime.utcnow().isoformat(timespec="seconds")),
                )


def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(minimum, min(maximum, parsed))


def clamp_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(minimum, min(maximum, parsed))


def fetch_user(username: str = "") -> dict[str, Any] | None:
    if not username:
        return None
    with get_db() as db:
        row = db.execute(
            """
            SELECT id, username, password_hash, full_name, role, age, height_cm, weight_kg, goal, experience_level, profile_completed,
                   gender, cycle_phase, equipment_access, fatigue_state, subscription_tier, billing_status,
                   gift_package, gifted_by, discount_code, discount_percent, trial_started_at, trial_ends_at
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
    return dict(row) if row else None


def current_user() -> dict[str, Any] | None:
    return fetch_user(session.get("username", ""))


def current_language() -> str:
    requested = str(request.args.get("lang") or session.get("lang") or "me").strip().lower()
    if requested not in LANGUAGES:
        requested = "me"
    session["lang"] = requested
    return requested


def language_pack() -> dict[str, str]:
    return LANGUAGES[current_language()]


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user.get("role") != "admin":
            return redirect(url_for("home"))
        return fn(*args, **kwargs)

    return wrapper


def ensure_column(db: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def recent_workouts(user_id: int, limit: int = 8) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, workout_date, coach_key, focus, duration_minutes, volume_load,
                   energy_score, effort_score, notes
            FROM workout_logs
            WHERE user_id = ?
            ORDER BY workout_date DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_metrics(user_id: int, limit: int = 6) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT metric_date, body_weight, body_fat, chest, waist, arm, thigh, sleep_hours, steps, form_score, checkin_note
            FROM body_metrics
            WHERE user_id = ?
            ORDER BY metric_date DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_meals(user_id: int, limit: int = 16) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT logged_at, meal_type, food_name, grams, calories, protein, carbs, fats, goal_tag, notes
            FROM meal_logs
            WHERE user_id = ?
            ORDER BY logged_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_exercises(user_id: int, limit: int = 16) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT logged_at, exercise_name, category, muscle_group, sets_count, reps_text, weight_kg, rpe, coach_key, notes
            FROM exercise_logs
            WHERE user_id = ?
            ORDER BY logged_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_photos(user_id: int, limit: int = 6) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT photo_date, pose, mood, lighting_score, visual_score, photo_url, notes
            FROM progress_photos
            WHERE user_id = ?
            ORDER BY photo_date DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_checkins(user_id: int, limit: int = 7) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT checkin_date, mood, energy_score, soreness_score, motivation_score, note
            FROM daily_checkins
            WHERE user_id = ?
            ORDER BY checkin_date DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_coach_messages(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT sender, message, created_at
            FROM coach_messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    items = [dict(row) for row in rows]
    items.reverse()
    return items


def today_plan_checks(user_id: int, check_date: str | None = None) -> set[str]:
    key = check_date or date.today().isoformat()
    with get_db() as db:
        rows = db.execute(
            """
            SELECT item_key
            FROM daily_plan_checks
            WHERE user_id = ? AND check_date = ? AND completed = 1
            ORDER BY id DESC
            """,
            (user_id, key),
        ).fetchall()
    return {str(row["item_key"]) for row in rows}


def coach_memory_items(user_id: int, limit: int = 6) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, memory_type, memory_text, created_at
            FROM coach_memory
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def calendar_items(user_id: int, limit: int = 14) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT event_date, event_type, title, details, coach_key
            FROM calendar_events
            WHERE user_id = ?
            ORDER BY event_date ASC, id ASC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def trainer_profiles() -> list[dict[str, Any]]:
    return [
        {
            "name": "Vera Iron",
            "title": "Strength Director",
            "specialty": "Max strength, squat and barbell progression",
            "signature": "Heavy compounds, clean technique, top-set intelligence",
        },
        {
            "name": "Noah Mass",
            "title": "Hypertrophy Architect",
            "specialty": "Muscle growth, density and visual shape",
            "signature": "Deep tension, stretch-mediated work and pump finishers",
        },
        {
            "name": "Mila Engine",
            "title": "Conditioning Lead",
            "specialty": "Work capacity, body recomposition and athletic engine",
            "signature": "Intervals, carries, sleds and brutal but smart finishers",
        },
    ]


def exercise_library() -> list[dict[str, Any]]:
    return [
        {"name": "Back squat", "category": "strength", "muscle_group": "legs", "best_for": "performance"},
        {"name": "Romanian deadlift", "category": "strength", "muscle_group": "posterior chain", "best_for": "muscle"},
        {"name": "Incline dumbbell press", "category": "hypertrophy", "muscle_group": "chest", "best_for": "muscle"},
        {"name": "Pull-up", "category": "strength", "muscle_group": "back", "best_for": "performance"},
        {"name": "Walking lunges", "category": "hypertrophy", "muscle_group": "legs", "best_for": "cut"},
        {"name": "Echo bike intervals", "category": "conditioning", "muscle_group": "engine", "best_for": "cut"},
        {"name": "Sled push", "category": "conditioning", "muscle_group": "engine", "best_for": "performance"},
        {"name": "Cable lateral raise", "category": "hypertrophy", "muscle_group": "shoulders", "best_for": "muscle"},
    ]


def build_tracking_stats(workouts: list[dict[str, Any]], metrics: list[dict[str, Any]]) -> dict[str, Any]:
    today = date.today()
    week_start = today - timedelta(days=6)
    weekly_sessions = 0
    weekly_volume = 0
    weekly_minutes = 0
    for workout in workouts:
        workout_date = date.fromisoformat(workout["workout_date"])
        if workout_date >= week_start:
            weekly_sessions += 1
            weekly_volume += workout["volume_load"]
            weekly_minutes += workout["duration_minutes"]

    latest_metric = metrics[0] if metrics else None
    previous_metric = metrics[1] if len(metrics) > 1 else None
    weight_delta = 0.0
    waist_delta = 0.0
    if latest_metric and previous_metric:
        weight_delta = round(latest_metric["body_weight"] - previous_metric["body_weight"], 1)
        waist_delta = round(latest_metric["waist"] - previous_metric["waist"], 1)

    pr_count = sum(1 for workout in workouts if workout["effort_score"] >= 9 and workout["energy_score"] >= 8)

    return {
        "weekly_sessions": weekly_sessions,
        "weekly_volume": weekly_volume,
        "weekly_minutes": weekly_minutes,
        "pr_count": pr_count,
        "latest_metric": latest_metric,
        "weight_delta": weight_delta,
        "waist_delta": waist_delta,
    }


def build_nutrition_stats(meals: list[dict[str, Any]]) -> dict[str, Any]:
    today_key = date.today().isoformat()
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fats": 0.0}
    for meal in meals:
        if str(meal["logged_at"]).startswith(today_key):
            totals["calories"] += float(meal["calories"])
            totals["protein"] += float(meal["protein"])
            totals["carbs"] += float(meal["carbs"])
            totals["fats"] += float(meal["fats"])
    return {key: round(value, 1) for key, value in totals.items()}


def catalog_payload() -> dict[str, Any]:
    return load_json(FOODS_FILE)


def filtered_foods(goal: str, meal_type: str, search: str) -> list[dict[str, Any]]:
    catalog = catalog_payload()
    search_key = search.strip().lower()
    items = []
    for food in catalog["foods"]:
        if goal != "all" and goal not in food["goals"]:
            continue
        if meal_type != "all" and meal_type not in food["meal_types"]:
            continue
        haystack = f'{food["name"]} {" ".join(food["tags"])}'.lower()
        if search_key and search_key not in haystack:
            continue
        items.append(food)
    return items


def filtered_recipes(goal: str, meal_type: str) -> list[dict[str, Any]]:
    catalog = catalog_payload()
    items = []
    for recipe in catalog["recipes"]:
        if goal != "all" and goal not in recipe["goals"]:
            continue
        if meal_type != "all" and recipe["meal_type"] != meal_type:
            continue
        items.append(recipe)
    return items


def build_recommendation(
    coach_key: str,
    mood: str,
    energy: int,
    equipment: str,
    minutes: int,
    goal: str,
    workouts: list[dict[str, Any]],
    research: list[dict[str, str]],
) -> dict[str, Any]:
    coach = COACHES.get(coach_key, COACHES["strength"])
    latest_focus = workouts[0]["focus"].lower() if workouts else ""
    if "lower" in latest_focus:
        base_focus = "Upper body push and pull"
    elif "upper" in latest_focus or "push" in latest_focus:
        base_focus = "Lower body strength and posterior chain"
    elif "conditioning" in latest_focus:
        base_focus = "Strength emphasis with controlled accessories"
    else:
        base_focus = "Full body athletic blend"

    if coach_key == "hypertrophy":
        base_focus = "Hypertrophy split with deep tension and pump work"
    elif coach_key == "conditioning":
        base_focus = "Engine builder with intervals, carries and low-impact finishers"
    elif coach_key == "mobility":
        base_focus = "Mobility and tissue quality reset with core stability"

    intensity = "Moderate"
    if energy >= 8 and mood in {"great", "locked in", "aggressive"}:
        intensity = "High"
    elif energy <= 4 or mood in {"tired", "flat", "sore"}:
        intensity = "Low"

    block_library = {
        "High": [
            "Primary lift: 1 top set + 3 back-off sets",
            "Secondary lift: 4 x 6-8",
            "Athletic finisher: 8 hard rounds",
        ],
        "Moderate": [
            "Primary lift: 4 x 5 at smooth speed",
            "Secondary lift: 3 x 8-10",
            "Accessory superset: 3 rounds",
        ],
        "Low": [
            "Tempo lift: 3 x 6 with full control",
            "Single-leg or machine pattern: 3 x 10",
            "Breath and mobility finish: 8 minutes",
        ],
    }
    blocks = block_library[intensity]

    if equipment == "home":
        blocks = [
            item.replace("machine", "dumbbell").replace("Primary lift", "Main home lift")
            for item in blocks
        ]
    elif equipment == "full gym":
        blocks = [item + " using full gym options" for item in blocks]

    principles = []
    for item in research:
        if "adapt" in item["principle"].lower() or "track" in item["principle"].lower():
            principles.append(item["principle"])
    principles = principles[:3]

    next_step = "Log all working sets with load and RPE so tomorrow's suggestion gets smarter."
    if goal == "cut":
        next_step = "Keep density high and finish with 10 minutes zone-2 or sled work."
    elif goal == "muscle":
        next_step = "Prioritize execution and add one high-rep pump finisher for the target muscle."
    elif goal == "performance":
        next_step = "Keep speed on the first rep honest and stop before technique drops."

    return {
        "coach_key": coach_key,
        "coach_name": coach["name"],
        "coach_role": coach["role"],
        "headline": base_focus,
        "intensity": intensity,
        "duration": minutes,
        "equipment": equipment,
        "goal": goal,
        "tone": coach["tone"],
        "blocks": blocks,
        "principles": principles,
        "next_step": next_step,
    }


def list_users() -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, username, full_name, role, subscription_tier, billing_status, gift_package, gifted_by,
                   discount_code, discount_percent, trial_started_at, trial_ends_at, gender, cycle_phase, equipment_access, fatigue_state,
                   age, height_cm, weight_kg, goal, experience_level, created_at
            FROM users
            ORDER BY role DESC, created_at ASC, id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def build_adaptive_filters(user: dict[str, Any]) -> list[dict[str, Any]]:
    weight = float(user["weight_kg"])
    weight_class = "light"
    if weight >= 95:
        weight_class = "heavy"
    elif weight >= 75:
        weight_class = "middle"
    return [
        {"label": "Gender", "value": str(user.get("gender", "male")).title()},
        {"label": "Weight class", "value": weight_class.title()},
        {"label": "Goal", "value": str(user["goal"]).title()},
        {"label": "Experience", "value": str(user["experience_level"]).title()},
        {"label": "Equipment", "value": str(user.get("equipment_access", "full gym")).title()},
        {"label": "Fatigue", "value": str(user.get("fatigue_state", "steady")).title()},
        {"label": "Cycle mode", "value": str(user.get("cycle_phase", "neutral")).title()},
    ]


def build_folder_cards(user: dict[str, Any], assistant: dict[str, Any]) -> list[dict[str, Any]]:
    first_plan = assistant["suggestions"][0] if assistant.get("suggestions") else None
    return [
        {
            "title": "Train",
            "anchor": "/hub/train",
            "detail": "Open today's training room, then jump into the live player.",
            "kicker": "Start",
            "metric": "Live session",
        },
        {
            "title": "Program",
            "anchor": "/hub/program",
            "detail": f"{len(assistant['suggestions'])} ready-made programs with fixed training days and sessions.",
            "kicker": "Plans",
            "metric": "Ready to run",
        },
        {
            "title": "Fuel",
            "anchor": "/nutrition-mode",
            "detail": f"Meals, macros and timing built around {assistant['targets']['calories']} kcal.",
            "kicker": "Fuel",
            "metric": f"{assistant['targets']['protein']}g protein",
        },
        {
            "title": "Track",
            "anchor": "/hub/track",
            "detail": "Body change, PRs and adherence in one clean place.",
            "kicker": "Track",
            "metric": "Body + strength",
        },
        {
            "title": "Coach",
            "anchor": "/hub/coach",
            "detail": "Adaptive coaching, weekly adjustment and recovery guidance.",
            "kicker": "Coach",
            "metric": "Adaptive engine",
        },
        {
            "title": "Profile",
            "anchor": "/hub/profile",
            "detail": "Update body data, goal and training context any time.",
            "kicker": "Setup",
            "metric": "Personalized",
        },
        {
            "title": "Calendar",
            "anchor": "/hub/calendar",
            "detail": "Weekly layout, next sessions and recovery rhythm.",
            "kicker": "Calendar",
            "metric": "Weekly flow",
        },
    ]


def build_dashboard_core_widgets(
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
    session_analytics: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {
            "kicker": "Train",
            "title": today_blueprint.get("title", "Today's session"),
            "detail": today_blueprint.get("focus_line", "Open the training room and follow the written order."),
            "metric": today_blueprint.get("duration", "Live session"),
            "anchor": "/hub/train",
        },
        {
            "kicker": "Fuel",
            "title": nutrition_intelligence.get("next_meal_title", "Next meal"),
            "detail": nutrition_intelligence.get("next_meal_detail", "Keep food timing clean and simple."),
            "metric": f"{nutrition_intelligence.get('protein_left', 0)}g protein left",
            "anchor": "/hub/fuel",
        },
        {
            "kicker": "Track",
            "title": f"{today_progress.get('completion_percent', 0)}% day complete",
            "detail": f"{today_progress.get('done_items', 0)}/{today_progress.get('total_items', 0)} blocks are already closed.",
            "metric": session_analytics.get("coach_note", "Stay consistent."),
            "anchor": "/hub/track",
        },
        {
            "kicker": "Coach",
            "title": "What to do next",
            "detail": "Open the coach lane for the shortest next step, not more information.",
            "metric": today_blueprint.get("coach_name", "Coach"),
            "anchor": "/hub/coach",
        },
    ]


def build_fast_lane(
    single_next_action: dict[str, str],
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
    session_analytics: dict[str, Any],
) -> list[dict[str, str]]:
    exercise_left = max(int(today_progress.get("exercise_total", 0)) - int(today_progress.get("exercise_done", 0)), 0)
    meal_left = max(int(today_progress.get("meal_total", 0)) - int(today_progress.get("meal_done", 0)), 0)
    return [
        {
            "kicker": "Do next",
            "title": single_next_action.get("title", "Open today's plan"),
            "detail": single_next_action.get("detail", "Move the day forward from one place."),
            "metric": single_next_action.get("tag", "Next step"),
            "anchor": single_next_action.get("anchor", "/dashboard"),
            "cta": single_next_action.get("cta", "Open"),
            "emphasis": "primary",
        },
        {
            "kicker": "Train",
            "title": today_blueprint.get("title", "Today's session"),
            "detail": f"{exercise_left} exercise blocks left today. Open the player and stay in sequence.",
            "metric": today_blueprint.get("duration", "Live session"),
            "anchor": "/workout-mode" if str(today_blueprint.get("day_type")) == "training" else "/hub/train",
            "cta": "Open train",
            "emphasis": "train",
        },
        {
            "kicker": "Fuel",
            "title": nutrition_intelligence.get("next_meal_title", "Next meal"),
            "detail": nutrition_intelligence.get("next_meal_detail", "Keep the next block easy to close."),
            "metric": f"{meal_left} meal blocks left",
            "anchor": "/nutrition-mode",
            "cta": "Open fuel",
            "emphasis": "fuel",
        },
        {
            "kicker": "Track",
            "title": session_analytics.get("coach_note", "Stay consistent."),
            "detail": "Open progress, body change and weekly review without leaving the daily flow.",
            "metric": f"{today_progress.get('completion_percent', 0)}% complete",
            "anchor": "/hub/track",
            "cta": "Open track",
            "emphasis": "track",
        },
    ]


def build_today_agenda(
    personal_calendar: list[dict[str, Any]],
    today_blueprint: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
    today_progress: dict[str, Any],
    checkins: list[dict[str, Any]],
) -> list[dict[str, str]]:
    today_key = date.today().isoformat()
    has_checkin_today = any(str(item.get("checkin_date") or "").startswith(today_key) for item in checkins)
    today_slots = list((personal_calendar[0] if personal_calendar else {}).get("slots") or [])
    agenda: list[dict[str, str]] = []
    for slot in today_slots[:4]:
        slot_type = str(slot.get("type") or "focus")
        state = "up next"
        anchor = "/dashboard"
        if slot_type == "checkin":
            state = "done" if has_checkin_today else "now"
            anchor = "/daily-checkin"
        elif slot_type == "training":
            exercise_left = max(int(today_progress.get("exercise_total", 0)) - int(today_progress.get("exercise_done", 0)), 0)
            state = "done" if exercise_left == 0 else "up next"
            anchor = "/workout-mode"
        elif slot_type == "nutrition":
            meal_left = max(int(today_progress.get("meal_total", 0)) - int(today_progress.get("meal_done", 0)), 0)
            state = "done" if meal_left == 0 else "up next"
            anchor = "/nutrition-mode"
        elif slot_type == "recovery":
            anchor = "/hub/coach"
        agenda.append(
            {
                "time": str(slot.get("time") or "--:--"),
                "title": str(slot.get("title") or "Today's block"),
                "detail": str(slot.get("detail") or ""),
                "state": state,
                "anchor": anchor,
            }
        )
    if not agenda:
        agenda = [
            {
                "time": "08:00",
                "title": "Daily check-in",
                "detail": "Open readiness and set the tone for the day.",
                "state": "now" if not has_checkin_today else "done",
                "anchor": "/daily-checkin",
            },
            {
                "time": "17:30",
                "title": today_blueprint.get("title", "Today's training"),
                "detail": today_blueprint.get("focus_line", "Open the player and follow the written order."),
                "state": "up next",
                "anchor": "/workout-mode" if str(today_blueprint.get("day_type")) == "training" else "/hub/train",
            },
            {
                "time": "20:00",
                "title": nutrition_intelligence.get("next_meal_title", "Next meal"),
                "detail": nutrition_intelligence.get("next_meal_detail", "Close the next meal block."),
                "state": "up next",
                "anchor": "/nutrition-mode",
            },
        ]
    return agenda


def build_profile_tools(user: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "title": "Profile",
            "detail": f"Update {user.get('goal', 'training')} setup, body data and weekly context.",
            "anchor": "/hub/profile",
        },
        {
            "title": "Calendar",
            "detail": "Open the weekly rhythm and see training, meals and recovery slots.",
            "anchor": "/hub/calendar",
        },
        {
            "title": "Logout",
            "detail": "Switch user or close the session without hunting through screens.",
            "anchor": "/logout",
        },
    ]


def build_today_snapshot(
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
    progress_system: dict[str, Any],
) -> list[dict[str, str]]:
    exercise_left = max(int(today_progress.get("exercise_total", 0)) - int(today_progress.get("exercise_done", 0)), 0)
    meal_left = max(int(today_progress.get("meal_total", 0)) - int(today_progress.get("meal_done", 0)), 0)
    return [
        {
            "label": "Day type",
            "value": str(today_blueprint.get("status_label", "Today")),
            "detail": today_blueprint.get("focus_line", "Follow the plan in order."),
        },
        {
            "label": "Training blocks",
            "value": f"{exercise_left} left",
            "detail": today_blueprint.get("duration", "Live session"),
        },
        {
            "label": "Food blocks",
            "value": f"{meal_left} left",
            "detail": nutrition_intelligence.get("next_meal_title", "Next meal"),
        },
        {
            "label": "Recomp score",
            "value": f"{progress_system.get('recomposition_score', 0)}/10",
            "detail": progress_system.get("next_checkpoint", "Stay consistent this week."),
        },
    ]


def build_tactical_cards(
    today_blueprint: dict[str, Any],
    live_session: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
    weekly_review: dict[str, Any],
) -> list[dict[str, str]]:
    queue = list(live_session.get("queue") or [])
    current = queue[0] if queue else {}
    next_item = queue[1] if len(queue) > 1 else current
    return [
        {
            "kicker": "Train now",
            "title": current.get("name", today_blueprint.get("title", "Open training")),
            "detail": current.get("detail", today_blueprint.get("focus_line", "Open the player and follow the sequence.")),
            "anchor": "/workout-mode" if str(today_blueprint.get("day_type")) == "training" else "/hub/train",
            "cta": "Open workout",
        },
        {
            "kicker": "Next up",
            "title": next_item.get("name", "Close the current block"),
            "detail": next_item.get("detail", "The next block appears here once the current one is done."),
            "anchor": "/hub/train",
            "cta": "See queue",
        },
        {
            "kicker": "Eat next",
            "title": nutrition_intelligence.get("next_meal_title", "Next meal"),
            "detail": nutrition_intelligence.get("next_meal_detail", "Keep fuel simple and on time."),
            "anchor": "/nutrition-mode",
            "cta": "Open fuel",
        },
        {
            "kicker": "Coach call",
            "title": "This week adjustment",
            "detail": weekly_review.get("next_week_adjustment", weekly_review.get("adjustment", "Hold the plan and execute cleanly.")),
            "anchor": "/hub/coach",
            "cta": "Open coach",
        },
    ]


def build_mission_control(
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
    coach_briefing: dict[str, Any],
    weekly_review: dict[str, Any],
) -> dict[str, Any]:
    day_type = str(today_blueprint.get("day_type") or "training")
    exercise_left = max(int(today_progress.get("exercise_total", 0)) - int(today_progress.get("exercise_done", 0)), 0)
    meal_left = max(int(today_progress.get("meal_total", 0)) - int(today_progress.get("meal_done", 0)), 0)
    headline = "Training day in control" if day_type == "training" else "Recovery day in control"
    subline = (
        f"{exercise_left} training blocks and {meal_left} food blocks are still open today."
        if day_type == "training"
        else f"Recovery is the job today. {meal_left} food blocks still matter."
    )
    cue = coach_briefing.get("headline", "Keep the order simple and clean.")
    if exercise_left == 0 and meal_left == 0:
        cue = "Main work is closed. Recover well and prep the next day."
    return {
        "headline": headline,
        "subline": subline,
        "cue": cue,
        "coach_signal": weekly_review.get("next_week_adjustment", weekly_review.get("adjustment", "Hold quality and stay consistent.")),
        "nutrition_signal": nutrition_intelligence.get("next_meal_detail", "Close the next meal block on time."),
        "focus_signal": today_blueprint.get("focus_line", "Follow today's plan in order."),
    }


def build_quick_capture(
    today_progress: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
) -> list[dict[str, str]]:
    meal_left = max(int(today_progress.get("meal_total", 0)) - int(today_progress.get("meal_done", 0)), 0)
    return [
        {
            "title": "Daily check-in",
            "detail": "Log energy, soreness and focus in under a minute.",
            "anchor": "/daily-checkin",
            "tag": "60 sec",
        },
        {
            "title": "Log meal",
            "detail": nutrition_intelligence.get("next_meal_title", "Close the next meal block."),
            "anchor": "/nutrition-mode",
            "tag": f"{meal_left} left",
        },
        {
            "title": "Open train",
            "detail": "Jump straight into the player and keep sequence clean.",
            "anchor": "/workout-mode",
            "tag": "Live",
        },
        {
            "title": "Weekly reset",
            "detail": "Review the week and prep the next block.",
            "anchor": "/weekly-reset",
            "tag": "Reset",
        },
    ]


def build_signal_stack(
    notifications: list[dict[str, str]],
    today_progress: dict[str, Any],
) -> list[dict[str, str]]:
    stack = []
    for item in notifications[:3]:
        stack.append(
            {
                "title": item.get("title", "Signal"),
                "detail": item.get("detail", ""),
                "level": item.get("level", "info"),
            }
        )
    stack.append(
        {
            "title": "Day completion",
            "detail": f"{today_progress.get('completion_percent', 0)}% of today's plan is already closed.",
            "level": "progress",
        }
    )
    return stack[:4]


def build_command_strip(
    single_next_action: dict[str, str],
    workspace_hub: list[dict[str, str]],
    profile_tools: list[dict[str, str]],
) -> list[dict[str, str]]:
    strip = [
        {
            "kicker": "Now",
            "title": single_next_action.get("cta", "Open next step"),
            "detail": single_next_action.get("title", "Move the day forward."),
            "anchor": single_next_action.get("anchor", "/dashboard"),
        }
    ]
    for item in workspace_hub[:2]:
        strip.append(
            {
                "kicker": "Room",
                "title": item.get("title", "Open room"),
                "detail": item.get("detail", "Go straight to the focused workspace."),
                "anchor": item.get("anchor", "/dashboard"),
            }
        )
    for item in profile_tools[:1]:
        strip.append(
            {
                "kicker": "Account",
                "title": item.get("title", "Profile"),
                "detail": item.get("detail", "Open account tools."),
                "anchor": item.get("anchor", "/hub/profile"),
            }
        )
    return strip[:4]


def build_priority_stack(
    today_blueprint: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
    daily_tasks: list[dict[str, str]],
    scores: dict[str, Any],
) -> list[dict[str, str]]:
    top_task = daily_tasks[0] if daily_tasks else {"title": "Close the first block", "detail": "Start with the next scheduled action."}
    return [
        {
            "kicker": "Train",
            "title": today_blueprint.get("title", "Today's training"),
            "detail": today_blueprint.get("focus_line", "Open the training room and follow the sequence."),
            "meta": today_blueprint.get("duration", "Live session"),
        },
        {
            "kicker": "Fuel",
            "title": nutrition_intelligence.get("next_meal_title", "Next meal"),
            "detail": nutrition_intelligence.get("next_meal_detail", "Keep the next meal block simple and on time."),
            "meta": f"{nutrition_intelligence.get('protein_left', 0)}g protein left",
        },
        {
            "kicker": "Focus",
            "title": top_task.get("title", "Close the next block"),
            "detail": top_task.get("detail", "Move one clean step at a time."),
            "meta": f"Recovery {scores.get('recovery_score', 0)}/10",
        },
    ]


def build_train_room(
    today_blueprint: dict[str, Any],
    live_session: dict[str, Any],
    session_analytics: dict[str, Any],
    exercise_mastery: list[dict[str, Any]],
) -> dict[str, Any]:
    queue = list(live_session.get("queue") or [])
    current = queue[0] if queue else {}
    next_item = queue[1] if len(queue) > 1 else current
    return {
        "headline": today_blueprint.get("title", "Today's training room"),
        "detail": today_blueprint.get("focus_line", "Open the player and follow the order."),
        "current_name": current.get("name", live_session.get("next_move", "Open the player")),
        "current_detail": current.get("detail", live_session.get("coach_prompt", "Live session ready.")),
        "current_machine": current.get("machine_label", "Training station"),
        "current_machine_focus": current.get("machine_focus", today_blueprint.get("status_label", "Training")),
        "current_machine_image": current.get("machine_image", ""),
        "current_weight": current.get("weight_suggestion", "Use clean execution first."),
        "current_prescription": exercise_prescription_text(current) if current else today_blueprint.get("duration", "Live session"),
        "next_name": next_item.get("name", "Open workout mode"),
        "next_detail": next_item.get("detail", "The next movement appears here once the current block is closed."),
        "queue_preview": queue[:5],
        "mastery_preview": exercise_mastery[:3],
        "session_tiles": session_analytics.get("tiles", [])[:4],
    }


def build_fuel_room(
    nutrition_os: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
    shopping_list: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "headline": nutrition_os.get("headline", "Fuel room"),
        "next_meal": nutrition_intelligence.get("next_meal_title", "Next meal"),
        "next_detail": nutrition_intelligence.get("next_meal_detail", "Close the next meal block."),
        "protein_left": nutrition_intelligence.get("protein_left", 0),
        "calories_left": nutrition_intelligence.get("calories_left", 0),
        "smart_swaps": list(nutrition_intelligence.get("smart_swaps", []))[:4],
        "prep_call": list(nutrition_os.get("prep_call", []))[:3],
        "weekly_plan": list(nutrition_os.get("weekly_plan", []))[:4],
        "shopping_preview": list(shopping_list or [])[:6],
    }


def build_track_room(
    progress_system: dict[str, Any],
    transformation_dashboard: dict[str, Any],
    weekly_review: dict[str, Any],
) -> dict[str, Any]:
    return {
        "headline": transformation_dashboard.get("headline", "Track room"),
        "recomp": progress_system.get("recomposition_score", 0),
        "adherence": progress_system.get("adherence_score", 0),
        "checkpoint": progress_system.get("next_checkpoint", "Stay consistent this week."),
        "wins": list(progress_system.get("wins", []))[:4],
        "watchouts": list(progress_system.get("watchouts", []))[:4],
        "tiles": list(transformation_dashboard.get("tiles", []))[:4],
        "trends": list(transformation_dashboard.get("trends", []))[:4],
        "review": weekly_review.get("next_week_adjustment", weekly_review.get("adjustment", "Hold the plan and improve execution.")),
    }


def build_train_os(
    today_blueprint: dict[str, Any],
    train_room: dict[str, Any],
    live_session: dict[str, Any],
    session_analytics: dict[str, Any],
) -> dict[str, Any]:
    queue = list(train_room.get("queue_preview") or [])
    active = queue[0] if queue else {}
    return {
        "headline": train_room.get("headline", "Train OS"),
        "primary_call": active.get("name", train_room.get("current_name", "Open live player")),
        "primary_detail": active.get("detail", train_room.get("detail", "Run the written order and keep rest clean.")),
        "primary_weight": active.get("weight_suggestion", train_room.get("current_weight", "Use stable working load.")),
        "station": active.get("machine_label", train_room.get("current_machine", "Training station")),
        "station_focus": active.get("machine_focus", train_room.get("current_machine_focus", "Main station")),
        "autoplay_note": "Finish the current block and move straight to the next one in sequence.",
        "next_up": train_room.get("next_name", "Next movement"),
        "next_detail": train_room.get("next_detail", "The next movement appears as soon as the current block is done."),
        "summary_tiles": list(session_analytics.get("tiles", []))[:4],
        "completion_note": session_analytics.get("next_session_call", "Keep execution clean and log the whole session."),
        "day_type": str(today_blueprint.get("day_type") or "training"),
    }


def build_fuel_os(
    fuel_room: dict[str, Any],
    nutrition_os: dict[str, Any],
    shopping_list: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "headline": fuel_room.get("headline", "Fuel OS"),
        "eat_now": fuel_room.get("next_meal", "Next meal"),
        "eat_now_detail": fuel_room.get("next_detail", "Close the next meal block on time."),
        "macro_call": f"{fuel_room.get('protein_left', 0)}g protein left · {fuel_room.get('calories_left', 0)} kcal left",
        "prep_stack": list(fuel_room.get("prep_call", []))[:3],
        "swap_stack": list(fuel_room.get("smart_swaps", []))[:4],
        "shopping_stack": list(shopping_list or [])[:5],
        "weekly_lane": list(nutrition_os.get("weekly_plan", []))[:3],
    }


def build_track_os(
    track_room: dict[str, Any],
    transformation_dashboard: dict[str, Any],
    progress_system: dict[str, Any],
) -> dict[str, Any]:
    tiles = list(track_room.get("tiles", []))
    trends = list(track_room.get("trends", []))
    return {
        "headline": track_room.get("headline", "Track OS"),
        "trajectory": transformation_dashboard.get("headline", "Transformation review"),
        "trajectory_detail": progress_system.get("next_checkpoint", "Stay consistent through the current block."),
        "recomp": track_room.get("recomp", 0),
        "adherence": track_room.get("adherence", 0),
        "wins": list(track_room.get("wins", []))[:3],
        "watchouts": list(track_room.get("watchouts", []))[:3],
        "tiles": tiles[:4],
        "trends": trends[:4],
    }


def build_admin_growth(users: list[dict[str, Any]]) -> dict[str, Any]:
    if not users:
        return {
            "headline": "No member data yet",
            "summary": "Admin growth view appears when users and packages start filling in.",
            "tiles": [],
        }
    total = len(users)
    paid = sum(1 for user in users if str(user.get("billing_status") or "").lower() == "paid")
    gifted = sum(1 for user in users if str(user.get("gift_package") or "").strip())
    elite = sum(1 for user in users if str(user.get("subscription_tier") or "").lower() == "elite")
    pro = sum(1 for user in users if str(user.get("subscription_tier") or "").lower() == "pro")
    return {
        "headline": "Growth overview",
        "summary": "See who is on paid access, who is gifted, and where premium growth is coming from.",
        "tiles": [
            {"label": "Members", "value": str(total), "detail": "Total accounts in the system."},
            {"label": "Paid", "value": str(paid), "detail": "Currently billed members."},
            {"label": "Gifted", "value": str(gifted), "detail": "Admin gifted package access."},
            {"label": "Elite + Pro", "value": str(elite + pro), "detail": "Premium package footprint."},
        ],
    }


def build_fuel_os_pro(
    fuel_os: dict[str, Any],
    weekly_plan: list[dict[str, Any]],
    nutrition_intelligence: dict[str, Any],
) -> dict[str, Any]:
    replacement_map = [
        "Chicken bowl -> turkey wrap when you need something faster.",
        "Rice + beef -> potatoes + fish when digestion needs to stay lighter.",
        "Greek yogurt bowl -> shake + banana when time is tight.",
        "Egg breakfast -> skyr + oats when you need a cleaner prep option.",
    ]
    return {
        "three_day_plan": list(weekly_plan or [])[:3],
        "replacement_stack": replacement_map[:4],
        "shopping_mode": [item.get("name", "") for item in fuel_os.get("shopping_stack", [])[:5]],
        "next_macro_move": nutrition_intelligence.get("macro_nudge", "Keep protein first and close the next meal block on time.")
        if isinstance(nutrition_intelligence, dict)
        else "Keep protein first and close the next meal block on time.",
    }


def build_transformation_mode(
    transformation_dashboard: dict[str, Any],
    recomposition_dashboard: dict[str, Any],
    progress_system: dict[str, Any],
    metrics: list[dict[str, Any]],
    photos: list[dict[str, Any]],
) -> dict[str, Any]:
    latest = metrics[0] if metrics else {}
    return {
        "headline": transformation_dashboard.get("headline", "Transformation review"),
        "score": progress_system.get("recomposition_score", 0),
        "checkpoint": progress_system.get("next_checkpoint", "Stay consistent through this block."),
        "tiles": list(transformation_dashboard.get("tiles", []))[:4],
        "trends": list(transformation_dashboard.get("trends", []))[:4],
        "latest_weight": str(latest.get("body_weight", "--")),
        "latest_waist": str(latest.get("waist", "--")),
        "photo_count": str(len(photos)),
        "review_call": recomposition_dashboard.get("headline", "Body change and strength are moving together."),
    }


def build_coach_memory_pro(
    coach_memory: list[dict[str, Any]],
    workouts: list[dict[str, Any]],
    checkins: list[dict[str, Any]],
) -> dict[str, Any]:
    latest_focus = workouts[0]["focus"] if workouts else "No logged session yet"
    recent_energy = round(sum(int(item.get("energy_score", 7)) for item in checkins[:5]) / len(checkins[:5]), 1) if checkins[:5] else 7.0
    notes = [str(item.get("memory_text") or "") for item in coach_memory[:4] if str(item.get("memory_text") or "").strip()]
    if not notes:
        notes = [
            "Coach memory will start filling as you log sessions, meals and check-ins.",
            "The system will keep weak points, favorite lifts and skipped patterns here.",
        ]
    stagnation_flag = "No stagnation flag yet"
    if workouts and len(workouts) >= 3 and all("upper" in str(item.get("focus", "")).lower() for item in workouts[:3]):
        stagnation_flag = "Upper-body bias detected. Rebalance lower-body consistency next block."
    elif recent_energy <= 5.5:
        stagnation_flag = "Energy is trending lower. Hold intensity and prioritize recovery quality."
    return {
        "headline": "Coach memory pro",
        "latest_focus": latest_focus,
        "energy_lane": f"{recent_energy}/10 average readiness",
        "stagnation_flag": stagnation_flag,
        "notes": notes[:4],
    }


def build_admin_conversion_cockpit(
    business: dict[str, Any] | None,
    users: list[dict[str, Any]],
) -> dict[str, Any]:
    if not business:
        return {"tiles": [], "summary": ""}
    members = [user for user in users if str(user.get("role")) == "member"]
    trialing = sum(1 for user in members if str(user.get("billing_status") or "").lower() not in {"paid", "gifted"} and str(user.get("trial_ends_at") or "").strip())
    paid = int(business.get("active_paid_users", 0))
    gifted = int(business.get("gifted_users", 0))
    conversion = f"{round((paid / len(members)) * 100):.0f}%" if members else "0%"
    return {
        "tiles": [
            {"label": "Trialing", "value": str(trialing), "detail": "Members currently inside free access."},
            {"label": "Paid", "value": str(paid), "detail": "Members on paid packages."},
            {"label": "Gifted", "value": str(gifted), "detail": "Admin granted access."},
            {"label": "Conversion", "value": conversion, "detail": "Paid members as part of total member base."},
        ],
        "summary": f"MRR is {business.get('mrr', 0)} with {business.get('pro_users', 0)} Pro and {business.get('elite_users', 0)} Elite members.",
    }


def build_train_os_pro(
    train_os: dict[str, Any],
    live_session: dict[str, Any],
    voice_coach: dict[str, Any],
    exercise_mastery: list[dict[str, Any]],
) -> dict[str, Any]:
    queue = list(live_session.get("queue") or [])
    autoplay_lane = []
    for item in queue[:4]:
        autoplay_lane.append(
            {
                "name": item.get("name", "Next movement"),
                "detail": item.get("detail", "Follow the order."),
                "station": item.get("machine_label", "Training station"),
                "load": item.get("weight_suggestion", "Use stable working load."),
            }
        )
    cue_stack = []
    for item in exercise_mastery[:4]:
        cue_stack.append(
            {
                "name": item.get("name", "Movement"),
                "execution": item.get("execution", "Move with control."),
                "mistake": item.get("mistake", "Avoid rushing setup."),
            }
        )
    return {
        "headline": "Train OS 3.0",
        "autoplay_lane": autoplay_lane,
        "cue_stack": cue_stack,
        "voice_label": voice_coach.get("mode_label", "Voice cue ready"),
        "voice_line": voice_coach.get("line", "Stay clean on setup, pace and finish the full written order."),
        "finish_stack": [
            "Close the final set, then open post-workout fuel.",
            "Log the session and leave one coach note before you exit.",
            "Use the weekly review to adjust next block, not mid-session guessing.",
        ],
        "next_move": train_os.get("next_up", "Finish the current movement and continue."),
    }


def build_transformation_shell(
    transformation_mode: dict[str, Any],
    progress_trends: list[dict[str, str]],
    photos: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "headline": "Transformation shell",
        "hero": transformation_mode.get("review_call", "Body change and strength are moving together."),
        "checkpoint": transformation_mode.get("checkpoint", "Stay consistent through this block."),
        "latest_photo_label": f"{len(photos)} progress photos logged",
        "trend_stack": list(progress_trends or [])[:4],
        "review_tiles": list(transformation_mode.get("tiles", []))[:4],
    }


def build_admin_revenue_cockpit(
    business: dict[str, Any] | None,
    users: list[dict[str, Any]],
) -> dict[str, Any]:
    if not business:
        return {"headline": "Revenue cockpit", "summary": "", "tiles": []}
    members = [user for user in users if str(user.get("role")) == "member"]
    trials_ending = 0
    today = date.today()
    for user in members:
        trial_end = str(user.get("trial_ends_at") or "").strip()
        if not trial_end:
            continue
        try:
            end_date = date.fromisoformat(trial_end[:10])
        except ValueError:
            continue
        if 0 <= (end_date - today).days <= 3:
            trials_ending += 1
    paid = int(business.get("active_paid_users", 0))
    gifted = int(business.get("gifted_users", 0))
    total_members = int(business.get("total_members", 0)) or len(members)
    retention_base = total_members if total_members else 1
    return {
        "headline": "Revenue cockpit",
        "summary": f"MRR {business.get('mrr', 0)} · {paid} paid · {gifted} gifted · {trials_ending} trials ending soon.",
        "tiles": [
            {"label": "MRR", "value": str(business.get("mrr", 0)), "detail": "Current monthly recurring revenue estimate."},
            {"label": "Retention base", "value": f"{round((paid / retention_base) * 100):.0f}%", "detail": "Paid share across active members."},
            {"label": "Trials ending", "value": str(trials_ending), "detail": "Users to watch for conversion in the next 3 days."},
            {"label": "Elite users", "value": str(business.get("elite_users", 0)), "detail": "Highest package footprint."},
        ],
    }


def build_section_menu(user: dict[str, Any]) -> list[dict[str, str]]:
    items = [
        {"title": "Train", "anchor": "/hub/train"},
        {"title": "Program", "anchor": "/hub/program"},
        {"title": "Coach", "anchor": "/hub/coach"},
        {"title": "Fuel", "anchor": "/nutrition-mode"},
        {"title": "Track", "anchor": "/hub/track"},
        {"title": "Calendar", "anchor": "/hub/calendar"},
        {"title": "Profile", "anchor": "/hub/profile"},
    ]
    if str(user.get("role")) == "admin":
        items.append({"title": "Admin", "anchor": "/hub/profile"})
    return items


def build_goal_suggestions(user: dict[str, Any], assistant_coach: str, training_days: int) -> list[dict[str, Any]]:
    goal = str(user["goal"]).lower()
    gender = str(user.get("gender", "male")).lower()
    weight = float(user["weight_kg"])
    frame = "athletic"
    if weight >= 95:
        frame = "power"
    elif weight < 70:
        frame = "lightweight"
    if goal == "performance":
        options = [
            {
                "title": "Full body performance",
                "coach_key": "strength",
                "coach_role": COACHES["strength"]["role"],
                "days": training_days,
                "focus": "Whole body output",
                "summary": f"Best for {frame} {gender} athletes who want stronger full-body output with simple weekly structure.",
                "blocks": ["Day 1 squat + press", "Day 2 hinge + pull", "Day 3 athletic full body", "Day 4 engine + carries"],
                "nutrition": "Higher carbs around the two heaviest days and simple repeatable recovery meals.",
                "sessions": [
                    {"day": "Day 1", "title": "Full body strength", "prescription": "4 lifts / 60-75 min", "exercises": ["Back squat 5x5", "Bench press 4x6", "Chest supported row 4x8", "Farmer carry 4 x 20 m"]},
                    {"day": "Day 2", "title": "Posterior chain + pull", "prescription": "4 lifts / 55-70 min", "exercises": ["Romanian deadlift 4x6", "Weighted pull-up 4x6-8", "DB incline press 3x10", "Split squat 3x10 / leg"]},
                    {"day": "Day 3", "title": "Athletic total body", "prescription": "5 lifts / 55-65 min", "exercises": ["Front squat 4x5", "Push press 4x5", "Cable row 4x10", "Walking lunge 3x12 / leg", "Sled push 6 x 20 m"]},
                ],
            },
            {
                "title": "Upper body specialization",
                "coach_key": "strength",
                "coach_role": COACHES["strength"]["role"],
                "days": training_days,
                "focus": "Upper body focus",
                "summary": f"Push pressing strength, shoulders and back while keeping legs on maintenance volume.",
                "blocks": ["Upper heavy", "Lower maintenance", "Upper volume", "Arms + delts"],
                "nutrition": "Keep carbs around upper-body sessions and do not under-eat on the heavy press day.",
                "sessions": [
                    {"day": "Day 1", "title": "Upper heavy", "prescription": "5 lifts / 65 min", "exercises": ["Bench press 5x5", "Weighted pull-up 4x6", "Seated DB press 4x8", "Barbell row 4x8", "Rope pressdown 3x12"]},
                    {"day": "Day 2", "title": "Upper volume", "prescription": "5 lifts / 60 min", "exercises": ["Incline DB press 4x10", "Lat pulldown 4x10", "Cable lateral raise 4x15", "Chest supported row 3x12", "EZ curl 3x12"]},
                    {"day": "Day 3", "title": "Arms and delts", "prescription": "5 lifts / 50 min", "exercises": ["Machine shoulder press 4x10", "Cable curl 4x12", "Overhead triceps extension 4x12", "Rear delt fly 3x15", "Push-up burnout 2 rounds"]},
                ],
            },
            {
                "title": "Conditioning performance",
                "coach_key": "conditioning",
                "coach_role": COACHES["conditioning"]["role"],
                "days": training_days,
                "focus": "Conditioning focus",
                "summary": f"Built for users who want speed, work capacity and conditioning without losing their main strength anchors.",
                "blocks": ["Strength anchor", "Intervals", "Density full body", "Zone 2 + carries"],
                "nutrition": "Keep pre-workout carbs sharp and use lower-fat meals before conditioning days.",
                "sessions": [
                    {"day": "Day 1", "title": "Strength anchor", "prescription": "4 lifts / 50-60 min", "exercises": ["Back squat 4x4", "Bench press 4x5", "Row 4x8", "Bike intervals 8 x 30/60"]},
                    {"day": "Day 2", "title": "Engine day", "prescription": "4 blocks / 40-50 min", "exercises": ["Rower intervals 10 x 45/45", "Walking lunge 3x12", "Burpee broad jump 3x8", "Farmer carry 5 x 20 m"]},
                    {"day": "Day 3", "title": "Density full body", "prescription": "Circuit / 45-55 min", "exercises": ["Goblet squat 4x12", "Push-up 4x15", "TRX or cable row 4x12", "Sled push 6 x 20 m"]},
                ],
            },
        ]
    elif goal == "muscle":
        options = [
            {
                "title": "Bodybuilding growth split",
                "coach_key": "hypertrophy",
                "coach_role": COACHES["hypertrophy"]["role"],
                "days": training_days,
                "focus": "Bodybuilding focus",
                "summary": f"True muscle-building package with fixed hypertrophy days, exercise order and volume progression.",
                "blocks": ["Push", "Pull", "Legs", "Upper pump"],
                "nutrition": "Small surplus, protein at every feeding and carbs pre/post workout.",
                "sessions": [
                    {"day": "Day 1", "title": "Push", "prescription": "5 lifts / 60-70 min", "exercises": ["Incline DB press 4x8-10", "Machine chest press 4x10", "Seated DB press 3x10", "Cable lateral raise 4x15", "Overhead triceps extension 3x12"]},
                    {"day": "Day 2", "title": "Pull", "prescription": "5 lifts / 60-70 min", "exercises": ["Lat pulldown 4x10", "Chest supported row 4x10", "Single-arm cable row 3x12", "Face pull 3x15", "EZ curl 4x12"]},
                    {"day": "Day 3", "title": "Legs", "prescription": "5 lifts / 65-75 min", "exercises": ["Hack squat 4x8", "Romanian deadlift 4x8", "Leg press 3x12", "Leg curl 3x12", "Standing calf raise 4x15"]},
                ],
            },
            {
                "title": "Upper body growth",
                "coach_key": "hypertrophy",
                "coach_role": COACHES["hypertrophy"]["role"],
                "days": training_days,
                "focus": "Upper body focus",
                "summary": f"More chest, back, delts and arms while legs stay strong on lower maintenance volume.",
                "blocks": ["Upper press", "Upper pull", "Legs maintenance", "Arms + delts"],
                "nutrition": "Keep calories highest on upper volume days and maintain protein every 3-4 hours.",
                "sessions": [
                    {"day": "Day 1", "title": "Upper press", "prescription": "5 lifts / 60 min", "exercises": ["Incline DB press 4x10", "Machine shoulder press 4x10", "Cable fly 3x15", "Lateral raise 4x15", "Triceps pressdown 4x12"]},
                    {"day": "Day 2", "title": "Upper pull", "prescription": "5 lifts / 60 min", "exercises": ["Pull-up or pulldown 4x8-10", "Chest supported row 4x10", "Cable row 3x12", "Rear delt fly 3x15", "Hammer curl 4x12"]},
                    {"day": "Day 3", "title": "Arms and shoulders", "prescription": "6 lifts / 55 min", "exercises": ["DB shoulder press 4x8", "Cable lateral raise 4x15", "EZ curl 4x10", "Cable curl 3x12", "Dip machine 3x12", "Overhead rope extension 3x12"]},
                ],
            },
            {
                "title": "Leg day specialization",
                "coach_key": "hypertrophy",
                "coach_role": COACHES["hypertrophy"]["role"],
                "days": training_days,
                "focus": "Leg focus",
                "summary": f"Prioritize quads, glutes and hamstrings with coach-led lower-body sessions and clear weekly progression.",
                "blocks": ["Quads", "Upper support", "Posterior chain", "Glute + calves"],
                "nutrition": "Push carbs hardest before and after leg days to recover output and volume.",
                "sessions": [
                    {"day": "Day 1", "title": "Quads dominant", "prescription": "5 lifts / 70 min", "exercises": ["Hack squat 4x8", "Leg press 4x12", "Bulgarian split squat 3x10 / leg", "Leg extension 3x15", "Calf raise 4x15"]},
                    {"day": "Day 2", "title": "Posterior chain", "prescription": "5 lifts / 65 min", "exercises": ["Romanian deadlift 4x8", "Hip thrust 4x10", "Seated leg curl 4x12", "Walking lunge 3x12 / leg", "Back extension 3x15"]},
                    {"day": "Day 3", "title": "Glute and calves", "prescription": "4 lifts / 50 min", "exercises": ["Hip thrust 4x8", "Cable kickback 3x15", "Leg press high stance 3x12", "Standing calf raise 5x15"]},
                ],
            },
            {
                "title": "Arms specialization",
                "coach_key": "hypertrophy",
                "coach_role": COACHES["hypertrophy"]["role"],
                "days": training_days,
                "focus": "Arms focus",
                "summary": f"Dedicated arm growth package with enough upper-body work to support biceps and triceps size fast.",
                "blocks": ["Push arms", "Pull arms", "Upper support", "Arm pump day"],
                "nutrition": "Stay in a small surplus and keep the pre-workout meal consistent for arm sessions.",
                "sessions": [
                    {"day": "Day 1", "title": "Triceps priority", "prescription": "5 lifts / 50-60 min", "exercises": ["Close grip press 4x6", "Cable pressdown 4x12", "Overhead rope extension 4x12", "Machine chest press 3x10", "Lateral raise 3x15"]},
                    {"day": "Day 2", "title": "Biceps priority", "prescription": "5 lifts / 50-60 min", "exercises": ["EZ curl 4x10", "Incline DB curl 4x12", "Cable curl 3x12", "Lat pulldown 4x10", "Chest supported row 3x12"]},
                    {"day": "Day 3", "title": "Arm pump day", "prescription": "6 lifts / 45-55 min", "exercises": ["Cable curl 3x15", "Rope pressdown 3x15", "Hammer curl 3x12", "Skull crusher 3x12", "Preacher curl 2x15", "Dip machine 2x15"]},
                ],
            },
        ]
    else:
        options = [
            {
                "title": "Full body fat-loss",
                "coach_key": "conditioning",
                "coach_role": COACHES["conditioning"]["role"],
                "days": training_days,
                "focus": "Whole body output",
                "summary": f"Simple fat-loss package with full-body lifting and enough conditioning to keep calorie burn high.",
                "blocks": ["Full body A", "Conditioning", "Full body B", "Zone 2 + mobility"],
                "nutrition": "Protein high, carbs around training, tighter food quality on rest days.",
                "sessions": [
                    {"day": "Day 1", "title": "Full body A", "prescription": "5 lifts / 55-65 min", "exercises": ["Goblet squat 4x10", "Bench press or DB press 4x8", "Lat pulldown 4x10", "Romanian deadlift 3x10", "Bike finisher 8 min"]},
                    {"day": "Day 2", "title": "Conditioning focus", "prescription": "4 blocks / 35-45 min", "exercises": ["Rower intervals 10 x 30/45", "Sled push 6 x 20 m", "Walking lunge 3x12 / leg", "Carry complex 4 rounds"]},
                    {"day": "Day 3", "title": "Full body B", "prescription": "5 lifts / 55-65 min", "exercises": ["Front squat 4x8", "Machine press 4x10", "Chest supported row 4x10", "Leg curl 3x12", "Incline treadmill walk 10 min"]},
                ],
            },
            {
                "title": "Legs and conditioning",
                "coach_key": "conditioning",
                "coach_role": COACHES["conditioning"]["role"],
                "days": training_days,
                "focus": "Leg focus",
                "summary": f"Bias lower body, steps and work capacity for users who want leaner legs and stronger conditioning.",
                "blocks": ["Lower density", "Intervals", "Posterior chain", "Zone 2"],
                "nutrition": "Keep carbs around the hardest lower sessions and keep dinner cleaner on recovery days.",
                "sessions": [
                    {"day": "Day 1", "title": "Lower density", "prescription": "5 lifts / 60 min", "exercises": ["Hack squat 4x10", "Walking lunge 4x12 / leg", "Leg curl 3x12", "Step-up 3x12 / leg", "Sled push 5 x 20 m"]},
                    {"day": "Day 2", "title": "Posterior chain", "prescription": "4 lifts / 50-60 min", "exercises": ["Romanian deadlift 4x8", "Hip thrust 4x10", "Back extension 3x15", "Bike intervals 10 x 30/30"]},
                    {"day": "Day 3", "title": "Conditioning reset", "prescription": "3 blocks / 35 min", "exercises": ["Incline walk 20 min", "Farmer carry 4 x 20 m", "Mobility flow 10 min"]},
                ],
            },
            {
                "title": "Conditioning block",
                "coach_key": "conditioning",
                "coach_role": COACHES["conditioning"]["role"],
                "days": training_days,
                "focus": "Conditioning focus",
                "summary": f"Mainly for users who want physique change through better work capacity, sweat and session density.",
                "blocks": ["Intervals", "Machine circuit", "Carries", "Recovery walk"],
                "nutrition": "Use lighter fats pre-workout and keep protein high every day of the week.",
                "sessions": [
                    {"day": "Day 1", "title": "Intervals", "prescription": "30-40 min", "exercises": ["Bike intervals 12 x 20/40", "Push-up 3x15", "Bodyweight squat 3x20", "Plank 3x40 sec"]},
                    {"day": "Day 2", "title": "Machine circuit", "prescription": "5 stations / 35-45 min", "exercises": ["Leg press 15 reps", "Machine chest press 12 reps", "Seated row 12 reps", "Walking lunge 12 / leg", "Rower 250 m"]},
                    {"day": "Day 3", "title": "Carry and core", "prescription": "4 blocks / 35 min", "exercises": ["Farmer carry 6 x 20 m", "Sled push 6 x 20 m", "Cable chop 3x12 / side", "Incline walk 15 min"]},
                ],
            },
            {
                "title": "Upper body cut support",
                "coach_key": "strength",
                "coach_role": COACHES["strength"]["role"],
                "days": training_days,
                "focus": "Upper body focus",
                "summary": f"Keep upper-body muscle and strength signal high while bodyweight trends downward.",
                "blocks": ["Upper strength", "Conditioning", "Upper density", "Zone 2"],
                "nutrition": "Hold protein high, cluster carbs near the upper-body sessions and keep the deficit controlled.",
                "sessions": [
                    {"day": "Day 1", "title": "Upper strength", "prescription": "5 lifts / 55 min", "exercises": ["Bench press 4x5", "Pull-up or pulldown 4x8", "DB shoulder press 3x10", "Chest supported row 3x10", "EZ curl 3x12"]},
                    {"day": "Day 2", "title": "Upper density", "prescription": "5 lifts / 50 min", "exercises": ["Incline DB press 4x10", "Cable row 4x12", "Lateral raise 4x15", "Rope pressdown 3x12", "Hammer curl 3x12"]},
                    {"day": "Day 3", "title": "Conditioning support", "prescription": "3 blocks / 35-40 min", "exercises": ["Bike intervals 10 x 30/30", "Farmer carry 4 x 20 m", "Incline treadmill walk 15 min"]},
                ],
            },
        ]
    return options


def build_package_filters(suggestions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in suggestions:
        focus = str(item.get("focus") or "Coach flow")
        counts[focus] = counts.get(focus, 0) + 1
    filters = []
    for focus, count in counts.items():
        filters.append({"focus": focus, "count": count, "label": f"{focus} ({count})"})
    return filters


def build_active_package(assistant: dict[str, Any], workouts: list[dict[str, Any]], calendar: list[dict[str, Any]]) -> dict[str, Any]:
    suggestion = (assistant.get("suggestions") or [{}])[0]
    latest_work = workouts[0]["focus"] if workouts else "No logged session yet"
    next_calendar = calendar[0]["title"] if calendar else "Next block will be built from the selected package"
    return {
        "title": suggestion.get("title", "Coach package"),
        "focus": suggestion.get("focus", "Daily coaching"),
        "coach_role": suggestion.get("coach_role", assistant.get("coach_role", "Coach")),
        "summary": suggestion.get("summary", assistant.get("headline", "Coach-led package")),
        "days": suggestion.get("days", 4),
        "latest_work": latest_work,
        "next_calendar": next_calendar,
        "sessions": suggestion.get("sessions", []),
    }


def build_program_board(active_package: dict[str, Any]) -> list[dict[str, Any]]:
    board: list[dict[str, Any]] = []
    sessions = active_package.get("sessions", [])
    for idx, session in enumerate(sessions, start=1):
        board.append(
            {
                "day": session.get("day", f"Day {idx}"),
                "title": session.get("title", "Session"),
                "prescription": session.get("prescription", "Coach block"),
                "focus": active_package.get("focus", "Training focus"),
                "top_exercises": (session.get("exercises") or [])[:3],
            }
        )
    while len(board) < 5:
        extra_idx = len(board) + 1
        board.append(
            {
                "day": f"Day {extra_idx}",
                "title": "Recovery / prep",
                "prescription": "Steps, mobility, food prep, sleep target",
                "focus": "Recovery support",
                "top_exercises": ["Walk 20-30 min", "Mobility 10 min", "Prep next training day"],
            }
        )
    return board[:5]


def build_program_builder(active_package: dict[str, Any], periodization_engine: dict[str, Any]) -> list[dict[str, Any]]:
    base_sessions = active_package.get("sessions", []) or []
    if not base_sessions:
        return []
    week_labels = [
        ("Week 1", "Base quality", "Own clean reps and stable technique."),
        ("Week 2", "Volume push", "Add one quality set or one small load jump on key lifts."),
        ("Week 3", "Peak week", "Push the main pattern while keeping accessories efficient."),
        ("Week 4", "Deload / reset", "Keep the movement patterns, reduce fatigue and sharpen recovery."),
    ]
    builder: list[dict[str, Any]] = []
    for idx, (label, focus, call) in enumerate(week_labels, start=1):
        sample = base_sessions[(idx - 1) % len(base_sessions)]
        builder.append(
            {
                "week": label,
                "focus": focus,
                "coach_call": call,
                "session_title": sample.get("title", f"Session {idx}"),
                "session_prescription": sample.get("prescription", "Coach block"),
                "top_exercises": (sample.get("exercises") or [])[:4],
                "phase": periodization_engine.get("block_name", "Current block"),
            }
        )
    return builder


def build_workspace_hub(
    user: dict[str, Any],
    active_package: dict[str, Any],
    today_blueprint: dict[str, Any],
    access: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "title": "Train",
            "anchor": "#today-plan",
            "detail": today_blueprint.get("title", "Today's training"),
            "metric": today_blueprint.get("duration", "Ready"),
        },
        {
            "title": "Program",
            "anchor": "#plans",
            "detail": active_package.get("title", "Coach package"),
            "metric": f"{active_package.get('days', 4)} days",
        },
        {
            "title": "Fuel",
            "anchor": "#mission",
            "detail": "Meals, macros and timing for today.",
            "metric": access.get("status_label", "Active"),
        },
        {
            "title": "Coach",
            "anchor": "#assistant",
            "detail": f"{user.get('full_name', 'Athlete')} guidance and weekly adjustment.",
            "metric": active_package.get("focus", "Coach flow"),
        },
        {
            "title": "Track",
            "anchor": "#progress",
            "detail": "Recomposition, PRs and adherence.",
            "metric": user.get("goal", "Goal").title(),
        },
    ]


def build_operating_board(
    today_blueprint: dict[str, Any],
    active_package: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
    coach_briefing: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "title": "Current mission",
            "detail": today_blueprint.get("focus_line", "Follow today's plan."),
            "note": coach_briefing.get("next_step", "Stay on the next useful action."),
        },
        {
            "title": "Active package",
            "detail": active_package.get("title", "Coach package"),
            "note": active_package.get("focus", "Coach focus"),
        },
        {
            "title": "Nutrition next",
            "detail": nutrition_intelligence.get("next_meal_title", "Next meal block"),
            "note": nutrition_intelligence.get("next_meal_detail", "Keep fuel aligned."),
        },
    ]


def build_customer_delight(
    user: dict[str, Any],
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
    adaptive_training_engine: dict[str, Any],
    periodization_engine: dict[str, Any],
    coach_briefing: dict[str, Any],
    access: dict[str, Any],
) -> dict[str, Any]:
    exercise_total = int(today_progress.get("exercise_total", 0))
    meal_total = int(today_progress.get("meal_total", 0))
    completion = int(today_progress.get("completion_percent", 0))
    success_title = "Win today by finishing the written plan."
    success_detail = (
        f"Close {exercise_total} exercise blocks and {meal_total} food blocks."
        if today_blueprint.get("day_type") == "training"
        else "Keep recovery simple: move, eat clean and finish the check-in."
    )
    if completion >= 80:
        success_title = "Today is almost closed."
        success_detail = "Stay calm, finish the last useful block and protect recovery tonight."

    return {
        "headline": f"{user.get('full_name', 'Athlete')}, your day is already organized.",
        "subline": "Open one widget, follow the written flow, and let the app carry the decisions.",
        "cards": [
            {
                "kicker": "Success today",
                "title": success_title,
                "detail": success_detail,
                "tag": f"{completion}% complete",
            },
            {
                "kicker": "Why this plan fits",
                "title": adaptive_training_engine.get("readiness", "Stay on plan"),
                "detail": (
                    f"{periodization_engine.get('week_label', 'Current block')} - "
                    f"{periodization_engine.get('block_name', 'Coach block')}. "
                    f"{adaptive_training_engine.get('today_rule', 'Keep quality high.')}"
                ),
                "tag": periodization_engine.get("phase_signal", "On track"),
            },
            {
                "kicker": "Keep it simple",
                "title": coach_briefing.get("next_step", "Do the next useful thing."),
                "detail": (
                    f"Next meal: {nutrition_intelligence.get('next_meal_title', 'Meal block')}."
                    f" Access: {access.get('status_label', 'Active')}."
                ),
                "tag": today_blueprint.get("status_label", "Ready"),
            },
        ],
    }


def build_delight_board(
    user: dict[str, Any],
    today_blueprint: dict[str, Any],
    customer_delight: dict[str, Any],
    active_package: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
    access: dict[str, Any],
    single_next_action: dict[str, Any],
) -> dict[str, Any]:
    return {
        "headline": f"{user.get('full_name', 'Athlete')}, today's plan is ready.",
        "subline": "Start the workout, finish meals, and close the day clean.",
        "primary_cta": {"label": single_next_action.get("cta", "Open today"), "anchor": single_next_action.get("anchor", "#today-plan")},
        "secondary_cta": {"label": "Open workout mode", "anchor": "/workout-mode"},
        "cards": customer_delight.get("cards", []),
        "widgets": [
            {
                "title": "Today",
                "detail": today_blueprint.get("title", "Today's plan"),
                "metric": today_blueprint.get("duration", "Ready"),
                "anchor": "#today-plan",
            },
            {
                "title": "Program",
                "detail": active_package.get("title", "Coach package"),
                "metric": active_package.get("focus", "Coach flow"),
                "anchor": "#plans",
            },
            {
                "title": "Fuel",
                "detail": nutrition_intelligence.get("next_meal_title", "Next meal"),
                "metric": f"{nutrition_intelligence.get('protein_left', 0)}g protein left",
                "anchor": "#mission",
            },
            {
                "title": "Access",
                "detail": access.get("status_label", "Active"),
                "metric": access.get("recommended_tier", "pro").title(),
                "anchor": "#pricing",
            },
        ],
    }


def focus_hub_meta(hub_key: str) -> dict[str, str]:
    mapping = {
        "train": {
            "title": "Train hub",
            "heading": "Today's training room",
            "copy": "Open the room, see the exact order, then move straight into the live player.",
        },
        "program": {
            "title": "Program hub",
            "heading": "Coach packages and active plan",
            "copy": "See the block, the focus, and the sessions for this phase.",
        },
        "fuel": {
            "title": "Fuel hub",
            "heading": "Nutrition autopilot",
            "copy": "Meals, swaps and shopping are all in one place.",
        },
        "coach": {
            "title": "Coach hub",
            "heading": "AI trainer and coach squad",
            "copy": "Open this when you need guidance, adjustments or recovery coaching.",
        },
        "track": {
            "title": "Track hub",
            "heading": "Progress and body change",
            "copy": "Review body change, adherence and training quality.",
        },
        "profile": {
            "title": "Profile hub",
            "heading": "Body data and setup",
            "copy": "Only personal data, goal setup and athlete profile controls live here.",
        },
        "calendar": {
            "title": "Calendar hub",
            "heading": "Weekly layout and personal flow",
            "copy": "See your week by day without mixing it into the main home screen.",
        },
    }
    return mapping.get(hub_key, mapping["program"])


def build_meal_suggestions(goal: str, calories_target: int, protein_target: int) -> list[dict[str, Any]]:
    library = {
        "performance": [
            {"title": "Pre-lift power bowl", "time": "Breakfast", "details": "Oats, banana, whey and Greek yogurt for quick carbs and protein."},
            {"title": "Post-workout recovery plate", "time": "Lunch", "details": "Chicken, rice and fruit to reload glycogen and recovery."},
            {"title": "Evening performance dinner", "time": "Dinner", "details": "Salmon, potatoes and vegetables for recovery and micronutrients."},
        ],
        "muscle": [
            {"title": "Mass builder breakfast", "time": "Breakfast", "details": "Eggs, oats, peanut butter and yogurt for calorie-dense protein."},
            {"title": "Growth lunch", "time": "Lunch", "details": "Beef or chicken, rice and olive oil for a surplus without junk."},
            {"title": "Anabolic dinner", "time": "Dinner", "details": "Pasta with lean meat and parmesan plus a protein dessert."},
        ],
        "cut": [
            {"title": "Lean start meal", "time": "Breakfast", "details": "Egg whites, berries and yogurt to stay full with low calories."},
            {"title": "Deficit lunch", "time": "Lunch", "details": "Chicken salad, potatoes and fruit with high protein focus."},
            {"title": "Tight dinner", "time": "Dinner", "details": "White fish or turkey, vegetables and rice with precise portions."},
        ],
    }
    items = library.get(goal, library["performance"])
    items[0]["macro"] = f"{protein_target}g protein target"
    items[1]["macro"] = f"{calories_target} kcal structure"
    items[2]["macro"] = "Hydration + digestion friendly finish"
    return items


def build_nutrition_os(user: dict[str, Any], assistant: dict[str, Any], nutrition_intelligence: dict[str, Any]) -> dict[str, Any]:
    goal = str(user.get("goal") or "performance").lower()
    day_templates = {
        "performance": [
            ("Day 1", "Heavy training fuel", "Higher carbs before and after training.", ["Oats + whey", "Chicken rice bowl", "Fruit + yogurt", "Salmon + potatoes"]),
            ("Day 2", "Steady output", "Keep protein anchored and hydration high.", ["Eggs + toast", "Turkey wrap", "Skyr + berries", "Beef + rice"]),
            ("Day 3", "Recovery day", "Lower fats late, keep digestion easy.", ["Greek yogurt bowl", "Chicken salad", "Protein shake", "White fish + potatoes"]),
        ],
        "muscle": [
            ("Day 1", "Mass day", "Push surplus through clean high-protein meals.", ["Eggs + oats", "Beef + rice", "Bagel + whey", "Pasta + chicken"]),
            ("Day 2", "Growth support", "Keep calories high without junk food.", ["Yogurt + granola", "Chicken burrito bowl", "Rice cakes + PB", "Salmon + rice"]),
            ("Day 3", "Appetite management", "Use easy-to-eat dense meals.", ["Shake + oats", "Turkey pasta", "Fruit + yogurt", "Burger bowl"]),
        ],
        "cut": [
            ("Day 1", "Lean training day", "Cluster carbs around training and stay full.", ["Egg whites + oats", "Chicken + potatoes", "Skyr + berries", "White fish + rice"]),
            ("Day 2", "Deficit control", "Protein first and cleaner dinners.", ["Greek yogurt", "Lean beef salad", "Protein pudding", "Turkey + vegetables"]),
            ("Day 3", "Recovery nutrition", "Lower calories without lowering protein.", ["Egg whites", "Chicken soup", "Fruit + whey", "White fish + greens"]),
        ],
    }
    week = []
    for day, theme, rule, meals in day_templates.get(goal, day_templates["performance"]):
        week.append({"day": day, "theme": theme, "rule": rule, "meals": meals})
    return {
        "headline": "Nutrition OS",
        "next_meal": nutrition_intelligence.get("next_meal_title", "Next meal"),
        "protein_left": nutrition_intelligence.get("protein_left", 0),
        "calories_left": nutrition_intelligence.get("calories_left", 0),
        "weekly_plan": week,
        "prep_call": nutrition_intelligence.get("prep_steps", []),
        "targets": assistant.get("targets", {}),
    }


def build_nutrition_intelligence(
    user: dict[str, Any],
    assistant: dict[str, Any],
    meals: list[dict[str, Any]],
    today_blueprint: dict[str, Any],
) -> dict[str, Any]:
    today_key = date.today().isoformat()
    calories_eaten = sum(float(item["calories"]) for item in meals if str(item["logged_at"]).startswith(today_key))
    protein_eaten = sum(float(item["protein"]) for item in meals if str(item["logged_at"]).startswith(today_key))
    carbs_eaten = sum(float(item["carbs"]) for item in meals if str(item["logged_at"]).startswith(today_key))
    fats_eaten = sum(float(item["fats"]) for item in meals if str(item["logged_at"]).startswith(today_key))
    targets = assistant["targets"]
    next_meal = (today_blueprint.get("nutrition") or [{}])[0]
    for item in today_blueprint.get("nutrition") or []:
        if item.get("item_key"):
            next_meal = item
            break
    goal = str(user["goal"]).lower()
    swaps = {
        "performance": [
            "Rice -> potatoes when digestion is heavy.",
            "Chicken -> lean beef when you need more iron and fullness.",
            "Greek yogurt -> whey + fruit when you need faster digestion.",
        ],
        "muscle": [
            "Rice -> pasta when calories need to go up easier.",
            "Chicken -> salmon when fats are too low.",
            "Oats -> granola + yogurt when appetite is poor.",
        ],
        "cut": [
            "Rice -> potatoes for more fullness per calorie.",
            "Whole eggs -> egg whites when fats are too high.",
            "Beef -> white fish when you need a leaner dinner.",
        ],
    }
    prep = {
        "performance": ["Cook 2 carb sources", "Prep 2 lean proteins", "Keep electrolytes ready"],
        "muscle": ["Prep surplus lunch boxes", "Keep protein snacks visible", "Pre-log dinner calories"],
        "cut": ["Prep low-calorie proteins", "Wash vegetables ahead", "Lock dinner portions early"],
    }
    return {
        "headline": "Nutrition autopilot",
        "day_type": today_blueprint.get("day_type", "training"),
        "calories_left": max(int(targets["calories"] - calories_eaten), 0),
        "protein_left": max(int(targets["protein"] - protein_eaten), 0),
        "carbs_left": max(int(targets["carbs"] - carbs_eaten), 0),
        "fats_left": max(int(targets["fats"] - fats_eaten), 0),
        "next_meal_title": next_meal.get("title", "Next meal"),
        "next_meal_detail": next_meal.get("meal", "Open nutrition mode for the next block."),
        "next_meal_purpose": next_meal.get("purpose", "Stay aligned with today's goal."),
        "smart_swaps": swaps.get(goal, swaps["performance"]),
        "prep_steps": prep.get(goal, prep["performance"]),
    }


def build_adaptive_training_engine(
    user: dict[str, Any],
    today_blueprint: dict[str, Any],
    workouts: list[dict[str, Any]],
    exercises: list[dict[str, Any]],
    checkins: list[dict[str, Any]],
) -> dict[str, Any]:
    latest_checkin = checkins[0] if checkins else None
    energy = int(latest_checkin["energy_score"]) if latest_checkin else 7
    soreness = int(latest_checkin["soreness_score"]) if latest_checkin else 4
    fatigue = str(user.get("fatigue_state", "steady")).lower()
    readiness_label = "Push"
    if energy <= 5 or soreness >= 7 or fatigue in {"high", "drained"}:
        readiness_label = "Pull back"
    elif energy >= 8 and soreness <= 4:
        readiness_label = "Push progression"

    recent_focus = workouts[0]["focus"] if workouts else "No prior log"
    substitutions = []
    equipment = str(user.get("equipment_access", "full gym")).lower()
    if equipment == "home":
        substitutions.extend(["Barbell work -> dumbbell equivalent", "Cable work -> band equivalent"])
    if fatigue in {"high", "drained"}:
        substitutions.append("Drop the final accessory if form quality falls.")
    if soreness >= 7:
        substitutions.append("Use the first warm-up block to decide if the main lift should stay or switch.")
    if not substitutions:
        substitutions.append("Keep the written order and only progress if execution stays clean.")

    next_week = (
        "Add load to the first main lift and keep the rest of the structure stable."
        if readiness_label == "Push progression"
        else "Hold top-set load steady and improve execution quality before adding more."
        if readiness_label == "Push"
        else "Reduce one accessory block and bias recovery until readiness improves."
    )
    volume_anchor = sum(float(item.get("weight_kg", 0) or 0) * int(item.get("sets_count", 0) or 0) for item in exercises[:8])
    return {
        "headline": "Adaptive training engine",
        "readiness": readiness_label,
        "today_rule": (
            "Run the day exactly as written."
            if readiness_label == "Push progression"
            else "Keep 1-2 reps in reserve and prioritize clean reps."
            if readiness_label == "Push"
            else "Shorten the session, reduce load or stop one block early."
        ),
        "recent_focus": recent_focus,
        "volume_anchor": f"{int(volume_anchor)} logged load" if volume_anchor else "No volume anchor yet",
        "substitutions": substitutions,
        "next_week": next_week,
        "session_order": [
            f"{item['order']}. {item['name']} - {item['sets']}x{item['reps']} - rest {item['rest']}"
            for item in (today_blueprint.get("exercises") or [])[:5]
        ] if today_blueprint.get("day_type") == "training" else today_blueprint.get("rest_day_actions", []),
    }


def build_progress_system(
    user: dict[str, Any],
    metrics: list[dict[str, Any]],
    workouts: list[dict[str, Any]],
    photos: list[dict[str, Any]],
    checkins: list[dict[str, Any]],
    stats: dict[str, Any],
) -> dict[str, Any]:
    latest = metrics[0] if metrics else None
    previous = metrics[1] if len(metrics) > 1 else None
    body_weight_delta = round(float(latest["body_weight"]) - float(previous["body_weight"]), 1) if latest and previous else 0.0
    waist_delta = round(float(latest["waist"]) - float(previous["waist"]), 1) if latest and previous else 0.0
    adherence = min(100, max(35, len(workouts[:7]) * 16 + len(checkins[:7]) * 6))
    photo_score = int(photos[0]["visual_score"]) if photos else 7
    recomposition_score = min(100, max(40, int(stats["pr_count"] * 9 + adherence * 0.45 + photo_score * 2)))
    wins = []
    if body_weight_delta:
        wins.append(f"Scale trend: {body_weight_delta:+.1f} kg")
    if waist_delta:
        wins.append(f"Waist trend: {waist_delta:+.1f} cm")
    wins.append(f"Weekly sessions: {stats['weekly_sessions']}")
    wins.append(f"PR-quality sessions: {stats['pr_count']}")
    watchouts = []
    if adherence < 70:
        watchouts.append("Adherence is the first fix before changing the whole plan.")
    if latest and float(latest["sleep_hours"]) < 7:
        watchouts.append("Sleep is dragging recovery and probably performance too.")
    if checkins and sum(int(item["energy_score"]) for item in checkins[:3]) / min(len(checkins[:3]), 3) < 6:
        watchouts.append("Energy trend is soft - reduce junk fatigue and tighten meals.")
    if not watchouts:
        watchouts.append("Current trend is stable - keep execution high and log everything.")
    return {
        "headline": "Progress operating system",
        "recomposition_score": recomposition_score,
        "adherence_score": adherence,
        "body_weight_delta": f"{body_weight_delta:+.1f} kg",
        "waist_delta": f"{waist_delta:+.1f} cm",
        "wins": wins,
        "watchouts": watchouts,
        "next_checkpoint": "Add a body metric and a progress photo this week so the trend engine gets sharper.",
    }


def build_transformation_dashboard(
    progress_system: dict[str, Any],
    recomposition_dashboard: dict[str, Any],
    progress_trends: list[dict[str, Any]],
    weekly_review: dict[str, Any],
) -> dict[str, Any]:
    headline_tiles = [
        {"label": "Recomp score", "value": progress_system.get("recomposition_score", 0), "detail": "How body change and training quality currently align."},
        {"label": "Adherence", "value": f"{progress_system.get('adherence_score', 0)}%", "detail": "This is the biggest predictor of change."},
        {"label": "Weekly review", "value": f"{weekly_review.get('score', 0)}/100", "detail": weekly_review.get("headline", "Weekly coaching score.")},
    ]
    checkpoints = [
        progress_system.get("next_checkpoint", "Log one more clean week."),
        weekly_review.get("next_week_adjustment", "Hold the plan steady next week."),
        recomposition_dashboard.get("coach_call", "Keep execution high and track honestly."),
    ]
    return {
        "headline": "Transformation dashboard",
        "tiles": headline_tiles,
        "trends": progress_trends[:4],
        "checkpoints": checkpoints,
        "wins": progress_system.get("wins", []),
        "watchouts": progress_system.get("watchouts", []),
    }


def build_periodization_engine(
    user: dict[str, Any],
    workouts: list[dict[str, Any]],
    checkins: list[dict[str, Any]],
    today_blueprint: dict[str, Any],
) -> dict[str, Any]:
    goal = str(user["goal"]).lower()
    sessions = len(workouts[:12])
    avg_energy = round(sum(int(item["energy_score"]) for item in checkins[:5]) / len(checkins[:5]), 1) if checkins[:5] else 7.0
    mesocycle_week = (sessions % 4) + 1 if sessions else 1
    phase_map = {
        "performance": ["Base output", "Strength build", "Intensification", "Deload / speed reset"],
        "muscle": ["Volume base", "Hypertrophy push", "Overreach pump", "Deload / resensitize"],
        "cut": ["Deficit base", "Density push", "Conditioning bias", "Deload / fatigue clean-up"],
    }
    phase_name = phase_map.get(goal, phase_map["performance"])[mesocycle_week - 1]
    if avg_energy <= 5.5:
        phase_signal = "Recovery bias"
        coach_call = "Keep the phase objective but lower junk volume and reduce one accessory block."
    elif avg_energy >= 8:
        phase_signal = "Push progression"
        coach_call = "You can push load or density this week without changing the main structure."
    else:
        phase_signal = "Hold structure"
        coach_call = "Stay on plan and earn progression through execution quality."
    week_focus = (
        "Own top sets and bar speed."
        if goal == "performance"
        else "Drive quality volume and recover well."
        if goal == "muscle"
        else "Keep output high while preserving muscle."
    )
    return {
        "headline": "Periodization engine",
        "block_name": phase_name,
        "week_label": f"Week {mesocycle_week} / 4",
        "phase_signal": phase_signal,
        "coach_call": coach_call,
        "week_focus": week_focus,
        "today_fit": f"Today's session fits the {phase_name.lower()} block: {today_blueprint.get('title', 'Training day')}.",
        "up_next": phase_map.get(goal, phase_map["performance"])[mesocycle_week % 4],
    }


def build_recomposition_dashboard(
    metrics: list[dict[str, Any]],
    photos: list[dict[str, Any]],
    pr_tracker: list[dict[str, Any]],
    progress_system: dict[str, Any],
) -> dict[str, Any]:
    latest = metrics[0] if metrics else None
    body_fat = f"{float(latest['body_fat']):.1f}%" if latest and latest.get("body_fat") is not None else "No body-fat trend"
    form_score = f"{int(latest['form_score'])}/10" if latest else "No form check"
    photo_score = f"{int(photos[0]['visual_score'])}/10" if photos else "No photo score"
    top_pr = pr_tracker[0]["exercise_name"] if pr_tracker else "No PR yet"
    return {
        "headline": "Recomposition dashboard",
        "tiles": [
            {"label": "Recomp score", "value": f"{progress_system['recomposition_score']}/100", "detail": "Single body-change score from training, adherence and physique inputs."},
            {"label": "Body-fat trend", "value": body_fat, "detail": "Keep this moving in the right direction, not fast direction."},
            {"label": "Visual score", "value": photo_score, "detail": "Latest physique check quality and visual consistency."},
            {"label": "Top lift", "value": top_pr, "detail": "Best current PR anchor in your recent logbook."},
            {"label": "Form score", "value": form_score, "detail": "How sharp the physique and recovery checks look."},
            {"label": "Waist delta", "value": progress_system["waist_delta"], "detail": "One of the cleanest signals for recomposition."},
        ]
    }


def build_session_analytics(
    today_blueprint: dict[str, Any],
    exercise_logs: list[dict[str, Any]],
    completed_today: set[str] | list[str],
) -> dict[str, Any]:
    completed = set(completed_today)
    exercises = today_blueprint.get("exercises") or []
    total_sets = sum(clamp_int(item.get("sets"), 3, 1, 12) for item in exercises)
    total_reps = sum(clamp_int(str(item.get("reps", "8")).split("-")[0].split("/")[0], 8, 1, 30) * clamp_int(item.get("sets"), 3, 1, 12) for item in exercises)
    completed_exercises = sum(1 for item in exercises if item["item_key"] in completed)
    completion_score = int(round((completed_exercises / len(exercises)) * 100)) if exercises else 0
    avg_rpe = 0.0
    if exercise_logs[:5]:
        avg_rpe = round(sum(float(item.get("rpe", 8) or 8) for item in exercise_logs[:5]) / len(exercise_logs[:5]), 1)
    estimated_calories = max(120, len(exercises) * 70 + total_sets * 6)
    tonnage = int(sum(float(item.get("weight_kg", 0) or 0) * clamp_int(item.get("sets"), 3, 1, 12) for item in exercises))
    return {
        "headline": "Session analytics",
        "tiles": [
            {"label": "Session score", "value": f"{completion_score}%", "detail": "How much of today's written plan is already closed."},
            {"label": "Total sets", "value": str(total_sets), "detail": "Useful for managing weekly volume and fatigue."},
            {"label": "Estimated reps", "value": str(total_reps), "detail": "Approximate work count from today's prescription."},
            {"label": "Estimated kcal", "value": str(estimated_calories), "detail": "Session energy cost estimate, not a lab number."},
            {"label": "Logged RPE", "value": f"{avg_rpe}/10" if avg_rpe else "No log yet", "detail": "Average recent effort on your logged working sets."},
            {"label": "Tonnage", "value": f"{tonnage} kg" if tonnage else "Bodyweight / no load", "detail": "Approximate session load from prescribed working sets."},
        ],
        "coach_note": "Use this after the session to decide whether next time should progress, hold or deload slightly.",
    }


def exercise_mastery_profile(exercise_name: str) -> dict[str, Any]:
    name = exercise_name.lower()
    library = {
        "bench": {
            "setup": "Feet planted, upper back tight, eyes under the bar before every rep.",
            "execution": "Lower with control to the same touch point, press back and up, keep wrists stacked.",
            "mistake": "Do not let elbows flare early or lose leg drive off the chest.",
            "swap": "If shoulder stress rises, switch to dumbbell press or machine press for this block.",
        },
        "squat": {
            "setup": "Brace before you unlock the bar, feet stable and ribs stacked over pelvis.",
            "execution": "Sit between the hips, keep pressure through mid-foot, drive up with chest and hips together.",
            "mistake": "Avoid losing brace at the bottom or shifting hard onto the toes.",
            "swap": "Use front squat or hack squat if mobility or back fatigue limits quality depth.",
        },
        "deadlift": {
            "setup": "Bar over mid-foot, lats on, pull slack out before the floor leaves.",
            "execution": "Push the floor away, keep bar close, lock out with glutes instead of leaning back.",
            "mistake": "Do not yank from a loose start or let the bar drift from the body.",
            "swap": "Use Romanian deadlift or trap-bar deadlift when recovery or setup quality is lower.",
        },
        "row": {
            "setup": "Chest proud, brace trunk, set shoulder blades before the pull starts.",
            "execution": "Drive elbows toward hips, pause briefly, lower under control.",
            "mistake": "Avoid turning every row into body English or shrugging through the pull.",
            "swap": "Use chest-supported row when lower-back fatigue is high.",
        },
        "pull": {
            "setup": "Start from a dead hang or clean stretch with ribs down and glutes tight.",
            "execution": "Lead with elbows, bring chest toward handle or bar, control the negative fully.",
            "mistake": "Do not crank the neck forward or shorten the range to chase reps.",
            "swap": "Use assisted pull-ups or pulldown variations to keep full range.",
        },
        "press": {
            "setup": "Squeeze glutes, brace abs, stack wrist-elbow under the load.",
            "execution": "Press in a straight path, finish with biceps by ears, lower smoothly.",
            "mistake": "Do not overarch the low back or lose a stable rib position.",
            "swap": "Use seated dumbbell press or machine shoulder press if stability is the limiter.",
        },
        "curl": {
            "setup": "Keep elbows quiet and torso still before the first rep.",
            "execution": "Curl through full range, squeeze the top, lower slowly.",
            "mistake": "Avoid swinging hips or cutting the eccentric short.",
            "swap": "Cable curls work well when you want constant tension without cheating.",
        },
        "triceps": {
            "setup": "Set shoulders down and lock elbows close to the body.",
            "execution": "Extend fully, pause, return without shoulders rolling forward.",
            "mistake": "Do not turn the movement into a shoulder swing.",
            "swap": "Cable pressdowns are the cleanest option when elbows are sensitive.",
        },
        "lunge": {
            "setup": "Stay tall, brace lightly and own balance before every step.",
            "execution": "Drop straight down, front foot rooted, push back through full foot.",
            "mistake": "Avoid crashing the knee forward or losing pelvic control.",
            "swap": "Split squats are easier to load consistently if balance is limiting output.",
        },
    }
    profile = next((data for key, data in library.items() if key in name), None)
    if profile:
        return profile
    return {
        "setup": "Set posture first, brace the trunk and make the start position identical every set.",
        "execution": "Control the eccentric, own the target range, then finish the rep cleanly.",
        "mistake": "Do not chase speed or load if joint position breaks down.",
        "swap": "Swap to a more stable machine or dumbbell pattern if quality drops.",
    }


def machine_profile(exercise_name: str) -> dict[str, str]:
    name = exercise_name.lower()
    if any(key in name for key in ["squat", "leg press", "split squat", "lunge", "hack squat"]):
        return {"label": "Rack / leg station", "icon": "rack", "focus": "Lower body station"}
    if any(key in name for key in ["bench", "press", "chest", "push-up", "floor press"]):
        return {"label": "Bench / chest press", "icon": "bench", "focus": "Pressing station"}
    if any(key in name for key in ["row", "pulldown", "pull-up", "pull", "lat"]):
        return {"label": "Cable / pull station", "icon": "cable", "focus": "Back station"}
    if any(key in name for key in ["deadlift", "hinge", "romanian"]):
        return {"label": "Barbell platform", "icon": "barbell", "focus": "Hinge station"}
    if any(key in name for key in ["carry", "bike", "rower", "interval", "sled"]):
        return {"label": "Conditioning lane", "icon": "conditioning", "focus": "Engine station"}
    if any(key in name for key in ["curl", "triceps", "lateral", "shoulder", "raise"]):
        return {"label": "Cable / dumbbell bay", "icon": "dumbbell", "focus": "Arms and delts"}
    return {"label": "Free-weight station", "icon": "dumbbell", "focus": "General training station"}


def machine_image_uri(icon: str, label: str) -> str:
    templates = {
        "rack": """
            <svg xmlns='http://www.w3.org/2000/svg' width='320' height='220' viewBox='0 0 320 220'>
              <rect width='320' height='220' rx='28' fill='#161616'/>
              <rect x='38' y='28' width='16' height='150' rx='8' fill='#ff8b39'/>
              <rect x='266' y='28' width='16' height='150' rx='8' fill='#ff8b39'/>
              <rect x='54' y='42' width='212' height='10' rx='5' fill='#f4e9d7'/>
              <rect x='90' y='96' width='140' height='12' rx='6' fill='#ffc14d'/>
              <circle cx='75' cy='102' r='18' fill='#2b2b2b'/><circle cx='245' cy='102' r='18' fill='#2b2b2b'/>
              <rect x='120' y='150' width='80' height='14' rx='7' fill='#f4e9d7'/>
              <text x='24' y='204' font-size='20' fill='#f7efdf' font-family='Arial'>__LABEL__</text>
            </svg>
        """,
        "bench": """
            <svg xmlns='http://www.w3.org/2000/svg' width='320' height='220' viewBox='0 0 320 220'>
              <rect width='320' height='220' rx='28' fill='#161616'/>
              <rect x='74' y='114' width='140' height='18' rx='9' fill='#ffc14d'/>
              <rect x='98' y='84' width='92' height='18' rx='9' fill='#f4e9d7'/>
              <rect x='92' y='132' width='10' height='42' rx='5' fill='#ff8b39'/>
              <rect x='190' y='132' width='10' height='42' rx='5' fill='#ff8b39'/>
              <rect x='228' y='48' width='12' height='126' rx='6' fill='#f4e9d7'/>
              <rect x='70' y='58' width='180' height='10' rx='5' fill='#f4e9d7'/>
              <circle cx='70' cy='63' r='18' fill='#2b2b2b'/><circle cx='250' cy='63' r='18' fill='#2b2b2b'/>
              <text x='24' y='204' font-size='20' fill='#f7efdf' font-family='Arial'>__LABEL__</text>
            </svg>
        """,
        "cable": """
            <svg xmlns='http://www.w3.org/2000/svg' width='320' height='220' viewBox='0 0 320 220'>
              <rect width='320' height='220' rx='28' fill='#161616'/>
              <rect x='66' y='32' width='16' height='148' rx='8' fill='#f4e9d7'/>
              <rect x='238' y='32' width='16' height='148' rx='8' fill='#f4e9d7'/>
              <rect x='82' y='44' width='156' height='12' rx='6' fill='#ff8b39'/>
              <rect x='148' y='62' width='24' height='92' rx='12' fill='#2b2b2b'/>
              <line x1='160' y1='56' x2='118' y2='110' stroke='#ffc14d' stroke-width='6'/>
              <line x1='160' y1='56' x2='202' y2='110' stroke='#ffc14d' stroke-width='6'/>
              <circle cx='116' cy='112' r='8' fill='#ffc14d'/><circle cx='204' cy='112' r='8' fill='#ffc14d'/>
              <text x='24' y='204' font-size='20' fill='#f7efdf' font-family='Arial'>__LABEL__</text>
            </svg>
        """,
        "barbell": """
            <svg xmlns='http://www.w3.org/2000/svg' width='320' height='220' viewBox='0 0 320 220'>
              <rect width='320' height='220' rx='28' fill='#161616'/>
              <rect x='40' y='102' width='240' height='12' rx='6' fill='#f4e9d7'/>
              <rect x='46' y='86' width='10' height='44' rx='5' fill='#ff8b39'/>
              <rect x='264' y='86' width='10' height='44' rx='5' fill='#ff8b39'/>
              <circle cx='64' cy='108' r='22' fill='#2b2b2b'/><circle cx='96' cy='108' r='16' fill='#2b2b2b'/>
              <circle cx='256' cy='108' r='22' fill='#2b2b2b'/><circle cx='224' cy='108' r='16' fill='#2b2b2b'/>
              <rect x='136' y='136' width='48' height='14' rx='7' fill='#ffc14d'/>
              <text x='24' y='204' font-size='20' fill='#f7efdf' font-family='Arial'>__LABEL__</text>
            </svg>
        """,
        "conditioning": """
            <svg xmlns='http://www.w3.org/2000/svg' width='320' height='220' viewBox='0 0 320 220'>
              <rect width='320' height='220' rx='28' fill='#161616'/>
              <rect x='62' y='126' width='132' height='22' rx='11' fill='#ff8b39'/>
              <rect x='174' y='86' width='24' height='40' rx='12' fill='#ffc14d'/>
              <rect x='204' y='68' width='18' height='58' rx='9' fill='#f4e9d7'/>
              <rect x='232' y='54' width='14' height='72' rx='7' fill='#f4e9d7'/>
              <circle cx='88' cy='154' r='18' fill='#2b2b2b'/><circle cx='168' cy='154' r='18' fill='#2b2b2b'/>
              <path d='M56 92 C100 46, 160 46, 206 92' stroke='#f4e9d7' stroke-width='8' fill='none'/>
              <text x='24' y='204' font-size='20' fill='#f7efdf' font-family='Arial'>__LABEL__</text>
            </svg>
        """,
        "dumbbell": """
            <svg xmlns='http://www.w3.org/2000/svg' width='320' height='220' viewBox='0 0 320 220'>
              <rect width='320' height='220' rx='28' fill='#161616'/>
              <rect x='96' y='100' width='128' height='20' rx='10' fill='#f4e9d7'/>
              <rect x='74' y='86' width='20' height='48' rx='10' fill='#ff8b39'/>
              <rect x='52' y='80' width='18' height='60' rx='9' fill='#ffc14d'/>
              <rect x='226' y='86' width='20' height='48' rx='10' fill='#ff8b39'/>
              <rect x='250' y='80' width='18' height='60' rx='9' fill='#ffc14d'/>
              <text x='24' y='204' font-size='20' fill='#f7efdf' font-family='Arial'>__LABEL__</text>
            </svg>
        """,
    }
    svg = templates.get(icon, templates["dumbbell"]).replace("__LABEL__", label[:22])
    return "data:image/svg+xml;utf8," + quote(" ".join(svg.split()))


def build_daily_tasks(today_blueprint: dict[str, Any], today_progress: dict[str, Any], access: dict[str, Any]) -> list[dict[str, str]]:
    tasks = [
        {
            "title": "Open workout player",
            "detail": today_blueprint.get("title", "Today's workout"),
            "state": "Ready" if today_blueprint.get("day_type") == "training" else "Recovery",
        },
        {
            "title": "Close nutrition blocks",
            "detail": f"{max(int(today_progress.get('meal_total', 0)) - int(today_progress.get('meal_done', 0)), 0)} meals still open today.",
            "state": "Nutrition",
        },
        {
            "title": "Log the day",
            "detail": "Finish the check-in and keep the coach data clean for tomorrow.",
            "state": access.get("status_label", "Active"),
        },
    ]
    if today_blueprint.get("day_type") != "training":
        tasks[0] = {
            "title": "Run recovery flow",
            "detail": "Walk, mobility and low-stress output are enough today.",
            "state": "Recovery",
        }
    return tasks


def build_exercise_mastery(today_blueprint: dict[str, Any]) -> list[dict[str, Any]]:
    if today_blueprint.get("day_type") != "training":
        return [
            {
                "name": "Recovery technique",
                "setup": "Use today to rehearse movement quality, mobility and breathing.",
                "execution": "Walk, mobilize and keep intensity low enough to finish fresher than you started.",
                "mistake": "Do not turn a recovery day into a hidden training day.",
                "swap": "Use incline walk, bike or mobility flow if joints feel loaded.",
            }
        ]
    cards: list[dict[str, Any]] = []
    for item in today_blueprint.get("exercises", [])[:4]:
        profile = exercise_mastery_profile(str(item.get("name", "")))
        cards.append(
            {
                "name": item.get("name", "Exercise"),
                "setup": profile["setup"],
                "execution": profile["execution"],
                "mistake": profile["mistake"],
                "swap": profile["swap"],
            }
        )
    return cards


def build_recomp_home(progress_system: dict[str, Any], recomposition_dashboard: dict[str, Any]) -> dict[str, Any]:
    top_tiles = recomposition_dashboard.get("tiles", [])[:3]
    checkpoint = progress_system.get("next_checkpoint", "Add one more quality week before making big changes.")
    return {
        "headline": "Body recomposition home",
        "cards": top_tiles,
        "checkpoint": checkpoint,
    }


def build_weekly_adaptive_block_plan(
    periodization_engine: dict[str, Any],
    adaptive_training_engine: dict[str, Any],
    weekly_review: dict[str, Any],
    progress_system: dict[str, Any],
) -> dict[str, Any]:
    score = weekly_review.get("score", 70)
    if score >= 85 and progress_system.get("adherence_score", 70) >= 80:
        mode = "Push next week"
        changes = [
            "Add one top-set load jump on the main lift.",
            "Keep accessories the same but tighten execution quality.",
            "Keep recovery habits stable so progression sticks.",
        ]
    elif score <= 60:
        mode = "Recovery bias"
        changes = [
            "Trim one accessory block from lower-value work.",
            "Keep compounds but stop 1 rep earlier on hard sets.",
            "Prioritize sleep, steps and meal consistency before adding load.",
        ]
    else:
        mode = "Hold and earn"
        changes = [
            "Repeat the current split and beat execution, not chaos.",
            "Progress one or two lifts only if bar speed and form stay clean.",
            "Use the same meal structure and push adherence above 85%.",
        ]
    return {
        "headline": "Weekly adaptive block",
        "mode": mode,
        "week_label": periodization_engine.get("week_label", "Week plan"),
        "focus": periodization_engine.get("week_focus", adaptive_training_engine.get("today_rule", "Stay on structure.")),
        "changes": changes,
        "coach_call": weekly_review.get("next_week_adjustment", periodization_engine.get("coach_call", "Stay on plan.")),
    }


def build_voice_coach_payload(today_blueprint: dict[str, Any], live_session: dict[str, Any]) -> dict[str, Any]:
    session_type = "training" if today_blueprint.get("day_type") == "training" else "recovery"
    return {
        "headline": "Voice coach",
        "mode_label": "Voice cues ready",
        "auto_enabled": True,
        "session_type": session_type,
        "opening": f"{today_blueprint.get('coach_name', 'Coach')} will call the next move, rest cue and execution focus.",
        "fallback": "Voice cues are optional. If your device blocks audio, keep using the visual player.",
    }


def goal_training_days(user: dict[str, Any]) -> int:
    base = 4
    if str(user["goal"]).lower() == "cut":
        base = 5
    if float(user["weight_kg"]) >= 95:
        base = max(4, base - 1)
    if str(user.get("gender", "male")).lower() == "female" and str(user["goal"]).lower() == "muscle":
        base = max(base, 5)
    if str(user.get("fatigue_state", "steady")).lower() in {"high", "drained"}:
        base = max(3, base - 1)
    if str(user.get("equipment_access", "full gym")).lower() == "home":
        base = max(3, base)
    if str(user.get("gender", "male")).lower() == "female" and str(user.get("cycle_phase", "neutral")).lower() in {"recovery", "late_cycle"}:
        base = max(3, base - 1)
    return base


def build_athlete_scores(workouts: list[dict[str, Any]], metrics: list[dict[str, Any]], meals: list[dict[str, Any]]) -> dict[str, Any]:
    latest_metric = metrics[0] if metrics else None
    form_score = int(latest_metric["form_score"]) if latest_metric else 7
    sleep_score = min(10, round(float(latest_metric["sleep_hours"])) if latest_metric else 7)
    training_score = min(10, max(5, len(workouts[:6]) + 4))
    nutrition_score = min(10, max(5, round(sum(float(meal["protein"]) for meal in meals[:5]) / 35) if meals else 6))
    recovery_score = round((form_score + sleep_score + nutrition_score) / 3, 1)
    transformation_score = round((training_score + nutrition_score + form_score) / 3, 1)
    consistency_score = min(100, max(42, len(workouts) * 8 + len(metrics) * 6))
    return {
        "recovery_score": recovery_score,
        "transformation_score": transformation_score,
        "consistency_score": consistency_score,
        "sleep_score": sleep_score,
        "nutrition_score": nutrition_score,
        "training_score": training_score,
    }


def build_daily_mission(user: dict[str, Any], assistant: dict[str, Any], stats: dict[str, Any]) -> list[str]:
    goal = str(user["goal"]).lower()
    mission = [
        f"Hit {assistant['targets']['protein']}g protein before the end of the day.",
        f"Protect recovery score with 8h sleep focus and smart hydration.",
    ]
    if goal == "muscle":
        mission.insert(0, "Choose the highest-quality hypertrophy plan and push execution, not junk fatigue.")
    elif goal == "cut":
        mission.insert(0, "Stay in a clean deficit while keeping strength sessions sharp.")
    else:
        mission.insert(0, "Train for performance today and keep first working sets explosive.")
    if stats.get("latest_metric"):
        mission.append(f"Current body weight check-in is {stats['latest_metric']['body_weight']} kg, so keep portions aligned.")
    return mission


def build_achievements(stats: dict[str, Any], workouts: list[dict[str, Any]], metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = [
        {
            "title": "Consistency engine",
            "value": f"{max(7, len(workouts) * 4)} day streak",
            "detail": "Training entries are building a visible weekly rhythm.",
        },
        {
            "title": "Recovery control",
            "value": f"{stats['pr_count']} high-output sessions",
            "detail": "Quality sessions are staying high without losing structure.",
        },
    ]
    if metrics:
        items.append(
            {
                "title": "Physique tracking",
                "value": f"{metrics[0]['form_score']}/10 form score",
                "detail": "Body check-ins are staying active and useful for adjustments.",
            }
        )
    else:
        items.append(
            {
                "title": "First milestone",
                "value": "Add your first body check-in",
                "detail": "Once metrics start coming in, the assistant gets smarter.",
            }
        )
    return items


def build_weekly_planner(user: dict[str, Any], calendar: list[dict[str, Any]], assistant: dict[str, Any]) -> list[dict[str, Any]]:
    existing = {item["event_date"]: item for item in calendar}
    coach_name = assistant["coach_name"]
    fallback_titles = {
        "performance": "Performance session",
        "muscle": "Growth session",
        "cut": "Conditioning session",
    }
    planner = []
    for offset in range(7):
        day = date.today() + timedelta(days=offset)
        day_key = day.isoformat()
        item = existing.get(day_key)
        if item:
            planner.append(
                {
                    "day_label": day.strftime("%a"),
                    "date": day_key,
                    "title": item["title"],
                    "type": item["event_type"],
                    "details": item["details"],
                }
            )
            continue
        planner.append(
            {
                "day_label": day.strftime("%a"),
                "date": day_key,
                "title": fallback_titles.get(str(user["goal"]).lower(), "Training day"),
                "type": "adaptive",
                "details": f"{coach_name} keeps this day open for your selected plan and recovery state.",
            }
        )
    return planner


def build_pr_tracker(exercises: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prs: dict[str, dict[str, Any]] = {}
    for item in exercises:
        name = str(item["exercise_name"])
        load = float(item["weight_kg"])
        current = prs.get(name)
        if not current or load > current["weight_kg"]:
            prs[name] = {
                "exercise_name": name,
                "weight_kg": load,
                "reps_text": item["reps_text"],
                "logged_at": item["logged_at"],
                "category": item["category"],
            }
    ranked = sorted(prs.values(), key=lambda row: row["weight_kg"], reverse=True)
    return ranked[:6]


def build_wellness_panel(user: dict[str, Any], scores: dict[str, Any]) -> dict[str, Any]:
    gender = str(user.get("gender", "male")).lower()
    cycle_phase = str(user.get("cycle_phase", "neutral")).lower()
    fatigue = str(user.get("fatigue_state", "steady")).lower()

    if gender != "female":
        return {
            "title": "Recovery advisory",
            "tone": "Use fatigue and recovery score to auto-regulate volume and intensity.",
            "points": [
                f"Current fatigue state is {fatigue}.",
                f"Recovery score is {scores['recovery_score']}/10.",
                "Keep hydration, sleep and lower-stress accessories aligned with the current week.",
            ],
        }

    phase_guidance = {
        "neutral": "Balanced phase, normal progression and standard recovery.",
        "performance": "Performance phase, push quality work and harder top sets if readiness is good.",
        "recovery": "Recovery phase, reduce junk fatigue and protect sleep, iron intake and mobility.",
        "late_cycle": "Late cycle, keep execution sharp while lowering unnecessary stress.",
    }
    return {
        "title": "Female wellness panel",
        "tone": phase_guidance.get(cycle_phase, phase_guidance["neutral"]),
        "points": [
            f"Cycle mode is {cycle_phase}.",
            f"Fatigue state is {fatigue} and recovery score is {scores['recovery_score']}/10.",
            "Use this panel to bias recovery, food quality and session density before intensity.",
        ],
    }


def build_today_blueprint(
    user: dict[str, Any],
    assistant: dict[str, Any],
    workouts: list[dict[str, Any]],
    calendar: list[dict[str, Any]],
) -> dict[str, Any]:
    goal = str(user["goal"]).lower()
    gender = str(user.get("gender", "male")).lower()
    fatigue = str(user.get("fatigue_state", "steady")).lower()
    equipment = str(user.get("equipment_access", "full gym")).lower()
    today_key = date.today().isoformat()
    today_event = next((item for item in calendar if item["event_date"] == today_key), None)

    training_slots = [0, 1, 3, 4, 5][: goal_training_days(user)]
    is_training_day = date.today().weekday() in training_slots
    if today_event and today_event.get("event_type") in {"recovery", "nutrition", "checkin"}:
        is_training_day = False
    if today_event and today_event.get("event_type") == "training":
        is_training_day = True

    exercise_library = {
        "performance": [
            {"name": "Back squat", "sets": "5", "reps": "5", "rest": "150 sec", "block": "Primary strength", "duration": "18 min", "note": "Explosive first rep and clean bracing."},
            {"name": "Bench press", "sets": "4", "reps": "6", "rest": "120 sec", "block": "Secondary strength", "duration": "14 min", "note": "Own the pause and smooth bar speed."},
            {"name": "Chest supported row", "sets": "4", "reps": "8", "rest": "90 sec", "block": "Upper back support", "duration": "12 min", "note": "Drive elbows and control the lowering."},
            {"name": "Sled push / carries", "sets": "6", "reps": "20 m", "rest": "60 sec", "block": "Athletic finisher", "duration": "10 min", "note": "Finish powerful, not sloppy."},
        ],
        "muscle": [
            {"name": "Incline dumbbell press", "sets": "4", "reps": "8-10", "rest": "90 sec", "block": "Chest priority", "duration": "14 min", "note": "Deep stretch and controlled squeeze."},
            {"name": "Lat pulldown or pull-up", "sets": "4", "reps": "8-12", "rest": "75 sec", "block": "Back thickness", "duration": "12 min", "note": "Full range and chest up."},
            {"name": "Romanian deadlift", "sets": "4", "reps": "8", "rest": "120 sec", "block": "Posterior chain", "duration": "14 min", "note": "Hinge slow and own the hamstring stretch."},
            {"name": "Cable lateral raise", "sets": "3", "reps": "15-20", "rest": "45 sec", "block": "Shoulder finisher", "duration": "8 min", "note": "Chase tension, not momentum."},
        ],
        "cut": [
            {"name": "Goblet squat", "sets": "4", "reps": "10", "rest": "60 sec", "block": "Density opener", "duration": "10 min", "note": "Stay crisp and keep heart rate moving."},
            {"name": "Push-up / machine press", "sets": "4", "reps": "12", "rest": "45 sec", "block": "Upper density", "duration": "9 min", "note": "Clean reps with short breaks."},
            {"name": "Walking lunges", "sets": "3", "reps": "14/leg", "rest": "45 sec", "block": "Lower burn", "duration": "10 min", "note": "Long strides and steady pace."},
            {"name": "Bike or rower intervals", "sets": "10", "reps": "30/30", "rest": "30 sec", "block": "Conditioning", "duration": "12 min", "note": "Hard efforts with full rhythm control."},
        ],
    }

    nutrition_library = {
        "performance": [
            {"time": "07:30", "title": "Breakfast", "meal": "Oats, Greek yogurt, banana and whey.", "purpose": "Stable energy before the day."},
            {"time": "15:45", "title": "Pre-workout", "meal": "Rice cakes, honey and fruit.", "purpose": "Fast carbs before lifting."},
            {"time": "19:30", "title": "Post-workout", "meal": "Chicken, rice and vegetables.", "purpose": "Refill glycogen and recovery."},
            {"time": "21:30", "title": "Dinner", "meal": "Salmon, potatoes and salad.", "purpose": "Recovery and sleep support."},
        ],
        "muscle": [
            {"time": "08:00", "title": "Breakfast", "meal": "Eggs, oats, yogurt and berries.", "purpose": "Start with protein and calories."},
            {"time": "13:30", "title": "Lunch", "meal": "Beef or chicken with rice and olive oil.", "purpose": "Mass-building base meal."},
            {"time": "17:00", "title": "Pre/Post workout", "meal": "Whey shake plus banana.", "purpose": "Training support and faster recovery."},
            {"time": "20:30", "title": "Dinner", "meal": "Pasta with lean meat and parmesan.", "purpose": "Drive the daily surplus cleanly."},
        ],
        "cut": [
            {"time": "08:00", "title": "Breakfast", "meal": "Egg whites, berries and skyr.", "purpose": "Protein-first low-calorie start."},
            {"time": "13:00", "title": "Lunch", "meal": "Chicken salad with potatoes.", "purpose": "Stay full and sharp."},
            {"time": "16:30", "title": "Pre-workout", "meal": "Fruit and lean protein.", "purpose": "Low-fat fuel before training."},
            {"time": "20:00", "title": "Dinner", "meal": "White fish, rice and green vegetables.", "purpose": "Tight calorie finish."},
        ],
    }

    exercises = [dict(item) for item in exercise_library.get(goal, exercise_library["performance"])]
    if fatigue in {"high", "drained"}:
        exercises = exercises[:3]
        exercises[0]["note"] = f"{exercises[0]['note']} Keep 1-2 reps in reserve because fatigue is elevated."
    if equipment == "home":
        replacements = {
            "Back squat": "DB front squat",
            "Bench press": "DB floor press",
            "Chest supported row": "One-arm DB row",
            "Lat pulldown or pull-up": "Band pulldown / assisted pull-up",
            "Cable lateral raise": "DB lateral raise",
            "Bike or rower intervals": "Fast step-up intervals",
            "Sled push / carries": "Farmer carries / loaded step march",
        }
        for item in exercises:
            item["name"] = replacements.get(item["name"], item["name"])
    if gender == "female" and goal == "muscle":
        exercises.append(
            {
                "name": "Hip thrust",
                "sets": "3",
                "reps": "10-12",
                "rest": "75 sec",
                "block": "Glute finisher",
                "duration": "8 min",
                "note": "Use glute lockout and full control.",
            }
        )

    for idx, item in enumerate(exercises, start=1):
        item["order"] = idx
        item["item_key"] = f"exercise-{idx}-{item['name'].lower().replace(' ', '-').replace('/', '-')}"
        machine = machine_profile(str(item["name"]))
        item["machine_label"] = machine["label"]
        item["machine_focus"] = machine["focus"]
        item["machine_image"] = machine_image_uri(machine["icon"], machine["label"])

    latest_note = workouts[0]["focus"] if workouts else "No previous session logged yet."
    total_minutes = sum(clamp_int(item["duration"].split()[0], 10, 1, 60) for item in exercises)
    estimated_duration = f"{total_minutes + 10} min"

    rest_day_actions = [
        "20-30 min lagana setnja ili zone 2 cardio.",
        "10 min mobilnosti za kukove, grudni dio i ramena.",
        "Unesi korake, hidriraj se i idi ranije na spavanje.",
    ]
    if fatigue in {"high", "drained"}:
        rest_day_actions.insert(0, "Danas je recovery prioritet: bez jakog treninga i bez ego rada.")

    nutrition = nutrition_library.get(goal, nutrition_library["performance"])
    if not is_training_day:
        nutrition = [
            {"time": "08:00", "title": "Breakfast", "meal": nutrition[0]["meal"], "purpose": "Protein anchor and lower stress morning."},
            {"time": "13:00", "title": "Lunch", "meal": nutrition[1]["meal"], "purpose": "Keep calories structured without overeating."},
            {"time": "19:30", "title": "Dinner", "meal": nutrition[-1]["meal"], "purpose": "Recovery-focused finish for tomorrow."},
        ]
    for idx, meal in enumerate(nutrition, start=1):
        meal["item_key"] = f"meal-{idx}-{meal['title'].lower().replace(' ', '-')}"

    title_map = {
        "performance": "Performance execution day",
        "muscle": "Hypertrophy growth day",
        "cut": "Conditioning and fat-loss day",
    }

    if today_event and today_event.get("event_type") == "training":
        title = today_event.get("title") or title_map.get(goal, "Training day")
    elif is_training_day:
        title = title_map.get(goal, "Training day")
    else:
        title = "Recovery / rest day"

    focus_line = (
        today_event.get("details")
        if today_event
        else (
            "Heavy compound execution and speed quality."
            if is_training_day and goal == "performance"
            else "High-quality hypertrophy with stretch and control."
            if is_training_day and goal == "muscle"
            else "Dense work, calorie burn and muscle retention."
            if is_training_day
            else "Recovery day: lower stress, hit food structure and come back fresher tomorrow."
        )
    )
    daily_tasks = [
        {"title": "Open the player", "detail": "Start the workout timer and follow the exercise queue."},
        {"title": "Finish every written set", "detail": "Use one-tap completion so the coach can adapt tomorrow."},
        {"title": "Close the food plan", "detail": "Hit the written meals and protein target before the day ends."},
    ]
    if not is_training_day:
        daily_tasks = [
            {"title": "Run recovery flow", "detail": "Walk, mobility and breathing are the full goal today."},
            {"title": "Close food structure", "detail": "Keep meals clean and recovery-focused."},
            {"title": "Prepare tomorrow", "detail": "Sleep, hydration and light prep make the next session better."},
        ]

    return {
        "day_type": "training" if is_training_day else "recovery",
        "status_label": "Training day" if is_training_day else "Recovery day",
        "title": title,
        "coach_name": assistant["coach_name"],
        "coach_role": assistant["coach_role"],
        "duration": estimated_duration if is_training_day else "35 min recovery flow",
        "warmup": "8 min mobility + activation + 2 ramp-up sets per first movement." if is_training_day else "Lagani reset: setnja, disanje i mobilnost bez zamora.",
        "latest_note": latest_note,
        "exercises": exercises if is_training_day else [],
        "nutrition": nutrition,
        "focus_line": focus_line,
        "rest_day_actions": rest_day_actions,
        "daily_tasks": daily_tasks,
    }


def build_today_progress(today_blueprint: dict[str, Any], completed_today: set[str] | list[str]) -> dict[str, Any]:
    completed = set(completed_today)
    exercise_total = len(today_blueprint.get("exercises") or [])
    exercise_done = sum(1 for item in (today_blueprint.get("exercises") or []) if item["item_key"] in completed)
    meal_total = len(today_blueprint.get("nutrition") or [])
    meal_done = sum(1 for item in (today_blueprint.get("nutrition") or []) if item["item_key"] in completed)
    total_items = exercise_total + meal_total
    done_items = exercise_done + meal_done
    completion_percent = int(round((done_items / total_items) * 100)) if total_items else 0
    return {
        "exercise_total": exercise_total,
        "exercise_done": exercise_done,
        "meal_total": meal_total,
        "meal_done": meal_done,
        "total_items": total_items,
        "done_items": done_items,
        "completion_percent": completion_percent,
    }


def build_live_session(
    today_blueprint: dict[str, Any],
    completed_today: set[str] | list[str],
    exercise_logs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    completed = set(completed_today)
    exercises = today_blueprint.get("exercises") or []
    next_exercise = next((item for item in exercises if item["item_key"] not in completed), None)
    rest_presets = [
        {"label": "Power", "seconds": 150, "use": "Main compound lifts"},
        {"label": "Hypertrophy", "seconds": 90, "use": "Accessory work and clean volume"},
        {"label": "Density", "seconds": 45, "use": "Conditioning or high-output finishers"},
    ]
    recent_by_name = {}
    for logged in exercise_logs or []:
        recent_by_name.setdefault(str(logged["exercise_name"]), logged)
    progression = []
    for item in exercises[:4]:
        last = recent_by_name.get(item["name"])
        if not last:
            recommendation = "Start conservative today and leave 1-2 reps in reserve."
        else:
            last_rpe = float(last.get("rpe", 8) or 8)
            last_weight = float(last.get("weight_kg", 0) or 0)
            jump = 5 if any(word in item["name"].lower() for word in ["squat", "deadlift", "hip thrust"]) else 2.5
            if last_rpe <= 7.5 and last_weight > 0:
                recommendation = f"Increase by {jump} kg from your last logged {last_weight:.1f} kg."
            elif last_rpe <= 9:
                recommendation = f"Repeat last working load of {last_weight:.1f} kg and clean up execution."
            else:
                recommendation = f"Hold or reduce last load of {last_weight:.1f} kg by 5 percent to keep quality high."
        progression.append({"name": item["name"], "recommendation": recommendation})
    queue = []
    for item in exercises[:4]:
        set_count = clamp_int(item["sets"], 3, 1, 10)
        checkpoints = []
        for idx in range(1, set_count + 1):
            set_key = f"{item['item_key']}-set-{idx}"
            checkpoints.append(
                {
                    "label": f"Set {idx}",
                    "item_key": set_key,
                    "done": set_key in completed,
                }
            )
        queue.append(
            {
                "item_key": item["item_key"],
                "name": item["name"],
                "detail": f"{item['sets']} sets / {item['reps']} reps / rest {item['rest']}",
                "done": item["item_key"] in completed,
                "checkpoints": checkpoints,
                "weight_suggestion": next((entry["recommendation"] for entry in progression if entry["name"] == item["name"]), "Use a conservative starting load."),
                "machine_label": item.get("machine_label", "Training station"),
                "machine_focus": item.get("machine_focus", "Main station"),
                "machine_image": item.get("machine_image", ""),
            }
        )
    if today_blueprint.get("day_type") != "training":
        return {
            "mode": "recovery",
            "title": "Recovery mode",
            "coach_prompt": "Today is for lower stress output, mobility and recovery quality.",
            "next_move": "20-30 min easy walk, light mobility and hydration focus.",
            "rest_timer": "No timer needed",
            "queue": [],
            "technique": ["Easy breathing through the nose.", "Walk and move without fatigue.", "Finish with hydration and sleep prep."],
            "rest_presets": rest_presets,
            "completion_title": "Recovery complete",
            "completion_note": "Log your check-in and keep the day low stress.",
            "progression": [],
            "technique_source_label": "Recovery flow",
            "technique_source_url": "",
        }
    next_name = next_exercise["name"] if next_exercise else "Cooldown"
    guide = EXERCISE_TECHNIQUE_GUIDES.get(
        next_name,
        {
            "source_label": "Forge coaching standard",
            "source_url": "",
            "cues": ["Stay tight through setup.", "Control tempo and own each rep.", "Keep rest disciplined."],
        },
    )
    return {
        "mode": "training",
        "title": "Live workout mode",
        "coach_prompt": today_blueprint.get("warmup", ""),
        "next_move": f"Next up: {next_exercise['name']}" if next_exercise else "Workout complete. Move to cooldown and nutrition.",
        "rest_timer": next_exercise["rest"] if next_exercise else "Cooldown",
        "session_target_seconds": max(clamp_int(str(today_blueprint.get("duration", "60")).split()[0], 60, 15, 180) * 60, 900),
        "queue": queue,
        "technique": guide["cues"],
        "technique_source_label": guide["source_label"],
        "technique_source_url": guide["source_url"],
        "rest_presets": rest_presets,
        "completion_title": "Session finish",
        "completion_note": "After the final set, hit the post-workout meal, log the session and send a quick check-in.",
        "progression": progression,
    }


def build_weekly_review(user: dict[str, Any], workouts: list[dict[str, Any]], metrics: list[dict[str, Any]], checkins: list[dict[str, Any]]) -> dict[str, Any]:
    sessions = len(workouts[:7])
    avg_energy = round(sum(int(item["energy_score"]) for item in checkins[:7]) / len(checkins[:7]), 1) if checkins[:7] else 7.0
    latest_metric = metrics[0] if metrics else None
    weight_text = f"{latest_metric['body_weight']} kg" if latest_metric else "No body check-in yet"
    score = min(100, max(52, sessions * 14 + int(avg_energy * 4)))
    return {
        "headline": f"{user['full_name']} weekly coach review",
        "score": score,
        "points": [
            f"Completed {sessions} recent sessions in the current window.",
            f"Average readiness is {avg_energy}/10 based on check-ins.",
            f"Latest scale trend is {weight_text}.",
        ],
        "adjustment": "Keep the current plan and push quality." if score >= 78 else "Reduce junk volume, tighten food quality and focus on recovery before adding more work.",
        "next_week_adjustment": (
            "Next week add load to the first compound movement and keep the rest of the session structure stable."
            if score >= 82
            else "Next week hold top-set load steady, lower one accessory block and improve adherence before progressing."
            if score >= 68
            else "Next week reduce overall fatigue, shorten sessions and rebuild consistency before adding intensity."
        ),
    }


def build_notifications(user: dict[str, Any], today_blueprint: dict[str, Any], today_progress: dict[str, Any], checkins: list[dict[str, Any]]) -> list[dict[str, str]]:
    notices = []
    notices.append(
        {
            "title": "Today focus",
            "detail": today_blueprint["focus_line"],
            "level": "primary",
        }
    )
    if today_blueprint["day_type"] == "training":
        notices.append(
            {
                "title": "Training reminder",
                "detail": f"Block out {today_blueprint['duration']} and start with the first movement on time.",
                "level": "action",
            }
        )
    else:
        notices.append(
            {
                "title": "Recovery reminder",
                "detail": "Keep the day light, hit steps and protect sleep tonight.",
                "level": "recovery",
            }
        )
    if today_progress["meal_done"] < today_progress["meal_total"]:
        notices.append(
            {
                "title": "Meal structure",
                "detail": f"You still have {today_progress['meal_total'] - today_progress['meal_done']} nutrition blocks left today.",
                "level": "nutrition",
            }
        )
    latest_checkin = checkins[0] if checkins else None
    if latest_checkin and int(latest_checkin["energy_score"]) <= 5:
        notices.append(
            {
                "title": "Energy warning",
                "detail": "Energy is low. Keep 1-2 reps in reserve and shorten the last block if needed.",
                "level": "warning",
            }
        )
    else:
        notices.append(
            {
                "title": "Check-in reminder",
                "detail": "Log mood, soreness and motivation after the session so the coach keeps adapting.",
                "level": "coach",
            }
        )
    return notices[:4]


def build_personal_trainers(user: dict[str, Any], assistant: dict[str, Any]) -> list[dict[str, Any]]:
    goal = str(user["goal"]).lower()
    focus_map = {
        "performance": [
            ("Vera Iron", "Main performance block, top sets and progression."),
            ("Mila Engine", "Conditioning dosage and weekly output."),
            ("Tara Flow", "Mobility and recovery placement."),
        ],
        "muscle": [
            ("Noah Mass", "Volume, exercise order and hypertrophy quality."),
            ("Vera Iron", "Progressive overload and key compound anchors."),
            ("Tara Flow", "Recovery so weekly volume stays productive."),
        ],
        "cut": [
            ("Mila Engine", "Calorie burn, density and conditioning control."),
            ("Vera Iron", "Strength retention and exercise priority."),
            ("Tara Flow", "Recovery, steps and low-stress movement."),
        ],
    }
    assignments = focus_map.get(goal, focus_map["performance"])
    team = []
    for name, duty in assignments:
        coach_key = next((key for key, item in COACHES.items() if item["name"] == name), assistant["coach_key"])
        coach = COACHES[coach_key]
        team.append(
            {
                "name": coach["name"],
                "role": coach["role"],
                "duty": duty,
                "tone": coach["tone"],
                "lead": "Lead coach" if coach["name"] == assistant["coach_name"] else "Support coach",
            }
        )
    return team


def build_personal_calendar(user: dict[str, Any], assistant: dict[str, Any], weekly_planner: list[dict[str, Any]]) -> list[dict[str, Any]]:
    days = []
    for idx, item in enumerate(weekly_planner[:7]):
        if idx in {0, 2, 4}:
            slots = [
                {"time": "07:30", "type": "nutrition", "title": "Coach breakfast", "detail": "Protein-first meal aligned with today's work."},
                {"time": "17:30", "type": "training", "title": item["title"], "detail": item["details"]},
                {"time": "21:30", "type": "recovery", "title": "Sleep and recovery block", "detail": "Hydrate, walk, mobility and 8h sleep target."},
            ]
        elif idx in {1, 5}:
            slots = [
                {"time": "08:00", "type": "nutrition", "title": "Light structure", "detail": "Keep meals cleaner and hit macro target."},
                {"time": "18:00", "type": "recovery", "title": "Zone 2 or mobility", "detail": "Lower-stress output and joint recovery work."},
            ]
        else:
            slots = [
                {"time": "09:00", "type": "checkin", "title": "Body check-in", "detail": "Weight, steps, form score and readiness review."},
                {"time": "19:00", "type": "nutrition", "title": "Prep tomorrow", "detail": "Set meals, hydration and training clothes for next day."},
            ]
        days.append({"day_label": item["day_label"], "date": item["date"], "slots": slots})
    return days


def build_shopping_list(goal: str) -> list[dict[str, str]]:
    base = {
        "performance": ["Oats", "Greek yogurt", "Bananas", "Rice", "Chicken", "Salmon", "Potatoes", "Electrolytes"],
        "muscle": ["Eggs", "Oats", "Beef", "Chicken", "Rice", "Pasta", "Greek yogurt", "Peanut butter"],
        "cut": ["Egg whites", "Skyr", "Chicken breast", "White fish", "Potatoes", "Berries", "Rice", "Leafy greens"],
    }
    items = []
    for name in base.get(goal, base["performance"]):
        items.append({"name": name, "reason": f"Aligned with {goal} goal and easier daily adherence."})
    return items


def build_progress_trends(metrics: list[dict[str, Any]], workouts: list[dict[str, Any]], checkins: list[dict[str, Any]]) -> list[dict[str, str]]:
    latest = metrics[0] if metrics else None
    previous = metrics[1] if len(metrics) > 1 else None
    weight_delta = "0.0"
    waist_delta = "0.0"
    if latest and previous:
        weight_delta = f"{float(latest['body_weight']) - float(previous['body_weight']):+.1f}"
        waist_delta = f"{float(latest['waist']) - float(previous['waist']):+.1f}"
    energy_avg = "7.0"
    if checkins:
        energy_avg = f"{sum(int(item['energy_score']) for item in checkins) / len(checkins):.1f}"
    return [
        {"label": "Body weight trend", "value": weight_delta + " kg", "detail": "Change vs previous check-in."},
        {"label": "Waist trend", "value": waist_delta + " cm", "detail": "Use this to judge physique direction."},
        {"label": "Session rhythm", "value": str(len(workouts[:7])) + " sessions", "detail": "Recent training frequency window."},
        {"label": "Energy average", "value": energy_avg + "/10", "detail": "Daily readiness from your latest check-ins."},
    ]


def current_view_mode() -> str:
    mode = str(session.get("view_mode") or "simple").strip().lower()
    if mode == "minimal":
        mode = "simple"
    return mode if mode in {"simple", "pro"} else "simple"


def exercise_prescription_text(item: dict[str, Any]) -> str:
    return f"{item.get('sets', '?')} sets · {item.get('reps', '?')} reps · rest {item.get('rest', '?')}"


def build_single_next_action(
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    checkins: list[dict[str, Any]],
    completed_today: set[str] | list[str],
) -> dict[str, str]:
    completed = set(completed_today)
    today_key = date.today().isoformat()
    has_checkin_today = any(str(item.get("checkin_date") or "").startswith(today_key) for item in checkins)
    day_type = str(today_blueprint.get("day_type") or "training")
    meal_left = max(int(today_progress.get("meal_total", 0)) - int(today_progress.get("meal_done", 0)), 0)
    exercise_left = max(int(today_progress.get("exercise_total", 0)) - int(today_progress.get("exercise_done", 0)), 0)

    if not has_checkin_today:
        return {
            "title": "Start the day with a 30-second check-in",
            "detail": "Log energy, soreness and focus once, then let Forge adapt the rest of the day.",
            "anchor": "/daily-checkin",
            "cta": "Open check-in",
            "tag": "Daily reset",
        }
    if day_type == "training" and exercise_left:
        next_exercise = next(
            (item for item in (today_blueprint.get("exercises") or []) if item.get("item_key") not in completed),
            (today_blueprint.get("exercises") or [None])[0],
        )
        prescription = exercise_prescription_text(next_exercise) if next_exercise else today_blueprint.get("duration", "Live session")
        return {
            "title": f"Run today's session: {today_blueprint.get('title', 'Training day')}",
            "detail": f"Start with {next_exercise.get('name') if next_exercise else 'the first movement'} - {prescription}. The player already knows the order, rest and load suggestion.",
            "anchor": "/workout-mode",
            "cta": "Start workout",
            "tag": today_blueprint.get("duration", "Live session"),
        }
    if meal_left:
        return {
            "title": "Close today's nutrition blocks",
            "detail": f"{meal_left} meal blocks are still open. Use the nutrition screen instead of scrolling through the full dashboard.",
            "anchor": "/nutrition-mode",
            "cta": "Open nutrition",
            "tag": "Meals today",
        }
    return {
        "title": "Close the day and prep the next one",
        "detail": "Training and meals are mostly done. Review the week, recover and let Forge set up the next block.",
        "anchor": "/weekly-reset",
        "cta": "Open weekly reset",
        "tag": "Wrap-up",
    }


def build_day_flow(
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    checkins: list[dict[str, Any]],
) -> list[dict[str, str]]:
    today_key = date.today().isoformat()
    has_checkin_today = any(str(item.get("checkin_date") or "").startswith(today_key) for item in checkins)
    day_type = str(today_blueprint.get("day_type") or "training")
    exercise_left = max(int(today_progress.get("exercise_total", 0)) - int(today_progress.get("exercise_done", 0)), 0)
    meal_left = max(int(today_progress.get("meal_total", 0)) - int(today_progress.get("meal_done", 0)), 0)
    return [
        {
            "title": "Check in",
            "detail": "Log energy, soreness and focus so the day adapts correctly.",
            "anchor": "/daily-checkin",
            "cta": "Open check-in",
            "state": "done" if has_checkin_today else "now",
            "state_label": "Done" if has_checkin_today else "Now",
        },
        {
            "title": "Move",
            "detail": (
                " -> ".join(
                    f"{item['order']}. {item['name']}"
                    for item in (today_blueprint.get("exercises") or [])[:3]
                )
                if day_type == "training"
                else today_blueprint.get("title", "Session")
            ),
            "anchor": "/workout-mode" if day_type == "training" else "#today-plan",
            "cta": "Open session" if day_type == "training" else "Open recovery",
            "state": "done" if exercise_left == 0 else ("now" if has_checkin_today else "ready"),
            "state_label": "Done" if exercise_left == 0 else ("Now" if has_checkin_today else "Ready"),
        },
        {
            "title": "Eat",
            "detail": f"{meal_left} meal blocks left" if meal_left else "Food targets are on track for today.",
            "anchor": "/nutrition-mode",
            "cta": "Open nutrition",
            "state": "done" if meal_left == 0 else "ready",
            "state_label": "Done" if meal_left == 0 else "Ready",
        },
        {
            "title": "Reset",
            "detail": "Finish with review, recovery and tomorrow prep instead of guessing what comes next.",
            "anchor": "/weekly-reset",
            "cta": "Open reset",
            "state": "ready" if meal_left or exercise_left else "now",
            "state_label": "Ready" if meal_left or exercise_left else "Now",
        },
    ]


def build_coach_day_flow(today_blueprint: dict[str, Any], completed_today: set[str] | list[str]) -> list[dict[str, str]]:
    completed = set(completed_today)
    if today_blueprint.get("day_type") != "training":
        return [
            {
                "kicker": "Recovery",
                "title": "Walk and reset",
                "detail": "Keep the day simple and protect recovery instead of forcing training.",
                "prescription": "20-30 min walk · light mobility · low stress",
                "cue": "Finish the basics, hydrate and sleep earlier.",
                "anchor": "#today-plan",
                "cta": "Open recovery",
                "done": False,
            }
        ]

    steps = []
    for item in today_blueprint.get("exercises", []):
        steps.append(
            {
                "kicker": f"Step {item['order']}",
                "title": item["name"],
                "detail": item["block"],
                "prescription": exercise_prescription_text(item),
                "cue": item["note"],
                "anchor": "/workout-mode",
                "cta": "Open player",
                "done": item["item_key"] in completed,
            }
        )
    return steps[:6]


def build_focus_cards(
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    live_session: dict[str, Any],
    coach_briefing: dict[str, str],
    completed_today: set[str] | list[str],
) -> list[dict[str, str]]:
    completed = set(completed_today)
    next_exercise = next(
        (item for item in (today_blueprint.get("exercises") or []) if item.get("item_key") not in completed),
        (today_blueprint.get("exercises") or [None])[0],
    )
    return [
        {
            "kicker": "Next move",
            "title": next_exercise.get("name") if next_exercise else (live_session.get("next_move") or today_blueprint.get("title", "Open today")),
            "detail": exercise_prescription_text(next_exercise) if next_exercise else (coach_briefing.get("next_step") or "Open the main player and follow the next step."),
        },
        {
            "kicker": "Today score",
            "title": f"{today_progress.get('completion_percent', 0)}% complete",
            "detail": f"{today_progress.get('exercise_done', 0)}/{today_progress.get('exercise_total', 0)} exercise blocks and {today_progress.get('meal_done', 0)}/{today_progress.get('meal_total', 0)} meals are logged.",
        },
        {
            "kicker": "Session time",
            "title": today_blueprint.get("duration", "60 min lane"),
            "detail": today_blueprint.get("focus_line", "Stay simple: train, eat, recover."),
        },
    ]


def build_home_hub(
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
    single_next_action: dict[str, Any],
    coach_briefing: dict[str, Any],
) -> dict[str, Any]:
    return {
        "headline": today_blueprint.get("title", "Today's plan"),
        "detail": coach_briefing.get("next_step", "Open the next block and follow it."),
        "primary": {
            "label": single_next_action.get("cta", "Open today"),
            "anchor": single_next_action.get("anchor", "/workout-mode"),
        },
        "secondary": {
            "label": "Open food",
            "anchor": "/nutrition-mode",
        },
        "stats": [
            {
                "label": "Day type",
                "value": today_blueprint.get("status_label", "Ready"),
                "detail": today_blueprint.get("duration", "Planned session"),
            },
            {
                "label": "Progress",
                "value": f"{today_progress.get('completion_percent', 0)}%",
                "detail": f"{today_progress.get('done_items', 0)}/{today_progress.get('total_items', 0)} blocks closed today.",
            },
            {
                "label": "Next meal",
                "value": nutrition_intelligence.get("next_meal_title", "Meal block"),
                "detail": nutrition_intelligence.get("next_meal_detail", "Keep fuel aligned."),
            },
        ],
    }


def build_guided_day_flow_v2(
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    nutrition_intelligence: dict[str, Any],
) -> list[dict[str, str]]:
    training_day = str(today_blueprint.get("day_type") or "training") == "training"
    done_items = int(today_progress.get("done_items", 0))
    total_items = max(int(today_progress.get("total_items", 0)), 1)
    all_done = done_items >= total_items
    return [
        {
            "kicker": "1. Check-in",
            "title": "Start the day",
            "detail": "Log energy, soreness and recovery before you train.",
            "anchor": "/daily-checkin",
            "cta": "Open check-in",
            "state": "done" if int(today_progress.get("completion_percent", 0)) > 0 else "now",
        },
        {
            "kicker": "2. Training",
            "title": today_blueprint.get("title", "Today's training"),
            "detail": today_blueprint.get("focus_line", "Follow the session in order.") if training_day else "Recovery flow, mobility and steps only.",
            "anchor": "/workout-mode",
            "cta": "Open workout mode" if training_day else "Open recovery mode",
            "state": "now" if training_day and int(today_progress.get("exercise_done", 0)) == 0 else ("done" if int(today_progress.get("exercise_done", 0)) >= int(today_progress.get("exercise_total", 0)) else "ready"),
        },
        {
            "kicker": "3. Food",
            "title": nutrition_intelligence.get("next_meal_title", "Meal plan"),
            "detail": nutrition_intelligence.get("next_meal_detail", "Close your meal blocks and macros."),
            "anchor": "/nutrition-mode",
            "cta": "Open nutrition",
            "state": "done" if int(today_progress.get("meal_done", 0)) >= int(today_progress.get("meal_total", 0)) else "ready",
        },
        {
            "kicker": "4. Review",
            "title": "Close the day",
            "detail": "Finish the last block, save the session and reset for tomorrow." if not all_done else "Day closed. Review progress and get ready for tomorrow.",
            "anchor": "/weekly-reset",
            "cta": "Open review",
            "state": "done" if all_done else "ready",
        },
    ]


def build_mode_blueprint(view_mode: str) -> list[dict[str, Any]]:
    simple_active = view_mode == "simple"
    return [
        {
            "kicker": "Default mode",
            "title": "Simple",
            "detail": "Only today, today's flow and the few actions that matter.",
            "anchor": "/set-view-mode?mode=simple",
            "cta": "Use Simple",
            "active": simple_active,
        },
        {
            "kicker": "Advanced mode",
            "title": "Pro",
            "detail": "Program depth, analytics, adaptive cards and deeper review.",
            "anchor": "/set-view-mode?mode=pro",
            "cta": "Use Pro",
            "active": view_mode == "pro",
        },
    ]


def build_easy_mode(
    user: dict[str, Any],
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    access: dict[str, Any],
    ai_concierge: dict[str, Any],
) -> dict[str, Any]:
    day_type = str(today_blueprint.get("day_type") or "training")
    training_live = day_type == "training"
    meals_left = max(int(today_progress.get("meal_total", 0)) - int(today_progress.get("meal_done", 0)), 0)
    exercise_left = max(int(today_progress.get("exercise_total", 0)) - int(today_progress.get("exercise_done", 0)), 0)
    headline = "Your day is already organized"
    detail = (
        "Open the player and follow the next exercise step by step."
        if training_live
        else "Today is simplified for recovery, food structure and low-stress consistency."
    )
    primary_tag = "Training live" if training_live else "Recovery day"
    primary_actions = [
        {
            "kicker": "Start now",
            "title": "Open workout player" if training_live else "Open recovery plan",
            "detail": today_blueprint.get("duration", "Training flow"),
            "anchor": "/workout-mode" if training_live else "#today-plan",
            "tag": "Live",
        },
        {
            "kicker": "Food today",
            "title": f"{meals_left} meal blocks left" if meals_left else "Meals complete",
            "detail": "Log food and keep macros aligned with the goal.",
            "anchor": "/nutrition-mode",
            "tag": "Nutrition",
        },
        {
            "kicker": "Coach lane",
            "title": ai_concierge.get("name") or "Forge coach",
            "detail": "Ask the coach what to do next or how to adjust today.",
            "anchor": "/hub/coach",
            "tag": "AI",
        },
        {
            "kicker": "Progress",
            "title": f"{exercise_left} exercise blocks left" if training_live else f"{today_progress.get('completion_percent', 0)}% day complete",
            "detail": "See how the day is tracking and what is still open.",
            "anchor": "/hub/track",
            "tag": access.get("status_label", "Access"),
        },
    ]
    quick_dock = [
        {
            "kicker": "Main",
            "title": "Today",
            "detail": "Fast jump to the session and meal flow.",
            "anchor": "/workout-mode",
        },
        {
            "kicker": "Mode",
            "title": "Workout only",
            "detail": "Open the distraction-free session screen.",
            "anchor": "/workout-mode",
        },
        {
            "kicker": "Check-in",
            "title": "Daily wizard",
            "detail": "Log energy, soreness and note in one quick screen.",
            "anchor": "/daily-checkin",
        },
        {
            "kicker": "Coach",
            "title": "AI trainer",
            "detail": "Open chat and coaching summaries.",
            "anchor": "/hub/coach",
        },
        {
            "kicker": "Meals",
            "title": "Nutrition",
            "detail": "Log food without digging through the page.",
            "anchor": "/nutrition-mode",
        },
        {
            "kicker": "User",
            "title": "Profile",
            "detail": "Change body data, goal and equipment.",
            "anchor": "/hub/profile",
        },
    ]
    return {
        "headline": headline,
        "detail": detail,
        "primary_tag": primary_tag,
        "primary_actions": primary_actions,
        "quick_dock": quick_dock,
    }


def build_coach_briefing(
    user: dict[str, Any],
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    ai_concierge: dict[str, Any],
) -> dict[str, str]:
    day_type = str(today_blueprint.get("day_type") or "training")
    if day_type == "training":
        opening_moves = "; ".join(
            f"{item['order']}. {item['name']} ({item['sets']}x{item['reps']})"
            for item in (today_blueprint.get("exercises") or [])[:3]
        )
        opening = f"Today is {today_blueprint['title']}. Open the player and run the first movement before you overthink it."
        summary = f"{today_progress.get('exercise_total', 0)} exercises and {today_progress.get('meal_total', 0)} nutrition blocks are already organized for you. Order: {opening_moves}."
        next_step = "Tap Start workout, finish the first set, then let the live player carry the session."
    else:
        opening = "Today is a recovery day. Keep stress lower and stay consistent instead of forcing volume."
        summary = f"You still have {today_progress.get('meal_total', 0)} nutrition blocks and recovery work to close out the day. Walk, mobility and sleep prep are enough today."
        next_step = "Open Today, finish food structure, mobility and steps, then log the day."
    return {
        "coach": ai_concierge.get("name") or "Forge coach",
        "opening": opening,
        "summary": summary,
        "next_step": next_step,
    }


def build_reminder_center(
    today_blueprint: dict[str, Any],
    today_progress: dict[str, Any],
    access: dict[str, Any],
) -> list[dict[str, str]]:
    day_type = str(today_blueprint.get("day_type") or "training")
    reminders = [
        {
            "time": "Now",
            "title": "Open today's plan",
            "detail": "Use the player or recovery block instead of guessing what to do next.",
            "level": "primary",
        },
        {
            "time": "Midday",
            "title": "Hit your food structure",
            "detail": f"{max(today_progress.get('meal_total', 0) - today_progress.get('meal_done', 0), 0)} meal blocks are still open today.",
            "level": "nutrition",
        },
        {
            "time": "Evening",
            "title": "Close the day clean",
            "detail": "Finish check-in, hydration and recovery before sleep.",
            "level": "recovery",
        },
    ]
    if day_type == "training":
        reminders.insert(
            1,
            {
                "time": "Training window",
                "title": "Run the session live",
                "detail": f"Session length is {today_blueprint.get('duration', 'planned')} and the live player handles timing for you.",
                "level": "training",
            },
        )
    if not access.get("trial_active") and str(access.get("recommended_tier") or ""):
        reminders.append(
            {
                "time": "Access",
                "title": "Upgrade lane",
                "detail": f"Recommended package is {str(access['recommended_tier']).title()} when you want full coaching after trial.",
                "level": "billing",
            }
        )
    return reminders


def business_overview() -> dict[str, Any]:
    with get_db() as db:
        total_users = int(db.execute("SELECT COUNT(*) FROM users").fetchone()[0])
        total_members = int(db.execute("SELECT COUNT(*) FROM users WHERE role = 'member'").fetchone()[0])
        pro_users = int(db.execute("SELECT COUNT(*) FROM users WHERE subscription_tier = 'pro'").fetchone()[0])
        elite_users = int(db.execute("SELECT COUNT(*) FROM users WHERE subscription_tier = 'elite'").fetchone()[0])
        active_paid_users = int(db.execute("SELECT COUNT(*) FROM users WHERE billing_status = 'paid'").fetchone()[0])
        gifted_users = int(db.execute("SELECT COUNT(*) FROM users WHERE gift_package = 1").fetchone()[0])
        mrr = int(
            db.execute(
                """
                SELECT COALESCE(SUM(
                    CASE subscription_tier
                        WHEN 'pro' THEN 19
                        WHEN 'elite' THEN 49
                        ELSE 0
                    END
                ), 0)
                FROM users
                WHERE billing_status = 'paid'
                """
            ).fetchone()[0]
        )
    return {
        "total_users": total_users,
        "total_members": total_members,
        "pro_users": pro_users,
        "elite_users": elite_users,
        "active_paid_users": active_paid_users,
        "gifted_users": gifted_users,
        "mrr": mrr,
    }


def subscription_access_state(user: dict[str, Any]) -> dict[str, Any]:
    today = date.today()
    billing_status = str(user.get("billing_status") or "inactive")
    tier = str(user.get("subscription_tier") or "starter")
    trial_started_at = str(user.get("trial_started_at") or "")
    trial_ends_at = str(user.get("trial_ends_at") or "")

    days_left = 0
    trial_active = False
    if trial_ends_at:
        try:
            end_date = date.fromisoformat(trial_ends_at[:10])
            days_left = max((end_date - today).days, 0)
            trial_active = today <= end_date
        except ValueError:
            trial_active = False

    if billing_status in {"paid", "gifted"}:
        status_label = "Paid access" if billing_status == "paid" else "Gift access"
        full_access = True
    elif trial_active:
        status_label = f"Free trial active - {days_left} days left"
        full_access = True
    else:
        status_label = "Trial finished - upgrade recommended"
        full_access = tier != "starter"

    recommended = "pro"
    goal = str(user.get("goal") or "performance").lower()
    if goal in {"muscle", "bodybuilding"}:
        recommended = "elite"
    elif goal in {"cut", "performance"}:
        recommended = "pro"

    return {
        "status_label": status_label,
        "trial_active": trial_active,
        "days_left": days_left,
        "full_access": full_access,
        "recommended_tier": recommended,
        "trial_started_at": trial_started_at,
        "trial_ends_at": trial_ends_at,
    }


def has_elite_ai_access(user: dict[str, Any], access: dict[str, Any]) -> bool:
    tier = str(user.get("subscription_tier") or "starter").lower()
    billing_status = str(user.get("billing_status") or "inactive").lower()
    return bool(access.get("trial_active")) or tier == "elite" or (tier == "elite" and billing_status in {"paid", "gifted"})


def build_ai_concierge(user: dict[str, Any], access: dict[str, Any]) -> dict[str, Any]:
    full_name = str(user.get("full_name") or "").strip()
    username = str(user.get("username") or "").strip().lower()
    is_mitar = "mitar" in full_name.lower() or username == "mitar"
    elite_access = has_elite_ai_access(user, access)
    if is_mitar:
        return {
            "name": "Mitar Individual AI Coach",
            "mode": "individual",
            "greeting": "Mitra vodim kao privatni trener: govorim ti sta radis danas, kojim redom, kako izvodis i gdje pazis na tehniku.",
            "enabled": True,
        }
    if elite_access:
        return {
            "name": "Forge Elite AI Concierge",
            "mode": "elite",
            "greeting": "Ovo je tvoj premium AI trener za dnevne treninge, tehniku, ishranu i prilagodjavanje plana.",
            "enabled": True,
        }
    return {
        "name": "Forge Coach Preview",
        "mode": "preview",
        "greeting": "AI trener u punom obliku je rezervisan za Elite ili za aktivni trial period.",
        "enabled": False,
    }


def market_readiness_flags() -> list[dict[str, str]]:
    return [
        {"title": "Session security", "detail": "HTTPOnly, SameSite and optional secure session cookies are enabled."},
        {"title": "Safer auth defaults", "detail": f"Minimum password length is {MIN_PASSWORD_LENGTH} and admin seed supports env overrides."},
        {"title": "Monetization layer", "detail": "Starter, Pro and Elite tiers are available in the user model and admin tools."},
        {"title": "Discount codes", "detail": "Users can enter discount codes at package activation, while admins can gift premium access."},
        {"title": "Launch docs", "detail": "Terms and Privacy pages are exposed for public-facing deployment."},
    ]


def build_ai_trainer_reply(
    user: dict[str, Any],
    message: str,
    assistant: dict[str, Any],
    today_blueprint: dict[str, Any],
    checkins: list[dict[str, Any]],
    ai_concierge: dict[str, Any],
    coach_memory: list[dict[str, Any]] | None = None,
) -> str:
    prompt = message.strip().lower()
    goal = str(user["goal"]).lower()
    latest_checkin = checkins[0] if checkins else None
    coach_name = ai_concierge["name"]
    memory_suffix = ""
    if coach_memory:
        memory_suffix = " Zapamtio sam i ovo o tebi: " + "; ".join(item["memory_text"] for item in coach_memory[:3]) + "."
    if not ai_concierge.get("enabled"):
        return f"{coach_name}: otkljucaj Elite paket nakon triala da dobijes puni individualni AI coaching chat."
    if any(word in prompt for word in ["today", "danas", "workout", "trening"]):
        if today_blueprint["day_type"] != "training":
            return f"{coach_name}: danas ti je recovery dan. Odradi laganu setnju, mobilnost i drzi obroke ciste i proteinske.{memory_suffix}"
        first = today_blueprint["exercises"][0]
        return (
            f"{coach_name}: danas radi {today_blueprint['title']}. Kreni sa {first['name']} na {first['sets']} serija x {first['reps']} "
            f"sa odmorom {first['rest']}, pa nastavi kroz ostatak plana bez zurbe.{memory_suffix}"
        )
    if any(word in prompt for word in ["food", "meal", "eat", "jesti", "ishrana"]):
        first_meal = today_blueprint["nutrition"][0]
        return (
            f"{coach_name}: za cilj {goal} danas drzi protein na {assistant['targets']['protein']}g i fokusiraj se na {first_meal['title'].lower()} u {first_meal['time']}. "
            f"Meal: {first_meal['meal']} Poslije treninga idi na pun obrok sa proteinom i ugljenim hidratima.{memory_suffix}"
        )
    if any(word in prompt for word in ["tired", "umor", "sore", "bol"]):
        status = latest_checkin["mood"] if latest_checkin else "steady"
        return (
            f"{coach_name}: ako si danas pod umorom ({status}), skrati zadnju vjezbu, ostavi 1-2 reps in reserve i fokus prebaci na tehniku, hodanje i san.{memory_suffix}"
        )
    if any(word in prompt for word in ["mass", "muscle", "misi", "bodybuilding"]):
        return f"{coach_name}: za misice i bodybuilding sad ti je kljuc kvalitetan volumen, stabilan kalorijski suficit i uredan logbook na osnovnim vjezbama.{memory_suffix}"
    if any(word in prompt for word in ["cut", "mrsa", "fat loss"]):
        return f"{coach_name}: za mrsanje zadrzi snagu kao prioritet, deficit neka bude cist, a cardio neka bude dodatak, ne zamjena za trening.{memory_suffix}"
    return (
        f"{coach_name}: na osnovu cilja {goal}, danasnjeg plana i check-in podataka vodicu te kroz trening, hranu i recovery svaki dan.{memory_suffix}"
    )


def build_assistant_plan(
    user: dict[str, Any],
    workouts: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    meals: list[dict[str, Any]],
    calendar: list[dict[str, Any]],
    energy: int = 7,
    training_days: int = 4,
) -> dict[str, Any]:
    latest_metric = metrics[0] if metrics else None
    weight = float(latest_metric["body_weight"]) if latest_metric else float(user["weight_kg"])
    goal = str(user["goal"]).lower()
    equipment = str(user.get("equipment_access", "full gym")).lower()
    fatigue = str(user.get("fatigue_state", "steady")).lower()
    cycle_phase = str(user.get("cycle_phase", "neutral")).lower()
    protein_target = round(weight * (2.2 if goal == "muscle" else 2.0 if goal == "performance" else 1.9))
    carbs_target = round(weight * (4.0 if goal == "performance" else 3.3 if goal == "muscle" else 2.4))
    fats_target = round(weight * 0.8)
    calories_target = int(protein_target * 4 + carbs_target * 4 + fats_target * 9)

    assistant_coach = "strength"
    if goal == "muscle":
        assistant_coach = "hypertrophy"
    elif goal == "cut":
        assistant_coach = "conditioning"

    training_summary = [
        f"{training_days} training days this week with 1 recovery emphasis day.",
        f"Main lane: {COACHES[assistant_coach]['role']} with progressive overload and logged RPE.",
        f"Body profile: {user['height_cm']} cm, {round(weight, 1)} kg, age {user['age']}, equipment {equipment}.",
    ]
    if fatigue in {"high", "drained"}:
        training_summary.append("Fatigue state is elevated, so current blocks should stay cleaner and lower in junk volume.")
    if str(user.get("gender", "male")).lower() == "female" and cycle_phase != "neutral":
        training_summary.append(f"Current cycle mode is {cycle_phase}, so recovery and intensity are adjusted more intelligently.")
    if workouts:
        training_summary.append(f"Latest logged session: {workouts[0]['focus']} on {workouts[0]['workout_date']}.")
    if latest_metric:
        training_summary.append(
            f"Latest check-in: {latest_metric['body_weight']} kg, waist {latest_metric['waist']} cm, form {latest_metric['form_score']}/10."
        )

    nutrition_summary = [
        f"Daily target: {calories_target} kcal, {protein_target}g protein, {carbs_target}g carbs, {fats_target}g fats.",
        "Anchor each meal with lean protein, structured carbs around training and stable hydration.",
        "Use recipes in the nutrition lab to stay aligned with the current goal.",
    ]
    if fatigue in {"high", "drained"}:
        nutrition_summary.append("Push easier-to-digest meals and tighter hydration because current fatigue is high.")
    if str(user.get("gender", "male")).lower() == "female" and cycle_phase in {"recovery", "late_cycle"}:
        nutrition_summary.append("Bias recovery foods, iron-rich choices and lower stress meal timing in this phase.")
    if meals:
        nutrition_summary.append(f"Most recent meal logged: {meals[0]['food_name']} ({meals[0]['meal_type']}).")

    calendar_summary = calendar[:4] or [
        {
            "event_date": (date.today() + timedelta(days=1)).isoformat(),
            "event_type": "training",
            "title": "Upper performance session",
            "details": "Main lift, accessories and recovery block.",
            "coach_key": assistant_coach,
        }
    ]

    return {
        "coach_key": assistant_coach,
        "coach_name": COACHES[assistant_coach]["name"],
        "coach_role": COACHES[assistant_coach]["role"],
        "headline": f"{user['full_name']} plan for {goal}",
        "training_summary": training_summary,
        "nutrition_summary": nutrition_summary,
        "calendar_summary": calendar_summary,
        "targets": {
            "calories": calories_target,
            "protein": protein_target,
            "carbs": carbs_target,
            "fats": fats_target,
        },
        "suggestions": build_goal_suggestions(user, assistant_coach, training_days),
        "next_action": "Log workouts, meals and check-ins daily so the assistant keeps adapting to this athlete profile.",
    }


def dashboard_payload(user: dict[str, Any]) -> dict[str, Any]:
    seed = load_json(SEED_FILE)
    research = load_json(RESEARCH_FILE)["sources"]
    catalog = catalog_payload()
    workouts = recent_workouts(int(user["id"]))
    metrics = recent_metrics(int(user["id"]))
    meals = recent_meals(int(user["id"]))
    exercises = recent_exercises(int(user["id"]))
    photos = recent_photos(int(user["id"]))
    checkins = recent_checkins(int(user["id"]))
    coach_messages = recent_coach_messages(int(user["id"]))
    coach_memory = coach_memory_items(int(user["id"]))
    calendar = calendar_items(int(user["id"]))
    access = subscription_access_state(user)
    ai_concierge = build_ai_concierge(user, access)
    completed_today = today_plan_checks(int(user["id"]))
    stats = build_tracking_stats(workouts, metrics)
    nutrition_stats = build_nutrition_stats(meals)
    recommendation = build_recommendation(
        coach_key="strength" if user["goal"] == "performance" else "hypertrophy" if user["goal"] == "muscle" else "conditioning",
        mood="steady",
        energy=7,
        equipment="full gym",
        minutes=75,
        goal=str(user["goal"]).lower(),
        workouts=workouts,
        research=research,
    )

    seed["user"]["name"] = user["full_name"]
    seed["user"]["level"] = user["experience_level"].title()
    seed["user"]["goal"] = user["goal"].title()
    seed["user"]["readiness"] = 86 if stats["latest_metric"] else 74
    seed["user"]["streak_days"] = max(3, len(workouts) * 4)

    assistant = build_assistant_plan(user, workouts, metrics, meals, calendar, training_days=goal_training_days(user))
    scores = build_athlete_scores(workouts, metrics, meals)
    meal_suggestions = build_meal_suggestions(str(user["goal"]).lower(), assistant["targets"]["calories"], assistant["targets"]["protein"])
    daily_mission = build_daily_mission(user, assistant, stats)
    achievements = build_achievements(stats, workouts, metrics)
    adaptive_filters = build_adaptive_filters(user)
    folder_cards = build_folder_cards(user, assistant)
    section_menu = build_section_menu(user)
    weekly_planner = build_weekly_planner(user, calendar, assistant)
    today_blueprint = build_today_blueprint(user, assistant, workouts, calendar)
    today_progress = build_today_progress(today_blueprint, completed_today)
    live_session = build_live_session(today_blueprint, completed_today, exercises)
    notifications = build_notifications(user, today_blueprint, today_progress, checkins)
    weekly_review = build_weekly_review(user, workouts, metrics, checkins)
    personal_trainers = build_personal_trainers(user, assistant)
    personal_calendar = build_personal_calendar(user, assistant, weekly_planner)
    shopping_list = build_shopping_list(str(user["goal"]).lower())
    progress_trends = build_progress_trends(metrics, workouts, checkins)
    nutrition_intelligence = build_nutrition_intelligence(user, assistant, meals, today_blueprint)
    adaptive_training_engine = build_adaptive_training_engine(user, today_blueprint, workouts, exercises, checkins)
    progress_system = build_progress_system(user, metrics, workouts, photos, checkins, stats)
    periodization_engine = build_periodization_engine(user, workouts, checkins, today_blueprint)
    session_analytics = build_session_analytics(today_blueprint, exercises, completed_today)
    easy_mode = build_easy_mode(user, today_blueprint, today_progress, access, ai_concierge)
    coach_briefing = build_coach_briefing(user, today_blueprint, today_progress, ai_concierge)
    reminder_center = build_reminder_center(today_blueprint, today_progress, access)
    daily_tasks = build_daily_tasks(today_blueprint, today_progress, access)
    single_next_action = build_single_next_action(today_blueprint, today_progress, checkins, completed_today)
    day_flow = build_day_flow(today_blueprint, today_progress, checkins)
    coach_day_flow = build_coach_day_flow(today_blueprint, completed_today)
    focus_cards = build_focus_cards(today_blueprint, today_progress, live_session, coach_briefing, completed_today)
    pr_tracker = build_pr_tracker(exercises)
    recomposition_dashboard = build_recomposition_dashboard(metrics, photos, pr_tracker, progress_system)
    recomposition_home = build_recomp_home(progress_system, recomposition_dashboard)
    weekly_adaptive_block = build_weekly_adaptive_block_plan(periodization_engine, adaptive_training_engine, weekly_review, progress_system)
    exercise_mastery = build_exercise_mastery(today_blueprint)
    voice_coach = build_voice_coach_payload(today_blueprint, live_session)
    package_filters = build_package_filters(assistant["suggestions"])
    active_package = build_active_package(assistant, workouts, calendar)
    program_board = build_program_board(active_package)
    program_builder = build_program_builder(active_package, periodization_engine)
    workspace_hub = build_workspace_hub(user, active_package, today_blueprint, access)
    operating_board = build_operating_board(today_blueprint, active_package, nutrition_intelligence, coach_briefing)
    customer_delight = build_customer_delight(
        user,
        today_blueprint,
        today_progress,
        nutrition_intelligence,
        adaptive_training_engine,
        periodization_engine,
        coach_briefing,
        access,
    )
    delight_board = build_delight_board(
        user,
        today_blueprint,
        customer_delight,
        active_package,
        nutrition_intelligence,
        access,
        single_next_action if "single_next_action" in locals() else {"cta": "Open today", "anchor": "#today-plan"},
    )
    home_hub = build_home_hub(today_blueprint, today_progress, nutrition_intelligence, single_next_action, coach_briefing)
    guided_day_flow = build_guided_day_flow_v2(today_blueprint, today_progress, nutrition_intelligence)
    nutrition_os = build_nutrition_os(user, assistant, nutrition_intelligence)
    transformation_dashboard = build_transformation_dashboard(progress_system, recomposition_dashboard, progress_trends, weekly_review)
    wellness_panel = build_wellness_panel(user, scores)
    dashboard_core_widgets = build_dashboard_core_widgets(today_blueprint, today_progress, nutrition_intelligence, session_analytics)
    fast_lane = build_fast_lane(single_next_action, today_blueprint, today_progress, nutrition_intelligence, session_analytics)
    today_agenda = build_today_agenda(personal_calendar, today_blueprint, nutrition_intelligence, today_progress, checkins)
    profile_tools = build_profile_tools(user)
    today_snapshot = build_today_snapshot(today_blueprint, today_progress, nutrition_intelligence, progress_system)
    tactical_cards = build_tactical_cards(today_blueprint, live_session, nutrition_intelligence, weekly_review)
    mission_control = build_mission_control(today_blueprint, today_progress, nutrition_intelligence, coach_briefing, weekly_review)
    quick_capture = build_quick_capture(today_progress, nutrition_intelligence)
    signal_stack = build_signal_stack(notifications, today_progress)
    command_strip = build_command_strip(single_next_action, workspace_hub, profile_tools)
    priority_stack = build_priority_stack(today_blueprint, nutrition_intelligence, daily_tasks, scores)
    train_room = build_train_room(today_blueprint, live_session, session_analytics, exercise_mastery)
    fuel_room = build_fuel_room(nutrition_os, nutrition_intelligence, shopping_list)
    track_room = build_track_room(progress_system, transformation_dashboard, weekly_review)
    train_os = build_train_os(today_blueprint, train_room, live_session, session_analytics)
    fuel_os = build_fuel_os(fuel_room, nutrition_os, shopping_list)
    track_os = build_track_os(track_room, transformation_dashboard, progress_system)
    admin_growth = build_admin_growth(list_users() if user.get("role") == "admin" else [])
    lang = current_language()
    ui = language_pack()
    market_flags = market_readiness_flags()
    admin_users = list_users() if user.get("role") == "admin" else []
    business = business_overview() if user.get("role") == "admin" else None
    view_mode = current_view_mode()
    mode_blueprint = build_mode_blueprint(view_mode)
    fuel_os_pro = build_fuel_os_pro(fuel_os, fuel_room.get("weekly_plan", []), nutrition_intelligence)
    transformation_mode = build_transformation_mode(transformation_dashboard, recomposition_dashboard, progress_system, metrics, photos)
    coach_memory_pro = build_coach_memory_pro(coach_memory, workouts, checkins)
    admin_conversion = build_admin_conversion_cockpit(business, admin_users)
    train_os_pro = build_train_os_pro(train_os, live_session, voice_coach, exercise_mastery)
    transformation_shell = build_transformation_shell(transformation_mode, progress_trends, photos)
    admin_revenue = build_admin_revenue_cockpit(business, admin_users)

    return {
        "seed": seed,
        "lang": lang,
        "ui": ui,
        "languages": list(LANGUAGES.values()),
        "user": {k: v for k, v in user.items() if k != "password_hash"},
        "coaches": COACHES,
        "research": research,
        "workouts": workouts,
        "metrics": metrics,
        "stats": stats,
        "scores": scores,
        "nutrition_stats": nutrition_stats,
        "recommendation": recommendation,
        "assistant": assistant,
        "meal_suggestions": meal_suggestions,
        "daily_mission": daily_mission,
        "achievements": achievements,
        "adaptive_filters": adaptive_filters,
        "folder_cards": folder_cards,
        "section_menu": section_menu,
        "weekly_planner": weekly_planner,
        "today_blueprint": today_blueprint,
        "today_progress": today_progress,
        "live_session": live_session,
        "weekly_review": weekly_review,
        "personal_trainers": personal_trainers,
        "personal_calendar": personal_calendar,
        "pr_tracker": pr_tracker,
        "wellness_panel": wellness_panel,
        "calendar": calendar,
        "meals": meals,
        "exercises": exercises,
        "photos": photos,
        "checkins": checkins,
        "coach_messages": coach_messages,
        "coach_memory": coach_memory,
        "completed_today": list(completed_today),
        "shopping_list": shopping_list,
        "progress_trends": progress_trends,
        "nutrition_intelligence": nutrition_intelligence,
        "adaptive_training_engine": adaptive_training_engine,
        "progress_system": progress_system,
        "periodization_engine": periodization_engine,
        "session_analytics": session_analytics,
        "recomposition_dashboard": recomposition_dashboard,
        "recomposition_home": recomposition_home,
        "weekly_adaptive_block": weekly_adaptive_block,
        "exercise_mastery": exercise_mastery,
        "voice_coach": voice_coach,
        "package_filters": package_filters,
        "active_package": active_package,
        "program_board": program_board,
        "program_builder": program_builder,
        "workspace_hub": workspace_hub,
        "operating_board": operating_board,
        "customer_delight": customer_delight,
        "delight_board": delight_board,
        "home_hub": home_hub,
        "dashboard_core_widgets": dashboard_core_widgets,
        "fast_lane": fast_lane,
        "today_agenda": today_agenda,
        "profile_tools": profile_tools,
        "today_snapshot": today_snapshot,
        "tactical_cards": tactical_cards,
        "mission_control": mission_control,
        "quick_capture": quick_capture,
        "signal_stack": signal_stack,
        "command_strip": command_strip,
        "priority_stack": priority_stack,
        "guided_day_flow": guided_day_flow,
        "nutrition_os": nutrition_os,
        "transformation_dashboard": transformation_dashboard,
        "train_room": train_room,
        "fuel_room": fuel_room,
        "track_room": track_room,
        "train_os": train_os,
        "fuel_os": fuel_os,
        "track_os": track_os,
        "admin_growth": admin_growth,
        "easy_mode": easy_mode,
        "quick_dock": easy_mode["quick_dock"],
        "coach_briefing": coach_briefing,
        "reminder_center": reminder_center,
        "daily_tasks": daily_tasks,
        "single_next_action": single_next_action,
        "day_flow": day_flow,
        "coach_day_flow": coach_day_flow,
        "focus_cards": focus_cards,
        "subscription_plans": SUBSCRIPTION_PLANS,
        "commercial_offers": COMMERCIAL_OFFERS,
        "market_flags": market_flags,
        "access": access,
        "ai_concierge": ai_concierge,
        "notifications": notifications,
        "business": business,
        "fuel_os_pro": fuel_os_pro,
        "transformation_mode": transformation_mode,
        "transformation_shell": transformation_shell,
        "coach_memory_pro": coach_memory_pro,
        "admin_conversion": admin_conversion,
        "admin_revenue": admin_revenue,
        "train_os_pro": train_os_pro,
        "trainers": trainer_profiles(),
        "exercise_library": exercise_library(),
        "food_filters": catalog["filters"],
        "foods": filtered_foods("all", "all", ""),
        "recipes": filtered_recipes("all", "all"),
        "users": admin_users,
        "view_mode": view_mode,
        "mode_blueprint": mode_blueprint,
        "show_full_dashboard": False,
    }


def needs_onboarding(user: dict[str, Any] | None) -> bool:
    return bool(user and not int(user.get("profile_completed", 0)))


@app.route("/")
def home():
    if current_user():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/set-language")
def set_language():
    lang = str(request.args.get("lang") or "me").strip().lower()
    if lang not in LANGUAGES:
        lang = "me"
    session["lang"] = lang
    next_url = str(request.args.get("next") or "/dashboard").strip()
    if not next_url.startswith("/"):
        next_url = "/dashboard"
    return redirect(next_url)


@app.route("/set-view-mode")
@login_required
def set_view_mode():
    mode = str(request.args.get("mode") or "simple").strip().lower()
    if mode == "minimal":
        mode = "simple"
    session["view_mode"] = mode if mode in {"simple", "pro"} else "simple"
    next_url = str(request.args.get("next") or "/dashboard").strip()
    if not next_url.startswith("/"):
        next_url = "/dashboard"
    return redirect(next_url)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("onboarding") if needs_onboarding(current_user()) else url_for("dashboard"))

    if request.method == "POST":
        username = str(request.form.get("username") or "").strip().lower()
        password = str(request.form.get("password") or "")
        user = fetch_user(username)
        if user and check_password_hash(user["password_hash"], password):
            session["username"] = user["username"]
            return redirect(url_for("onboarding") if needs_onboarding(user) else url_for("dashboard"))
        flash("Pogresan username ili password.")

    return render_template_string(INLINE_LOGIN_TEMPLATE, commercial_offers=COMMERCIAL_OFFERS)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("onboarding") if needs_onboarding(current_user()) else url_for("dashboard"))

    if request.method == "POST":
        full_name = str(request.form.get("full_name") or "").strip()[:80]
        username = str(request.form.get("username") or "").strip().lower()[:40]
        password = str(request.form.get("password") or "").strip()

        if not full_name or not username or not password:
            flash("Ime, username i password su obavezni.")
            return render_template_string(INLINE_REGISTER_TEMPLATE, subscription_plans=SUBSCRIPTION_PLANS)
        if len(password) < MIN_PASSWORD_LENGTH:
            flash(f"Password mora imati najmanje {MIN_PASSWORD_LENGTH} karaktera.")
            return render_template_string(INLINE_REGISTER_TEMPLATE, subscription_plans=SUBSCRIPTION_PLANS)

        if fetch_user(username):
            flash("Taj username vec postoji.")
            return render_template_string(INLINE_REGISTER_TEMPLATE, subscription_plans=SUBSCRIPTION_PLANS)

        gender = str(request.form.get("gender") or "male").strip().lower()[:20]
        cycle_phase = "neutral"
        equipment_access = str(request.form.get("equipment_access") or "full gym").strip().lower()[:30]
        fatigue_state = str(request.form.get("fatigue_state") or "steady").strip().lower()[:20]
        age = clamp_int(request.form.get("age"), 25, 13, 100)
        height_cm = clamp_float(request.form.get("height_cm"), 180.0, 100.0, 250.0)
        weight_kg = clamp_float(request.form.get("weight_kg"), 80.0, 30.0, 350.0)
        goal = str(request.form.get("goal") or "performance").strip().lower()[:30]
        experience_level = str(request.form.get("experience_level") or "beginner").strip().lower()[:30]
        subscription_tier = valid_subscription_tier(str(request.form.get("subscription_tier") or "starter").strip().lower())
        trial_started_at = date.today().isoformat()
        trial_ends_at = (date.today() + timedelta(days=TRIAL_DAYS)).isoformat()

        with get_db() as db:
            db.execute(
                """
                INSERT INTO users (
                    username, password_hash, full_name, role, subscription_tier, gender, cycle_phase,
                    billing_status, trial_started_at, trial_ends_at, equipment_access, fatigue_state, age, height_cm, weight_kg,
                    goal, experience_level, profile_completed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    generate_password_hash(password),
                    full_name,
                    "member",
                    subscription_tier,
                    gender,
                    cycle_phase,
                    "trial",
                    trial_started_at,
                    trial_ends_at,
                    equipment_access,
                    fatigue_state,
                    age,
                    height_cm,
                    weight_kg,
                    goal,
                    experience_level,
                    0,
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )

        session["username"] = username
        flash("Nalog je napravljen. Dovrsi svoj profil i filtere.")
        return redirect(url_for("onboarding"))

    return render_template_string(INLINE_REGISTER_TEMPLATE, subscription_plans=SUBSCRIPTION_PLANS)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    if needs_onboarding(user):
        return redirect(url_for("onboarding"))
    payload = dashboard_payload(user)
    return render_template_string(INLINE_DASHBOARD_TEMPLATE, payload=payload, today=date.today().isoformat())


@app.route("/workout-mode")
@login_required
def workout_mode():
    user = current_user()
    if needs_onboarding(user):
        return redirect(url_for("onboarding"))
    payload = dashboard_payload(user)
    return render_template_string(INLINE_WORKOUT_ONLY_TEMPLATE, payload=payload)


@app.route("/hub/<hub_key>")
@login_required
def focus_hub(hub_key: str):
    user = current_user()
    if needs_onboarding(user):
        return redirect(url_for("onboarding"))
    allowed = {"train", "program", "fuel", "coach", "track", "profile", "calendar"}
    if hub_key not in allowed:
        return redirect(url_for("dashboard"))
    payload = dashboard_payload(user)
    meta = focus_hub_meta(hub_key)
    return render_template_string(
        INLINE_FOCUS_HUB_TEMPLATE,
        payload=payload,
        hub_key=hub_key,
        hub_title=meta["title"],
        hub_heading=meta["heading"],
        hub_copy=meta["copy"],
    )


@app.route("/daily-checkin")
@login_required
def daily_checkin_wizard():
    user = current_user()
    if needs_onboarding(user):
        return redirect(url_for("onboarding"))
    payload = dashboard_payload(user)
    return render_template_string(INLINE_DAILY_CHECKIN_TEMPLATE, payload=payload)


@app.route("/nutrition-mode")
@login_required
def nutrition_mode():
    user = current_user()
    if needs_onboarding(user):
        return redirect(url_for("onboarding"))
    payload = dashboard_payload(user)
    return render_template_string(INLINE_NUTRITION_ONLY_TEMPLATE, payload=payload, today=date.today().isoformat())


@app.route("/weekly-reset")
@login_required
def weekly_reset():
    user = current_user()
    if needs_onboarding(user):
        return redirect(url_for("onboarding"))
    payload = dashboard_payload(user)
    return render_template_string(INLINE_WEEKLY_RESET_TEMPLATE, payload=payload)


@app.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    user = current_user()
    if request.method == "POST":
        full_name = str(request.form.get("full_name") or user["full_name"]).strip()[:80]
        gender = str(request.form.get("gender") or user.get("gender") or "male").strip().lower()[:20]
        cycle_phase = str(request.form.get("cycle_phase") or user.get("cycle_phase") or "neutral").strip().lower()[:20]
        equipment_access = str(request.form.get("equipment_access") or user.get("equipment_access") or "full gym").strip().lower()[:30]
        fatigue_state = str(request.form.get("fatigue_state") or user.get("fatigue_state") or "steady").strip().lower()[:20]
        age = clamp_int(request.form.get("age"), int(user["age"]), 13, 100)
        height_cm = clamp_float(request.form.get("height_cm"), float(user["height_cm"]), 100.0, 250.0)
        weight_kg = clamp_float(request.form.get("weight_kg"), float(user["weight_kg"]), 30.0, 350.0)
        goal = str(request.form.get("goal") or user["goal"]).strip().lower()[:30]
        experience_level = str(request.form.get("experience_level") or user["experience_level"]).strip().lower()[:30]

        with get_db() as db:
            db.execute(
                """
                UPDATE users
                SET full_name = ?, gender = ?, cycle_phase = ?, equipment_access = ?, fatigue_state = ?, age = ?, height_cm = ?, weight_kg = ?, goal = ?, experience_level = ?, profile_completed = 1
                WHERE id = ?
                """,
                (full_name, gender, cycle_phase, equipment_access, fatigue_state, age, height_cm, weight_kg, goal, experience_level, int(user["id"])),
            )

        flash("Profil je sacuvan. Forge sada pravi plan za tebe.")
        return redirect(url_for("dashboard"))

    return render_template_string(INLINE_ONBOARDING_TEMPLATE, user=user)


@app.route("/manifest.json")
def manifest():
    return send_from_directory(STATIC_DIR, "manifest.json", mimetype="application/manifest+json")


@app.route("/service-worker.js")
def service_worker():
    response = send_from_directory(STATIC_DIR, "service-worker.js", mimetype="application/javascript")
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/health")
def health():
    return {"status": "ok", "app": "forge"}


@app.route("/terms")
def terms():
    return render_template_string(
        """
        <!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Forge Terms</title></head>
        <body style="margin:0;padding:24px;background:#0b0b0c;color:#f6efdf;font-family:Arial,Helvetica,sans-serif;">
        <div style="max-width:820px;margin:0 auto;">
        <h1>Forge Terms</h1>
        <p>Forge provides fitness planning, tracking and coaching guidance for informational use. Users remain responsible for training choices, medical clearance and safe execution.</p>
        <p>Accounts are personal, subscription access may vary by plan, and abuse or misuse can lead to suspension.</p>
        <p><a href="/login" style="color:#ffb000;">Back to app</a></p>
        </div></body></html>
        """
    )


@app.route("/privacy")
def privacy():
    return render_template_string(
        """
        <!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Forge Privacy</title></head>
        <body style="margin:0;padding:24px;background:#0b0b0c;color:#f6efdf;font-family:Arial,Helvetica,sans-serif;">
        <div style="max-width:820px;margin:0 auto;">
        <h1>Forge Privacy</h1>
        <p>Forge stores account, training, nutrition and progress data to personalize coaching, planning and analytics.</p>
        <p>Sensitive data should be protected in production with secure hosting, backups, environment-managed secrets and proper access controls.</p>
        <p><a href="/login" style="color:#ffb000;">Back to app</a></p>
        </div></body></html>
        """
    )


@app.route("/app-version")
def app_version():
    return {
        "build": "APP.PY ONLY BUILD V59",
        "login_title": "Secure athlete login V59",
        "dashboard_title": "Adaptive athlete dashboard V59",
    }


@app.route("/api/dashboard")
@login_required
def dashboard_api():
    return jsonify(dashboard_payload(current_user()))


@app.route("/api/nutrition")
@login_required
def nutrition_api():
    goal = str(request.args.get("goal") or "all").strip().lower()
    meal_type = str(request.args.get("meal_type") or "all").strip().lower()
    search = str(request.args.get("q") or "")
    return jsonify(
        {
            "foods": filtered_foods(goal, meal_type, search),
            "recipes": filtered_recipes(goal, meal_type),
            "filters": catalog_payload()["filters"],
        }
    )


@app.route("/api/exercises")
@login_required
def exercises_api():
    query = str(request.args.get("q") or "").strip().lower()
    goal = str(request.args.get("goal") or "all").strip().lower()
    items = []
    for item in exercise_library():
        haystack = f'{item["name"]} {item["category"]} {item["muscle_group"]}'.lower()
        if query and query not in haystack:
            continue
        if goal != "all" and item["best_for"] != goal:
            continue
        items.append(item)
    return jsonify({"exercises": items})


@app.route("/api/recommendation", methods=["POST"])
@login_required
def recommendation_api():
    research = load_json(RESEARCH_FILE)["sources"]
    user = current_user()
    workouts = recent_workouts(int(user["id"]))
    data = request.get_json(silent=True) or {}
    coach_key = str(data.get("coach") or "strength")
    mood = str(data.get("mood") or "steady").strip().lower()
    energy = clamp_int(data.get("energy"), 7, 1, 10)
    equipment = str(data.get("equipment") or "full gym").strip().lower()
    minutes = clamp_int(data.get("minutes"), 75, 20, 180)
    goal = str(data.get("goal") or "performance").strip().lower()
    recommendation = build_recommendation(coach_key, mood, energy, equipment, minutes, goal, workouts, research)
    return jsonify(recommendation)


@app.route("/api/assistant-plan", methods=["POST"])
@login_required
def assistant_plan_api():
    user = current_user()
    data = request.get_json(silent=True) or {}
    energy = clamp_int(data.get("energy"), 7, 1, 10)
    training_days = clamp_int(data.get("training_days"), 4, 2, 7)
    workouts = recent_workouts(int(user["id"]))
    metrics = recent_metrics(int(user["id"]))
    meals = recent_meals(int(user["id"]))
    calendar = calendar_items(int(user["id"]))
    return jsonify(build_assistant_plan(user, workouts, metrics, meals, calendar, energy=energy, training_days=training_days))


@app.route("/plan/select", methods=["POST"])
@login_required
def select_plan():
    user = current_user()
    title = str(request.form.get("title") or "Selected plan").strip()[:120]
    details = str(request.form.get("details") or "").strip()[:300]
    coach_key = str(request.form.get("coach_key") or "strength").strip()[:40]
    event_date = (date.today() + timedelta(days=1)).isoformat()

    with get_db() as db:
        db.execute(
            """
            INSERT INTO calendar_events (
                user_id, event_date, event_type, title, details, coach_key, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user["id"]),
                event_date,
                "training",
                title,
                details,
                coach_key,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )

    flash(f"Izabran plan: {title}. Dodat je u tvoj kalendar.")
    return redirect(url_for("dashboard") + "#calendar")


@app.route("/subscribe", methods=["POST"])
@login_required
def subscribe():
    user = current_user()
    tier = valid_subscription_tier(str(request.form.get("subscription_tier") or "starter").strip().lower())
    if tier == "starter":
        flash(f"Starter je vec ukljucen kao besplatan full trial od {TRIAL_DAYS} dana.")
        return redirect(url_for("dashboard") + "#market")
    discount = resolve_discount_code(request.form.get("discount_code"))
    with get_db() as db:
        db.execute(
            """
            UPDATE users
            SET subscription_tier = ?, billing_status = ?, gift_package = 0, gifted_by = '', discount_code = ?, discount_percent = ?
            WHERE id = ?
            """,
            (tier, "active" if tier == "starter" else "paid", discount["code"], discount["percent"], int(user["id"])),
        )
    if discount["percent"] > 0:
        flash(f"Paket {tier.title()} je aktiviran uz kod {discount['code']} i popust od {discount['percent']}%.")
    elif discount["code"]:
        flash(f"Paket {tier.title()} je aktiviran, ali kod {discount['code']} nije validan.")
    else:
        flash(f"Paket {tier.title()} je aktiviran.")
    return redirect(url_for("dashboard") + "#market")


@app.route("/admin/gift-package", methods=["POST"])
@admin_required
def admin_gift_package():
    admin = current_user()
    user_id = clamp_int(request.form.get("user_id"), 0, 0, 10_000_000)
    tier = valid_subscription_tier(str(request.form.get("subscription_tier") or "pro").strip().lower(), "pro")
    gift_note = str(request.form.get("gift_note") or "").strip()

    if not user_id:
        flash("Izaberi korisnika za gift paket.")
        return redirect(url_for("dashboard") + "#admin")

    with get_db() as db:
        db.execute(
            """
            UPDATE users
            SET subscription_tier = ?, billing_status = 'gifted', gift_package = 1, gifted_by = ?, discount_code = ?, discount_percent = 100
            WHERE id = ? AND role != 'admin'
            """,
            (tier, admin["username"], f"GIFT:{gift_note[:30] if gift_note else 'ADMIN'}", user_id),
        )

    flash(f"Gift paket {tier.title()} je dodijeljen korisniku.")
    return redirect(url_for("dashboard") + "#admin")


@app.route("/assistant/chat", methods=["POST"])
@login_required
def assistant_chat():
    user = current_user()
    access = subscription_access_state(user)
    ai_concierge = build_ai_concierge(user, access)
    if not ai_concierge["enabled"]:
        flash("Puni AI trener je dostupan u Elite paketu ili tokom trial perioda.")
        return redirect(url_for("dashboard") + "#ai-trainer")
    message = str(request.form.get("message") or "").strip()[:500]
    if not message:
        flash("Unesi poruku za AI trenera.")
        return redirect(url_for("dashboard") + "#ai-trainer")

    workouts = recent_workouts(int(user["id"]))
    metrics = recent_metrics(int(user["id"]))
    meals = recent_meals(int(user["id"]))
    calendar = calendar_items(int(user["id"]))
    checkins = recent_checkins(int(user["id"]))
    memory = coach_memory_items(int(user["id"]))
    assistant = build_assistant_plan(user, workouts, metrics, meals, calendar, training_days=goal_training_days(user))
    today_blueprint = build_today_blueprint(user, assistant, workouts, calendar)
    reply = build_ai_trainer_reply(user, message, assistant, today_blueprint, checkins, ai_concierge, memory)

    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_db() as db:
        db.execute(
            "INSERT INTO coach_messages (user_id, sender, message, created_at) VALUES (?, ?, ?, ?)",
            (int(user["id"]), "user", message, now),
        )
        db.execute(
            "INSERT INTO coach_messages (user_id, sender, message, created_at) VALUES (?, ?, ?, ?)",
            (int(user["id"]), "coach", reply, now),
        )

    flash("AI trener ti je poslao novi odgovor.")
    return redirect(url_for("dashboard") + "#ai-trainer")


@app.route("/today/check", methods=["POST"])
@login_required
def mark_today_check():
    user = current_user()
    item_type = str(request.form.get("item_type") or "").strip().lower()[:20]
    item_key = str(request.form.get("item_key") or "").strip()[:120]
    is_xhr = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if item_type not in {"exercise", "meal", "set"} or not item_key:
        if is_xhr:
            return {"ok": False, "message": "Today check nije prosao."}, 400
        flash("Nije prosao today check.")
        return redirect(url_for("dashboard") + "#today-plan")

    today_key = date.today().isoformat()
    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM daily_plan_checks WHERE user_id = ? AND check_date = ? AND item_type = ? AND item_key = ?",
            (int(user["id"]), today_key, item_type, item_key),
        ).fetchone()
        if existing:
            db.execute("UPDATE daily_plan_checks SET completed = 1 WHERE id = ?", (int(existing["id"]),))
        else:
            db.execute(
                """
                INSERT INTO daily_plan_checks (user_id, check_date, item_type, item_key, completed, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (int(user["id"]), today_key, item_type, item_key, 1, datetime.utcnow().isoformat(timespec="seconds")),
            )

    if is_xhr:
        return {"ok": True, "item_type": item_type, "item_key": item_key}
    flash("Danasnji zadatak je oznacen kao zavrsen.")
    return redirect(url_for("dashboard") + "#today-plan")


@app.route("/coach-memory", methods=["POST"])
@login_required
def save_coach_memory():
    user = current_user()
    memory_text = str(request.form.get("memory_text") or "").strip()[:300]
    if not memory_text:
        flash("Unesi biljesku za AI trenera.")
        return redirect(url_for("dashboard") + "#ai-trainer")
    with get_db() as db:
        db.execute(
            "INSERT INTO coach_memory (user_id, memory_type, memory_text, created_at) VALUES (?, ?, ?, ?)",
            (int(user["id"]), "preference", memory_text, datetime.utcnow().isoformat(timespec="seconds")),
        )
    flash("Coach memory je sacuvan.")
    return redirect(url_for("dashboard") + "#ai-trainer")


@app.route("/checkin/daily", methods=["POST"])
@login_required
def daily_checkin():
    user = current_user()
    mood = str(request.form.get("mood") or "steady").strip().lower()[:30]
    energy_score = clamp_int(request.form.get("energy_score"), 7, 1, 10)
    soreness_score = clamp_int(request.form.get("soreness_score"), 4, 1, 10)
    motivation_score = clamp_int(request.form.get("motivation_score"), 7, 1, 10)
    note = str(request.form.get("note") or "").strip()[:400]
    today_key = date.today().isoformat()

    with get_db() as db:
        db.execute(
            """
            INSERT INTO daily_checkins (
                user_id, checkin_date, mood, energy_score, soreness_score, motivation_score, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (int(user["id"]), today_key, mood, energy_score, soreness_score, motivation_score, note, datetime.utcnow().isoformat(timespec="seconds")),
        )

    flash("Daily check-in je sacuvan.")
    return redirect(url_for("dashboard") + "#ai-trainer")


@app.route("/admin/users", methods=["POST"])
@admin_required
def create_user():
    username = str(request.form.get("username") or "").strip().lower()[:40]
    password = str(request.form.get("password") or "").strip()
    full_name = str(request.form.get("full_name") or "").strip()[:80]

    if not username or not password or not full_name:
        flash("Username, password i puno ime su obavezni.")
        return redirect(url_for("dashboard") + "#admin")
    if len(password) < MIN_PASSWORD_LENGTH:
        flash(f"Password mora imati najmanje {MIN_PASSWORD_LENGTH} karaktera.")
        return redirect(url_for("dashboard") + "#admin")

    if fetch_user(username):
        flash("Taj username vec postoji.")
        return redirect(url_for("dashboard") + "#admin")

    age = clamp_int(request.form.get("age"), 25, 13, 100)
    gender = str(request.form.get("gender") or "male").strip().lower()[:20]
    cycle_phase = str(request.form.get("cycle_phase") or "neutral").strip().lower()[:20]
    equipment_access = str(request.form.get("equipment_access") or "full gym").strip().lower()[:30]
    fatigue_state = str(request.form.get("fatigue_state") or "steady").strip().lower()[:20]
    height_cm = clamp_float(request.form.get("height_cm"), 180.0, 100.0, 250.0)
    weight_kg = clamp_float(request.form.get("weight_kg"), 80.0, 30.0, 350.0)
    goal = str(request.form.get("goal") or "performance").strip().lower()[:30]
    experience_level = str(request.form.get("experience_level") or "intermediate").strip().lower()[:30]
    subscription_tier = valid_subscription_tier(str(request.form.get("subscription_tier") or "starter").strip().lower(), "starter")
    role = "admin" if str(request.form.get("role") or "member").strip().lower() == "admin" else "member"
    trial_started_at = date.today().isoformat() if role == "member" else ""
    trial_ends_at = (date.today() + timedelta(days=TRIAL_DAYS)).isoformat() if role == "member" else ""
    billing_status = "trial" if role == "member" else "active"

    with get_db() as db:
        db.execute(
            """
            INSERT INTO users (
                username, password_hash, full_name, role, subscription_tier, billing_status, trial_started_at, trial_ends_at, gender, cycle_phase, equipment_access, fatigue_state, age, height_cm, weight_kg, goal, experience_level, profile_completed, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                generate_password_hash(password),
                full_name,
                role,
                subscription_tier,
                billing_status,
                trial_started_at,
                trial_ends_at,
                gender,
                cycle_phase,
                equipment_access,
                fatigue_state,
                age,
                height_cm,
                weight_kg,
                goal,
                experience_level,
                0 if role == "member" else 1,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )

    flash(f"Korisnik {username} je napravljen.")
    return redirect(url_for("dashboard") + "#admin")


@app.route("/log-workout", methods=["POST"])
@login_required
def log_workout():
    user = current_user()
    workout_date = str(request.form.get("workout_date") or date.today().isoformat())
    coach_key = str(request.form.get("coach_key") or "strength")
    focus = str(request.form.get("focus") or "Custom session").strip()[:120]
    duration = clamp_int(request.form.get("duration_minutes"), 60, 10, 240)
    volume = clamp_int(request.form.get("volume_load"), 0, 0, 500000)
    energy = clamp_int(request.form.get("energy_score"), 7, 1, 10)
    effort = clamp_int(request.form.get("effort_score"), 8, 1, 10)
    notes = str(request.form.get("notes") or "").strip()[:500]

    with get_db() as db:
        db.execute(
            """
            INSERT INTO workout_logs (
                user_id, workout_date, coach_key, focus, duration_minutes, volume_load,
                energy_score, effort_score, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user["id"]),
                workout_date,
                coach_key,
                focus,
                duration,
                volume,
                energy,
                effort,
                notes,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
    return redirect(url_for("dashboard") + "#track")


@app.route("/log-metric", methods=["POST"])
@login_required
def log_metric():
    user = current_user()
    metric_date = str(request.form.get("metric_date") or date.today().isoformat())
    body_weight = clamp_float(request.form.get("body_weight"), 80.0, 30.0, 300.0)
    body_fat = clamp_float(request.form.get("body_fat"), 15.0, 2.0, 60.0)
    chest = clamp_float(request.form.get("chest"), 100.0, 50.0, 200.0)
    waist = clamp_float(request.form.get("waist"), 80.0, 40.0, 200.0)
    arm = clamp_float(request.form.get("arm"), 35.0, 15.0, 80.0)
    thigh = clamp_float(request.form.get("thigh"), 55.0, 20.0, 100.0)
    sleep_hours = clamp_float(request.form.get("sleep_hours"), 8.0, 0.0, 24.0)
    steps = clamp_int(request.form.get("steps"), 8000, 0, 100000)
    form_score = clamp_int(request.form.get("form_score"), 7, 1, 10)
    checkin_note = str(request.form.get("checkin_note") or "").strip()[:500]

    with get_db() as db:
        db.execute(
            """
            INSERT INTO body_metrics (
                user_id, metric_date, body_weight, body_fat, chest, waist, arm, thigh,
                sleep_hours, steps, form_score, checkin_note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user["id"]),
                metric_date,
                body_weight,
                body_fat,
                chest,
                waist,
                arm,
                thigh,
                sleep_hours,
                steps,
                form_score,
                checkin_note,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
    return redirect(url_for("dashboard") + "#metrics")


@app.route("/log-meal", methods=["POST"])
@login_required
def log_meal():
    user = current_user()
    logged_at = str(request.form.get("logged_at") or datetime.now().strftime("%Y-%m-%dT%H:%M"))
    meal_type = str(request.form.get("meal_type") or "meal").strip()[:30]
    food_name = str(request.form.get("food_name") or "Custom food").strip()[:120]
    grams = clamp_float(request.form.get("grams"), 100.0, 1.0, 5000.0)
    calories = clamp_float(request.form.get("calories"), 0.0, 0.0, 10000.0)
    protein = clamp_float(request.form.get("protein"), 0.0, 0.0, 1000.0)
    carbs = clamp_float(request.form.get("carbs"), 0.0, 0.0, 1000.0)
    fats = clamp_float(request.form.get("fats"), 0.0, 0.0, 1000.0)
    goal_tag = str(request.form.get("goal_tag") or "performance").strip()[:30]
    notes = str(request.form.get("notes") or "").strip()[:300]

    with get_db() as db:
        db.execute(
            """
            INSERT INTO meal_logs (
                user_id, logged_at, meal_type, food_name, grams, calories, protein, carbs,
                fats, goal_tag, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user["id"]),
                logged_at,
                meal_type,
                food_name,
                grams,
                calories,
                protein,
                carbs,
                fats,
                goal_tag,
                notes,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
    return redirect(url_for("dashboard") + "#nutrition")


@app.route("/log-exercise", methods=["POST"])
@login_required
def log_exercise():
    user = current_user()
    logged_at = str(request.form.get("logged_at") or datetime.now().strftime("%Y-%m-%dT%H:%M"))
    exercise_name = str(request.form.get("exercise_name") or "Custom exercise").strip()[:120]
    category = str(request.form.get("category") or "strength").strip()[:40]
    muscle_group = str(request.form.get("muscle_group") or "full body").strip()[:60]
    sets_count = clamp_int(request.form.get("sets_count"), 3, 1, 20)
    reps_text = str(request.form.get("reps_text") or "8,8,8").strip()[:120]
    weight_kg = clamp_float(request.form.get("weight_kg"), 0.0, 0.0, 1000.0)
    rpe = clamp_float(request.form.get("rpe"), 8.0, 1.0, 10.0)
    coach_key = str(request.form.get("coach_key") or "strength").strip()[:40]
    notes = str(request.form.get("notes") or "").strip()[:300]

    with get_db() as db:
        db.execute(
            """
            INSERT INTO exercise_logs (
                user_id, logged_at, exercise_name, category, muscle_group, sets_count, reps_text,
                weight_kg, rpe, coach_key, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user["id"]),
                logged_at,
                exercise_name,
                category,
                muscle_group,
                sets_count,
                reps_text,
                weight_kg,
                rpe,
                coach_key,
                notes,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
    return redirect(url_for("dashboard") + "#exercise")


@app.route("/log-photo", methods=["POST"])
@login_required
def log_photo():
    user = current_user()
    photo_date = str(request.form.get("photo_date") or date.today().isoformat())
    pose = str(request.form.get("pose") or "Front").strip()[:40]
    mood = str(request.form.get("mood") or "Sharp").strip()[:40]
    lighting_score = clamp_int(request.form.get("lighting_score"), 8, 1, 10)
    visual_score = clamp_int(request.form.get("visual_score"), 8, 1, 10)
    photo_url = str(request.form.get("photo_url") or "").strip()[:500]
    notes = str(request.form.get("notes") or "").strip()[:300]

    if not photo_url:
        photo_url = "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=900&q=80"

    with get_db() as db:
        db.execute(
            """
            INSERT INTO progress_photos (
                user_id, photo_date, pose, mood, lighting_score, visual_score, photo_url, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user["id"]),
                photo_date,
                pose,
                mood,
                lighting_score,
                visual_score,
                photo_url,
                notes,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
    return redirect(url_for("dashboard") + "#gallery")


@app.route("/calendar/add", methods=["POST"])
@login_required
def add_calendar_event():
    user = current_user()
    event_date = str(request.form.get("event_date") or date.today().isoformat())
    event_type = str(request.form.get("event_type") or "training").strip()[:40]
    title = str(request.form.get("title") or "Planned session").strip()[:120]
    details = str(request.form.get("details") or "").strip()[:300]
    coach_key = str(request.form.get("coach_key") or "strength").strip()[:40]

    with get_db() as db:
        db.execute(
            """
            INSERT INTO calendar_events (
                user_id, event_date, event_type, title, details, coach_key, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user["id"]),
                event_date,
                event_type,
                title,
                details,
                coach_key,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )

    return redirect(url_for("dashboard") + "#calendar")


@app.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    user = current_user()
    full_name = str(request.form.get("full_name") or user["full_name"]).strip()[:80]
    gender = str(request.form.get("gender") or user.get("gender") or "male").strip().lower()[:20]
    age = clamp_int(request.form.get("age"), int(user["age"]), 13, 100)
    height_cm = clamp_float(request.form.get("height_cm"), float(user["height_cm"]), 100.0, 250.0)
    weight_kg = clamp_float(request.form.get("weight_kg"), float(user["weight_kg"]), 30.0, 350.0)
    goal = str(request.form.get("goal") or user["goal"]).strip().lower()[:30]
    experience_level = str(request.form.get("experience_level") or user["experience_level"]).strip().lower()[:30]

    with get_db() as db:
        db.execute(
            """
            UPDATE users
            SET full_name = ?, gender = ?, age = ?, height_cm = ?, weight_kg = ?, goal = ?, experience_level = ?, profile_completed = 1
            WHERE id = ?
            """,
            (full_name, gender, age, height_cm, weight_kg, goal, experience_level, int(user["id"])),
        )

    flash("Profil je aĹľuriran i preporuke su osvjeĹľene.")
    return redirect(url_for("dashboard") + "#profile")


init_db()


if __name__ == "__main__":
    app.run(debug=True, port=5055)


