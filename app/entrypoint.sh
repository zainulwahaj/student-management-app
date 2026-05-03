#!/bin/sh
set -e

echo "==> Waiting for MySQL at ${DB_HOST}:${DB_PORT:-3306}..."
python - <<'PY'
import os, time, sys
import pymysql

host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', '3306'))
user = os.environ.get('DB_USER', 'root')
pwd  = os.environ.get('DB_PASSWORD', 'rootpassword')
db   = os.environ.get('DB_NAME', 'students_db')

for attempt in range(1, 61):
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=pwd, database=db)
        conn.close()
        print(f"    DB ready after {attempt} attempt(s).")
        sys.exit(0)
    except Exception as e:
        print(f"    [{attempt}/60] not ready: {e.__class__.__name__}")
        time.sleep(2)

print("    Database failed to come up in time.")
sys.exit(1)
PY

echo "==> Creating tables (if needed)..."
python - <<'PY'
from app import app, db
with app.app_context():
    db.create_all()
print("    Schema ready.")
PY

echo "==> Starting Gunicorn on :5000"
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 60 --access-logfile - app:app
