#!/bin/bash

# Script to fix 502 Bad Gateway error by restarting Gunicorn on musicu-server
# Date: Wed Jun 04 18:23 CDT 2025

LOG_FILE="/music_scheduler/logs/fix_gunicorn.log"

echo "Starting fix_gunicorn.sh at $(date)" | tee -a "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Debug: Logging initialized for fix_gunicorn.sh"

# Step 1: Check Gunicorn service status
echo "Checking Gunicorn service status..." | tee -a "$LOG_FILE"
systemctl status music_scheduler_gunicorn.service 2>&1 | tee -a "$LOG_FILE"

# Step 2: Restart Gunicorn service
echo "Restarting Gunicorn service..." | tee -a "$LOG_FILE"
systemctl restart music_scheduler_gunicorn.service 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to restart Gunicorn service" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 3: Verify Gunicorn is listening on 127.0.0.1:8000
echo "Verifying Gunicorn is listening on 127.0.0.1:8000..." | tee -a "$LOG_FILE"
sleep 2  # Give Gunicorn a moment to start
netstat -tuln | grep :8000 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Gunicorn is not listening on 127.0.0.1:8000" | tee -a "$LOG_FILE"
    echo "Checking Gunicorn logs for errors..." | tee -a "$LOG_FILE"
    journalctl -u music_scheduler_gunicorn.service --since "2025-06-04 18:00:00" -n 50 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

# Step 4: Test API endpoint with curl
echo "Testing API endpoint /api/check-auth..." | tee -a "$LOG_FILE"
curl -v http://127.0.0.1:80/api/check-auth 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Warning: API endpoint test failed. Check Gunicorn logs and Nginx configuration." | tee -a "$LOG_FILE"
fi

echo "Script completed successfully. Next steps:" | tee -a "$LOG_FILE"
echo "1. Test access from your testing VM (e.g., http://192.168.1.63 from 192.168.1.64)." | tee -a "$LOG_FILE"
echo "2. Verify application functionality, including the notes feature." | tee -a "$LOG_FILE"
echo "Check the log for details: cat $LOG_FILE" | tee -a "$LOG_FILE"
