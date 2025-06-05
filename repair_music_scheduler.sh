#!/bin/bash

# Script to repair music scheduler login issue by configuring Flask sessions and Nginx
# Run as root: sudo bash repair_music_scheduler.sh

# Exit on any error
set -e

# Define paths and variables
FLASK_APP="/music_scheduler/app.py"
SESSIONS_DIR="/music_scheduler/sessions"
NGINX_CONFIG="/etc/nginx/sites-enabled/music_scheduler"
BACKUP_DIR="/music_scheduler/backup_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/music_scheduler/logs/repair_$(date +%Y%m%d_%H%M%S).log"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Create log file
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"
log "Starting repair script for music scheduler"

# Step 1: Create sessions directory
log "Creating sessions directory: $SESSIONS_DIR"
if [ ! -d "$SESSIONS_DIR" ]; then
    mkdir -p "$SESSIONS_DIR"
    chmod -R 775 "$SESSIONS_DIR"
    chown -R www-data:www-data "$SESSIONS_DIR"
    log "Sessions directory created and permissions set"
else
    log "Sessions directory already exists"
    chmod -R 775 "$SESSIONS_DIR"
    chown -R www-data:www-data "$SESSIONS_DIR"
    log "Updated permissions for sessions directory"
fi

# Step 2: Backup Flask app file
log "Backing up $FLASK_APP"
mkdir -p "$BACKUP_DIR"
cp "$FLASK_APP" "$BACKUP_DIR/app.py_$(date +%Y%m%d_%H%M%S)"
log "Backup created at $BACKUP_DIR"

# Step 3: Update Flask app for session configuration
log "Updating Flask session configuration in $FLASK_APP"
# Check if session config exists
if ! grep -q "app.config\['SECRET_KEY'\]" "$FLASK_APP"; then
    # Generate a random secret key
    SECRET_KEY=$(openssl rand -hex 16)
    # Insert session config after Flask app initialization
    sed -i '/app = Flask(__name__)/a \
app.config["SECRET_KEY"] = "'"$SECRET_KEY"'"\
app.config["SESSION_TYPE"] = "filesystem"\
app.config["SESSION_FILE_DIR"] = "'"$SESSIONS_DIR"'"\
app.config["SESSION_FILE_THRESHOLD"] = 500\
app.config["SESSION_FILE_MODE"] = 0o775' "$FLASK_APP"
    log "Added session configuration to $FLASK_APP"
else
    log "Session configuration already present in $FLASK_APP"
fi

# Step 4: Backup Nginx configuration
log "Backing up Nginx configuration: $NGINX_CONFIG"
if [ -f "$NGINX_CONFIG" ]; then
    cp "$NGINX_CONFIG" "$BACKUP_DIR/nginx_config_$(date +%Y%m%d_%H%M%S)"
    log "Nginx config backed up to $BACKUP_DIR"
else
    log "Nginx config file $NGINX_CONFIG not found, creating new"
fi

# Step 5: Update Nginx configuration
log "Updating Nginx configuration"
cat > "$NGINX_CONFIG" << 'EOF'
server {
    listen 80;
    server_name 192.168.1.63 musicu-server.local;
    root /music_scheduler/static;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Cookie $http_cookie;
        proxy_pass_header Set-Cookie;
    }
}
EOF
log "Nginx configuration updated at $NGINX_CONFIG"

# Step 6: Test Nginx configuration
log "Testing Nginx configuration"
if nginx -t; then
    log "Nginx configuration test passed"
else
    log "ERROR: Nginx configuration test failed. Check $NGINX_CONFIG"
    exit 1
fi

# Step 7: Restart services
log "Restarting Gunicorn and Nginx services"
systemctl restart music_scheduler_gunicorn.service
systemctl reload nginx
log "Services restarted"

# Step 8: Test login with curl
log "Testing login with curl for admin"
CURL_ADMIN=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://192.168.1.63/api/login -H "Content-Type: application/json" -d '{"username":"admin","password":"MusicU2025"}' -c /tmp/cookies.txt)
if [ "$CURL_ADMIN" -eq 200 ]; then
    log "Admin login test successful (HTTP 200)"
else
    log "ERROR: Admin login test failed (HTTP $CURL_ADMIN)"
fi

log "Testing login with curl for instructor1"
CURL_INSTRUCTOR=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://192.168.1.63/api/login -H "Content-Type: application/json" -d '{"username":"instructor1","password":"MusicU2025"}' -c /tmp/cookies.txt)
if [ "$CURL_INSTRUCTOR" -eq 200 ]; then
    log "Instructor1 login test successful (HTTP 200)"
else
    log "ERROR: Instructor1 login test failed (HTTP $CURL_INSTRUCTOR)"
fi

# Step 9: Check session files
log "Checking for session files in $SESSIONS_DIR"
if ls "$SESSIONS_DIR"/*.sess > /dev/null 2>&1; then
    log "Session files found, session persistence is working"
else
    log "WARNING: No session files found in $SESSIONS_DIR. Frontend may still fail."
fi

# Step 10: Final instructions
log "Repair script completed. Please test login in a browser at http://192.168.1.63/"
log "1. Clear browser cache and try logging in with admin/MusicU2025 and instructor1/MusicU2025."
log "2. Open browser developer tools (F12) and check Console/Network for errors if login fails."
log "3. If issues persist, share /music_scheduler/logs/repair_*.log and browser Console errors."
log "4. Backups are stored in $BACKUP_DIR."

exit 0
