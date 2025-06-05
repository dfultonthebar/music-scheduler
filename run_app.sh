#!/bin/bash
source /music_scheduler/venv/bin/activate
exec gunicorn -b 127.0.0.1:8000 -w 4 app:app --log-file=/music_scheduler/logs/flask_app.log --log-level=info
