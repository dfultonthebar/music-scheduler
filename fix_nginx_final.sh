#!/bin/bash

# Script to fix Nginx 403 Forbidden error and server name conflict on musicu-server (final revision)
# Date: Wed Jun 04 18:15 CDT 2025

LOG_FILE="/music_scheduler/logs/fix_nginx_final.log"

echo "Starting fix_nginx_final.sh at $(date)" | tee -a "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Debug: Logging initialized for fix_nginx_final.sh"

# Step 1: Backup current Nginx configuration
echo "Backing up current Nginx configuration..." | tee -a "$LOG_FILE"
BACKUP_DIR="/root/nginx_backups_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR" 2>&1 | tee -a "$LOG_FILE"
cp -r /etc/nginx "$BACKUP_DIR/nginx_current" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup current Nginx configuration" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 2: Clean up /etc/nginx/conf.d/ and /etc/nginx/sites-enabled/ to remove conflicts
echo "Cleaning up /etc/nginx/conf.d/ to remove potential conflicts..." | tee -a "$LOG_FILE"
rm -rf /etc/nginx/conf.d/* 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to clean /etc/nginx/conf.d/" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Cleaning up /etc/nginx/sites-enabled/..." | tee -a "$LOG_FILE"
rm -rf /etc/nginx/sites-enabled/* 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to clean /etc/nginx/sites-enabled/" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 3: Remove any server blocks from /etc/nginx/nginx.conf
echo "Removing server blocks from /etc/nginx/nginx.conf..." | tee -a "$LOG_FILE"
sed -i '/server {/,/}/d' /etc/nginx/nginx.conf 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to remove server blocks from /etc/nginx/nginx.conf" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 4: Update server block in /etc/nginx/sites-available/music_scheduler
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

# Step 5: Create symlink in /etc/nginx/sites-enabled/
echo "Creating symlink in /etc/nginx/sites-enabled/..." | tee -a "$LOG_FILE"
ln -s /etc/nginx/sites-available/music_scheduler /etc/nginx/sites-enabled/music_scheduler 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create symlink in /etc/nginx/sites-enabled/" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 6: Verify index.html exists in /music_scheduler/static
echo "Verifying index.html exists in /music_scheduler/static..." | tee -a "$LOG_FILE"
if [ ! -f "/music_scheduler/static/index.html" ]; then
    echo "Error: /music_scheduler/static/index.html does not exist" | tee -a "$LOG_FILE"
    echo "Listing contents of /music_scheduler/static:" | tee -a "$LOG_FILE"
    ls -la /music_scheduler/static 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

# Step 7: Test and restart Nginx
echo "Testing Nginx configuration..." | tee -a "$LOG_FILE"
nginx -t 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Nginx configuration test failed. Restoring current backup..." | tee -a "$LOG_FILE"
    cp -r "$BACKUP_DIR/nginx_current" /etc/nginx 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

echo "Restarting Nginx..." | tee -a "$LOG_FILE"
systemctl restart nginx 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to restart Nginx" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Script completed successfully. Next steps:" | tee -a "$LOG_FILE"
echo "1. Test access from your testing VM (e.g., http://192.168.1.63 from 192.168.1.64)." | tee -a "$LOG_FILE"
echo "2. Verify application functionality, including the notes feature." | tee -a "$LOG_FILE"
echo "Backup of current Nginx configuration is available in $BACKUP_DIR if needed." | tee -a "$LOG_FILE"
echo "Check the log for details: cat $LOG_FILE" | tee -a "$LOG_FILE"
