# Forge Gym App

Standalone mobile-first gym app, fully separated from the older projects in the workspace.

## Local run

```bash
cd gym_app
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5055`.

## What v2 includes

- premium mobile-first athlete dashboard
- SQLite workout tracking
- body metrics and progress ledger
- multiple in-app coaches
- adaptive workout recommendation engine
- research-backed product principles from major fitness apps
- PWA manifest and service worker
- Render-ready deploy files

## Render deploy

1. Put only `gym_app` in a dedicated GitHub repo.
2. In Render choose `New +` then `Blueprint`.
3. Connect the repo and confirm `render.yaml`.
4. Render will use `pip install -r requirements.txt`.
5. Start command is `python wsgi.py`.
6. Health check path is `/health`.
