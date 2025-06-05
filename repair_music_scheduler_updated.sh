#!/bin/bash

# Updated script to repair music scheduler login issue
# Run as root: sudo bash repair_music_scheduler_updated.sh

set -e

FLASK_APP="/music_scheduler/app.py"
SESSIONS_DIR="/music_scheduler/sessions"
NGINX_CONFIG="/etc/nginx/sites-enabled/music_scheduler"
BACKUP_DIR="/music_scheduler/backup_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/music_scheduler/logs/repair_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"
log "Starting updated repair script for music scheduler"

# Install flask_session
log "Installing flask_session"
pip install flask_session || log "WARNING: Failed to install flask_session"

# Create sessions directory
log "Creating sessions directory: $SESSIONS_DIR"
if [ ! -d "$SESSIONS_DIR" ]; then
    mkdir -p "$SESSIONS_DIR"
    chmod -R 775 "$SESSIONS_DIR"
    chown -R www-data:www-data "$SESSIONS_DIR"
    log "Sessions directory created and permissions set"
else
    chmod -R 775 "$SESSIONS_DIR"
    chown -R www-data:www-data "$SESSIONS_DIR"
    log "Updated permissions for sessions directory"
fi

# Backup Flask app
log "Backing up $FLASK_APP"
mkdir -p "$BACKUP_DIR"
cp "$FLASK_APP" "$BACKUP_DIR/app.py_$(date +%Y%m%d_%H%M%S)"
log "Backup created at $BACKUP_DIR"

# Update Flask app
log "Updating Flask session configuration in $FLASK_APP"
if ! grep -q "from flask_session import Session" "$FLASK_APP"; then
    sed -i '/from flask import Flask/a from flask_session import Session' "$FLASK_APP"
    log "Added flask_session import to $FLASK_APP"
fi
if ! grep -q "app.config\['SECRET_KEY'\]" "$FLASK_APP"; then
    SECRET_KEY=$(openssl rand -hex 16)
    sed -i '/app = Flask(__name__)/a \
app.config["SECRET_KEY"] = "'"$SECRET_KEY"'"\
app.config["SESSION_TYPE"] = "filesystem"\
app.config["SESSION_FILE_DIR"] = "'"$SESSIONS_DIR"'"\
app.config["SESSION_FILE_THRESHOLD"] = 500\
app.config["SESSION_FILE_MODE"] = 0o775\
Session(app)' "$FLASK_APP"
    log "Added session configuration to $FLASK_APP"
else
    log "Session configuration already present"
fi

# Backup Nginx config
log "Backing up Nginx configuration: $NGINX_CONFIG"
if [ -f "$NGINX_CONFIG" ]; then
    cp "$NGINX_CONFIG" "$BACKUP_DIR/nginx_config_$(date +%Y%m%d_%H%M%S)"
    log "Nginx config backed up to $BACKUP_DIR"
fi

# Update Nginx config
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
log "Nginx configuration updated"

# Test Nginx config
log "Testing Nginx configuration"
if nginx -t; then
    log "Nginx configuration test passed"
else
    log "ERROR: Nginx configuration test failed"
    exit 1
fi

# Restart services
log "Restarting Gunicorn and Nginx services"
systemctl restart music_scheduler_gunicorn.service
systemctl reload nginx
log "Services restarted"

# Test login
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

# Check session files
log "Checking for session files in $SESSIONS_DIR"
if ls "$SESSIONS_DIR"/*.sess > /dev/null 2>&1; then
    log "Session files found, session persistence is working"
else
    log "WARNING: No session files found in $SESSIONS_DIR"
fi

# Final instructions
log "Repair script completed. Test login at http://192.168.1.63/"
log "1. Clear browser cache and try admin/MusicU2025 and instructor1/MusicU2025."
log "2. Check browser Console/Network (F12) for errors if login fails."
log "3. Share /music_scheduler/logs/repair_*.log and Console errors if issues persist."
log "4. Backups are in $BACKUP_DIR."

exit 0
