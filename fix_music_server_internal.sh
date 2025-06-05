#!/bin/bash

# Script to fix iptables and music server issues on musicu-server for internal testing
# Date: Wed Jun 04 16:00 CDT 2025

LOG_FILE="/music_scheduler/logs/fix_music_server_internal.log"

echo "Starting fix_music_server_internal.sh at $(date)" | tee -a "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Debug: Logging initialized for fix_music_server_internal.sh"

# Step 1: Install iptables-persistent to manage persistent firewall rules
echo "Installing iptables-persistent..." | tee -a "$LOG_FILE"
apt-get update | tee -a "$LOG_FILE"
DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to install iptables-persistent" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 2: Simplify iptables rules for internal testing
echo "Removing iptables rule for port 8010..." | tee -a "$LOG_FILE"
iptables -D INPUT -p tcp --dport 8010 -j ACCEPT 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Warning: Failed to remove iptables rule for port 8010 (may not exist)" | tee -a "$LOG_FILE"
fi

echo "Ensuring iptables rule for port 80 allows internal traffic..." | tee -a "$LOG_FILE"
iptables -D INPUT -p tcp --dport 80 -j ACCEPT 2>&1 | tee -a "$LOG_FILE" # Remove existing rule to avoid duplicates
iptables -A INPUT -p tcp --dport 80 -s 192.168.1.0/24 -j ACCEPT 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to add iptables rule for port 80" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Saving iptables rules..." | tee -a "$LOG_FILE"
iptables-save > /etc/iptables/rules.v4 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to save iptables rules to /etc/iptables/rules.v4" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 3: Update Nginx configuration to fix 404 error
echo "Backing up Nginx configuration files..." | tee -a "$LOG_FILE"
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S) 2>&1 | tee -a "$LOG_FILE"
cp /etc/nginx/sites-available/music_scheduler /etc/nginx/sites-available/music_scheduler.bak_$(date +%Y%m%d_%H%M%S) 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup Nginx configuration files" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Updating /etc/nginx/nginx.conf to disable default server block..." | tee -a "$LOG_FILE"
sed -i '/# Default server block to catch unmatched requests/,/}/ s/^/# /' /etc/nginx/nginx.conf 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to update /etc/nginx/nginx.conf" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Verifying /etc/nginx/sites-available/music_scheduler configuration..." | tee -a "$LOG_FILE"
# Ensure the correct server block configuration for internal access
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
    deny all;
}
EOF
if [ $? -ne 0 ]; then
    echo "Error: Failed to update /etc/nginx/sites-available/music_scheduler" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 4: Test and reload Nginx
echo "Testing Nginx configuration..." | tee -a "$LOG_FILE"
nginx -t 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Nginx configuration test failed. Restoring backups..." | tee -a "$LOG_FILE"
    cp /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S) /etc/nginx/nginx.conf 2>&1 | tee -a "$LOG_FILE"
    cp /etc/nginx/sites-available/music_scheduler.bak_$(date +%Y%m%d_%H%M%S) /etc/nginx/sites-available/music_scheduler 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

echo "Reloading Nginx..." | tee -a "$LOG_FILE"
systemctl reload nginx 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to reload Nginx" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Script completed successfully. Next steps:" | tee -a "$LOG_FILE"
echo "1. Test access from your testing VM (e.g., http://192.168.1.63 from 192.168.1.64)." | tee -a "$LOG_FILE"
echo "2. Verify application functionality, including the notes feature." | tee -a "$LOG_FILE"
echo "Check the log for details: cat $LOG_FILE" | tee -a "$LOG_FILE"
