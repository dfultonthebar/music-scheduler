
-- Email notification system database schema extension

-- Table to store SMTP configuration (encrypted)
CREATE TABLE IF NOT EXISTS smtp_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    smtp_host VARCHAR(255) NOT NULL,
    smtp_port INT NOT NULL DEFAULT 587,
    smtp_security ENUM('NONE', 'STARTTLS', 'SSL') DEFAULT 'STARTTLS',
    smtp_username VARCHAR(255) NOT NULL,
    smtp_password_encrypted TEXT NOT NULL,
    from_email VARCHAR(255) NOT NULL,
    from_name VARCHAR(255) DEFAULT 'Music Scheduler',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table to store email service global settings
CREATE TABLE IF NOT EXISTS email_service_settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_enabled BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by VARCHAR(255) NULL
);

-- Insert default email service setting (enabled by default)
INSERT IGNORE INTO email_service_settings (service_enabled, updated_by) VALUES (TRUE, 'system');

-- Email templates for different notification types
CREATE TABLE IF NOT EXISTS email_templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    template_name VARCHAR(100) NOT NULL UNIQUE,
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    template_type ENUM('lesson_confirmation', 'lesson_notification', 'lesson_update', 'lesson_cancellation') NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Email activity log for audit and troubleshooting
CREATE TABLE IF NOT EXISTS email_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    recipient_email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    email_type VARCHAR(100) NOT NULL,
    lesson_id INT NULL,
    status ENUM('sent', 'failed', 'pending', 'skipped') NOT NULL,
    error_message TEXT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
);

-- Add skipped status to existing email_logs table if it doesn't exist
ALTER TABLE email_logs MODIFY COLUMN status ENUM('sent', 'failed', 'pending', 'skipped') NOT NULL;

-- Add email field to users table if not exists (for instructors)
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) NULL;

-- Insert default email templates
INSERT IGNORE INTO email_templates (template_name, subject_template, body_template, template_type) VALUES
('lesson_confirmation_student', 
 'Lesson Confirmation - {student_name}', 
 '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #2c3e50; text-align: center;">🎵 Lesson Confirmation</h2>
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <p>Dear <strong>{student_name}</strong>,</p>
        <p>Your music lesson has been successfully scheduled!</p>
        
        <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <h3 style="color: #27ae60; margin-top: 0;">Lesson Details:</h3>
            <ul style="list-style: none; padding: 0;">
                <li><strong>📅 Date:</strong> {lesson_date}</li>
                <li><strong>🕐 Time:</strong> {lesson_time}</li>
                <li><strong>⏱️ Duration:</strong> {duration} minutes</li>
                <li><strong>🎼 Instrument:</strong> {instrument}</li>
                <li><strong>👨‍🏫 Instructor:</strong> {instructor_name}</li>
            </ul>
        </div>
        
        {lesson_notes}
        
        <p>If you have any questions or need to reschedule, please contact your instructor or our office.</p>
        <p>We look forward to your lesson!</p>
        
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
        <p style="color: #666; font-size: 12px;">This is an automated message from the Music Scheduler system.</p>
    </div>
</div>', 
'lesson_confirmation'),

('lesson_notification_instructor',
 'New Lesson Scheduled - {student_name}',
 '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #2c3e50; text-align: center;">🎵 New Lesson Scheduled</h2>
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <p>Hello <strong>{instructor_name}</strong>,</p>
        <p>A new lesson has been scheduled for you:</p>
        
        <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <h3 style="color: #3498db; margin-top: 0;">Lesson Details:</h3>
            <ul style="list-style: none; padding: 0;">
                <li><strong>👤 Student:</strong> {student_name}</li>
                <li><strong>📅 Date:</strong> {lesson_date}</li>
                <li><strong>🕐 Time:</strong> {lesson_time}</li>
                <li><strong>⏱️ Duration:</strong> {duration} minutes</li>
                <li><strong>🎼 Instrument:</strong> {instrument}</li>
            </ul>
        </div>
        
        {lesson_notes}
        
        <p>Please make sure to prepare for this lesson. If you have any conflicts, please contact the administration immediately.</p>
        
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
        <p style="color: #666; font-size: 12px;">This is an automated message from the Music Scheduler system.</p>
    </div>
</div>',
'lesson_notification'),

('lesson_update_notification',
 'Lesson Updated - {student_name}',
 '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #f39c12; text-align: center;">🎵 Lesson Updated</h2>
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <p>Dear <strong>{recipient_name}</strong>,</p>
        <p>Your lesson details have been updated:</p>
        
        <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <h3 style="color: #f39c12; margin-top: 0;">Updated Lesson Details:</h3>
            <ul style="list-style: none; padding: 0;">
                <li><strong>👤 Student:</strong> {student_name}</li>
                <li><strong>👨‍🏫 Instructor:</strong> {instructor_name}</li>
                <li><strong>📅 Date:</strong> {lesson_date}</li>
                <li><strong>🕐 Time:</strong> {lesson_time}</li>
                <li><strong>⏱️ Duration:</strong> {duration} minutes</li>
                <li><strong>🎼 Instrument:</strong> {instrument}</li>
            </ul>
        </div>
        
        {lesson_notes}
        
        <p>Please update your calendar with these new details. If you have any questions, please contact us.</p>
        
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
        <p style="color: #666; font-size: 12px;">This is an automated message from the Music Scheduler system.</p>
    </div>
</div>',
'lesson_update'),

('lesson_cancellation_notification',
 'Lesson Cancelled - {student_name}',
 '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #e74c3c; text-align: center;">🎵 Lesson Cancelled</h2>
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <p>Dear <strong>{recipient_name}</strong>,</p>
        <p>We regret to inform you that the following lesson has been cancelled:</p>
        
        <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #e74c3c;">
            <h3 style="color: #e74c3c; margin-top: 0;">Cancelled Lesson Details:</h3>
            <ul style="list-style: none; padding: 0;">
                <li><strong>👤 Student:</strong> {student_name}</li>
                <li><strong>👨‍🏫 Instructor:</strong> {instructor_name}</li>
                <li><strong>📅 Date:</strong> {lesson_date}</li>
                <li><strong>🕐 Time:</strong> {lesson_time}</li>
                <li><strong>🎼 Instrument:</strong> {instrument}</li>
            </ul>
        </div>
        
        <p>We apologize for any inconvenience this may cause. Please contact us to reschedule at your earliest convenience.</p>
        
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
        <p style="color: #666; font-size: 12px;">This is an automated message from the Music Scheduler system.</p>
    </div>
</div>',
'lesson_cancellation');
