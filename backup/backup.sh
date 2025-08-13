
#!/bin/bash

# Music Scheduler Backup Script
# This script creates automated backups of the database and application files

set -e

# Configuration
BACKUP_DIR="/var/backups/music-scheduler"
DB_NAME="music_scheduler"
DB_USER="music_user"
APP_DIR="/opt/music-scheduler"
RETENTION_DAYS=30
DATE=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Create backup directory if it doesn't exist
create_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
        chmod 750 "$BACKUP_DIR"
    fi
}

# Get database password from app configuration
get_db_password() {
    if [[ -f "$APP_DIR/.env" ]]; then
        DB_PASS=$(grep "MYSQL_PASSWORD=" "$APP_DIR/.env" | cut -d '=' -f2)
        if [[ -z "$DB_PASS" ]]; then
            error "Could not find database password in $APP_DIR/.env"
            exit 1
        fi
    else
        error "Environment file not found: $APP_DIR/.env"
        exit 1
    fi
}

# Backup database
backup_database() {
    log "Starting database backup..."
    
    DB_BACKUP_FILE="$BACKUP_DIR/db_backup_${DATE}.sql"
    
    if mysqldump -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" > "$DB_BACKUP_FILE"; then
        # Compress the SQL file
        gzip "$DB_BACKUP_FILE"
        success "Database backup completed: ${DB_BACKUP_FILE}.gz"
        
        # Set appropriate permissions
        chmod 640 "${DB_BACKUP_FILE}.gz"
        
        return 0
    else
        error "Database backup failed"
        return 1
    fi
}

# Backup application files
backup_app_files() {
    log "Starting application files backup..."
    
    APP_BACKUP_FILE="$BACKUP_DIR/app_backup_${DATE}.tar.gz"
    
    # Create temporary directory for app backup
    TEMP_DIR=$(mktemp -d)
    
    # Copy application files (excluding virtual environment and logs)
    rsync -av --exclude='venv/' --exclude='*.log' --exclude='__pycache__/' \
          --exclude='*.pyc' --exclude='.git/' "$APP_DIR/" "$TEMP_DIR/"
    
    # Create compressed archive
    if tar -czf "$APP_BACKUP_FILE" -C "$(dirname "$TEMP_DIR")" "$(basename "$TEMP_DIR")"; then
        success "Application backup completed: $APP_BACKUP_FILE"
        chmod 640 "$APP_BACKUP_FILE"
        
        # Clean up temporary directory
        rm -rf "$TEMP_DIR"
        return 0
    else
        error "Application backup failed"
        rm -rf "$TEMP_DIR"
        return 1
    fi
}

# Clean old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Count files before cleanup
    OLD_COUNT=$(find "$BACKUP_DIR" -name "*.gz" -o -name "*.tar.gz" -mtime +$RETENTION_DAYS | wc -l)
    
    if [[ $OLD_COUNT -gt 0 ]]; then
        find "$BACKUP_DIR" -name "*.gz" -o -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
        success "Removed $OLD_COUNT old backup files"
    else
        log "No old backup files to remove"
    fi
    
    # Show current backup status
    CURRENT_COUNT=$(find "$BACKUP_DIR" -name "*.gz" -o -name "*.tar.gz" | wc -l)
    BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
    log "Current backups: $CURRENT_COUNT files, total size: $BACKUP_SIZE"
}

# Send notification (optional - can be extended with email notifications)
send_notification() {
    local status=$1
    local message=$2
    
    # Log to system journal
    logger -t "music-scheduler-backup" "$status: $message"
    
    # You can extend this function to send email notifications
    # Example: echo "$message" | mail -s "Music Scheduler Backup $status" admin@example.com
}

# Health check - verify backups
verify_backups() {
    log "Verifying backup integrity..."
    
    # Check if database backup exists and is not empty
    DB_BACKUP=$(find "$BACKUP_DIR" -name "db_backup_${DATE}.sql.gz" -size +0c)
    if [[ -n "$DB_BACKUP" ]]; then
        # Test gzip file integrity
        if gzip -t "$DB_BACKUP" 2>/dev/null; then
            success "Database backup integrity verified"
        else
            error "Database backup file is corrupted"
            return 1
        fi
    else
        error "Database backup file not found or empty"
        return 1
    fi
    
    # Check if app backup exists and is not empty
    APP_BACKUP=$(find "$BACKUP_DIR" -name "app_backup_${DATE}.tar.gz" -size +0c)
    if [[ -n "$APP_BACKUP" ]]; then
        # Test tar file integrity
        if tar -tzf "$APP_BACKUP" >/dev/null 2>&1; then
            success "Application backup integrity verified"
        else
            error "Application backup file is corrupted"
            return 1
        fi
    else
        error "Application backup file not found or empty"
        return 1
    fi
    
    return 0
}

# Main backup function
main() {
    log "Starting Music Scheduler backup process..."
    
    # Initialize
    create_backup_dir
    get_db_password
    
    # Perform backups
    local db_success=0
    local app_success=0
    
    backup_database && db_success=1
    backup_app_files && app_success=1
    
    # Verify backups if both succeeded
    if [[ $db_success -eq 1 && $app_success -eq 1 ]]; then
        if verify_backups; then
            success "All backups completed and verified successfully"
            send_notification "SUCCESS" "Music Scheduler backup completed successfully on $(hostname)"
        else
            error "Backup verification failed"
            send_notification "ERROR" "Music Scheduler backup verification failed on $(hostname)"
            exit 1
        fi
    else
        error "One or more backups failed"
        send_notification "ERROR" "Music Scheduler backup failed on $(hostname)"
        exit 1
    fi
    
    # Cleanup old backups
    cleanup_old_backups
    
    success "Backup process completed successfully"
}

# Handle script arguments
case "${1:-}" in
    --verify)
        log "Running backup verification only..."
        get_db_password
        verify_backups
        ;;
    --cleanup)
        log "Running cleanup only..."
        create_backup_dir
        cleanup_old_backups
        ;;
    --help|-h)
        echo "Usage: $0 [options]"
        echo "Options:"
        echo "  --verify    Verify existing backups only"
        echo "  --cleanup   Run cleanup of old backups only"
        echo "  --help      Show this help message"
        echo ""
        echo "Run without arguments to perform full backup"
        ;;
    *)
        main
        ;;
esac
