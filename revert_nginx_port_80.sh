#!/bin/bash

# Script to revert Nginx on musicu-server to port 80 for music lesson scheduler application
# Date: Wed Jun 04 14:20 CDT 2025

echo "Starting revert_nginx_port_80.sh at $(date)"
exec > >(tee -a /music_scheduler/logs/revert_nginx_port_80.log) 2>&1

echo "Debug: Logging initialized for revert_nginx_port_80.sh"

# Backup current Nginx configuration files
echo "Backing up Nginx configuration files..."
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S)
cp /etc/nginx/sites-available/music_scheduler /etc/nginx/sites-available/music_scheduler.bak_$(date +%Y%m%d_%H%M%S)
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup Nginx configuration files"
    exit 1
fi

# Update /etc/nginx/sites-available/music_scheduler to listen on port 80
echo "Updating /etc/nginx/sites-available/music_scheduler to listen on port 80..."
# Replace any previous port (8007 or 8010) with 80
sed -i 's/listen [0-9]\+ default_server;/listen 80 default_server;/g' /etc/nginx/sites-available/music_scheduler
if [ $? -ne 0 ]; then
    echo "Error: Failed to update /etc/nginx/sites-available/music_scheduler"
    exit 1
fi

# Update /etc/nginx/nginx.conf to remove the existing server block on port 80
echo "Updating /etc/nginx/nginx.conf to remove existing server block on port 80..."
# Comment out the existing server block on port 80
sed -i '/server {/,/}/ { /listen 80;/,/}/ s/^/# /}' /etc/nginx/nginx.conf
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

echo "Nginx configuration reverted to use port 80 on musicu-server. Next steps:"
echo "1. Update your router's port forwarding to forward external port 80 to internal port 80 on 192.168.1.63 (instead of 192.168.1.64)."
echo "2. Update Proxmox firewall rules to allow port 80 (if previously changed to another port)."
echo "3. Test remote access at http://135.131.39.26."
echo "Check the log for details: cat /music_scheduler/logs/revert_nginx_port_80.log":wq

