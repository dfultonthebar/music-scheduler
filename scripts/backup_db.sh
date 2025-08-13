
#!/bin/bash

# Music Scheduler Database Backup Script
# This script creates a MySQL dump backup and pushes it to GitHub

set -e  # Exit on any error

# Load environment variables if .env exists
if [ -f ../.env ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
fi

# Database configuration with defaults
DB_HOST=${DB_HOST:-localhost}
DB_USER=${DB_USER:-music_user}
DB_PASSWORD=${DB_PASSWORD:-music_pass}
DB_NAME=${DB_NAME:-music_scheduler}

# Create backups directory if it doesn't exist
# Get the absolute path to the script directory and then find project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
BACKUP_DIR="$PROJECT_ROOT/database_backups"
mkdir -p "$BACKUP_DIR"

# Generate timestamp for backup filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/music_scheduler_backup_$TIMESTAMP.sql"
BACKUP_LOG="$BACKUP_DIR/backup_log.txt"

echo "$(date): Starting database backup..." >> "$BACKUP_LOG"

# Create MySQL dump
echo "Creating database backup: $BACKUP_FILE"
mysqldump -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" \
    --single-transaction \
    --routines \
    --triggers \
    --add-drop-table \
    --extended-insert \
    --create-options > "$BACKUP_FILE"

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "$(date): Backup created successfully: $BACKUP_FILE" >> "$BACKUP_LOG"
    echo "Backup created successfully: $BACKUP_FILE"
    
    # Compress the backup file
    gzip "$BACKUP_FILE"
    BACKUP_FILE="$BACKUP_FILE.gz"
    echo "Backup compressed: $BACKUP_FILE"
    
    # Get file size
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "$(date): Backup size: $FILE_SIZE" >> "$BACKUP_LOG"
    
    # Add backup to git and push to GitHub
    cd "$PROJECT_ROOT"
    git add "database_backups/$(basename $BACKUP_FILE)" "database_backups/backup_log.txt"
    git commit -m "Database backup: $TIMESTAMP

- Backup file: $(basename $BACKUP_FILE)
- Size: $FILE_SIZE
- Date: $(date)
- Automated backup via cron job"
    
    # Push to GitHub
    git push origin main
    
    if [ $? -eq 0 ]; then
        echo "$(date): Backup pushed to GitHub successfully" >> "database_backups/backup_log.txt"
        echo "Backup pushed to GitHub successfully"
        
        # Clean up old backups (keep last 30 days)
        find "database_backups" -name "*.sql.gz" -mtime +30 -delete
        echo "$(date): Cleaned up old backups (>30 days)" >> "database_backups/backup_log.txt"
    else
        echo "$(date): ERROR: Failed to push backup to GitHub" >> "database_backups/backup_log.txt"
        echo "ERROR: Failed to push backup to GitHub"
        exit 1
    fi
    
else
    echo "$(date): ERROR: Database backup failed" >> "$BACKUP_LOG"
    echo "ERROR: Database backup failed"
    exit 1
fi

echo "$(date): Backup process completed" >> "$BACKUP_LOG"
echo "Database backup completed successfully!"
