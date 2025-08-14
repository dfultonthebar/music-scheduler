#!/usr/bin/env python3
"""
Notification Handler for Music Scheduler Auto-Update System
Manages admin notifications in database for update system
"""

import sqlite3
import json
import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

class UpdateNotificationHandler:
    def __init__(self, config_path="/home/ubuntu/music_scheduler_update_system/config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.db_path = self.config['system']['database_path']
        
        # Setup logging
        log_dir = Path(self.config['system']['log_path'])
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / 'notification_handler.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            schema_path = "/home/ubuntu/music_scheduler_update_system/database_schema.sql"
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema_sql)
                conn.commit()
            
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
    
    def create_notification(self, 
                          notification_type: str,
                          title: str,
                          message: str,
                          severity: str = 'info',
                          current_version: Optional[str] = None,
                          available_version: Optional[str] = None,
                          commit_count: int = 0,
                          commit_details: Optional[List] = None,
                          requires_action: bool = False,
                          admin_user_id: Optional[int] = None,
                          metadata: Optional[Dict] = None) -> int:
        """Create a new notification"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO update_notifications 
                    (notification_type, title, message, severity, current_version, 
                     available_version, commit_count, commit_details, requires_action, 
                     admin_user_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    notification_type, title, message, severity, current_version,
                    available_version, commit_count, 
                    json.dumps(commit_details) if commit_details else None,
                    requires_action, admin_user_id,
                    json.dumps(metadata) if metadata else None
                ))
                
                notification_id = cursor.lastrowid
                conn.commit()
                
                self.logger.info(f"Created notification {notification_id}: {title}")
                return notification_id
                
        except Exception as e:
            self.logger.error(f"Error creating notification: {str(e)}")
            return 0
    
    def create_update_available_notification(self, update_info: Dict) -> int:
        """Create notification for available updates"""
        if update_info['status'] != 'updates_available':
            return 0
        
        current_hash = update_info['current_version']['hash'][:8]
        remote_hash = update_info['remote_version']['hash'][:8]
        commit_count = update_info['commit_count']
        
        title = f"Update Available ({commit_count} new commits)"
        message = f"""
New updates are available for the Music Scheduler.

Current Version: {current_hash}
Available Version: {remote_hash}
New Commits: {commit_count}

Latest commit: {update_info['remote_version']['message']}
By: {update_info['remote_version']['author']}

Please review the changes and update when ready.
        """.strip()
        
        return self.create_notification(
            notification_type='update_available',
            title=title,
            message=message,
            severity='info',
            current_version=current_hash,
            available_version=remote_hash,
            commit_count=commit_count,
            commit_details=update_info['new_commits'],
            requires_action=True,
            metadata=update_info
        )
    
    def create_update_completed_notification(self, update_result: Dict) -> int:
        """Create notification for completed updates"""
        title = "Update Completed Successfully"
        message = f"""
The Music Scheduler has been updated successfully.

Updated to version: {update_result.get('new_version', 'Unknown')}
Update duration: {update_result.get('duration', 'Unknown')}
Backup created: {'Yes' if update_result.get('backup_created') else 'No'}

The system is now running the latest version.
        """.strip()
        
        return self.create_notification(
            notification_type='update_completed',
            title=title,
            message=message,
            severity='success',
            available_version=update_result.get('new_version'),
            metadata=update_result
        )
    
    def create_update_failed_notification(self, error_info: Dict) -> int:
        """Create notification for failed updates"""
        title = "Update Failed"
        message = f"""
The Music Scheduler update failed and has been rolled back.

Error: {error_info.get('error', 'Unknown error')}
Rollback status: {error_info.get('rollback_status', 'Unknown')}
Backup available: {'Yes' if error_info.get('backup_available') else 'No'}

Please check the logs for more details or contact support.
        """.strip()
        
        return self.create_notification(
            notification_type='update_failed',
            title=title,
            message=message,
            severity='error',
            requires_action=True,
            metadata=error_info
        )
    
    def get_active_notifications(self, admin_user_id: Optional[int] = None) -> List[Dict]:
        """Get active (non-dismissed) notifications"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM update_notifications 
                    WHERE is_dismissed = FALSE
                """
                params = []
                
                if admin_user_id:
                    query += " AND (admin_user_id = ? OR admin_user_id IS NULL)"
                    params.append(admin_user_id)
                
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                
                notifications = []
                for row in cursor.fetchall():
                    notification = dict(zip(columns, row))
                    # Parse JSON fields
                    if notification['commit_details']:
                        notification['commit_details'] = json.loads(notification['commit_details'])
                    if notification['metadata']:
                        notification['metadata'] = json.loads(notification['metadata'])
                    notifications.append(notification)
                
                return notifications
                
        except Exception as e:
            self.logger.error(f"Error getting active notifications: {str(e)}")
            return []
    
    def mark_notification_read(self, notification_id: int, admin_user_id: Optional[int] = None) -> bool:
        """Mark a notification as read"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "UPDATE update_notifications SET is_read = TRUE, read_at = ? WHERE id = ?"
                params = [datetime.datetime.now().isoformat(), notification_id]
                
                if admin_user_id:
                    query += " AND (admin_user_id = ? OR admin_user_id IS NULL)"
                    params.append(admin_user_id)
                
                cursor.execute(query, params)
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Error marking notification as read: {str(e)}")
            return False
    
    def dismiss_notification(self, notification_id: int, admin_user_id: Optional[int] = None) -> bool:
        """Dismiss a notification"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "UPDATE update_notifications SET is_dismissed = TRUE WHERE id = ?"
                params = [notification_id]
                
                if admin_user_id:
                    query += " AND (admin_user_id = ? OR admin_user_id IS NULL)"
                    params.append(admin_user_id)
                
                cursor.execute(query, params)
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Error dismissing notification: {str(e)}")
            return False
    
    def cleanup_old_notifications(self, days: int = 30) -> int:
        """Clean up old notifications"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM update_notifications 
                    WHERE created_at < ? AND is_dismissed = TRUE
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"Cleaned up {deleted_count} old notifications")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Error cleaning up notifications: {str(e)}")
            return 0
    
    def get_notification_stats(self) -> Dict:
        """Get notification statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get counts by type and status
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN is_read = FALSE THEN 1 ELSE 0 END) as unread,
                        SUM(CASE WHEN is_dismissed = FALSE THEN 1 ELSE 0 END) as active,
                        SUM(CASE WHEN requires_action = TRUE AND is_dismissed = FALSE THEN 1 ELSE 0 END) as action_required
                    FROM update_notifications
                """)
                
                stats = dict(zip(['total', 'unread', 'active', 'action_required'], cursor.fetchone()))
                
                # Get counts by notification type
                cursor.execute("""
                    SELECT notification_type, COUNT(*) as count
                    FROM update_notifications
                    WHERE created_at > datetime('now', '-30 days')
                    GROUP BY notification_type
                """)
                
                stats['by_type'] = dict(cursor.fetchall())
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error getting notification stats: {str(e)}")
            return {}

if __name__ == "__main__":
    handler = UpdateNotificationHandler()
    
    # Example usage
    test_update_info = {
        'status': 'updates_available',
        'current_version': {'hash': 'abc123def456'},
        'remote_version': {
            'hash': 'def456ghi789',
            'message': 'Fix critical security issue',
            'author': 'Developer'
        },
        'commit_count': 3,
        'new_commits': []
    }
    
    notification_id = handler.create_update_available_notification(test_update_info)
    print(f"Created test notification: {notification_id}")
    
    stats = handler.get_notification_stats()
    print(f"Notification stats: {json.dumps(stats, indent=2)}")
