
#!/bin/bash

# Music Scheduler Backup List Script
# This script lists all available database backups with details

BACKUP_DIR="../database_backups"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "No backup directory found"
    exit 1
fi

echo "Available Database Backups:"
echo "=========================="
echo

# Check for backup files
if ls "$BACKUP_DIR"/*.sql* 1> /dev/null 2>&1; then
    for backup in "$BACKUP_DIR"/*.sql*; do
        if [ -f "$backup" ]; then
            filename=$(basename "$backup")
            size=$(du -h "$backup" | cut -f1)
            modified=$(stat -c %y "$backup" | cut -d'.' -f1)
            
            echo "File: $filename"
            echo "Size: $size"
            echo "Date: $modified"
            echo "Path: $backup"
            echo "---"
        fi
    done
else
    echo "No backup files found in $BACKUP_DIR"
fi

# Show log files if they exist
if [ -f "$BACKUP_DIR/backup_log.txt" ]; then
    echo
    echo "Recent Backup Activity:"
    echo "======================"
    tail -10 "$BACKUP_DIR/backup_log.txt"
fi

if [ -f "$BACKUP_DIR/restore_log.txt" ]; then
    echo
    echo "Recent Restore Activity:"
    echo "======================="
    tail -5 "$BACKUP_DIR/restore_log.txt"
fi
