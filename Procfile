web: gunicorn flask_app:app --bind 0.0.0.0:$PORT --timeout 600 --workers 1 --worker-class sync --max-requests 10 --max-requests-jitter 5
