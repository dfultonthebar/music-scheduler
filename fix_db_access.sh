#!/bin/bash

# Script to fix database access issues for music_user on musicu-server
# Date: Wed Jun 04 18:50 CDT 2025

LOG_FILE="/music_scheduler/logs/fix_db_access.log"

echo "Starting fix_db_access.sh at $(date)" | tee -a "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Debug: Logging initialized for fix_db_access.sh"

# Step 1: Stop Gunicorn service
echo "Stopping Gunicorn service..." | tee -a "$LOG_FILE"
systemctl stop music_scheduler_gunicorn.service 2>&1 | tee -a "$LOG_FILE"

# Step 2: Verify MariaDB service is running
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

# Step 3: Create music_user and music_scheduler database using sudo mysql
echo "Creating music_user and music_scheduler database..." | tee -a "$LOG_FILE"
sudo mysql -e "CREATE USER IF NOT EXISTS 'music_user'@'localhost' IDENTIFIED BY 'MusicU2025'; GRANT ALL PRIVILEGES ON music_scheduler.* TO 'music_user'@'localhost'; FLUSH PRIVILEGES;" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create music_user" | tee -a "$LOG_FILE"
    exit 1
fi

sudo mysql -e "CREATE DATABASE IF NOT EXISTS music_scheduler;" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create music_scheduler database" | tee -a "$LOG_FILE"
    exit 1
fi

sudo mysql -D music_scheduler -e "CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, password VARCHAR(255) NOT NULL, role ENUM('admin', 'instructor') NOT NULL);" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create users table" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 4: Insert initial users with hashed passwords
echo "Inserting initial users with hashed passwords..." | tee -a "$LOG_FILE"
# Hashed passwords for 'MusicU2025' using bcrypt (generated previously or can be generated using Python)
ADMIN_HASH='$2b$12$8nxnDdBPYKAVpwVrROSBMOm8I.pgNPLr4jmXKxDd/DFzauV8DyoHa'
INSTRUCTOR_HASH='$2b$12$8nxnDdBPYKAVpwVrROSBMOm8I.pgNPLr4jmXKxDd/DFzauV8DyoHa'

sudo mysql -D music_scheduler -e "INSERT IGNORE INTO users (username, password, role) VALUES ('admin', '$ADMIN_HASH', 'admin'), ('instructor1', '$INSTRUCTOR_HASH', 'instructor');" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to insert initial users" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 5: Restart Gunicorn service
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

# Step 7: Test API endpoints with curl
echo "Testing API endpoint /api/check-auth..." | tee -a "$LOG_FILE"
curl -v http://127.0.0.1:80/api/check-auth 2>&1 | tee -a "$LOG_FILE"

echo "Testing API endpoint /api/login..." | tee -a "$LOG_FILE"
curl -v -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"MusicU2025"}' http://127.0.0.1:80/api/login 2>&1 | tee -a "$LOG_FILE"

echo "Script completed successfully. Next steps:" | tee -a "$LOG_FILE"
echo "1. Test access from your testing VM (e.g., http://192.168.1.63 from 192.168.1.64)." | tee -a "$LOG_FILE"
echo "2. Verify application functionality, including the notes feature." | tee -a "$LOG_FILE"
echo "Check the log for details: cat $LOG_FILE" | tee -a "$LOG_FILE"
