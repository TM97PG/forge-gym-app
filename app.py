from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
SEED_FILE = DATA_DIR / "seed.json"
RESEARCH_FILE = DATA_DIR / "research_sources.json"
FOODS_FILE = DATA_DIR / "foods.json"
DB_FILE = DATA_DIR / "forge.sqlite3"

app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder=str(TEMPLATES_DIR))


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


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS workout_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                photo_date TEXT NOT NULL,
                pose TEXT NOT NULL,
                mood TEXT NOT NULL,
                lighting_score INTEGER NOT NULL,
                visual_score INTEGER NOT NULL,
                photo_url TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )

        columns = {row["name"] for row in db.execute("PRAGMA table_info(body_metrics)").fetchall()}
        if "form_score" not in columns:
            db.execute("ALTER TABLE body_metrics ADD COLUMN form_score INTEGER NOT NULL DEFAULT 7")
        if "checkin_note" not in columns:
            db.execute("ALTER TABLE body_metrics ADD COLUMN checkin_note TEXT NOT NULL DEFAULT ''")

        existing_logs = db.execute("SELECT COUNT(*) AS count FROM workout_logs").fetchone()["count"]
        existing_metrics = db.execute("SELECT COUNT(*) AS count FROM body_metrics").fetchone()["count"]
        existing_meals = db.execute("SELECT COUNT(*) AS count FROM meal_logs").fetchone()["count"]
        existing_exercises = db.execute("SELECT COUNT(*) AS count FROM exercise_logs").fetchone()["count"]
        existing_photos = db.execute("SELECT COUNT(*) AS count FROM progress_photos").fetchone()["count"]

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
                        workout_date, coach_key, focus, duration_minutes, volume_load,
                        energy_score, effort_score, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*row, datetime.utcnow().isoformat(timespec="seconds")),
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
                        metric_date, body_weight, body_fat, chest, waist, arm, thigh,
                        sleep_hours, steps, form_score, checkin_note, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*row, datetime.utcnow().isoformat(timespec="seconds")),
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
                        logged_at, meal_type, food_name, grams, calories, protein, carbs,
                        fats, goal_tag, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*row, datetime.utcnow().isoformat(timespec="seconds")),
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
                        logged_at, exercise_name, category, muscle_group, sets_count, reps_text,
                        weight_kg, rpe, coach_key, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*row, datetime.utcnow().isoformat(timespec="seconds")),
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
                        photo_date, pose, mood, lighting_score, visual_score, photo_url, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*row, datetime.utcnow().isoformat(timespec="seconds")),
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


def recent_workouts(limit: int = 8) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, workout_date, coach_key, focus, duration_minutes, volume_load,
                   energy_score, effort_score, notes
            FROM workout_logs
            ORDER BY workout_date DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_metrics(limit: int = 6) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT metric_date, body_weight, body_fat, chest, waist, arm, thigh, sleep_hours, steps, form_score, checkin_note
            FROM body_metrics
            ORDER BY metric_date DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_meals(limit: int = 16) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT logged_at, meal_type, food_name, grams, calories, protein, carbs, fats, goal_tag, notes
            FROM meal_logs
            ORDER BY logged_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_exercises(limit: int = 16) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT logged_at, exercise_name, category, muscle_group, sets_count, reps_text, weight_kg, rpe, coach_key, notes
            FROM exercise_logs
            ORDER BY logged_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_photos(limit: int = 6) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT photo_date, pose, mood, lighting_score, visual_score, photo_url, notes
            FROM progress_photos
            ORDER BY photo_date DESC, id DESC
            LIMIT ?
            """,
            (limit,),
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


def dashboard_payload() -> dict[str, Any]:
    seed = load_json(SEED_FILE)
    research = load_json(RESEARCH_FILE)["sources"]
    catalog = catalog_payload()
    workouts = recent_workouts()
    metrics = recent_metrics()
    meals = recent_meals()
    exercises = recent_exercises()
    photos = recent_photos()
    stats = build_tracking_stats(workouts, metrics)
    nutrition_stats = build_nutrition_stats(meals)
    recommendation = build_recommendation(
        coach_key="strength",
        mood="steady",
        energy=7,
        equipment="full gym",
        minutes=75,
        goal="performance",
        workouts=workouts,
        research=research,
    )
    return {
        "seed": seed,
        "coaches": COACHES,
        "research": research,
        "workouts": workouts,
        "metrics": metrics,
        "stats": stats,
        "nutrition_stats": nutrition_stats,
        "recommendation": recommendation,
        "meals": meals,
        "exercises": exercises,
        "photos": photos,
        "trainers": trainer_profiles(),
        "exercise_library": exercise_library(),
        "food_filters": catalog["filters"],
        "foods": filtered_foods("all", "all", ""),
        "recipes": filtered_recipes("all", "all"),
    }


@app.route("/")
def home():
    payload = dashboard_payload()
    return render_template("index.html", payload=payload, today=date.today().isoformat())


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


@app.route("/api/dashboard")
def dashboard_api():
    return jsonify(dashboard_payload())


@app.route("/api/nutrition")
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
def recommendation_api():
    research = load_json(RESEARCH_FILE)["sources"]
    workouts = recent_workouts()
    data = request.get_json(silent=True) or {}
    coach_key = str(data.get("coach") or "strength")
    mood = str(data.get("mood") or "steady").strip().lower()
    energy = clamp_int(data.get("energy"), 7, 1, 10)
    equipment = str(data.get("equipment") or "full gym").strip().lower()
    minutes = clamp_int(data.get("minutes"), 75, 20, 180)
    goal = str(data.get("goal") or "performance").strip().lower()
    recommendation = build_recommendation(coach_key, mood, energy, equipment, minutes, goal, workouts, research)
    return jsonify(recommendation)


@app.route("/log-workout", methods=["POST"])
def log_workout():
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
                workout_date, coach_key, focus, duration_minutes, volume_load,
                energy_score, effort_score, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
    return redirect(url_for("home") + "#track")


@app.route("/log-metric", methods=["POST"])
def log_metric():
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
                metric_date, body_weight, body_fat, chest, waist, arm, thigh,
                sleep_hours, steps, form_score, checkin_note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
    return redirect(url_for("home") + "#metrics")


@app.route("/log-meal", methods=["POST"])
def log_meal():
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
                logged_at, meal_type, food_name, grams, calories, protein, carbs,
                fats, goal_tag, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
    return redirect(url_for("home") + "#nutrition")


@app.route("/log-exercise", methods=["POST"])
def log_exercise():
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
                logged_at, exercise_name, category, muscle_group, sets_count, reps_text,
                weight_kg, rpe, coach_key, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
    return redirect(url_for("home") + "#exercise")


@app.route("/log-photo", methods=["POST"])
def log_photo():
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
                photo_date, pose, mood, lighting_score, visual_score, photo_url, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
    return redirect(url_for("home") + "#gallery")


init_db()


if __name__ == "__main__":
    app.run(debug=True, port=5055)
