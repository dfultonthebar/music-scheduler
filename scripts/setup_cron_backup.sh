
#!/bin/bash

# Setup automatic database backups using cron
# This script adds a cron job to run database backup daily at 2:00 AM

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup_db.sh"

# Check if backup script exists
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "ERROR: Backup script not found at $BACKUP_SCRIPT"
    exit 1
fi

# Make sure backup script is executable
chmod +x "$BACKUP_SCRIPT"

# Add cron job for daily backup at 2:00 AM
CRON_ENTRY="0 2 * * * $BACKUP_SCRIPT >> /tmp/music_scheduler_backup_cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
    echo "Cron job for database backup already exists"
    echo "Current cron jobs:"
    crontab -l | grep "$BACKUP_SCRIPT"
else
    # Add the cron job
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    if [ $? -eq 0 ]; then
        echo "Automatic backup scheduled successfully!"
        echo "Backups will run daily at 2:00 AM"
        echo "Cron job: $CRON_ENTRY"
        echo
        echo "To view cron logs: tail -f /tmp/music_scheduler_backup_cron.log"
        echo "To remove automatic backup: crontab -e"
    else
        echo "ERROR: Failed to add cron job"
        exit 1
    fi
fi

echo
echo "Current cron jobs for this user:"
crontab -l
