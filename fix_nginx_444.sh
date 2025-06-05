#!/bin/bash

# Script to fix the 444 status code issue in Nginx configuration
# Date: Wed Jun 04 13:10 CDT 2025

echo "Starting fix_nginx_444.sh at $(date)"
exec > >(tee -a /music_scheduler/logs/fix_nginx_444.log) 2>&1

echo "Debug: Logging initialized for fix_nginx_444.sh"

# Backup the current nginx.conf
echo "Backing up /etc/nginx/nginx.conf..."
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S)
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup /etc/nginx/nginx.conf"
    exit 1
fi

# Modify nginx.conf to allow remote IP (70.60.82.222)
echo "Modifying /etc/nginx/nginx.conf to allow IP 70.60.82.222..."
sed -i '/return 444; # Close connection for unmatched requests/i \ \ \ \ \ \ \ \ allow 70.60.82.222;' /etc/nginx/nginx.conf
sed -i 's/return 444; # Close connection for unmatched requests/# return 444; # Close connection for unmatched requests (disabled)/' /etc/nginx/nginx.conf

if [ $? -ne 0 ]; then
    echo "Error: Failed to modify /etc/nginx/nginx.conf"
    exit 1
fi

# Test Nginx configuration
echo "Testing Nginx configuration..."
nginx -t
if [ $? -ne 0 ]; then
    echo "Error: Nginx configuration test failed. Restoring backup..."
    cp /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S) /etc/nginx/nginx.conf
    exit 1
fi

# Reload Nginx
echo "Reloading Nginx..."
systemctl reload nginx
if [ $? -ne 0 ]; then
    echo "Error: Failed to reload Nginx"
    exit 1
fi

echo "Nginx configuration updated successfully. Check the log for details: cat /music_scheduler/logs/fix_nginx_444.log"#!/bin/bash

# Script to fix the 444 status code issue in Nginx configuration
# Date: Wed Jun 04 13:10 CDT 2025

echo "Starting fix_nginx_444.sh at $(date)"
exec > >(tee -a /music_scheduler/logs/fix_nginx_444.log) 2>&1

echo "Debug: Logging initialized for fix_nginx_444.sh"

# Backup the current nginx.conf
echo "Backing up /etc/nginx/nginx.conf..."
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S)
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup /etc/nginx/nginx.conf"
    exit 1
fi

# Modify nginx.conf to allow remote IP (70.60.82.222)
echo "Modifying /etc/nginx/nginx.conf to allow IP 70.60.82.222..."
sed -i '/return 444; # Close connection for unmatched requests/i \ \ \ \ \ \ \ \ allow 70.60.82.222;' /etc/nginx/nginx.conf
sed -i 's/return 444; # Close connection for unmatched requests/# return 444; # Close connection for unmatched requests (disabled)/' /etc/nginx/nginx.conf

if [ $? -ne 0 ]; then
    echo "Error: Failed to modify /etc/nginx/nginx.conf"
    exit 1
fi

# Test Nginx configuration
echo "Testing Nginx configuration..."
nginx -t
if [ $? -ne 0 ]; then
    echo "Error: Nginx configuration test failed. Restoring backup..."
    cp /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S) /etc/nginx/nginx.conf
    exit 1
fi

# Reload Nginx
echo "Reloading Nginx..."
systemctl reload nginx
if [ $? -ne 0 ]; then
    echo "Error: Failed to reload Nginx"
    exit 1
fi

echo "Nginx configuration updated successfully. Check the log for details: cat /music_scheduler/logs/fix_nginx_444.log"
