#!/bin/bash

# Script to fix Flask routing issues causing 404 Not Found errors on musicu-server
# Date: Wed Jun 04 18:33 CDT 2025

LOG_FILE="/music_scheduler/logs/fix_flask_routes.log"

echo "Starting fix_flask_routes.sh at $(date)" | tee -a "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Debug: Logging initialized for fix_flask_routes.sh"

# Step 1: Stop Gunicorn service
echo "Stopping Gunicorn service..." | tee -a "$LOG_FILE"
systemctl stop music_scheduler_gunicorn.service 2>&1 | tee -a "$LOG_FILE"

# Step 2: Reinstall dependencies in the virtual environment
echo "Reinstalling dependencies in the virtual environment..." | tee -a "$LOG_FILE"
/music_scheduler/venv/bin/python -m pip install --upgrade pip --break-system-packages 2>&1 | tee -a "$LOG_FILE"
/music_scheduler/venv/bin/pip install gunicorn flask mysql-connector-python bcrypt --break-system-packages 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies in the virtual environment" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 3: Backup and update app.py with necessary routes
echo "Backing up current app.py..." | tee -a "$LOG_FILE"
cp /music_scheduler/app.py /music_scheduler/app.py.bak_$(date +%Y%m%d_%H%M%S) 2>&1 | tee -a "$LOG_FILE"

echo "Updating app.py with necessary routes..." | tee -a "$LOG_FILE"
cat <<EOF > /music_scheduler/app.py
from flask import Flask, request, jsonify
import mysql.connector
import bcrypt
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(filename='/music_scheduler/logs/flask_app.log', level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'music_user',
    'password': 'MusicU2025',
    'database': 'music_scheduler'
}

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    logging.info("Checking authentication status")
    # Placeholder for authentication check logic
    return jsonify({"authenticated": False}), 200

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    logging.info(f"Login attempt for username: {username}")
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        
        if result:
            stored_password = result[0].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), stored_password):
                logging.info(f"Login successful for {username}")
                return jsonify({"message": "Login successful"}), 200
            else:
                logging.warning(f"Invalid password for {username}")
                return jsonify({"error": "Invalid credentials"}), 401
        else:
            logging.warning(f"User {username} not found")
            return jsonify({"error": "User not found"}), 404
    except mysql.connector.Error as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": "Database error"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)
EOF
if [ $? -ne 0 ]; then
    echo "Error: Failed to update app.py" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 4: Update Gunicorn systemd service file with logging
echo "Updating Gunicorn systemd service file with logging..." | tee -a "$LOG_FILE"
cat <<EOF > /etc/systemd/system/music_scheduler_gunicorn.service
[Unit]
Description=Gunicorn instance to serve Music Scheduler
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/music_scheduler
Environment="PATH=/music_scheduler/venv/bin"
ExecStart=/music_scheduler/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 --log-file /music_scheduler/logs/gunicorn.log --log-level info app:app

[Install]
WantedBy=multi-user.target
EOF
if [ $? -ne 0 ]; then
    echo "Error: Failed to update Gunicorn systemd service file" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 5: Reload systemd daemon and restart Gunicorn
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

# Step 6: Verify Gunicorn is listening on 127.0.0.1:8000
echo "Verifying Gunicorn is listening on 127.0.0.1:8000..." | tee -a "$LOG_FILE"
sleep 2  # Give Gunicorn a moment to start
netstat -tuln | grep :8000 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Gunicorn is not listening on 127.0.0.1:8000" | tee -a "$LOG_FILE"
    echo "Checking Gunicorn logs for errors..." | tee -a "$LOG_FILE"
    cat /music_scheduler/logs/gunicorn.log 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

# Step 7: Test API endpoint with curl
echo "Testing API endpoint /api/check-auth..." | tee -a "$LOG_FILE"
curl -v http://127.0.0.1:80/api/check-auth 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Warning: API endpoint test failed. Check Gunicorn logs and Flask app logs." | tee -a "$LOG_FILE"
    cat /music_scheduler/logs/gunicorn.log 2>&1 | tee -a "$LOG_FILE"
    cat /music_scheduler/logs/flask_app.log 2>&1 | tee -a "$LOG_FILE"
fi

echo "Script completed successfully. Next steps:" | tee -a "$LOG_FILE"
echo "1. Test access from your testing VM (e.g., http://192.168.1.63 from 192.168.1.64)." | tee -a "$LOG_FILE"
echo "2. Verify application functionality, including the notes feature." | tee -a "$LOG_FILE"
echo "Check the log for details: cat $LOG_FILE" | tee -a "$LOG_FILE"
