#!/usr/bin/env python3
"""
Email Notification System for Music Scheduler Auto-Update
Sends email notifications to admin users about system updates
"""

import smtplib
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

class UpdateEmailNotifier:
    def __init__(self, config_path="/home/ubuntu/music_scheduler_update_system/config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.smtp_server = self.config['system']['smtp_server']
        self.smtp_port = self.config['system']['smtp_port']
        self.admin_emails = self.config['system']['admin_emails']
        
        # Setup logging
        log_dir = Path(self.config['system']['log_path'])
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / 'email_notifier.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def create_html_template(self, title: str, content: str, severity: str = 'info') -> str:
        """Create HTML email template"""
        
        # Color scheme based on severity
        colors = {
            'info': {'bg': '#e3f2fd', 'border': '#2196f3', 'text': '#0d47a1'},
            'success': {'bg': '#e8f5e8', 'border': '#4caf50', 'text': '#1b5e20'},
            'warning': {'bg': '#fff3e0', 'border': '#ff9800', 'text': '#e65100'},
            'error': {'bg': '#ffebee', 'border': '#f44336', 'text': '#b71c1c'}
        }
        
        color_scheme = colors.get(severity, colors['info'])
        
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background: white;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: {color_scheme['bg']};
                    border-left: 4px solid {color_scheme['border']};
                    padding: 15px 20px;
                    margin: -30px -30px 20px -30px;
                    border-radius: 8px 8px 0 0;
                }}
                .header h1 {{
                    color: {color_scheme['text']};
                    margin: 0;
                    font-size: 24px;
                }}
                .content {{
                    font-size: 16px;
                    line-height: 1.8;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 14px;
                    color: #666;
                    text-align: center;
                }}
                .button {{
                    display: inline-block;
                    background: {color_scheme['border']};
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 4px;
                    margin: 10px 0;
                    font-weight: bold;
                }}
                .code {{
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 4px;
                    padding: 15px;
                    font-family: 'Courier New', monospace;
                    font-size: 14px;
                    margin: 10px 0;
                    overflow-x: auto;
                }}
                .highlight {{
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                    padding: 12px;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎵 Music Scheduler Update</h1>
                </div>
                <div class="content">
                    {content}
                </div>
                <div class="footer">
                    <p>This is an automated message from the Music Scheduler Update System.<br>
                    Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def send_email(self, subject: str, body: str, html_body: Optional[str] = None, 
                   recipients: Optional[List[str]] = None) -> bool:
        """Send email notification"""
        try:
            if not recipients:
                recipients = self.admin_emails
            
            if not recipients:
                self.logger.warning("No recipients configured for email notifications")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[Music Scheduler] {subject}"
            msg['From'] = "noreply@music-scheduler.local"
            msg['To'] = ', '.join(recipients)
            
            # Add plain text version
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Add HTML version if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                # Uncomment if authentication is needed
                # server.starttls()
                # server.login(username, password)
                
                server.send_message(msg)
            
            self.logger.info(f"Email sent successfully to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email: {str(e)}")
            return False
    
    def send_update_available_notification(self, update_info: Dict) -> bool:
        """Send notification about available updates"""
        if update_info['status'] != 'updates_available':
            return False
        
        current_hash = update_info['current_version']['hash'][:8]
        remote_hash = update_info['remote_version']['hash'][:8]
        commit_count = update_info['commit_count']
        
        subject = f"Updates Available ({commit_count} commits)"
        
        # Plain text version
        plain_text = f"""
Music Scheduler Update Available

New updates are available for your Music Scheduler system.

Current Version: {current_hash}
Available Version: {remote_hash}
Number of new commits: {commit_count}

Latest Changes:
{update_info['remote_version']['message']}
By: {update_info['remote_version']['author']}

Please log into your admin panel to review and install the updates.

Update Details:
"""
        
        # Add commit details
        for i, commit in enumerate(update_info.get('new_commits', [])[:5], 1):
            plain_text += f"\n{i}. {commit['commit']['message'][:80]}..."
            plain_text += f"\n   By {commit['commit']['author']['name']} on {commit['commit']['author']['date'][:10]}"
        
        if len(update_info.get('new_commits', [])) > 5:
            plain_text += f"\n... and {len(update_info['new_commits']) - 5} more commits"
        
        # HTML version
        html_content = f"""
        <h2>🎵 New Updates Available!</h2>
        
        <div class="highlight">
            <p><strong>{commit_count} new commits</strong> are available for your Music Scheduler.</p>
        </div>
        
        <h3>Version Information</h3>
        <div class="code">
            Current Version: {current_hash}<br>
            Available Version: {remote_hash}
        </div>
        
        <h3>Latest Changes</h3>
        <p><strong>{update_info['remote_version']['message']}</strong><br>
        <em>By {update_info['remote_version']['author']}</em></p>
        
        <h3>Recent Commits</h3>
        <ul>
        """
        
        for commit in update_info.get('new_commits', [])[:5]:
            commit_msg = commit['commit']['message'][:80]
            author = commit['commit']['author']['name']
            date = commit['commit']['author']['date'][:10]
            html_content += f"<li><strong>{commit_msg}...</strong><br><small>By {author} on {date}</small></li>"
        
        if len(update_info.get('new_commits', [])) > 5:
            remaining = len(update_info['new_commits']) - 5
            html_content += f"<li><em>... and {remaining} more commits</em></li>"
        
        html_content += """
        </ul>
        
        <p><a href="#" class="button">Review & Install Updates</a></p>
        
        <p><em>Please review the changes carefully before installing updates. 
        A backup will be created automatically before installation.</em></p>
        """
        
        html_body = self.create_html_template(subject, html_content, 'info')
        
        return self.send_email(subject, plain_text, html_body)
    
    def send_update_completed_notification(self, update_result: Dict) -> bool:
        """Send notification about completed update"""
        subject = "Update Completed Successfully"
        
        new_version = update_result.get('new_version', 'Unknown')[:8]
        duration = update_result.get('duration', 'Unknown')
        backup_created = update_result.get('backup_created', False)
        
        plain_text = f"""
Music Scheduler Update Completed

Your Music Scheduler has been successfully updated!

New Version: {new_version}
Update Duration: {duration}
Backup Created: {'Yes' if backup_created else 'No'}
Update Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The system is now running the latest version with all new features and improvements.

If you experience any issues, you can rollback to the previous version from the admin panel.
        """
        
        html_content = f"""
        <h2>✅ Update Completed Successfully!</h2>
        
        <div class="highlight">
            <p>Your Music Scheduler has been successfully updated to version <strong>{new_version}</strong>!</p>
        </div>
        
        <h3>Update Summary</h3>
        <div class="code">
            New Version: {new_version}<br>
            Duration: {duration}<br>
            Backup Created: {'Yes' if backup_created else 'No'}<br>
            Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        
        <p>The system is now running the latest version with all new features and security improvements.</p>
        
        <p><strong>Next Steps:</strong></p>
        <ul>
            <li>Test your system functionality</li>
            <li>Review any new features</li>
            <li>Report any issues through the admin panel</li>
        </ul>
        
        <p><em>If you experience any problems, you can rollback to the previous version from the backup page.</em></p>
        """
        
        html_body = self.create_html_template(subject, html_content, 'success')
        
        return self.send_email(subject, plain_text, html_body)
    
    def send_update_failed_notification(self, error_info: Dict) -> bool:
        """Send notification about failed update"""
        subject = "Update Failed - Action Required"
        
        error_msg = error_info.get('error', 'Unknown error occurred')
        rollback_status = error_info.get('rollback_status', 'Unknown')
        backup_available = error_info.get('backup_available', False)
        
        plain_text = f"""
Music Scheduler Update Failed

Unfortunately, the Music Scheduler update failed and required intervention.

Error: {error_msg}
Rollback Status: {rollback_status}
Backup Available: {'Yes' if backup_available else 'No'}
Failed At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The system has been restored to its previous state to maintain stability.

Please check the system logs and contact support if this issue persists.
        """
        
        html_content = f"""
        <h2>❌ Update Failed</h2>
        
        <div class="highlight">
            <p><strong>The Music Scheduler update failed</strong> and has been rolled back to maintain system stability.</p>
        </div>
        
        <h3>Error Details</h3>
        <div class="code">
            Error: {error_msg}<br>
            Rollback: {rollback_status}<br>
            Backup Available: {'Yes' if backup_available else 'No'}<br>
            Failed At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        
        <p><strong>What happened:</strong></p>
        <ul>
            <li>Update process encountered an error</li>
            <li>System was automatically rolled back</li>
            <li>Original functionality has been restored</li>
        </ul>
        
        <p><strong>Next Steps:</strong></p>
        <ul>
            <li>Check system logs for detailed error information</li>
            <li>Verify system is functioning normally</li>
            <li>Contact support if issues persist</li>
            <li>Try updating again later</li>
        </ul>
        """
        
        html_body = self.create_html_template(subject, html_content, 'error')
        
        return self.send_email(subject, plain_text, html_body)
    
    def send_system_maintenance_notification(self, maintenance_info: Dict) -> bool:
        """Send notification about system maintenance"""
        subject = f"System Maintenance - {maintenance_info.get('type', 'Update')}"
        
        maintenance_type = maintenance_info.get('type', 'Update')
        start_time = maintenance_info.get('start_time', 'Unknown')
        estimated_duration = maintenance_info.get('duration', 'Unknown')
        
        plain_text = f"""
Music Scheduler Maintenance Scheduled

A {maintenance_type.lower()} maintenance is scheduled for your Music Scheduler.

Maintenance Type: {maintenance_type}
Scheduled Start: {start_time}
Estimated Duration: {estimated_duration}

During maintenance:
- The system may be temporarily unavailable
- Automatic backups will be created
- All data will be preserved
- Services will restart automatically

You will be notified when maintenance is complete.
        """
        
        html_content = f"""
        <h2>🔧 System Maintenance Scheduled</h2>
        
        <div class="highlight">
            <p>A <strong>{maintenance_type.lower()}</strong> maintenance is scheduled for your Music Scheduler system.</p>
        </div>
        
        <h3>Maintenance Details</h3>
        <div class="code">
            Type: {maintenance_type}<br>
            Scheduled: {start_time}<br>
            Duration: {estimated_duration}
        </div>
        
        <p><strong>What to expect:</strong></p>
        <ul>
            <li>Brief service interruption during update</li>
            <li>Automatic backup creation</li>
            <li>All data will be preserved</li>
            <li>Services will restart automatically</li>
        </ul>
        
        <p>You will receive a notification when the maintenance is completed.</p>
        """
        
        html_body = self.create_html_template(subject, html_content, 'warning')
        
        return self.send_email(subject, plain_text, html_body)

if __name__ == "__main__":
    notifier = UpdateEmailNotifier()
    
    # Test notification
    test_update_info = {
        'status': 'updates_available',
        'current_version': {'hash': 'abc123def456'},
        'remote_version': {
            'hash': 'def456ghi789',
            'message': 'Add new playlist features and fix bugs',
            'author': 'Developer'
        },
        'commit_count': 3,
        'new_commits': [
            {
                'commit': {
                    'message': 'Add drag and drop playlist reordering',
                    'author': {'name': 'John Doe', 'date': '2025-08-13T10:00:00Z'}
                }
            }
        ]
    }
    
    success = notifier.send_update_available_notification(test_update_info)
    print(f"Test email sent: {success}")
