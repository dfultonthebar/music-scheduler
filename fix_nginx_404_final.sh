#!/bin/bash

# Script to fix the persistent 404 Not Found error by ensuring music_scheduler server block is the default handler
# Date: Wed Jun 04 13:30 CDT 2025

echo "Starting fix_nginx_404_final.sh at $(date)"
exec > >(tee -a /music_scheduler/logs/fix_nginx_404_final.log) 2>&1

echo "Debug: Logging initialized for fix_nginx_404_final.sh"

# Backup current Nginx configuration files
echo "Backing up Nginx configuration files..."
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S)
cp /etc/nginx/sites-available/music_scheduler /etc/nginx/sites-available/music_scheduler.bak_$(date +%Y%m%d_%H%M%S)
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup Nginx configuration files"
    exit 1
fi

# Update /etc/nginx/sites-available/music_scheduler to be the default server on port 8080
echo "Updating /etc/nginx/sites-available/music_scheduler to be the default server..."
sed -i 's/listen 8080;/listen 8080 default_server;/' /etc/nginx/sites-available/music_scheduler
if [ $? -ne 0 ]; then
    echo "Error: Failed to update /etc/nginx/sites-available/music_scheduler"
    exit 1
fi

# Modify /etc/nginx/nginx.conf to remove or adjust the default server block on port 8080
echo "Updating /etc/nginx/nginx.conf to remove default server block on port 8080..."
# Comment out the default server block's listen directive
sed -i '/listen 8080 default_server;/s/^/#/' /etc/nginx/nginx.conf
# Ensure the allow directive is present (already added by previous script)
if ! grep -q "allow 70.60.82.222;" /etc/nginx/nginx.conf; then
    sed -i '/# return 444; # Close connection for unmatched requests (disabled)/i \ \ \ \ \ \ \ \ allow 70.60.82.222;' /etc/nginx/nginx.conf
fi

# Test Nginx configuration
echo "Testing Nginx configuration..."
nginx -t
if [ $? -ne 0 ]; then
    echo "Error: Nginx configuration test failed. Restoring backups..."
    cp /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S) /etc/nginx/nginx.conf
    cp /etc/nginx/sites-available/music_scheduler.bak_$(date +%Y%m%d_%H%M%S) /etc/nginx/sites-available/music_scheduler
    exit 1
fi

# Reload Nginx
echo "Reloading Nginx..."
systemctl reload nginx
if [ $? -ne 0 ]; then
    echo "Error: Failed to reload Nginx"
    exit 1
fi

echo "Nginx configuration updated to fix persistent 404 error. Check the log for details: cat /music_scheduler/logs/fix_nginx_404_final.log"
