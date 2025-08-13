
-- User deletion audit trail and management schema

-- Table to track user deletions for audit purposes
CREATE TABLE IF NOT EXISTS user_deletion_audit (
    id INT PRIMARY KEY AUTO_INCREMENT,
    deleted_user_id INT NOT NULL,
    deleted_username VARCHAR(255) NOT NULL,
    deleted_user_role ENUM('admin', 'instructor', 'student') NOT NULL,
    deleted_user_type ENUM('user', 'student') NOT NULL,
    deleted_by_admin_id INT NOT NULL,
    deleted_by_admin_username VARCHAR(255) NOT NULL,
    deletion_reason TEXT,
    affected_lessons_count INT DEFAULT 0,
    affected_assignments_count INT DEFAULT 0,
    affected_availability_count INT DEFAULT 0,
    related_data_summary JSON,
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_deleted_user_id (deleted_user_id),
    INDEX idx_deleted_by_admin (deleted_by_admin_id),
    INDEX idx_deletion_date (deleted_at)
);

-- Table to track affected data when users are deleted  
CREATE TABLE IF NOT EXISTS deletion_affected_data (
    id INT PRIMARY KEY AUTO_INCREMENT,
    deletion_audit_id INT NOT NULL,
    affected_table VARCHAR(100) NOT NULL,
    affected_record_id INT NOT NULL,
    affected_record_data JSON,
    action_taken ENUM('deleted', 'cancelled', 'reassigned', 'archived') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deletion_audit_id) REFERENCES user_deletion_audit(id) ON DELETE CASCADE,
    INDEX idx_deletion_audit (deletion_audit_id),
    INDEX idx_affected_table (affected_table)
);

-- Add soft delete columns to users table if needed (optional approach)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_by INT NULL;

-- Add soft delete columns to students table if needed (optional approach)  
ALTER TABLE students ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE students ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;
ALTER TABLE students ADD COLUMN IF NOT EXISTS deleted_by INT NULL;

-- Create indexes for soft delete queries
CREATE INDEX IF NOT EXISTS idx_users_deleted ON users(is_deleted, deleted_at);
CREATE INDEX IF NOT EXISTS idx_students_deleted ON students(is_deleted, deleted_at);
