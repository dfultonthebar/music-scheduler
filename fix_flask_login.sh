#!/bin/bash

# Script to fix 500 Internal Server Error on /api/login endpoint on musicu-server
# Date: Wed Jun 04 18:41 CDT 2025

LOG_FILE="/music_scheduler/logs/fix_flask_login.log"

echo "Starting fix_flask_login.sh at $(date)" | tee -a "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Debug: Logging initialized for fix_flask_login.sh"

# Step 1: Stop Gunicorn service
echo "Stopping Gunicorn service..." | tee -a "$LOG_FILE"
systemctl stop music_scheduler_gunicorn.service 2>&1 | tee -a "$LOG_FILE"

# Step 2: Fix virtual environment permissions
echo "Fixing virtual environment permissions..." | tee -a "$LOG_FILE"
chown -R root:www-data /music_scheduler/venv 2>&1 | tee -a "$LOG_FILE"
chmod -R 755 /music_scheduler/venv/bin 2>&1 | tee -a "$LOG_FILE"

# Step 3: Reinstall dependencies in the virtual environment
echo "Reinstalling dependencies in the virtual environment..." | tee -a "$LOG_FILE"
/music_scheduler/venv/bin/python -m pip install --upgrade pip --break-system-packages 2>&1 | tee -a "$LOG_FILE"
/music_scheduler/venv/bin/pip install gunicorn flask mysql-connector-python bcrypt --break-system-packages 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies in the virtual environment" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 4: Verify MariaDB service is running
echo "Verifying MariaDB service is running..." | tee -a "$LOG_FILE"
systemctl status mariadb 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "MariaDB service is not running. Starting MariaDB..." | tee -a "$LOG_FILE"
    systemctl start mariadb 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to start MariaDB service" | tee -a "$LOG_FILE"
        exit 1
    fi
fi

# Step 5: Validate database credentials and setup
echo "Validating database credentials and setup..." | tee -a "$LOG_FILE"
mysql -h localhost -u music_user -pMusicU2025 -e "USE music_scheduler; SHOW TABLES;" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to connect to database with current credentials. Attempting to set up..." | tee -a "$LOG_FILE"
    mysql -u root -e "CREATE USER IF NOT EXISTS 'music_user'@'localhost' IDENTIFIED BY 'MusicU2025'; GRANT ALL PRIVILEGES ON music_scheduler.* TO 'music_user'@'localhost'; FLUSH PRIVILEGES;" 2>&1 | tee -a "$LOG_FILE"
    mysql -u root -e "CREATE DATABASE IF NOT EXISTS music_scheduler;" 2>&1 | tee -a "$LOG_FILE"
    mysql -u root -D music_scheduler -e "CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, password VARCHAR(255) NOT NULL, role ENUM('admin', 'instructor') NOT NULL);" 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to set up database and user" | tee -a "$LOG_FILE"
        exit 1
    fi
fi

# Step 6: Update app.py with improved error handling and logging
echo "Updating app.py with improved error handling and logging..." | tee -a "$LOG_FILE"
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
    return jsonify({"authenticated": False}), 200

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            logging.error("No JSON data provided in login request")
            return jsonify({"error": "No data provided"}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            logging.error("Missing username or password in login request")
            return jsonify({"error": "Missing username or password"}), 400
        
        logging.info(f"Login attempt for username: {username}")
        
        conn = None
        cursor = None
        try:
            logging.debug("Attempting to connect to database")
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            logging.debug("Database connection successful")
            
            cursor.execute("SELECT password, role FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            
            if result:
                stored_password = result[0].encode('utf-8')
                user_role = result[1]
                logging.debug(f"User {username} found with role {user_role}")
                
                if bcrypt.checkpw(password.encode('utf-8'), stored_password):
                    logging.info(f"Login successful for {username} with role {user_role}")
                    return jsonify({"message": "Login successful", "role": user_role}), 200
                else:
                    logging.warning(f"Invalid password for {username}")
                    return jsonify({"error": "Invalid credentials"}), 401
            else:
                logging.warning(f"User {username} not found")
                return jsonify({"error": "User not found"}), 404
        except mysql.connector.Error as err:
            logging.error(f"Database error during login for {username}: {err}")
            return jsonify({"error": f"Database error: {str(err)}"}), 500
        except Exception as e:
            logging.error(f"Unexpected error during login for {username}: {e}")
            return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                conn.close()
                logging.debug("Database connection closed")
    except Exception as e:
        logging.error(f"Fatal error in login route: {e}")
        return jsonify({"error": "Server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
EOF
if [ $? -ne 0 ]; then
    echo "Error: Failed to update app.py" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 7: Update Gunicorn systemd service file with enhanced logging
echo "Updating Gunicorn systemd service file with enhanced logging..." | tee -a "$LOG_FILE"
cat <<EOF > /etc/systemd/system/music_scheduler_gunicorn.service
[Unit]
Description=Gunicorn instance to serve Music Scheduler
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/music_scheduler
Environment="PATH=/music_scheduler/venv/bin"
ExecStart=/music_scheduler/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 --log-file /music_scheduler/logs/gunicorn.log --log-level debug --access-logfile /music_scheduler/logs/gunicorn_access.log app:app

[Install]
WantedBy=multi-user.target
EOF
if [ $? -ne 0 ]; then
    echo "Error: Failed to update Gunicorn systemd service file" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 8: Reload systemd daemon and restart Gunicorn
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

# Step 9: Verify Gunicorn is listening on 127.0.0.1:8000
echo "Verifying Gunicorn is listening on 127.0.0.1:8000..." | tee -a "$LOG_FILE"
sleep 2  # Give Gunicorn a moment to start
netstat -tuln | grep :8000 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Gunicorn is not listening on 127.0.0.1:8000" | tee -a "$LOG_FILE"
    echo "Checking Gunicorn logs for errors..." | tee -a "$LOG_FILE"
    cat /music_scheduler/logs/gunicorn.log 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

# Step 10: Test API endpoints with curl
echo "Testing API endpoint /api/check-auth..." | tee -a "$LOG_FILE"
curl -v http://127.0.0.1:80/api/check-auth 2>&1 | tee -a "$LOG_FILE"

echo "Testing API endpoint /api/login..." | tee -a "$LOG_FILE"
curl -v -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"MusicU2025"}' http://127.0.0.1:80/api/login 2>&1 | tee -a "$LOG_FILE"

echo "Script completed successfully. Next steps:" | tee -a "$LOG_FILE"
echo "1. Test access from your testing VM (e.g., http://192.168.1.63 from 192.168.1.64)." | tee -a "$LOG_FILE"
echo "2. Verify application functionality, including the notes feature." | tee -a "$LOG_FILE"
echo "Check the log for details: cat $LOG_FILE" | tee -a "$LOG_FILE"
