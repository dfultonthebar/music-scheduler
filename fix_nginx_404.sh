#!/bin/bash

# Script to fix the 404 Not Found error in Nginx configuration by ensuring music_scheduler server block handles requests
# Date: Wed Jun 04 13:25 CDT 2025

echo "Starting fix_nginx_404.sh at $(date)"
exec > >(tee -a /music_scheduler/logs/fix_nginx_404.log) 2>&1

echo "Debug: Logging initialized for fix_nginx_404.sh"

# Backup current Nginx configuration files
echo "Backing up Nginx configuration files..."
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S)
cp /etc/nginx/sites-available/music_scheduler /etc/nginx/sites-available/music_scheduler.bak_$(date +%Y%m%d_%H%M%S)
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup Nginx configuration files"
    exit 1
fi

# Update /etc/nginx/sites-available/music_scheduler to handle requests correctly
echo "Updating /etc/nginx/sites-available/music_scheduler..."
cat <<EOF > /etc/nginx/sites-available/music_scheduler
server {
    listen 8080;
    server_name 135.131.39.26 musicu-server.local 192.168.1.63;

    # Serve static files from /music_scheduler/static
    root /music_scheduler/static;
    index index.html;

    # Serve favicon.ico directly if it exists
    location = /favicon.ico {
        try_files /favicon.ico =404;
    }

    # Proxy API requests to Gunicorn
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Serve static files for all other requests
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Allow access from specific IPs (already updated by previous script)
    allow 70.60.82.222;
    allow 192.168.1.0/24;
    deny all;
}
EOF

if [ $? -ne 0 ]; then
    echo "Error: Failed to update /etc/nginx/sites-available/music_scheduler"
    exit 1
fi

# Ensure /etc/nginx/nginx.conf default server block doesn't interfere
echo "Updating /etc/nginx/nginx.conf default server block..."
sed -i 's/listen 8080 default_server;/listen 8080 default_server;/g' /etc/nginx/nginx.conf
# Ensure the allow directive and commented return 444 are present (already added by previous script)
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

echo "Nginx configuration updated to fix 404 error. Check the log for details: cat /music_scheduler/logs/fix_nginx_404.log"
