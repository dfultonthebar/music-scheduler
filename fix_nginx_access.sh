#!/bin/bash

# Script to fix Nginx 403 Forbidden error, server name conflict, and logging on musicu-server
# Date: Wed Jun 04 18:10 CDT 2025

LOG_FILE="/music_scheduler/logs/fix_nginx_access.log"

echo "Starting fix_nginx_access.sh at $(date)" | tee -a "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Debug: Logging initialized for fix_nginx_access.sh"

# Step 1: Backup current Nginx configuration
echo "Backing up current Nginx configuration..." | tee -a "$LOG_FILE"
BACKUP_DIR="/root/nginx_backups_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR" 2>&1 | tee -a "$LOG_FILE"
cp -r /etc/nginx "$BACKUP_DIR/nginx_current" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup current Nginx configuration" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 2: Fix logging by ensuring log files are writable and directives are set
echo "Fixing Nginx logging configuration..." | tee -a "$LOG_FILE"
# Ensure log files exist and are writable by www-data
touch /var/log/nginx/access.log /var/log/nginx/error.log 2>&1 | tee -a "$LOG_FILE"
chown www-data:www-data /var/log/nginx/access.log /var/log/nginx/error.log 2>&1 | tee -a "$LOG_FILE"
chmod 644 /var/log/nginx/access.log /var/log/nginx/error.log 2>&1 | tee -a "$LOG_FILE"

# Update /etc/nginx/nginx.conf to ensure logging directives are not overridden
sed -i '/http {/a \    access_log /var/log/nginx/access.log;\n    error_log /var/log/nginx/error.log warn;' /etc/nginx/nginx.conf 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to update logging in /etc/nginx/nginx.conf" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 3: Clean up /etc/nginx/conf.d/ to remove potential conflicting configurations
echo "Cleaning up /etc/nginx/conf.d/ to remove potential conflicts..." | tee -a "$LOG_FILE"
rm -rf /etc/nginx/conf.d/* 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to clean /etc/nginx/conf.d/" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 4: Clean up /etc/nginx/sites-enabled/ again to ensure no conflicts
echo "Cleaning up /etc/nginx/sites-enabled/..." | tee -a "$LOG_FILE"
rm -rf /etc/nginx/sites-enabled/* 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to clean /etc/nginx/sites-enabled/" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 5: Update server block in /etc/nginx/sites-available/music_scheduler to fix 403 error
echo "Updating server block in /etc/nginx/sites-available/music_scheduler..." | tee -a "$LOG_FILE"
cat <<EOF > /etc/nginx/sites-available/music_scheduler
server {
    listen 80 default_server;
    server_name musicu-server.local 192.168.1.63;

    root /music_scheduler/static;
    index index.html;

    location = /favicon.ico {
        try_files /favicon.ico =404;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    allow 192.168.1.0/24;
    allow 127.0.0.1;
    deny all;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log warn;
}
EOF
if [ $? -ne 0 ]; then
    echo "Error: Failed to update /etc/nginx/sites-available/music_scheduler" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 6: Create symlink in /etc/nginx/sites-enabled/
echo "Creating symlink in /etc/nginx/sites-enabled/..." | tee -a "$LOG_FILE"
ln -s /etc/nginx/sites-available/music_scheduler /etc/nginx/sites-enabled/music_scheduler 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create symlink in /etc/nginx/sites-enabled/" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 7: Fix directory permissions for /music_scheduler/static
echo "Fixing directory permissions for /music_scheduler/static..." | tee -a "$LOG_FILE"
chown -R www-data:www-data /music_scheduler/static 2>&1 | tee -a "$LOG_FILE"
chmod -R 755 /music_scheduler/static 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to fix permissions for /music_scheduler/static" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 8: Test and start Nginx
echo "Testing Nginx configuration..." | tee -a "$LOG_FILE"
nginx -t 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Nginx configuration test failed. Restoring current backup..." | tee -a "$LOG_FILE"
    cp -r "$BACKUP_DIR/nginx_current" /etc/nginx 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

echo "Starting Nginx..." | tee -a "$LOG_FILE"
systemctl start nginx 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to start Nginx" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Script completed successfully. Next steps:" | tee -a "$LOG_FILE"
echo "1. Test access from your testing VM (e.g., http://192.168.1.63 from 192.168.1.64)." | tee -a "$LOG_FILE"
echo "2. Verify application functionality, including the notes feature." | tee -a "$LOG_FILE"
echo "Backup of current Nginx configuration is available in $BACKUP_DIR if needed." | tee -a "$LOG_FILE"
echo "Check the log for details: cat $LOG_FILE" | tee -a "$LOG_FILE"
