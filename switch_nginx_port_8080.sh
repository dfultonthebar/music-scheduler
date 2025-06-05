#!/bin/bash

# Script to switch Nginx to port 8080 and fix the 444 status code issue
# Date: Wed Jun 04 13:14 CDT 2025

echo "Starting switch_nginx_port_8080.sh at $(date)"
exec > >(tee -a /music_scheduler/logs/switch_nginx_port_8080.log) 2>&1

echo "Debug: Logging initialized for switch_nginx_port_8080.sh"

# Backup current Nginx configuration files
echo "Backing up Nginx configuration files..."
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S)
cp /etc/nginx/sites-available/music_scheduler /etc/nginx/sites-available/music_scheduler.bak_$(date +%Y%m%d_%H%M%S)
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup Nginx configuration files"
    exit 1
fi

# Update /etc/nginx/sites-available/music_scheduler to listen on port 8080
echo "Updating /etc/nginx/sites-available/music_scheduler to listen on port 8080..."
sed -i 's/listen 80;/listen 8080;/g' /etc/nginx/sites-available/music_scheduler
if [ $? -ne 0 ]; then
    echo "Error: Failed to update /etc/nginx/sites-available/music_scheduler"
    exit 1
fi

# Update /etc/nginx/nginx.conf to listen on port 8080 and allow remote IP (70.60.82.222)
echo "Updating /etc/nginx/nginx.conf..."
# Change the default server block to listen on 8080
sed -i 's/listen 80 default_server;/listen 8080 default_server;/g' /etc/nginx/nginx.conf
# Add allow directive for remote IP and comment out return 444
sed -i '/return 444; # Close connection for unmatched requests/i \ \ \ \ \ \ \ \ allow 70.60.82.222;' /etc/nginx/nginx.conf
sed -i 's/return 444; # Close connection for unmatched requests/# return 444; # Close connection for unmatched requests (disabled)/' /etc/nginx/nginx.conf
if [ $? -ne 0 ]; then
    echo "Error: Failed to update /etc/nginx/nginx.conf"
    exit 1
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

echo "Nginx configuration updated to use port 8080 and allow IP 70.60.82.222. Check the log for details: cat /music_scheduler/logs/switch_nginx_port_8080.log"
