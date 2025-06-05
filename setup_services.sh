#!/bin/bash

echo "Starting setup_services.sh logging at $(date)"
exec > >(tee -a /music_scheduler/logs/setup_services.log) 2>&1

echo "Debug: Logging initialized for setup_services.sh"

# Configure Nginx
echo "Configuring Nginx..."
cat > /etc/nginx/sites-available/music_scheduler << 'EOF'
server {
    listen 80;
    server_name musicu-server.local 192.168.1.63;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /music_scheduler/static/;
        expires 1d;
        add_header Cache-Control "public, must-revalidate";
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
    }
}
EOF

# Symlink to sites-enabled
ln -sf /etc/nginx/sites-available/music_scheduler /etc/nginx/sites-enabled/

# Verify Nginx configuration
echo "Verifying Nginx configuration..."
nginx -t
if [ $? -ne 0 ]; then
    echo "Error: Nginx configuration test failed"
    exit 1
fi

# Reload Nginx to apply the new configuration
echo "Reloading Nginx to apply the new configuration..."
systemctl reload nginx
if [ $? -ne 0 ]; then
    echo "Error: Failed to reload Nginx"
    journalctl -u nginx.service -n 20 --no-pager
    exit 1
fi

# Check Nginx status
echo "Checking Nginx status..."
systemctl status nginx | grep 'Active:'
if ! systemctl --quiet is-active nginx; then
    echo "Error: Nginx service is not running"
    exit 1
else
    echo "Nginx service is running."
fi

# Set up Avahi for mDNS
echo "Setting up Avahi for mDNS..."
cat > /etc/avahi/services/music_scheduler.service << 'EOF'
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
    <name replace-wildcards="yes">Music Scheduler on %h</name>
    <service>
        <type>_http._tcp</type>
        <port>80</port>
    </service>
</service-group>
EOF

# Open firewall for mDNS (UDP port 5353)
echo "Opening firewall for mDNS (UDP port 5353)..."
ufw allow 5353/udp

# Restart Avahi to apply the new service
systemctl restart avahi-daemon
if [ $? -ne 0 ]; then
    echo "Error: Failed to restart Avahi daemon"
    journalctl -u avahi-daemon.service -n 20 --no-pager
    exit 1
fi

# Check Avahi status
echo "Checking Avahi status..."
systemctl status avahi-daemon | grep 'Active:'
if ! systemctl --quiet is-active avahi-daemon; then
    echo "Error: Avahi service is not running"
    exit 1
else
    echo "Avahi service is running."
fi

# Wait for Avahi to register hostname
echo "Waiting for Avahi to register hostname..."
sleep 5

# Test mDNS resolution on the server
echo "Testing mDNS resolution on the server..."
avahi-resolve -n musicu-server.local
if [ $? -ne 0 ]; then
    echo "Error: mDNS resolution failed for musicu-server.local"
    exit 1
else
    echo "mDNS resolution successful for musicu-server.local."
fi

echo "Services setup complete! Check the setup log for details: cat /music_scheduler/logs/setup_services.log"
