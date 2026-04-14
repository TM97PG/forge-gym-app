from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any

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
DEFAULT_ADMIN_PASSWORD = os.environ.get("FORGE_ADMIN_PASSWORD", "daljamtelemont1")
DEFAULT_MITAR_USERNAME = os.environ.get("FORGE_MITAR_USERNAME", "mitar")
DEFAULT_MITAR_PASSWORD = os.environ.get("FORGE_MITAR_PASSWORD", "mitar12345")
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
    <div class="pill">APP.PY ONLY BUILD V22</div>
          <div class="eyebrow" style="margin-top:10px;">Forge Athlete OS</div>
        </div>
      </div>
      <div class="mini">Premium gym performance system</div>
    </div>
    <h1>Secure athlete login V22</h1>
    <p>Svaki korisnik ima svoj nalog, svoje godine, visinu, kilazu, cilj, predlozene treninge, ishranu i svoj kalendar. Forge sada izgleda i radi kao premium fitness proizvod spreman za prodaju.</p>
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
        <p>ÄŚist ulaz bez hintova, sa odvojenim nalozima i zasebnim planovima za svakog korisnika.</p>
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
<body>
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
    :root { --bg:#050505; --panel:rgba(17,17,19,.92); --line:rgba(255,255,255,.08); --text:#f7efdf; --muted:#baa992; --orange:#f15a24; --gold:#ffb000; --red:#cf3342; --green:#4eba72; }
    * { box-sizing:border-box; } html { scroll-behavior:smooth; }
    body { margin:0; color:var(--text); background:radial-gradient(circle at top left, rgba(241,90,36,.18), transparent 24%), radial-gradient(circle at right 18%, rgba(255,176,0,.16), transparent 20%), linear-gradient(180deg,#050505,#101112 58%,#070707); font-family:Arial,Helvetica,sans-serif; }
    .shell { width:min(1280px, calc(100vw - 24px)); margin:0 auto; padding:16px 0 110px; }
    .topbar,.hero,.panel,.option,.flash { background:var(--panel); border:1px solid var(--line); border-radius:26px; box-shadow:0 28px 90px rgba(0,0,0,.42); }
    .topbar { display:grid; grid-template-columns:1fr auto; gap:12px; align-items:center; padding:14px 16px; position:sticky; top:10px; z-index:4; backdrop-filter:blur(18px); margin-bottom:14px; }
    .toplinks { display:grid; grid-auto-flow:column; gap:10px; align-items:start; }
    .toplinks a,.logout,.pill,.tag { display:inline-flex; align-items:center; justify-content:center; padding:10px 12px; border-radius:999px; text-decoration:none; color:inherit; font-size:11px; text-transform:uppercase; letter-spacing:.12em; font-weight:800; }
    .pill,.logout { color:#17110a; background:linear-gradient(135deg,var(--orange),var(--gold)); }
    .toplinks a,.tag { border:1px solid var(--line); background:rgba(255,255,255,.05); }
    .hero { padding:28px; background:linear-gradient(135deg, rgba(241,90,36,.18), rgba(12,12,13,.96) 34%, rgba(255,176,0,.1)); }
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
    .kpi,.option,.log,.user-card { border-radius:22px; background:rgba(24,24,26,.98); border:1px solid rgba(255,255,255,.06); }
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
    .folder-menu { display:flex; gap:10px; overflow:auto; padding:10px 2px 2px; margin-top:14px; scrollbar-width:none; }
    .folder-menu::-webkit-scrollbar { display:none; }
    .folder-menu a { white-space:nowrap; text-decoration:none; color:var(--text); padding:12px 14px; border-radius:16px; border:1px solid var(--line); background:rgba(255,255,255,.05); font-size:12px; font-weight:800; letter-spacing:.05em; }
    .summary-strip { display:grid; grid-template-columns:1.1fr .9fr; gap:16px; margin-top:18px; }
    .summary-card { padding:18px; border-radius:22px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .task-meter { height:10px; width:100%; border-radius:999px; background:rgba(255,255,255,.06); overflow:hidden; margin-top:12px; }
    .task-meter span { display:block; height:100%; background:linear-gradient(135deg,var(--orange),var(--gold)); }
    .today-badge { display:inline-flex; padding:8px 12px; border-radius:999px; background:rgba(78,186,114,.14); border:1px solid rgba(78,186,114,.24); font-size:12px; font-weight:800; }
    .queue-list { display:grid; gap:10px; margin-top:14px; }
    .queue-row { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; padding:12px 14px; border-radius:16px; border:1px solid var(--line); background:rgba(255,255,255,.04); }
    .queue-row.done { opacity:.62; }
    .player-card { padding:20px; border-radius:26px; border:1px solid var(--line); background:linear-gradient(160deg, rgba(255,176,0,.1), rgba(255,255,255,.03) 45%, rgba(241,90,36,.1)); }
    .player-top { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
    .player-screen { margin-top:16px; padding:24px; border-radius:24px; background:rgba(0,0,0,.22); border:1px solid rgba(255,255,255,.06); text-align:center; }
    .player-time { font-size:clamp(42px, 8vw, 74px); font-family:Georgia,serif; line-height:1; margin:12px 0; }
    .player-controls { display:flex; justify-content:center; gap:12px; margin-top:16px; flex-wrap:wrap; }
    .player-btn { min-width:64px; min-height:64px; border-radius:999px; border:1px solid var(--line); background:rgba(255,255,255,.06); color:var(--text); font-size:18px; font-weight:900; display:inline-flex; align-items:center; justify-content:center; }
    .player-btn.primary { background:linear-gradient(135deg,var(--orange),var(--gold)); color:#17110a; }
    .player-meta { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:16px; }
    .player-meta .log { padding:14px; text-align:center; }
    .bottom { position:fixed; left:12px; right:12px; bottom:12px; display:none; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; padding:10px; background:rgba(15,15,16,.92); border:1px solid var(--line); border-radius:22px; backdrop-filter:blur(18px); }
    .bottom a { padding:12px 8px; text-decoration:none; text-align:center; border-radius:14px; font-size:12px; color:var(--muted); font-weight:800; }
    .bottom a:first-child { background:linear-gradient(135deg,var(--orange),var(--gold)); color:#17110a; }
    @media (max-width: 980px) { .page,.panel-grid,.hero-kpis,.grid3,.grid4,.users-grid,.quickbar,.meal-grid,.mission-grid,.achievement-grid,.folder-grid,.filter-grid,.planner-grid,.pr-grid,.coach-grid,.today-grid,.calendar-lane,.trend-grid,.chat-grid,.pricing-grid,.today-kpis,.summary-strip,.session-grid { grid-template-columns:1fr 1fr; } .topbar { grid-template-columns:1fr; } .top-nav-links { justify-content:flex-start; } }
    @media (max-width: 760px) { .shell { width:min(100vw - 14px,100%); } .page,.panel-grid,.hero-kpis,.grid3,.grid4,.users-grid,.quickbar,.form2,.meal-grid,.mission-grid,.achievement-grid,.folder-grid,.filter-grid,.planner-grid,.pr-grid,.coach-grid,.today-grid,.calendar-lane,.trend-grid,.chat-grid,.pricing-grid,.today-kpis,.summary-strip,.session-grid,.player-meta { grid-template-columns:1fr; } .hero,.panel { padding:18px; } .bottom { display:grid; bottom:max(12px, env(safe-area-inset-bottom)); } .lang-switch { justify-content:start; grid-auto-flow:row; } .folder-menu { margin-top:12px; padding-bottom:4px; } }
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div>
        <div class="mini">Forge athlete OS</div>
          <strong style="display:block;margin-top:6px;font-size:20px;">APP.PY ONLY BUILD V22</strong>
      </div>
      <div class="toplinks">
        <div class="lang-switch">
          {% for item in payload.languages %}
          <a class="lang-chip {% if item.code == payload.lang %}active{% endif %}" href="/set-language?lang={{ item.code }}&next=/dashboard">{{ item.flag }} {{ item.name }}</a>
          {% endfor %}
        </div>
        <div class="top-nav-links">
          <a href="#folders">Hub {{ payload.ui.folders }}</a>
          <a href="#plans">Coach {{ payload.ui.plans }}</a>
          <a href="#calendar">Daily {{ payload.ui.calendar }}</a>
          <a href="#admin">Admin {{ payload.ui.users }}</a>
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
          <p>{{ payload.ui.hero_text }}</p>
        </div>
        <div class="pill">Market ready + dashboard V22</div>
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
          <p>{{ payload.user.experience_level|title }} athlete with personal dashboard and assistant.</p>
        </div>
      </div>
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
      <div class="quickbar">
        <a href="#folders">Open {{ payload.ui.folders }}</a>
        <a href="#plans">View {{ payload.ui.plans }}</a>
        <a href="#assistant">Open {{ payload.ui.assistant_title }}</a>
        <a href="#profile">Edit profile</a>
      </div>
      <div class="filter-grid">
        {% for item in payload.adaptive_filters %}
        <article class="kpi">
          <span class="mini">{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
        {% endfor %}
      </div>
      <nav class="folder-menu" aria-label="Section menu">
        {% for item in payload.section_menu %}
        <a href="{{ item.anchor }}">{{ item.title }}</a>
        {% endfor %}
      </nav>
    </section>

    <section class="panel span" id="folders">
      <div class="section-head">
        <div><div class="mini">{{ payload.ui.folders }}</div><h2>{{ payload.ui.mobile_center }}</h2></div>
      </div>
      <div class="folder-grid">
        {% for item in payload.folder_cards %}
        <a href="{{ item.anchor }}" class="option" style="text-decoration:none;">
          <div class="mini">Folder</div>
          <strong>{{ item.title }}</strong>
          <p>{{ item.detail }}</p>
        </a>
        {% endfor %}
      </div>
    </section>

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
            <p>{{ option.summary }}</p>
            <ul class="list">
              {% for bullet in option.blocks %}
              <li>{{ bullet }}</li>
              {% endfor %}
            </ul>
            <div class="notice">Nutrition: {{ option.nutrition }}</div>
            <form method="post" action="/plan/select" style="margin-top:14px;">
              <input type="hidden" name="title" value="{{ option.title }}">
              <input type="hidden" name="coach_key" value="{{ option.coach_key }}">
              <input type="hidden" name="details" value="{{ option.summary }}">
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
        <div class="session-grid">
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
              <p id="player-status">{{ payload.live_session.coach_prompt }}</p>
              <div class="player-controls">
                <button type="button" class="player-btn primary" id="player-play" aria-label="Play workout">Play</button>
                <button type="button" class="player-btn" id="player-pause" aria-label="Pause workout">Pause</button>
                <button type="button" class="player-btn" id="player-reset" aria-label="Reset timer">Reset</button>
              </div>
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
              <div class="queue-row {% if item.done %}done{% endif %}">
                <div>
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
                <strong style="display:block;margin-top:6px;">{{ item.name }}</strong>
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
      </section>

      <section class="panel" id="assistant">
        <div class="section-head">
          <div><div class="mini">Assistant</div><h2>{{ payload.ui.assistant_title }}</h2></div>
        </div>
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
      </section>

      <section class="panel" id="mission">
        <div class="section-head">
          <div><div class="mini">Daily mission</div><h2>{{ payload.ui.mission_title }}</h2></div>
        </div>
        <div class="log">
          <ul class="list">
            {% for item in payload.daily_mission %}
            <li>{{ item }}</li>
            {% endfor %}
          </ul>
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
      </section>

      <section class="panel span" id="progress">
        <div class="section-head">
          <div><div class="mini">Progress</div><h2>{{ payload.ui.progress_title }}</h2></div>
        </div>
        <div class="trend-grid">
          {% for item in payload.progress_trends %}
          <article class="kpi">
            <span class="mini">{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.detail }}</p>
          </article>
          {% endfor %}
        </div>
      </section>

      <section class="panel span" id="market">
        <div class="section-head">
          <div><div class="mini">Launch</div><h2>{{ payload.ui.pricing_title }}</h2></div>
        </div>
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
      </section>

      <section class="panel" id="wellness">
        <div class="section-head">
          <div><div class="mini">{{ payload.ui.wellness_title }}</div><h2>{{ payload.wellness_panel.title }}</h2></div>
        </div>
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
      </section>

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

    <nav class="bottom">
      <a href="#today-plan">Today</a>
      <a href="#plans">Plans</a>
      <a href="#mission">Meals</a>
      <a href="#ai-trainer">Coach</a>
      <a href="#profile">Profile</a>
    </nav>
  </div>
  <script>
    (function () {
      const player = document.getElementById("workout-player");
      if (!player) return;
      const timerNode = document.getElementById("player-timer");
      const statusNode = document.getElementById("player-status");
      const playBtn = document.getElementById("player-play");
      const pauseBtn = document.getElementById("player-pause");
      const resetBtn = document.getElementById("player-reset");

      function parseRest(value) {
        const text = String(value || "").toLowerCase();
        const match = text.match(/(\\d+)/);
        return match ? Number(match[1]) : 60;
      }

      const defaultSeconds = parseRest(player.dataset.rest);
      let secondsLeft = defaultSeconds;
      let intervalId = null;

      function renderTime() {
        const mins = String(Math.floor(secondsLeft / 60)).padStart(2, "0");
        const secs = String(secondsLeft % 60).padStart(2, "0");
        timerNode.textContent = mins + ":" + secs;
      }

      function startTimer() {
        if (intervalId) return;
        statusNode.textContent = "Workout in progress. Follow the current block, then use the timer between sets.";
        intervalId = window.setInterval(function () {
          if (secondsLeft > 0) {
            secondsLeft -= 1;
            renderTime();
            return;
          }
          window.clearInterval(intervalId);
          intervalId = null;
          statusNode.textContent = "Rest block finished. Move to the next set or next exercise.";
        }, 1000);
      }

      function pauseTimer() {
        if (intervalId) {
          window.clearInterval(intervalId);
          intervalId = null;
        }
        statusNode.textContent = "Timer paused. Resume when you are ready.";
      }

      function resetTimer() {
        if (intervalId) {
          window.clearInterval(intervalId);
          intervalId = null;
        }
        secondsLeft = defaultSeconds;
        renderTime();
        statusNode.textContent = "Timer reset. Press play to begin the next rest block.";
      }

      renderTime();
      playBtn.addEventListener("click", startTimer);
      pauseBtn.addEventListener("click", pauseTimer);
      resetBtn.addEventListener("click", resetTimer);
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
    @media (max-width: 760px) { form,.grid { grid-template-columns:1fr; } .card { padding:20px; } h1 { font-size:34px; } }
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
    <form method="post">
      <label>Ime i prezime<input type="text" name="full_name" value="{{ user.full_name }}" required></label>
      <label>Pol
        <select name="gender">
          <option value="male" {% if user.gender == 'male' %}selected{% endif %}>Musko</option>
          <option value="female" {% if user.gender == 'female' %}selected{% endif %}>Zensko</option>
        </select>
      </label>
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
      <label>Godine<input type="number" name="age" value="{{ user.age }}" min="13" max="100" required></label>
      <label>Visina cm<input type="number" step="0.1" name="height_cm" value="{{ user.height_cm }}" required></label>
      <label>KilaĹľa kg<input type="number" step="0.1" name="weight_kg" value="{{ user.weight_kg }}" required></label>
      <label class="full">Cilj
        <select name="goal">
          <option value="performance" {% if user.goal == 'performance' %}selected{% endif %}>Performance</option>
          <option value="muscle" {% if user.goal == 'muscle' %}selected{% endif %}>Muscle</option>
          <option value="cut" {% if user.goal == 'cut' %}selected{% endif %}>Cut</option>
        </select>
      </label>
      <label class="full">Iskustvo
        <select name="experience_level">
          <option value="beginner" {% if user.experience_level == 'beginner' %}selected{% endif %}>Beginner</option>
          <option value="intermediate" {% if user.experience_level == 'intermediate' %}selected{% endif %}>Intermediate</option>
          <option value="advanced" {% if user.experience_level == 'advanced' %}selected{% endif %}>Advanced</option>
        </select>
      </label>
      <button class="full" type="submit">SaÄŤuvaj profil i nastavi</button>
    </form>
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
    return [
        {"title": "Training folder", "anchor": "#plans", "detail": f"Adaptive plans for {user['goal']} with {len(assistant['suggestions'])} plan options."},
        {"title": "Nutrition folder", "anchor": "#mission", "detail": f"Macro targets set to {assistant['targets']['calories']} kcal and {assistant['targets']['protein']}g protein."},
        {"title": "Recovery folder", "anchor": "#assistant", "detail": "Recovery score, daily mission and readiness cues in one place."},
        {"title": "Profile folder", "anchor": "#profile", "detail": "Update gender, weight, height, age and goal anytime from the dashboard."},
    ]


def build_section_menu(user: dict[str, Any]) -> list[dict[str, str]]:
    items = [
        {"title": "Today", "anchor": "#today-plan"},
        {"title": "Plans", "anchor": "#plans"},
        {"title": "Coach", "anchor": "#assistant"},
        {"title": "Nutrition", "anchor": "#mission"},
        {"title": "Progress", "anchor": "#progress"},
        {"title": "Calendar", "anchor": "#calendar"},
        {"title": "AI", "anchor": "#ai-trainer"},
        {"title": "Profile", "anchor": "#profile"},
    ]
    if str(user.get("role")) == "admin":
        items.append({"title": "Admin", "anchor": "#admin"})
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
    options = {
        "performance": [
            {
                "title": "Strength performance split",
                "coach_key": "strength",
                "coach_role": COACHES["strength"]["role"],
                "days": training_days,
                "summary": f"Heavy compounds, speed work and structured accessory balance for {frame} {gender} athletes chasing output.",
                "blocks": ["Day 1 upper strength", "Day 2 lower power", "Day 3 hypertrophy support", "Day 4 engine and mobility"],
                "nutrition": "Higher carbs around lifts, stable protein and hydration.",
            },
            {
                "title": "Athletic hybrid build",
                "coach_key": "conditioning",
                "coach_role": COACHES["conditioning"]["role"],
                "days": training_days,
                "summary": f"Blend of force, conditioning and recovery for {gender} athletes who want recomposition with performance.",
                "blocks": ["2 lifting days", "1 athletic conditioning day", "1 movement and trunk day"],
                "nutrition": "Carb cycling around hardest sessions and lighter recovery day meals.",
            },
            {
                "title": "Upper lower progression",
                "coach_key": "strength",
                "coach_role": COACHES["strength"]["role"],
                "days": training_days,
                "summary": f"Simple progression model tuned for {frame} body types and clear logbook progression.",
                "blocks": ["Upper A", "Lower A", "Upper B", "Lower B"],
                "nutrition": "Consistent calories with strong protein anchor every meal.",
            },
        ],
        "muscle": [
            {
                "title": "Hypertrophy growth split",
                "coach_key": "hypertrophy",
                "coach_role": COACHES["hypertrophy"]["role"],
                "days": training_days,
                "summary": f"High-quality volume and controlled execution for {gender} users pushing muscle gain.",
                "blocks": ["Push focus", "Pull focus", "Legs focus", "Upper density day"],
                "nutrition": "Small calorie surplus with high protein and pre/post workout carbs.",
            },
            {
                "title": "Upper lower muscle plan",
                "coach_key": "hypertrophy",
                "coach_role": COACHES["hypertrophy"]["role"],
                "days": training_days,
                "summary": f"Reliable upper/lower template with more weekly frequency and bodyweight-aware volume.",
                "blocks": ["Upper chest and back", "Lower quads and glutes", "Upper shoulders and arms", "Lower posterior chain"],
                "nutrition": "Repeatable meal structure with protein at every feeding window.",
            },
            {
                "title": "Bodybuilding recomposition",
                "coach_key": "conditioning",
                "coach_role": COACHES["conditioning"]["role"],
                "days": training_days,
                "summary": f"Muscle-focused work with controlled conditioning so {gender} users stay tighter while growing.",
                "blocks": ["3 hypertrophy days", "1 low-impact conditioning day", "1 optional mobility session"],
                "nutrition": "Moderate surplus on training days, cleaner intake on lighter days.",
            },
        ],
        "cut": [
            {
                "title": "Fat loss performance plan",
                "coach_key": "conditioning",
                "coach_role": COACHES["conditioning"]["role"],
                "days": training_days,
                "summary": f"Protect strength while increasing output and energy expenditure for {frame} athletes cutting down.",
                "blocks": ["2 full body strength days", "2 conditioning finish days", "Daily steps target"],
                "nutrition": "Calorie deficit with high protein and carbs focused around training.",
            },
            {
                "title": "Lean athlete split",
                "coach_key": "strength",
                "coach_role": COACHES["strength"]["role"],
                "days": training_days,
                "summary": f"Keep muscle signal high with lower junk volume and sharper recovery control for {gender} users.",
                "blocks": ["Upper strength", "Lower strength", "Density accessories", "Zone 2 + mobility"],
                "nutrition": "Protein first, moderate carbs, tighter food quality control.",
            },
            {
                "title": "Conditioning driven cut",
                "coach_key": "conditioning",
                "coach_role": COACHES["conditioning"]["role"],
                "days": training_days,
                "summary": f"Best for {gender} users who want aggressive output, sweat and precise weekly structure.",
                "blocks": ["Intervals", "Carries and sleds", "Machine circuits", "Recovery mobility"],
                "nutrition": "Low-fat peri-workout structure with precise calorie logging.",
            },
        ],
    }
    return options.get(goal, options["performance"])


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
        "focus_line": today_event.get("details") if today_event else ("Heavy compound execution and speed quality." if goal == "performance" else "High-quality hypertrophy with stretch and control." if goal == "muscle" else "Dense work, calorie burn and muscle retention."),
        "rest_day_actions": rest_day_actions,
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
                "name": item["name"],
                "detail": f"{item['sets']} sets / {item['reps']} reps / rest {item['rest']}",
                "done": item["item_key"] in completed,
                "checkpoints": checkpoints,
                "weight_suggestion": next((entry["recommendation"] for entry in progression if entry["name"] == item["name"]), "Use a conservative starting load."),
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
    pr_tracker = build_pr_tracker(exercises)
    wellness_panel = build_wellness_panel(user, scores)
    lang = current_language()
    ui = language_pack()
    market_flags = market_readiness_flags()
    business = business_overview() if user.get("role") == "admin" else None

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
        "subscription_plans": SUBSCRIPTION_PLANS,
        "commercial_offers": COMMERCIAL_OFFERS,
        "market_flags": market_flags,
        "access": access,
        "ai_concierge": ai_concierge,
        "notifications": notifications,
        "business": business,
        "trainers": trainer_profiles(),
        "exercise_library": exercise_library(),
        "food_filters": catalog["filters"],
        "foods": filtered_foods("all", "all", ""),
        "recipes": filtered_recipes("all", "all"),
        "users": list_users() if user.get("role") == "admin" else [],
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
        "build": "APP.PY ONLY BUILD V22",
        "login_title": "Secure athlete login V22",
        "dashboard_title": "Adaptive athlete dashboard V22",
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
    if item_type not in {"exercise", "meal", "set"} or not item_key:
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


