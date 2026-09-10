web: gunicorn --worker-class sync --workers 1 --threads 4 --worker-connections 1000 --max-requests 1000 --max-requests-jitter 50 --timeout 60 wsgi:app
