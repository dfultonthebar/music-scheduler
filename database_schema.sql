-- Database Schema for Music Scheduler Auto-Update System
-- Creates tables for managing update notifications, history, and admin settings

-- Table for storing update notifications
CREATE TABLE IF NOT EXISTS update_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_type TEXT NOT NULL CHECK (notification_type IN ('update_available', 'update_completed', 'update_failed', 'rollback_completed')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'error', 'success')),
    current_version TEXT,
    available_version TEXT,
    commit_count INTEGER DEFAULT 0,
    commit_details TEXT, -- JSON string containing commit information
    is_read BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    requires_action BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP NULL,
    admin_user_id INTEGER,
    metadata TEXT -- JSON string for additional data
);

-- Table for storing update history
CREATE TABLE IF NOT EXISTS update_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    update_type TEXT NOT NULL CHECK (update_type IN ('automatic_check', 'manual_download', 'installation', 'rollback')),
    status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'in_progress', 'cancelled')),
    version_from TEXT,
    version_to TEXT,
    commit_hash_from TEXT,
    commit_hash_to TEXT,
    backup_created BOOLEAN DEFAULT FALSE,
    backup_path TEXT,
    error_message TEXT,
    duration_seconds INTEGER,
    initiated_by TEXT, -- 'system' or admin username
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    rollback_available BOOLEAN DEFAULT TRUE,
    metadata TEXT -- JSON string for additional data
);

-- Table for admin update preferences
CREATE TABLE IF NOT EXISTS update_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_user_id INTEGER NOT NULL,
    email_notifications BOOLEAN DEFAULT TRUE,
    auto_download BOOLEAN DEFAULT FALSE,
    auto_install BOOLEAN DEFAULT FALSE,
    notification_frequency TEXT DEFAULT 'immediate' CHECK (notification_frequency IN ('immediate', 'daily', 'weekly', 'disabled')),
    backup_before_update BOOLEAN DEFAULT TRUE,
    rollback_timeout_hours INTEGER DEFAULT 24,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing system update settings
CREATE TABLE IF NOT EXISTS update_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    setting_type TEXT NOT NULL DEFAULT 'string' CHECK (setting_type IN ('string', 'integer', 'boolean', 'json')),
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for tracking backup files
CREATE TABLE IF NOT EXISTS update_backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_name TEXT NOT NULL,
    backup_path TEXT NOT NULL,
    backup_size_bytes INTEGER,
    version_backed_up TEXT,
    commit_hash TEXT,
    backup_type TEXT DEFAULT 'pre_update' CHECK (backup_type IN ('pre_update', 'manual', 'scheduled')),
    is_compressed BOOLEAN DEFAULT TRUE,
    can_rollback BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    metadata TEXT -- JSON string for additional backup info
);

-- Indexes for better performance
ALTER TABLE update_notifications DROP INDEX IF EXISTS idx_update_notifications_created_at;
CREATE INDEX idx_update_notifications_created_at ON update_notifications(created_at DESC);
ALTER TABLE update_notifications DROP INDEX IF EXISTS idx_update_notifications_is_read;
CREATE INDEX idx_update_notifications_is_read ON update_notifications(is_read);
ALTER TABLE update_notifications DROP INDEX IF EXISTS idx_update_notifications_admin_user;
CREATE INDEX idx_update_notifications_admin_user ON update_notifications(admin_user_id);
ALTER TABLE update_history DROP INDEX IF EXISTS idx_update_history_status;
CREATE INDEX idx_update_history_status ON update_history(status);
ALTER TABLE update_history DROP INDEX IF EXISTS idx_update_history_update_type;
CREATE INDEX idx_update_history_update_type ON update_history(update_type);
ALTER TABLE update_history DROP INDEX IF EXISTS idx_update_history_started_at;
CREATE INDEX idx_update_history_started_at ON update_history(started_at DESC);
ALTER TABLE update_backups DROP INDEX IF EXISTS idx_update_backups_created_at;
CREATE INDEX idx_update_backups_created_at ON update_backups(created_at DESC);
ALTER TABLE update_backups DROP INDEX IF EXISTS idx_update_backups_can_rollback;
CREATE INDEX idx_update_backups_can_rollback ON update_backups(can_rollback);

-- Insert default settings
INSERT OR IGNORE INTO update_settings (setting_key, setting_value, setting_type, description, is_system) VALUES
('last_check_timestamp', '0', 'integer', 'Timestamp of last successful update check', TRUE),
('last_successful_update', '', 'string', 'Hash of last successful update', TRUE),
('check_enabled', 'true', 'boolean', 'Whether automatic update checking is enabled', FALSE),
('maintenance_mode', 'false', 'boolean', 'Whether system is in maintenance mode for updates', TRUE),
('update_branch', 'main', 'string', 'Git branch to check for updates', FALSE),
('max_backup_retention_days', '90', 'integer', 'Maximum days to retain backups', FALSE),
('notification_cooldown_hours', '6', 'integer', 'Hours between duplicate notifications', FALSE);

-- Insert default admin preferences (will need to be updated with actual admin user IDs)
INSERT OR IGNORE INTO update_preferences (admin_user_id, email_notifications, auto_download, auto_install) 
VALUES (1, TRUE, FALSE, FALSE);

-- Views for easier data access
CREATE VIEW IF NOT EXISTS active_notifications AS
SELECT * FROM update_notifications 
WHERE is_dismissed = FALSE 
ORDER BY created_at DESC;

CREATE VIEW IF NOT EXISTS recent_update_history AS
SELECT 
    uh.*,
    ub.backup_path,
    ub.backup_size_bytes
FROM update_history uh
LEFT JOIN update_backups ub ON uh.backup_path = ub.backup_path
WHERE uh.started_at > datetime('now', '-30 days')
ORDER BY uh.started_at DESC;

CREATE VIEW IF NOT EXISTS available_backups AS
SELECT * FROM update_backups 
WHERE can_rollback = TRUE 
AND (expires_at IS NULL OR expires_at > datetime('now'))
ORDER BY created_at DESC;