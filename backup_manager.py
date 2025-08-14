#!/usr/bin/env python3
"""
Backup Manager for Music Scheduler Auto-Update System
Handles creation, management, and maintenance of system backups
"""

import os
import sys
import json
import shutil
import sqlite3
import datetime
import zipfile
import logging
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class BackupInfo:
    id: Optional[int]
    name: str
    path: str
    size_bytes: int
    version: Optional[str]
    commit_hash: Optional[str]
    backup_type: str
    is_compressed: bool
    can_rollback: bool
    created_at: datetime.datetime
    expires_at: Optional[datetime.datetime]
    metadata: Dict

class BackupManager:
    def __init__(self, config_path="/home/ubuntu/music_scheduler_update_system/config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.local_path = self.config['system']['local_path']
        self.backup_path = self.config['system']['backup_path']
        self.db_path = self.config['system']['database_path']
        self.retention_days = self.config['security']['backup_retention_days']
        
        # Ensure backup directory exists
        os.makedirs(self.backup_path, exist_ok=True)
        
        # Setup logging
        log_dir = Path(self.config['system']['log_path'])
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / 'backup_manager.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self.init_database()
    
    def init_database(self):
        """Initialize backup tracking database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS update_backups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        backup_name TEXT NOT NULL,
                        backup_path TEXT NOT NULL,
                        backup_size_bytes INTEGER,
                        version_backed_up TEXT,
                        commit_hash TEXT,
                        backup_type TEXT DEFAULT 'manual' CHECK (backup_type IN ('pre_update', 'manual', 'scheduled')),
                        is_compressed BOOLEAN DEFAULT TRUE,
                        can_rollback BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        metadata TEXT
                    )
                """)
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
    
    def get_current_version_info(self) -> Dict:
        """Get current system version information"""
        try:
            version_info = {
                'commit_hash': None,
                'branch': None,
                'last_update': None
            }
            
            # Get Git information if available
            git_dir = os.path.join(self.local_path, '.git')
            if os.path.exists(git_dir):
                import subprocess
                
                try:
                    # Get current commit hash
                    result = subprocess.run(
                        ['git', 'rev-parse', 'HEAD'],
                        cwd=self.local_path,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        version_info['commit_hash'] = result.stdout.strip()
                    
                    # Get current branch
                    result = subprocess.run(
                        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                        cwd=self.local_path,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        version_info['branch'] = result.stdout.strip()
                    
                    # Get last commit date
                    result = subprocess.run(
                        ['git', 'show', '-s', '--format=%ci', 'HEAD'],
                        cwd=self.local_path,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        version_info['last_update'] = result.stdout.strip()
                        
                except Exception as e:
                    self.logger.warning(f"Could not get Git information: {str(e)}")
            
            return version_info
            
        except Exception as e:
            self.logger.error(f"Error getting version info: {str(e)}")
            return {}
    
    def create_backup(self, 
                     backup_name: str,
                     backup_type: str = 'manual',
                     description: str = '',
                     include_data: bool = True,
                     compress: bool = True) -> Tuple[bool, str, Optional[str]]:
        """Create a new backup"""
        try:
            self.logger.info(f"Creating backup: {backup_name}")
            
            # Generate unique backup name if needed
            if not backup_name:
                backup_name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Ensure unique name
            backup_name = self.ensure_unique_backup_name(backup_name)
            
            # Determine backup file extension
            extension = '.zip' if compress else ''
            backup_filename = f"{backup_name}{extension}"
            backup_filepath = os.path.join(self.backup_path, backup_filename)
            
            # Get current version info
            version_info = self.get_current_version_info()
            
            # Create backup
            if compress:
                success, message = self.create_compressed_backup(backup_filepath, include_data)
            else:
                success, message = self.create_directory_backup(backup_filepath, include_data)
            
            if not success:
                return False, message, None
            
            # Calculate backup size
            backup_size = self.get_backup_size(backup_filepath)
            
            # Calculate expiration date
            expires_at = None
            if self.retention_days > 0:
                expires_at = datetime.datetime.now() + datetime.timedelta(days=self.retention_days)
            
            # Record backup in database
            backup_id = self.record_backup_in_database(
                backup_name=backup_name,
                backup_path=backup_filepath,
                backup_size=backup_size,
                version=version_info.get('commit_hash'),
                commit_hash=version_info.get('commit_hash'),
                backup_type=backup_type,
                is_compressed=compress,
                expires_at=expires_at,
                metadata={
                    'description': description,
                    'version_info': version_info,
                    'include_data': include_data
                }
            )
            
            if backup_id:
                self.logger.info(f"Backup created successfully: {backup_filepath}")
                return True, "Backup created successfully", backup_filepath
            else:
                return False, "Failed to record backup in database", None
                
        except Exception as e:
            error_msg = f"Backup creation failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def ensure_unique_backup_name(self, base_name: str) -> str:
        """Ensure backup name is unique"""
        counter = 1
        original_name = base_name
        
        while self.backup_name_exists(base_name):
            base_name = f"{original_name}_{counter}"
            counter += 1
        
        return base_name
    
    def backup_name_exists(self, backup_name: str) -> bool:
        """Check if backup name already exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM update_backups WHERE backup_name = ?",
                    (backup_name,)
                )
                count = cursor.fetchone()[0]
                return count > 0
        except:
            return False
    
    def create_compressed_backup(self, backup_filepath: str, include_data: bool = True) -> Tuple[bool, str]:
        """Create compressed zip backup"""
        try:
            with zipfile.ZipFile(backup_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Get list of items to backup
                items_to_backup = self.get_backup_items(include_data)
                
                for item_path, archive_name in items_to_backup:
                    if os.path.exists(item_path):
                        if os.path.isfile(item_path):
                            zipf.write(item_path, archive_name)
                        elif os.path.isdir(item_path):
                            for root, dirs, files in os.walk(item_path):
                                # Skip certain directories
                                dirs[:] = [d for d in dirs if not self.should_skip_directory(d)]
                                
                                for file in files:
                                    if not self.should_skip_file(file):
                                        file_path = os.path.join(root, file)
                                        # Calculate archive path
                                        rel_path = os.path.relpath(file_path, self.local_path)
                                        archive_path = os.path.join(archive_name, rel_path).replace('\\', '/')
                                        
                                        try:
                                            zipf.write(file_path, archive_path)
                                        except Exception as e:
                                            self.logger.warning(f"Could not backup file {file_path}: {str(e)}")
            
            return True, "Compressed backup created successfully"
            
        except Exception as e:
            return False, f"Compressed backup failed: {str(e)}"
    
    def create_directory_backup(self, backup_dirpath: str, include_data: bool = True) -> Tuple[bool, str]:
        """Create directory-based backup"""
        try:
            os.makedirs(backup_dirpath, exist_ok=True)
            
            items_to_backup = self.get_backup_items(include_data)
            
            for item_path, archive_name in items_to_backup:
                if os.path.exists(item_path):
                    dest_path = os.path.join(backup_dirpath, archive_name)
                    
                    if os.path.isfile(item_path):
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        shutil.copy2(item_path, dest_path)
                    elif os.path.isdir(item_path):
                        shutil.copytree(
                            item_path, 
                            dest_path,
                            ignore=shutil.ignore_patterns(*self.get_ignore_patterns())
                        )
            
            return True, "Directory backup created successfully"
            
        except Exception as e:
            return False, f"Directory backup failed: {str(e)}"
    
    def get_backup_items(self, include_data: bool = True) -> List[Tuple[str, str]]:
        """Get list of items to include in backup"""
        items = []
        
        # Application files
        app_files = [
            'app.py',
            'requirements.txt',
            'package.json',
            'config/',
            'templates/',
            'static/',
            'migrations/',
            'scripts/'
        ]
        
        for item in app_files:
            item_path = os.path.join(self.local_path, item)
            if os.path.exists(item_path):
                items.append((item_path, item))
        
        # Data directories (if requested)
        if include_data:
            data_items = [
                'data/',
                'uploads/',
                'backups/',
                'logs/'
            ]
            
            for item in data_items:
                item_path = os.path.join(self.local_path, item)
                if os.path.exists(item_path):
                    items.append((item_path, item))
        
        # Database files
        if os.path.exists(self.db_path):
            items.append((self.db_path, 'database.db'))
        
        # Configuration files
        config_files = [
            '.env',
            'config.ini',
            'settings.json'
        ]
        
        for config_file in config_files:
            config_path = os.path.join(self.local_path, config_file)
            if os.path.exists(config_path):
                items.append((config_path, config_file))
        
        return items
    
    def should_skip_directory(self, dirname: str) -> bool:
        """Check if directory should be skipped during backup"""
        skip_dirs = {
            '.git',
            '__pycache__',
            '.pytest_cache',
            'node_modules',
            '.venv',
            'venv',
            'env',
            'temp',
            'tmp'
        }
        return dirname in skip_dirs
    
    def should_skip_file(self, filename: str) -> bool:
        """Check if file should be skipped during backup"""
        skip_extensions = {'.pyc', '.pyo', '.pyd', '.log', '.tmp'}
        skip_files = {'.DS_Store', 'Thumbs.db', '.gitignore'}
        
        if filename in skip_files:
            return True
        
        _, ext = os.path.splitext(filename)
        return ext.lower() in skip_extensions
    
    def get_ignore_patterns(self) -> List[str]:
        """Get ignore patterns for directory copying"""
        return [
            '*.pyc',
            '*.pyo',
            '*.pyd',
            '__pycache__',
            '.git',
            '*.log',
            '*.tmp',
            'node_modules',
            '.DS_Store',
            'Thumbs.db'
        ]
    
    def get_backup_size(self, backup_path: str) -> int:
        """Get total size of backup"""
        try:
            if os.path.isfile(backup_path):
                return os.path.getsize(backup_path)
            elif os.path.isdir(backup_path):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(backup_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                        except (OSError, FileNotFoundError):
                            pass
                return total_size
            return 0
        except:
            return 0
    
    def record_backup_in_database(self,
                                 backup_name: str,
                                 backup_path: str,
                                 backup_size: int,
                                 version: Optional[str],
                                 commit_hash: Optional[str],
                                 backup_type: str,
                                 is_compressed: bool,
                                 expires_at: Optional[datetime.datetime],
                                 metadata: Dict) -> Optional[int]:
        """Record backup information in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO update_backups 
                    (backup_name, backup_path, backup_size_bytes, version_backed_up, 
                     commit_hash, backup_type, is_compressed, can_rollback, 
                     expires_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    backup_name,
                    backup_path,
                    backup_size,
                    version,
                    commit_hash,
                    backup_type,
                    is_compressed,
                    True,  # can_rollback
                    expires_at.isoformat() if expires_at else None,
                    json.dumps(metadata)
                ))
                
                backup_id = cursor.lastrowid
                conn.commit()
                
                return backup_id
                
        except Exception as e:
            self.logger.error(f"Failed to record backup in database: {str(e)}")
            return None
    
    def list_backups(self, backup_type: Optional[str] = None, include_expired: bool = False) -> List[BackupInfo]:
        """List all backups"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT id, backup_name, backup_path, backup_size_bytes, version_backed_up,
                           commit_hash, backup_type, is_compressed, can_rollback, 
                           created_at, expires_at, metadata
                    FROM update_backups
                    WHERE 1=1
                """
                params = []
                
                if backup_type:
                    query += " AND backup_type = ?"
                    params.append(backup_type)
                
                if not include_expired:
                    query += " AND (expires_at IS NULL OR expires_at > ?)"
                    params.append(datetime.datetime.now().isoformat())
                
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                backups = []
                for row in rows:
                    backup = BackupInfo(
                        id=row[0],
                        name=row[1],
                        path=row[2],
                        size_bytes=row[3],
                        version=row[4],
                        commit_hash=row[5],
                        backup_type=row[6],
                        is_compressed=bool(row[7]),
                        can_rollback=bool(row[8]),
                        created_at=datetime.datetime.fromisoformat(row[9]),
                        expires_at=datetime.datetime.fromisoformat(row[10]) if row[10] else None,
                        metadata=json.loads(row[11]) if row[11] else {}
                    )
                    backups.append(backup)
                
                return backups
                
        except Exception as e:
            self.logger.error(f"Failed to list backups: {str(e)}")
            return []
    
    def get_backup_by_id(self, backup_id: int) -> Optional[BackupInfo]:
        """Get backup by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, backup_name, backup_path, backup_size_bytes, version_backed_up,
                           commit_hash, backup_type, is_compressed, can_rollback, 
                           created_at, expires_at, metadata
                    FROM update_backups
                    WHERE id = ?
                """, (backup_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return BackupInfo(
                    id=row[0],
                    name=row[1],
                    path=row[2],
                    size_bytes=row[3],
                    version=row[4],
                    commit_hash=row[5],
                    backup_type=row[6],
                    is_compressed=bool(row[7]),
                    can_rollback=bool(row[8]),
                    created_at=datetime.datetime.fromisoformat(row[9]),
                    expires_at=datetime.datetime.fromisoformat(row[10]) if row[10] else None,
                    metadata=json.loads(row[11]) if row[11] else {}
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get backup by ID: {str(e)}")
            return None
    
    def delete_backup(self, backup_id: int) -> Tuple[bool, str]:
        """Delete a backup"""
        try:
            backup = self.get_backup_by_id(backup_id)
            if not backup:
                return False, "Backup not found"
            
            # Delete backup file/directory
            if os.path.exists(backup.path):
                if os.path.isfile(backup.path):
                    os.remove(backup.path)
                elif os.path.isdir(backup.path):
                    shutil.rmtree(backup.path)
            
            # Remove from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM update_backups WHERE id = ?", (backup_id,))
                conn.commit()
            
            self.logger.info(f"Backup deleted: {backup.name}")
            return True, "Backup deleted successfully"
            
        except Exception as e:
            error_msg = f"Failed to delete backup: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def cleanup_expired_backups(self) -> Tuple[int, List[str]]:
        """Clean up expired backups"""
        try:
            deleted_count = 0
            deleted_names = []
            
            # Get expired backups
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, backup_name, backup_path 
                    FROM update_backups 
                    WHERE expires_at IS NOT NULL AND expires_at <= ?
                """, (datetime.datetime.now().isoformat(),))
                
                expired_backups = cursor.fetchall()
                
                for backup_id, backup_name, backup_path in expired_backups:
                    try:
                        # Delete file/directory
                        if os.path.exists(backup_path):
                            if os.path.isfile(backup_path):
                                os.remove(backup_path)
                            elif os.path.isdir(backup_path):
                                shutil.rmtree(backup_path)
                        
                        # Remove from database
                        cursor.execute("DELETE FROM update_backups WHERE id = ?", (backup_id,))
                        
                        deleted_count += 1
                        deleted_names.append(backup_name)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to delete expired backup {backup_name}: {str(e)}")
                
                conn.commit()
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} expired backups")
            
            return deleted_count, deleted_names
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            return 0, []
    
    def verify_backup_integrity(self, backup_id: int) -> Tuple[bool, str]:
        """Verify backup integrity"""
        try:
            backup = self.get_backup_by_id(backup_id)
            if not backup:
                return False, "Backup not found"
            
            if not os.path.exists(backup.path):
                return False, "Backup file does not exist"
            
            if backup.is_compressed:
                # Test zip file integrity
                try:
                    with zipfile.ZipFile(backup.path, 'r') as zipf:
                        result = zipf.testzip()
                        if result is not None:
                            return False, f"Corrupted file in backup: {result}"
                except zipfile.BadZipFile:
                    return False, "Backup file is not a valid zip archive"
            
            # Check file size matches recorded size
            actual_size = self.get_backup_size(backup.path)
            if abs(actual_size - backup.size_bytes) > 1024:  # Allow 1KB difference
                return False, f"Backup size mismatch: expected {backup.size_bytes}, got {actual_size}"
            
            return True, "Backup integrity verified"
            
        except Exception as e:
            return False, f"Verification failed: {str(e)}"
    
    def get_backup_stats(self) -> Dict:
        """Get backup statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total backups
                cursor.execute("SELECT COUNT(*) FROM update_backups")
                total_backups = cursor.fetchone()[0]
                
                # Total size
                cursor.execute("SELECT SUM(backup_size_bytes) FROM update_backups")
                total_size = cursor.fetchone()[0] or 0
                
                # By type
                cursor.execute("""
                    SELECT backup_type, COUNT(*), SUM(backup_size_bytes)
                    FROM update_backups
                    GROUP BY backup_type
                """)
                by_type = {}
                for backup_type, count, size in cursor.fetchall():
                    by_type[backup_type] = {'count': count, 'size': size or 0}
                
                # Recent backups (last 30 days)
                thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*) FROM update_backups 
                    WHERE created_at >= ?
                """, (thirty_days_ago,))
                recent_backups = cursor.fetchone()[0]
                
                # Expired backups
                cursor.execute("""
                    SELECT COUNT(*) FROM update_backups 
                    WHERE expires_at IS NOT NULL AND expires_at <= ?
                """, (datetime.datetime.now().isoformat(),))
                expired_backups = cursor.fetchone()[0]
                
                return {
                    'total_backups': total_backups,
                    'total_size_bytes': total_size,
                    'total_size_mb': round(total_size / (1024 * 1024), 2),
                    'by_type': by_type,
                    'recent_backups': recent_backups,
                    'expired_backups': expired_backups
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get backup stats: {str(e)}")
            return {}

if __name__ == "__main__":
    # Example usage
    manager = BackupManager()
    
    # Create a test backup
    success, message, backup_path = manager.create_backup(
        backup_name="test_backup",
        backup_type="manual",
        description="Test backup created from script",
        compress=True
    )
    
    print(f"Backup creation: {success}")
    print(f"Message: {message}")
    if backup_path:
        print(f"Backup path: {backup_path}")
    
    # List backups
    backups = manager.list_backups()
    print(f"\nFound {len(backups)} backups:")
    for backup in backups[:5]:  # Show first 5
        print(f"  {backup.name} - {backup.backup_type} - {backup.size_bytes} bytes")
    
    # Get stats
    stats = manager.get_backup_stats()
    print(f"\nBackup statistics: {json.dumps(stats, indent=2)}")
    
    # Cleanup expired backups
    deleted_count, deleted_names = manager.cleanup_expired_backups()
    print(f"\nCleaned up {deleted_count} expired backups")
