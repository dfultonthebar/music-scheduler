
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import os
import logging
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
import base64

class EmailService:
    """
    Comprehensive email service for the music scheduler system
    Handles SMTP configuration, template rendering, and email sending with encryption and logging
    """
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.logger = self._setup_logging()
        self._encryption_key = self._get_or_create_encryption_key()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for email service"""
        logger = logging.getLogger('EmailService')
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            # Ensure logs directory exists
            os.makedirs('logs', exist_ok=True)
            
            # Create file handler
            handler = logging.FileHandler('logs/email_service.log')
            handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            
            logger.addHandler(handler)
        
        return logger
    
    def _get_or_create_encryption_key(self) -> Fernet:
        """Get or create encryption key for SMTP credentials"""
        key_file = '.email_encryption_key'
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Make the key file readable only by owner
            os.chmod(key_file, 0o600)
        
        return Fernet(key)
    
    def _encrypt_password(self, password: str) -> str:
        """Encrypt SMTP password"""
        encrypted = self._encryption_key.encrypt(password.encode())
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt SMTP password"""
        try:
            encrypted_data = base64.b64decode(encrypted_password.encode())
            decrypted = self._encryption_key.decrypt(encrypted_data)
            return decrypted.decode()
        except Exception as e:
            self.logger.error(f"Password decryption failed: {e}")
            raise ValueError("Failed to decrypt password")
    
    def _get_db_connection(self):
        """Get database connection"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                return connection
        except Error as e:
            self.logger.error(f"Database connection failed: {e}")
            return None
    
    def save_smtp_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save SMTP configuration to database with encrypted password
        """
        connection = self._get_db_connection()
        if not connection:
            return {"success": False, "error": "Database connection failed"}
        
        try:
            cursor = connection.cursor()
            
            # Encrypt the password
            encrypted_password = self._encrypt_password(config['smtp_password'])
            
            # Check if configuration already exists
            cursor.execute("SELECT id FROM smtp_config WHERE is_active = 1")
            existing = cursor.fetchone()
            
            if existing:
                # Update existing configuration
                cursor.execute("""
                    UPDATE smtp_config 
                    SET smtp_host = %s, smtp_port = %s, smtp_security = %s, 
                        smtp_username = %s, smtp_password_encrypted = %s,
                        from_email = %s, from_name = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE is_active = 1
                """, (
                    config['smtp_host'], config['smtp_port'], config['smtp_security'],
                    config['smtp_username'], encrypted_password,
                    config['from_email'], config['from_name']
                ))
                self.logger.info("SMTP configuration updated successfully")
            else:
                # Insert new configuration
                cursor.execute("""
                    INSERT INTO smtp_config 
                    (smtp_host, smtp_port, smtp_security, smtp_username, smtp_password_encrypted, from_email, from_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    config['smtp_host'], config['smtp_port'], config['smtp_security'],
                    config['smtp_username'], encrypted_password,
                    config['from_email'], config['from_name']
                ))
                self.logger.info("SMTP configuration saved successfully")
            
            connection.commit()
            return {"success": True, "message": "SMTP configuration saved successfully"}
            
        except Error as e:
            self.logger.error(f"Failed to save SMTP config: {e}")
            return {"success": False, "error": f"Database error: {str(e)}"}
        finally:
            cursor.close()
            connection.close()
    
    def get_smtp_config(self) -> Optional[Dict[str, Any]]:
        """Get active SMTP configuration from database"""
        connection = self._get_db_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT smtp_host, smtp_port, smtp_security, smtp_username, 
                       smtp_password_encrypted, from_email, from_name
                FROM smtp_config 
                WHERE is_active = 1 
                ORDER BY updated_at DESC 
                LIMIT 1
            """)
            config = cursor.fetchone()
            
            if config:
                # Decrypt password for use
                config['smtp_password'] = self._decrypt_password(config['smtp_password_encrypted'])
                del config['smtp_password_encrypted']  # Remove encrypted version
                
            return config
            
        except Error as e:
            self.logger.error(f"Failed to get SMTP config: {e}")
            return None
        finally:
            cursor.close()
            connection.close()
    
    def test_smtp_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test SMTP connection with given configuration"""
        try:
            # Create SMTP connection based on security type
            if config['smtp_security'] == 'SSL':
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(config['smtp_host'], config['smtp_port'], context=context)
            else:
                server = smtplib.SMTP(config['smtp_host'], config['smtp_port'])
                if config['smtp_security'] == 'STARTTLS':
                    context = ssl.create_default_context()
                    server.starttls(context=context)
            
            # Authenticate
            server.login(config['smtp_username'], config['smtp_password'])
            server.quit()
            
            self.logger.info("SMTP connection test successful")
            return {"success": True, "message": "SMTP connection successful"}
            
        except smtplib.SMTPAuthenticationError:
            error_msg = "SMTP authentication failed. Check username and password."
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except smtplib.SMTPConnectError:
            error_msg = "Failed to connect to SMTP server. Check host and port."
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"SMTP test failed: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_email_template(self, template_type: str) -> Optional[Dict[str, Any]]:
        """Get email template by type"""
        connection = self._get_db_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT subject_template, body_template
                FROM email_templates 
                WHERE template_type = %s AND is_active = 1
                LIMIT 1
            """, (template_type,))
            
            return cursor.fetchone()
            
        except Error as e:
            self.logger.error(f"Failed to get email template: {e}")
            return None
        finally:
            cursor.close()
            connection.close()
    
    def render_template(self, template: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, str]:
        """Render email template with context variables"""
        try:
            subject = template['subject_template']
            body = template['body_template']
            
            # Replace template variables
            for key, value in context.items():
                placeholder = f"{{{key}}}"
                subject = subject.replace(placeholder, str(value) if value is not None else "")
                body = body.replace(placeholder, str(value) if value is not None else "")
            
            # Handle special formatting for lesson notes
            if context.get('lesson_notes'):
                notes_html = f"""
                <div style="background-color: #e8f5e8; padding: 10px; border-radius: 5px; margin: 10px 0;">
                    <strong>📝 Notes:</strong><br>
                    {context['lesson_notes']}
                </div>
                """
                body = body.replace('{lesson_notes}', notes_html)
            else:
                body = body.replace('{lesson_notes}', '')
            
            return {"subject": subject, "body": body}
            
        except Exception as e:
            self.logger.error(f"Template rendering failed: {e}")
            return {"subject": "Notification", "body": "An error occurred rendering this email."}
    
    def is_email_service_enabled(self) -> bool:
        """Check if email service is globally enabled"""
        connection = self._get_db_connection()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT service_enabled FROM email_service_settings 
                ORDER BY updated_at DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            return result['service_enabled'] if result else True
            
        except Error as e:
            self.logger.error(f"Failed to check email service status: {e}")
            return False  # Default to disabled if we can't check
        finally:
            cursor.close()
            connection.close()
    
    def set_email_service_enabled(self, enabled: bool, updated_by: str = 'admin') -> Dict[str, Any]:
        """Enable or disable email service globally"""
        connection = self._get_db_connection()
        if not connection:
            return {"success": False, "error": "Database connection failed"}
        
        try:
            cursor = connection.cursor()
            
            # Check if a record exists
            cursor.execute("SELECT id FROM email_service_settings LIMIT 1")
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE email_service_settings 
                    SET service_enabled = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP
                """, (enabled, updated_by))
            else:
                cursor.execute("""
                    INSERT INTO email_service_settings (service_enabled, updated_by)
                    VALUES (%s, %s)
                """, (enabled, updated_by))
            
            connection.commit()
            status = "enabled" if enabled else "disabled"
            self.logger.info(f"Email service {status} by {updated_by}")
            return {"success": True, "message": f"Email service {status} successfully"}
            
        except Error as e:
            self.logger.error(f"Failed to update email service status: {e}")
            return {"success": False, "error": f"Database error: {str(e)}"}
        finally:
            cursor.close()
            connection.close()
    
    def get_email_service_status(self) -> Dict[str, Any]:
        """Get detailed email service status information"""
        connection = self._get_db_connection()
        if not connection:
            return {"success": False, "error": "Database connection failed"}
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT service_enabled, updated_at, updated_by
                FROM email_service_settings 
                ORDER BY updated_at DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                return {
                    "success": True,
                    "enabled": result['service_enabled'],
                    "updated_at": result['updated_at'].isoformat() if result['updated_at'] else None,
                    "updated_by": result['updated_by']
                }
            else:
                return {
                    "success": True,
                    "enabled": True,  # Default enabled
                    "updated_at": None,
                    "updated_by": "system"
                }
                
        except Error as e:
            self.logger.error(f"Failed to get email service status: {e}")
            return {"success": False, "error": f"Database error: {str(e)}"}
        finally:
            cursor.close()
            connection.close()

    def send_email(self, to_email: str, subject: str, body: str, email_type: str, lesson_id: Optional[int] = None) -> Dict[str, Any]:
        """Send email and log the result"""
        # Check if email service is enabled
        if not self.is_email_service_enabled():
            skip_msg = f"Email service is disabled. Skipping email to {to_email} with subject: {subject}"
            self.logger.info(skip_msg)
            self._log_email_attempt(to_email, subject, email_type, lesson_id, "skipped", "Email service disabled")
            return {"success": True, "message": "Email service is disabled", "skipped": True}
        
        config = self.get_smtp_config()
        if not config:
            error_msg = "No SMTP configuration found"
            self.logger.error(error_msg)
            self._log_email_attempt(to_email, subject, email_type, lesson_id, "failed", error_msg)
            return {"success": False, "error": error_msg}
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{config['from_name']} <{config['from_email']}>"
            message["To"] = to_email
            
            # Create HTML part
            html_part = MIMEText(body, "html")
            message.attach(html_part)
            
            # Create SMTP connection
            if config['smtp_security'] == 'SSL':
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(config['smtp_host'], config['smtp_port'], context=context)
            else:
                server = smtplib.SMTP(config['smtp_host'], config['smtp_port'])
                if config['smtp_security'] == 'STARTTLS':
                    context = ssl.create_default_context()
                    server.starttls(context=context)
            
            # Authenticate and send
            server.login(config['smtp_username'], config['smtp_password'])
            text = message.as_string()
            server.sendmail(config['from_email'], to_email, text)
            server.quit()
            
            self.logger.info(f"Email sent successfully to {to_email}")
            self._log_email_attempt(to_email, subject, email_type, lesson_id, "sent", None)
            return {"success": True, "message": "Email sent successfully"}
            
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            self.logger.error(error_msg)
            self._log_email_attempt(to_email, subject, email_type, lesson_id, "failed", error_msg)
            return {"success": False, "error": error_msg}
    
    def _log_email_attempt(self, recipient: str, subject: str, email_type: str, lesson_id: Optional[int], status: str, error_message: Optional[str]):
        """Log email attempt to database"""
        connection = self._get_db_connection()
        if not connection:
            return
        
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO email_logs (recipient_email, subject, email_type, lesson_id, status, error_message)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (recipient, subject, email_type, lesson_id, status, error_message))
            connection.commit()
            
        except Error as e:
            self.logger.error(f"Failed to log email attempt: {e}")
        finally:
            cursor.close()
            connection.close()
    
    def send_lesson_notification(self, lesson_data: Dict[str, Any], notification_type: str) -> Dict[str, Any]:
        """
        Send lesson notification to both instructor and student
        notification_type: 'confirmation', 'update', 'cancellation'
        """
        results = {"student": None, "instructor": None}
        
        # Send to student if email exists
        if lesson_data.get('student_email'):
            student_template = self.get_email_template(f'lesson_{notification_type}' if notification_type == 'confirmation' else f'lesson_{notification_type}_notification')
            if student_template:
                context = lesson_data.copy()
                context['recipient_name'] = lesson_data['student_name']
                
                rendered = self.render_template(student_template, context)
                results["student"] = self.send_email(
                    lesson_data['student_email'],
                    rendered['subject'],
                    rendered['body'],
                    f'lesson_{notification_type}_student',
                    lesson_data.get('lesson_id')
                )
        
        # Send to instructor if email exists
        if lesson_data.get('instructor_email'):
            instructor_template = self.get_email_template(f'lesson_{notification_type}_notification' if notification_type != 'confirmation' else 'lesson_notification_instructor')
            if instructor_template:
                context = lesson_data.copy()
                context['recipient_name'] = lesson_data['instructor_name']
                
                rendered = self.render_template(instructor_template, context)
                results["instructor"] = self.send_email(
                    lesson_data['instructor_email'],
                    rendered['subject'],
                    rendered['body'],
                    f'lesson_{notification_type}_instructor',
                    lesson_data.get('lesson_id')
                )
        
        return results
    
    def get_email_logs(self, limit: int = 100) -> list:
        """Get recent email logs for admin review"""
        connection = self._get_db_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT el.*, l.lesson_date, l.lesson_time, s.name as student_name
                FROM email_logs el
                LEFT JOIN lessons l ON el.lesson_id = l.id
                LEFT JOIN students s ON l.student_id = s.id
                ORDER BY el.sent_at DESC
                LIMIT %s
            """, (limit,))
            
            return cursor.fetchall()
            
        except Error as e:
            self.logger.error(f"Failed to get email logs: {e}")
            return []
        finally:
            cursor.close()
            connection.close()
    
    def update_email_template(self, template_name: str, subject: str, body: str) -> Dict[str, Any]:
        """Update email template"""
        connection = self._get_db_connection()
        if not connection:
            return {"success": False, "error": "Database connection failed"}
        
        try:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE email_templates 
                SET subject_template = %s, body_template = %s, updated_at = CURRENT_TIMESTAMP
                WHERE template_name = %s
            """, (subject, body, template_name))
            
            if cursor.rowcount > 0:
                connection.commit()
                self.logger.info(f"Email template '{template_name}' updated successfully")
                return {"success": True, "message": "Template updated successfully"}
            else:
                return {"success": False, "error": "Template not found"}
                
        except Error as e:
            self.logger.error(f"Failed to update email template: {e}")
            return {"success": False, "error": f"Database error: {str(e)}"}
        finally:
            cursor.close()
            connection.close()
    
    def get_all_templates(self) -> list:
        """Get all email templates for admin management"""
        connection = self._get_db_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT template_name, subject_template, body_template, template_type, is_active
                FROM email_templates
                ORDER BY template_type, template_name
            """)
            
            return cursor.fetchall()
            
        except Error as e:
            self.logger.error(f"Failed to get email templates: {e}")
            return []
        finally:
            cursor.close()
            connection.close()
