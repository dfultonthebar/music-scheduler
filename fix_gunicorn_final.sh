#!/bin/bash

# Script to fix Gunicorn failure (status=203/EXEC) and resolve 502 Bad Gateway error on musicu-server
# Date: Wed Jun 04 18:28 CDT 2025

LOG_FILE="/music_scheduler/logs/fix_gunicorn_final.log"

echo "Starting fix_gunicorn_final.sh at $(date)" | tee -a "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Debug: Logging initialized for fix_gunicorn_final.sh"

# Step 1: Stop Gunicorn service if running
echo "Stopping Gunicorn service if running..." | tee -a "$LOG_FILE"
systemctl stop music_scheduler_gunicorn.service 2>&1 | tee -a "$LOG_FILE"

# Step 2: Check for existence of Gunicorn executable
echo "Checking for existence of Gunicorn executable..." | tee -a "$LOG_FILE"
if [ ! -f "/music_scheduler/venv/bin/gunicorn" ]; then
    echo "Error: /music_scheduler/venv/bin/gunicorn does not exist" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 3: Check permissions of Gunicorn executable
echo "Checking permissions of Gunicorn executable..." | tee -a "$LOG_FILE"
ls -la /music_scheduler/venv/bin/gunicorn 2>&1 | tee -a "$LOG_FILE"
chmod +x /music_scheduler/venv/bin/gunicorn 2>&1 | tee -a "$LOG_FILE"

# Step 4: Check for existence of app.py
echo "Checking for existence of app.py..." | tee -a "$LOG_FILE"
if [ ! -f "/music_scheduler/app.py" ]; then
    echo "Error: /music_scheduler/app.py does not exist" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 5: Reinstall dependencies in the virtual environment
echo "Reinstalling dependencies in the virtual environment..." | tee -a "$LOG_FILE"
source /music_scheduler/venv/bin/activate 2>&1 | tee -a "$LOG_FILE"
pip install --upgrade pip 2>&1 | tee -a "$LOG_FILE"
pip install gunicorn flask mysql-connector-python bcrypt 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies in the virtual environment" | tee -a "$LOG_FILE"
    exit 1
fi
deactivate 2>&1 | tee -a "$LOG_FILE"

# Step 6: Update Gunicorn systemd service file
echo "Updating Gunicorn systemd service file..." | tee -a "$LOG_FILE"
cat <<EOF > /etc/systemd/system/music_scheduler_gunicorn.service
[Unit]
Description=Gunicorn instance to serve Music Scheduler
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/music_scheduler
Environment="PATH=/music_scheduler/venv/bin"
ExecStart=/music_scheduler/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 -m 007 app:app

[Install]
WantedBy=multi-user.target
EOF
if [ $? -ne 0 ]; then
    echo "Error: Failed to update Gunicorn systemd service file" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 7: Reload systemd daemon and restart Gunicorn
echo "Reloading systemd daemon..." | tee -a "$LOG_FILE"
systemctl daemon-reload 2>&1 | tee -a "$LOG_FILE"

echo "Restarting Gunicorn service..." | tee -a "$LOG_FILE"
systemctl restart music_scheduler_gunicorn.service 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to restart Gunicorn service" | tee -a "$LOG_FILE"
    echo "Checking Gunicorn service status for errors..." | tee -a "$LOG_FILE"
    systemctl status music_scheduler_gunicorn.service 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

# Step 8: Verify Gunicorn is listening on 127.0.0.1:8000
echo "Verifying Gunicorn is listening on 127.0.0.1:8000..." | tee -a "$LOG_FILE"
sleep 2  # Give Gunicorn a moment to start
netstat -tuln | grep :8000 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Gunicorn is not listening on 127.0.0.1:8000" | tee -a "$LOG_FILE"
    echo "Checking Gunicorn logs for errors..." | tee -a "$LOG_FILE"
    journalctl -u music_scheduler_gunicorn.service --since "2025-06-04 18:00:00" -n 50 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

# Step 9: Test API endpoint with curl
echo "Testing API endpoint /api/check-auth..." | tee -a "$LOG_FILE"
curl -v http://127.0.0.1:80/api/check-auth 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Warning: API endpoint test failed. Check Gunicorn logs and Nginx configuration." | tee -a "$LOG_FILE"
fi

echo "Script completed successfully. Next steps:" | tee -a "$LOG_FILE"
echo "1. Test access from your testing VM (e.g., http://192.168.1.63 from 192.168.1.64)." | tee -a "$LOG_FILE"
echo "2. Verify application functionality, including the notes feature." | tee -a "$LOG_FILE"
echo "Check the log for details: cat $LOG_FILE" | tee -a "$LOG_FILE"
