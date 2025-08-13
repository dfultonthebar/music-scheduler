
#!/bin/bash

# Music Scheduler Database Restore Script
# This script restores the MySQL database from a backup file

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

# Check if backup file is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file.sql or backup_file.sql.gz>"
    echo "Available backup files:"
    ls -la ../database_backups/*.sql* 2>/dev/null || echo "No backup files found"
    exit 1
fi

BACKUP_FILE="$1"
RESTORE_LOG="../database_backups/restore_log.txt"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file '$BACKUP_FILE' not found"
    exit 1
fi

echo "$(date): Starting database restore from $BACKUP_FILE..." >> "$RESTORE_LOG"
echo "Starting database restore from: $BACKUP_FILE"

# Validate backup file
if [[ "$BACKUP_FILE" == *.gz ]]; then
    # Test if gzip file is valid
    if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
        echo "$(date): ERROR: Invalid or corrupted gzip file: $BACKUP_FILE" >> "$RESTORE_LOG"
        echo "ERROR: Invalid or corrupted gzip file"
        exit 1
    fi
    echo "Backup file validation: OK (compressed)"
elif [[ "$BACKUP_FILE" == *.sql ]]; then
    # Test if SQL file contains MySQL dump header
    if ! head -10 "$BACKUP_FILE" | grep -q "MySQL dump"; then
        echo "$(date): ERROR: File does not appear to be a MySQL dump: $BACKUP_FILE" >> "$RESTORE_LOG"
        echo "ERROR: File does not appear to be a MySQL dump"
        exit 1
    fi
    echo "Backup file validation: OK (uncompressed)"
else
    echo "$(date): ERROR: Unsupported file format. Use .sql or .sql.gz files" >> "$RESTORE_LOG"
    echo "ERROR: Unsupported file format. Use .sql or .sql.gz files"
    exit 1
fi

# Confirmation prompt
echo "WARNING: This will replace all data in database '$DB_NAME'"
echo "Make sure you have a current backup before proceeding!"
read -p "Are you sure you want to restore? (type 'YES' to confirm): " -r
if [[ ! "$REPLY" == "YES" ]]; then
    echo "Restore cancelled by user"
    echo "$(date): Restore cancelled by user" >> "$RESTORE_LOG"
    exit 0
fi

# Create a backup before restore
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PRE_RESTORE_BACKUP="../database_backups/pre_restore_backup_$TIMESTAMP.sql.gz"
echo "Creating pre-restore backup: $PRE_RESTORE_BACKUP"
mysqldump -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" \
    --single-transaction --routines --triggers --add-drop-table | gzip > "$PRE_RESTORE_BACKUP"

if [ $? -eq 0 ]; then
    echo "Pre-restore backup created successfully"
    echo "$(date): Pre-restore backup created: $PRE_RESTORE_BACKUP" >> "$RESTORE_LOG"
else
    echo "ERROR: Failed to create pre-restore backup"
    echo "$(date): ERROR: Failed to create pre-restore backup" >> "$RESTORE_LOG"
    exit 1
fi

# Restore database
echo "Restoring database..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    # Restore from compressed file
    gunzip -c "$BACKUP_FILE" | mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME"
else
    # Restore from uncompressed file
    mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$BACKUP_FILE"
fi

# Check if restore was successful
if [ $? -eq 0 ]; then
    echo "$(date): Database restore completed successfully from $BACKUP_FILE" >> "$RESTORE_LOG"
    echo "Database restore completed successfully!"
    echo "Pre-restore backup saved as: $PRE_RESTORE_BACKUP"
else
    echo "$(date): ERROR: Database restore failed from $BACKUP_FILE" >> "$RESTORE_LOG"
    echo "ERROR: Database restore failed"
    echo "You may need to restore from the pre-restore backup: $PRE_RESTORE_BACKUP"
    exit 1
fi
