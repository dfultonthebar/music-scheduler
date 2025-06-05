#!/bin/bash

# Script to safely run setup_core.sh with backups and logging
# Date: Wed Jun 04 16:46 CDT 2025

LOG_FILE="/music_scheduler/logs/run_setup_core.log"

echo "Starting run_setup_core.sh at $(date)" | tee -a "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Debug: Logging initialized for run_setup_core.sh"

# Step 1: Backup current configurations
echo "Backing up current configurations..." | tee -a "$LOG_FILE"
BACKUP_DIR="/root/backups_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR" 2>&1 | tee -a "$LOG_FILE"

# Backup Nginx configuration
cp -r /etc/nginx "$BACKUP_DIR/nginx" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup Nginx configuration" | tee -a "$LOG_FILE"
    exit 1
fi

# Backup iptables rules
iptables-save > "$BACKUP_DIR/iptables_rules.v4" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup iptables rules" | tee -a "$LOG_FILE"
    exit 1
fi

# Backup Gunicorn service configuration
cp /etc/systemd/system/music_scheduler_gunicorn.service "$BACKUP_DIR/music_scheduler_gunicorn.service" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to backup Gunicorn service configuration" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Backups saved to $BACKUP_DIR" | tee -a "$LOG_FILE"

# Step 2: Stop services to avoid conflicts
echo "Stopping Nginx and Gunicorn services..." | tee -a "$LOG_FILE"
systemctl stop nginx 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to stop Nginx" | tee -a "$LOG_FILE"
    exit 1
fi

systemctl stop music_scheduler_gunicorn 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to stop Gunicorn" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 3: Run setup_core.sh
echo "Running setup_core.sh..." | tee -a "$LOG_FILE"
if [ -f "/music_scheduler/setup_core.sh" ]; then
    bash /music_scheduler/setup_core.sh 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "Error: setup_core.sh failed. Check logs above for details." | tee -a "$LOG_FILE"
        echo "Restoring services..." | tee -a "$LOG_FILE"
        systemctl start nginx 2>&1 | tee -a "$LOG_FILE"
        systemctl start music_scheduler_gunicorn 2>&1 | tee -a "$LOG_FILE"
        exit 1
    fi
else
    echo "Error: setup_core.sh not found in /music_scheduler/" | tee -a "$LOG_FILE"
    echo "Restoring services..." | tee -a "$LOG_FILE"
    systemctl start nginx 2>&1 | tee -a "$LOG_FILE"
    systemctl start music_scheduler_gunicorn 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

# Step 4: Restart services
echo "Restarting Nginx and Gunicorn services..." | tee -a "$LOG_FILE"
systemctl start nginx 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to start Nginx" | tee -a "$LOG_FILE"
    exit 1
fi

systemctl start music_scheduler_gunicorn 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to start Gunicorn" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Script completed successfully. Next steps:" | tee -a "$LOG_FILE"
echo "1. Test access from your testing VM (e.g., http://192.168.1.63 from 192.168.1.64)." | tee -a "$LOG_FILE"
echo "2. Verify application functionality, including the notes feature." | tee -a "$LOG_FILE"
echo "Backups are available in $BACKUP_DIR if needed." | tee -a "$LOG_FILE"
echo "Check the log for details: cat $LOG_FILE" | tee -a "$LOG_FILE"
