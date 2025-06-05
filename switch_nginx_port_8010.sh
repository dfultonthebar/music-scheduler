#!/bin/bash

# Script to switch Nginx to port 8010 for music lesson scheduler application
# Date: Wed Jun 04 14:15 CDT 2025

echo "Starting switch_nginx_port_8010.sh at $(date)"
exec > >(tee -a /music_scheduler/logs/switch_nginx_port_8010.log) 2>&1

echo "Debug: Logging initialized for switch_nginx_port_8010.sh"

# Backup current Nginx configuration files
echo "Backing up Nginx configuration files..."
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S)
cp /etc/nginx/sites-available/music_scheduler /etc/nginx/sites-available/music_scheduler.bak_$(date +%Y%m%d_%H%M%S)
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup Nginx configuration files"
    exit 1
fi

# Update /etc/nginx/sites-available/music_scheduler to listen on port 8010
echo "Updating /etc/nginx/sites-available/music_scheduler to listen on port 8010..."
sed -i 's/listen 8007 default_server;/listen 8010 default_server;/g' /etc/nginx/sites-available/music_scheduler
if [ $? -ne 0 ]; then
    echo "Error: Failed to update /etc/nginx/sites-available/music_scheduler"
    exit 1
fi

# Ensure /etc/nginx/nginx.conf has no conflicting server block on port 8010
echo "Checking /etc/nginx/nginx.conf for port conflicts..."
if grep -q "listen 8010" /etc/nginx/nginx.conf; then
    echo "Warning: Found a server block listening on port 8010 in /etc/nginx/nginx.conf. Commenting it out..."
    sed -i '/listen 8010/s/^/#/' /etc/nginx/nginx.conf
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

echo "Nginx configuration updated to use port 8010. Next steps:"
echo "1. Update your router's port forwarding to forward external port 8010 to internal port 8010 on 192.168.1.63."
echo "2. Update Proxmox firewall rules to allow port 8010 (previously set for 8007)."
echo "3. Test remote access at http://135.131.39.26:8010."
echo "Check the log for details: cat /music_scheduler/logs/switch_nginx_port_8010.log"
