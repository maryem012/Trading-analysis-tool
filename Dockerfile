# Backend API deploy. Repo root is the build context (not backend/) because
# api.py imports sibling modules (backtester.py, data_fetcher.py,
# strategy_lab.py) that live one level up from backend/ — see api.py's
# sys.path comment. Everything gets copied in, deps install from
# backend/requirements.txt, then the process runs from inside backend/ to
# match local dev exactly.
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r backend/requirements.txt

WORKDIR /app/backend
CMD uvicorn api:app --host 0.0.0.0 --port $PORT
