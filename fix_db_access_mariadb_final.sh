#!/bin/bash

# Script to fix database access issues for music_user on musicu-server (MariaDB 10.11.11 final)
# Date: Wed Jun 04 19:25 CDT 2025

LOG_FILE="/music_scheduler/logs/fix_db_access_mariadb_final.log"

echo "Starting fix_db_access_mariadb_final.sh at $(date)" | tee -a "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Debug: Logging initialized for fix_db_access_mariadb_final.sh"

# Step 1: Stop Gunicorn service
echo "Stopping Gunicorn service..." | tee -a "$LOG_FILE"
systemctl stop music_scheduler_gunicorn.service 2>&1 | tee -a "$LOG_FILE"

# Step 2: Stop MariaDB service
echo "Stopping MariaDB service..." | tee -a "$LOG_FILE"
systemctl stop mariadb 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to stop MariaDB service" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 3: Start MariaDB in safe mode to bypass authentication
echo "Starting MariaDB in safe mode to bypass authentication..." | tee -a "$LOG_FILE"
sudo mysqld_safe --skip-grant-tables > /tmp/mysqld_safe.log 2>&1 &
MARIADB_PID=$!
sleep 5

# Verify mysqld_safe started
if ! ps -p $MARIADB_PID > /dev/null; then
    echo "Error: Failed to start MariaDB in safe mode" | tee -a "$LOG_FILE"
    cat /tmp/mysqld_safe.log | tee -a "$LOG_FILE"
    exit 1
fi

# Step 4: Create a temporary SQL script to reset root password
echo "Creating temporary SQL script to reset root password..." | tee -a "$LOG_FILE"
cat <<EOF > /tmp/reset_root_password.sql
ALTER USER 'root'@'localhost' IDENTIFIED BY 'RootPassword2025';
FLUSH PRIVILEGES;
EOF

# Step 5: Stop mysqld_safe
echo "Stopping mysqld_safe..." | tee -a "$LOG_FILE"
kill $MARIADB_PID
sleep 5

# Step 6: Restart MariaDB with the initialization script
echo "Restarting MariaDB with initialization script..." | tee -a "$LOG_FILE"
sudo mysqld_safe --init-file=/tmp/reset_root_password.sql > /tmp/mysqld_init.log 2>&1 &
MARIADB_PID=$!
sleep 5

# Verify mysqld_safe started
if ! ps -p $MARIADB_PID > /dev/null; then
    echo "Error: Failed to start MariaDB with initialization script" | tee -a "$LOG_FILE"
    cat /tmp/mysqld_init.log | tee -a "$LOG_FILE"
    exit 1
fi

# Stop mysqld_safe
echo "Stopping mysqld_safe after initialization..." | tee -a "$LOG_FILE"
kill $MARIADB_PID
sleep 5

# Clean up temporary SQL script
rm /tmp/reset_root_password.sql

# Step 7: Restart MariaDB service normally
echo "Restarting MariaDB service normally..." | tee -a "$LOG_FILE"
systemctl start mariadb 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to restart MariaDB service" | tee -a "$LOG_FILE"
    exit 1
fi
sleep 5

# Step 8: Verify root user access and configure
echo "Verifying root user access and configuring..." | tee -a "$LOG_FILE"
mysql -u root -pRootPassword2025 -e "SELECT 1;" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to authenticate as root user with new password" | tee -a "$LOG_FILE"
    exit 1
fi

# Ensure root uses mysql_native_password
mysql -u root -pRootPassword2025 -e "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('RootPassword2025'); FLUSH PRIVILEGES;" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to configure root user authentication plugin" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 9: Create music_user and music_scheduler database
echo "Creating music_user and music_scheduler database..." | tee -a "$LOG_FILE"
mysql -u root -pRootPassword2025 -e "CREATE USER IF NOT EXISTS 'music_user'@'localhost' IDENTIFIED BY 'MusicU2025'; GRANT ALL PRIVILEGES ON music_scheduler.* TO 'music_user'@'localhost'; FLUSH PRIVILEGES;" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create music_user" | tee -a "$LOG_FILE"
    exit 1
fi

mysql -u root -pRootPassword2025 -e "CREATE DATABASE IF NOT EXISTS music_scheduler;" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create music_scheduler database" | tee -a "$LOG_FILE"
    exit 1
fi

mysql -u root -pRootPassword2025 -D music_scheduler -e "CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, password VARCHAR(255) NOT NULL, role ENUM('admin', 'instructor') NOT NULL);" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create users table" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 10: Insert initial users with hashed passwords
echo "Inserting initial users with hashed passwords..." | tee -a "$LOG_FILE"
# Hashed passwords for 'MusicU2025' using bcrypt
ADMIN_HASH='$2b$12$8nxnDdBPYKAVpwVrROSBMOm8I.pgNPLr4jmXKxDd/DFzauV8DyoHa'
INSTRUCTOR_HASH='$2b$12$8nxnDdBPYKAVpwVrROSBMOm8I.pgNPLr4jmXKxDd/DFzauV8DyoHa'

mysql -u root -pRootPassword2025 -D music_scheduler -e "INSERT IGNORE INTO users (username, password, role) VALUES ('admin', '$ADMIN_HASH', 'admin'), ('instructor1', '$INSTRUCTOR_HASH', 'instructor');" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to insert initial users" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 11: Restart Gunicorn service
echo "Restarting Gunicorn service..." | tee -a "$LOG_FILE"
systemctl restart music_scheduler_gunicorn.service 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to restart Gunicorn service" | tee -a "$LOG_FILE"
    echo "Checking Gunicorn service status for errors..." | tee -a "$LOG_FILE"
    systemctl status music_scheduler_gunicorn.service 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

# Step 12: Verify Gunicorn is listening on 127.0.0.1:8000
echo "Verifying Gunicorn is listening on 127.0.0.1:8000..." | tee -a "$LOG_FILE"
sleep 2  # Give Gunicorn a moment to start
netstat -tuln | grep :8000 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Gunicorn is not listening on 127.0.0.1:8000" | tee -a "$LOG_FILE"
    echo "Checking Gunicorn logs for errors..." | tee -a "$LOG_FILE"
    cat /music_scheduler/logs/gunicorn.log 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

# Step 13: Test API endpoints with curl
echo "Testing API endpoint /api/check-auth..." | tee -a "$LOG_FILE"
curl -v http://127.0.0.1:80/api/check-auth 2>&1 | tee -a "$LOG_FILE"

echo "Testing API endpoint /api/login..." | tee -a "$LOG_FILE"
curl -v -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"MusicU2025"}' http://127.0.0.1:80/api/login 2>&1 | tee -a "$LOG_FILE"

echo "Script completed successfully. Next steps:" | tee -a "$LOG_FILE"
echo "1. Test access from your testing VM (e.g., http://192.168.1.63 from 192.168.1.64)." | tee -a "$LOG_FILE"
echo "2. Verify application functionality, including the notes feature." | tee -a "$LOG_FILE"
echo "Check the log for details: cat $LOG_FILE" | tee -a "$LOG_FILE"
