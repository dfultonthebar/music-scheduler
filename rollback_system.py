#!/usr/bin/env python3
"""
Rollback System for Music Scheduler Auto-Update System
Handles safe rollback operations to previous system states
"""

import os
import sys
import json
import shutil
import sqlite3
import datetime
import zipfile
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class RollbackTarget:
    backup_id: int
    backup_name: str
    backup_path: str
    version: Optional[str]
    commit_hash: Optional[str]
    created_at: datetime.datetime
    backup_type: str
    metadata: Dict

class RollbackSystem:
    def __init__(self, config_path="/home/ubuntu/music_scheduler_update_system/config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.local_path = self.config['system']['local_path']
        self.backup_path = self.config['system']['backup_path']
        self.db_path = self.config['system']['database_path']
        self.max_rollback_days = self.config['security']['max_rollback_days']
        
        # Setup logging
        log_dir = Path(self.config['system']['log_path'])
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / 'rollback_system.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.temp_dir = None
    
    def get_available_rollback_targets(self) -> List[RollbackTarget]:
        """Get list of available rollback targets"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=self.max_rollback_days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, backup_name, backup_path, version_backed_up, 
                           commit_hash, created_at, backup_type, metadata
                    FROM update_backups
                    WHERE can_rollback = TRUE 
                    AND created_at >= ?
                    AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY created_at DESC
                """, (cutoff_date.isoformat(), datetime.datetime.now().isoformat()))
                
                targets = []
                for row in cursor.fetchall():
                    target = RollbackTarget(
                        backup_id=row[0],
                        backup_name=row[1],
                        backup_path=row[2],
                        version=row[3],
                        commit_hash=row[4],
                        created_at=datetime.datetime.fromisoformat(row[5]),
                        backup_type=row[6],
                        metadata=json.loads(row[7]) if row[7] else {}
                    )
                    
                    # Verify backup still exists
                    if os.path.exists(target.backup_path):
                        targets.append(target)
                    else:
                        self.logger.warning(f"Backup file missing: {target.backup_path}")
                
                return targets
                
        except Exception as e:
            self.logger.error(f"Failed to get rollback targets: {str(e)}")
            return []
    
    def validate_rollback_request(self, backup_id: int, initiated_by: str = 'system') -> Tuple[bool, str, Optional[RollbackTarget]]:
        """Validate rollback request"""
        try:
            # Get rollback target
            targets = self.get_available_rollback_targets()
            target = None
            for t in targets:
                if t.backup_id == backup_id:
                    target = t
                    break
            
            if not target:
                return False, "Rollback target not found or not available", None
            
            # Check if backup file exists
            if not os.path.exists(target.backup_path):
                return False, f"Backup file does not exist: {target.backup_path}", None
            
            # Check backup integrity
            if not self.verify_backup_integrity(target):
                return False, "Backup integrity check failed", None
            
            # Check if rolling back to current state
            current_hash = self.get_current_commit_hash()
            if current_hash and current_hash == target.commit_hash:
                return False, "Cannot rollback to current version", None
            
            # Check permissions
            if not self.check_rollback_permissions():
                return False, "Insufficient permissions for rollback", None
            
            # Check disk space
            if not self.check_disk_space_for_rollback(target):
                return False, "Insufficient disk space for rollback", None
            
            return True, "Rollback validation successful", target
            
        except Exception as e:
            error_msg = f"Rollback validation failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def verify_backup_integrity(self, target: RollbackTarget) -> bool:
        """Verify backup integrity before rollback"""
        try:
            if target.backup_path.endswith('.zip'):
                # Verify zip file
                with zipfile.ZipFile(target.backup_path, 'r') as zipf:
                    result = zipf.testzip()
                    if result is not None:
                        self.logger.error(f"Corrupted file in backup: {result}")
                        return False
            elif os.path.isdir(target.backup_path):
                # Basic directory existence check
                if not os.listdir(target.backup_path):
                    self.logger.error("Backup directory is empty")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Backup integrity check failed: {str(e)}")
            return False
    
    def get_current_commit_hash(self) -> Optional[str]:
        """Get current Git commit hash"""
        try:
            if not os.path.exists(os.path.join(self.local_path, '.git')):
                return None
            
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.local_path,
                capture_output=True,
                text=True
            )
            
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None
    
    def check_rollback_permissions(self) -> bool:
        """Check if we have necessary permissions for rollback"""
        try:
            # Check write permissions on target directory
            if not os.access(self.local_path, os.W_OK):
                return False
            
            # Try creating a test file
            test_file = os.path.join(self.local_path, '.rollback_permission_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                return True
            except:
                return False
                
        except:
            return False
    
    def check_disk_space_for_rollback(self, target: RollbackTarget, buffer_gb: float = 2.0) -> bool:
        """Check if there's enough disk space for rollback"""
        try:
            # Calculate required space (backup size + current system size + buffer)
            backup_size = self.get_backup_size(target.backup_path)
            current_system_size = self.get_directory_size(self.local_path)
            
            # Get available space
            stat = shutil.disk_usage(self.local_path)
            available_space = stat.free
            
            # Require backup size + current system size + buffer (for safety)
            required_space = backup_size + current_system_size + (buffer_gb * 1024 * 1024 * 1024)
            
            self.logger.info(f"Rollback space check: required {required_space}, available {available_space}")
            return available_space > required_space
            
        except Exception as e:
            self.logger.error(f"Disk space check failed: {str(e)}")
            return False
    
    def get_backup_size(self, backup_path: str) -> int:
        """Get backup size"""
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
    
    def get_directory_size(self, path: str) -> int:
        """Get total size of directory"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        pass
        except:
            pass
        return total_size
    
    def create_pre_rollback_backup(self, rollback_target: str) -> Tuple[bool, str, Optional[str]]:
        """Create backup of current state before rollback"""
        try:
            from backup_manager import BackupManager
            backup_manager = BackupManager()
            
            backup_name = f"pre_rollback_{rollback_target}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            success, message, backup_path = backup_manager.create_backup(
                backup_name=backup_name,
                backup_type='pre_rollback',
                description=f"Backup before rollback to {rollback_target}",
                compress=True
            )
            
            if success:
                self.logger.info(f"Pre-rollback backup created: {backup_path}")
            
            return success, message, backup_path
            
        except Exception as e:
            error_msg = f"Pre-rollback backup failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def extract_backup_to_temp(self, target: RollbackTarget) -> Tuple[bool, str, Optional[str]]:
        """Extract backup to temporary directory"""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix='music_scheduler_rollback_')
            
            if target.backup_path.endswith('.zip'):
                # Extract zip file
                with zipfile.ZipFile(target.backup_path, 'r') as zipf:
                    # Security check: prevent zip slip attacks
                    for member in zipf.namelist():
                        if os.path.isabs(member) or '..' in member:
                            return False, f"Unsafe path in backup: {member}", None
                    
                    zipf.extractall(self.temp_dir)
                
                # Find extracted content
                extracted_items = os.listdir(self.temp_dir)
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(self.temp_dir, extracted_items[0])):
                    extracted_path = os.path.join(self.temp_dir, extracted_items[0])
                else:
                    extracted_path = self.temp_dir
                    
            elif os.path.isdir(target.backup_path):
                # Copy directory
                extracted_path = os.path.join(self.temp_dir, 'extracted')
                shutil.copytree(target.backup_path, extracted_path)
            else:
                return False, "Unknown backup format", None
            
            self.logger.info(f"Backup extracted to: {extracted_path}")
            return True, "Backup extracted successfully", extracted_path
            
        except Exception as e:
            error_msg = f"Backup extraction failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def stop_services(self):
        """Stop application services for rollback"""
        try:
            services = ['music-scheduler', 'nginx']  # Adjust as needed
            
            for service in services:
                try:
                    subprocess.run(['sudo', 'systemctl', 'stop', service], 
                                 check=True, capture_output=True)
                    self.logger.info(f"Stopped service: {service}")
                except subprocess.CalledProcessError:
                    self.logger.warning(f"Could not stop service: {service}")
                    
        except Exception as e:
            self.logger.error(f"Error stopping services: {str(e)}")
    
    def start_services(self):
        """Start application services after rollback"""
        try:
            services = ['music-scheduler', 'nginx']  # Adjust as needed
            
            for service in services:
                try:
                    subprocess.run(['sudo', 'systemctl', 'start', service], 
                                 check=True, capture_output=True)
                    self.logger.info(f"Started service: {service}")
                except subprocess.CalledProcessError as e:
                    self.logger.error(f"Could not start service {service}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Error starting services: {str(e)}")
    
    def perform_rollback_restore(self, extracted_path: str) -> Tuple[bool, str]:
        """Perform the actual rollback restore"""
        try:
            self.logger.info("Starting rollback restore process")
            
            # Create staging area
            staging_dir = os.path.join(self.temp_dir, 'staging')
            shutil.copytree(extracted_path, staging_dir)
            
            # Preserve critical files
            preserved_files = self.preserve_critical_files()
            
            # Remove current application files (except preserved ones)
            self.remove_current_files()
            
            # Restore files from backup
            self.restore_files_from_backup(staging_dir)
            
            # Restore preserved files
            self.restore_preserved_files(preserved_files)
            
            # Handle database rollback if needed
            self.handle_database_rollback(staging_dir)
            
            # Run post-rollback scripts
            self.run_post_rollback_scripts(staging_dir)
            
            self.logger.info("Rollback restore completed successfully")
            return True, "Rollback restore completed successfully"
            
        except Exception as e:
            error_msg = f"Rollback restore failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def preserve_critical_files(self) -> Dict[str, str]:
        """Preserve critical files during rollback"""
        try:
            preserved = {}
            
            # Files to preserve during rollback
            preserve_paths = [
                'config/local.json',
                '.env',
                'logs/',  # Keep current logs
                'data/uploads/',  # Keep uploaded files
            ]
            
            preserve_temp_dir = os.path.join(self.temp_dir, 'preserved')
            os.makedirs(preserve_temp_dir, exist_ok=True)
            
            for preserve_path in preserve_paths:
                source_path = os.path.join(self.local_path, preserve_path)
                if os.path.exists(source_path):
                    dest_name = preserve_path.replace('/', '_')
                    dest_path = os.path.join(preserve_temp_dir, dest_name)
                    
                    try:
                        if os.path.isdir(source_path):
                            shutil.copytree(source_path, dest_path)
                        else:
                            shutil.copy2(source_path, dest_path)
                        
                        preserved[preserve_path] = dest_path
                        self.logger.info(f"Preserved: {preserve_path}")
                        
                    except Exception as e:
                        self.logger.warning(f"Could not preserve {preserve_path}: {str(e)}")
            
            return preserved
            
        except Exception as e:
            self.logger.error(f"Error preserving files: {str(e)}")
            return {}
    
    def remove_current_files(self):
        """Remove current application files"""
        try:
            # Items to keep during rollback
            keep_items = [
                '.git',
                'config/local.json',
                '.env',
                'logs',
                'data/uploads'
            ]
            
            for item in os.listdir(self.local_path):
                if item in keep_items:
                    continue
                
                item_path = os.path.join(self.local_path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    self.logger.debug(f"Removed: {item_path}")
                except Exception as e:
                    self.logger.warning(f"Could not remove {item_path}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Error removing current files: {str(e)}")
            raise
    
    def restore_files_from_backup(self, staging_dir: str):
        """Restore files from backup"""
        try:
            for item in os.listdir(staging_dir):
                source_path = os.path.join(staging_dir, item)
                dest_path = os.path.join(self.local_path, item)
                
                try:
                    if os.path.isdir(source_path):
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        shutil.copy2(source_path, dest_path)
                    
                    self.logger.debug(f"Restored: {item}")
                    
                except Exception as e:
                    self.logger.error(f"Could not restore {item}: {str(e)}")
                    raise
                    
        except Exception as e:
            self.logger.error(f"Error restoring files: {str(e)}")
            raise
    
    def restore_preserved_files(self, preserved_files: Dict[str, str]):
        """Restore preserved critical files"""
        try:
            for original_path, preserved_path in preserved_files.items():
                dest_path = os.path.join(self.local_path, original_path)
                
                try:
                    # Ensure destination directory exists
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    if os.path.isdir(preserved_path):
                        # Remove existing directory if it exists
                        if os.path.exists(dest_path):
                            shutil.rmtree(dest_path)
                        shutil.copytree(preserved_path, dest_path)
                    else:
                        shutil.copy2(preserved_path, dest_path)
                    
                    self.logger.info(f"Restored preserved file: {original_path}")
                    
                except Exception as e:
                    self.logger.warning(f"Could not restore preserved file {original_path}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Error restoring preserved files: {str(e)}")
    
    def handle_database_rollback(self, staging_dir: str):
        """Handle database rollback if needed"""
        try:
            # Check if backup contains database
            db_backup_path = None
            possible_db_paths = [
                os.path.join(staging_dir, 'database.db'),
                os.path.join(staging_dir, 'data', 'database.db'),
                os.path.join(staging_dir, 'db', 'database.db')
            ]
            
            for db_path in possible_db_paths:
                if os.path.exists(db_path):
                    db_backup_path = db_path
                    break
            
            if db_backup_path:
                # Create backup of current database
                current_db_backup = f"{self.db_path}.rollback_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                if os.path.exists(self.db_path):
                    shutil.copy2(self.db_path, current_db_backup)
                    self.logger.info(f"Current database backed up to: {current_db_backup}")
                
                # Restore database from backup
                shutil.copy2(db_backup_path, self.db_path)
                self.logger.info("Database restored from backup")
                
                # Run any database migration/compatibility scripts
                self.run_database_compatibility_check()
            
        except Exception as e:
            self.logger.error(f"Database rollback failed: {str(e)}")
            raise
    
    def run_database_compatibility_check(self):
        """Run database compatibility checks after rollback"""
        try:
            # Check if database schema is compatible
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Basic schema validation
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                required_tables = ['update_backups', 'update_history', 'update_notifications']
                for table in required_tables:
                    if table not in tables:
                        self.logger.warning(f"Required table missing after rollback: {table}")
            
            self.logger.info("Database compatibility check completed")
            
        except Exception as e:
            self.logger.error(f"Database compatibility check failed: {str(e)}")
    
    def run_post_rollback_scripts(self, staging_dir: str):
        """Run post-rollback scripts if they exist"""
        try:
            script_path = os.path.join(staging_dir, 'scripts', 'post_rollback.py')
            if os.path.exists(script_path):
                subprocess.run([sys.executable, script_path], check=True, cwd=self.local_path)
                self.logger.info("Post-rollback scripts completed")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Post-rollback script failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error running post-rollback scripts: {str(e)}")
    
    def verify_rollback_success(self, target: RollbackTarget) -> bool:
        """Verify that rollback was successful"""
        try:
            # Check if main application files exist
            main_files = ['app.py', 'requirements.txt']  # Adjust as needed
            for main_file in main_files:
                if not os.path.exists(os.path.join(self.local_path, main_file)):
                    self.logger.error(f"Main file missing after rollback: {main_file}")
                    return False
            
            # Check if services can start
            # This is a basic check - you might want more sophisticated verification
            
            # Check if target version matches (if available)
            if target.commit_hash:
                current_hash = self.get_current_commit_hash()
                if current_hash and current_hash != target.commit_hash:
                    self.logger.warning(f"Version mismatch after rollback: expected {target.commit_hash[:8]}, got {current_hash[:8] if current_hash else 'None'}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback verification failed: {str(e)}")
            return False
    
    def record_rollback_history(self, rollback_info: Dict, status: str, error_msg: Optional[str] = None):
        """Record rollback operation in history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO update_history 
                    (update_type, status, version_from, version_to, commit_hash_from, 
                     commit_hash_to, backup_created, backup_path, error_message, 
                     duration_seconds, initiated_by, started_at, completed_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    'rollback',
                    status,
                    rollback_info.get('current_version'),
                    rollback_info.get('target_version'),
                    rollback_info.get('current_hash'),
                    rollback_info.get('target_hash'),
                    rollback_info.get('backup_created', False),
                    rollback_info.get('backup_path'),
                    error_msg,
                    rollback_info.get('duration_seconds'),
                    rollback_info.get('initiated_by', 'system'),
                    rollback_info.get('started_at'),
                    datetime.datetime.now().isoformat(),
                    json.dumps(rollback_info.get('metadata', {}))
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to record rollback history: {str(e)}")
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.info("Temporary rollback files cleaned up")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
    
    def rollback_from_backup(self, backup_id: int, initiated_by: str = 'system') -> Dict:
        """Complete rollback process from backup"""
        start_time = datetime.datetime.now()
        current_hash = self.get_current_commit_hash()
        
        try:
            # Validate rollback request
            valid, validation_msg, target = self.validate_rollback_request(backup_id, initiated_by)
            if not valid:
                return {
                    'success': False,
                    'error': f"Rollback validation failed: {validation_msg}",
                    'stage': 'validation'
                }
            
            self.logger.info(f"Starting rollback to backup: {target.backup_name}")
            
            # Create pre-rollback backup
            backup_success, backup_msg, pre_rollback_backup = self.create_pre_rollback_backup(
                target.backup_name
            )
            if not backup_success:
                self.logger.warning(f"Pre-rollback backup failed: {backup_msg}")
            
            # Stop services
            self.stop_services()
            
            try:
                # Extract backup
                extract_success, extract_msg, extracted_path = self.extract_backup_to_temp(target)
                if not extract_success:
                    return {
                        'success': False,
                        'error': extract_msg,
                        'stage': 'extraction'
                    }
                
                # Perform rollback
                restore_success, restore_msg = self.perform_rollback_restore(extracted_path)
                if not restore_success:
                    return {
                        'success': False,
                        'error': restore_msg,
                        'stage': 'restoration'
                    }
                
                # Start services
                self.start_services()
                
                # Verify rollback
                if not self.verify_rollback_success(target):
                    return {
                        'success': False,
                        'error': "Rollback verification failed",
                        'stage': 'verification'
                    }
                
                # Record success
                duration = (datetime.datetime.now() - start_time).total_seconds()
                self.record_rollback_history({
                    'current_hash': current_hash,
                    'target_hash': target.commit_hash,
                    'target_version': target.version,
                    'backup_created': backup_success,
                    'backup_path': pre_rollback_backup,
                    'duration_seconds': duration,
                    'started_at': start_time.isoformat(),
                    'initiated_by': initiated_by,
                    'target_backup_name': target.backup_name
                }, 'success')
                
                self.logger.info(f"Rollback completed successfully to backup: {target.backup_name}")
                
                return {
                    'success': True,
                    'message': f'Rollback completed successfully to {target.backup_name}',
                    'target_version': target.version,
                    'duration_seconds': duration,
                    'pre_rollback_backup': pre_rollback_backup
                }
                
            except Exception as e:
                # If rollback fails, try to restart services anyway
                try:
                    self.start_services()
                except:
                    pass
                raise e
                
        except Exception as e:
            error_msg = f"Rollback failed: {str(e)}"
            self.logger.error(error_msg)
            
            # Record failure
            duration = (datetime.datetime.now() - start_time).total_seconds()
            self.record_rollback_history({
                'current_hash': current_hash,
                'target_hash': target.commit_hash if target else None,
                'duration_seconds': duration,
                'started_at': start_time.isoformat(),
                'initiated_by': initiated_by
            }, 'failed', error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'stage': 'unexpected_error'
            }
            
        finally:
            # Always cleanup temp files
            self.cleanup_temp_files()
    
    def emergency_rollback(self, initiated_by: str = 'system') -> Dict:
        """Emergency rollback to the most recent backup"""
        try:
            targets = self.get_available_rollback_targets()
            if not targets:
                return {
                    'success': False,
                    'error': 'No rollback targets available',
                    'stage': 'target_selection'
                }
            
            # Use the most recent backup
            most_recent = targets[0]
            self.logger.info(f"Emergency rollback to most recent backup: {most_recent.backup_name}")
            
            return self.rollback_from_backup(most_recent.backup_id, initiated_by)
            
        except Exception as e:
            error_msg = f"Emergency rollback failed: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'stage': 'emergency_rollback'
            }

if __name__ == "__main__":
    # Example usage
    rollback_system = RollbackSystem()
    
    # List available rollback targets
    targets = rollback_system.get_available_rollback_targets()
    print(f"Available rollback targets: {len(targets)}")
    for target in targets:
        print(f"  {target.backup_name} - {target.version} - {target.created_at}")
    
    # Example rollback (uncomment to test)
    # if targets:
    #     result = rollback_system.rollback_from_backup(targets[0].backup_id, 'admin')
    #     print(f"Rollback result: {json.dumps(result, indent=2)}")
