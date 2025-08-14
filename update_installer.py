#!/usr/bin/env python3
"""
Secure Update Installer for Music Scheduler
Handles downloading, validating, and installing updates with security checks
"""

import os
import sys
import json
import shutil
import hashlib
import subprocess
import tempfile
import zipfile
import requests
import datetime
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from backup_manager import BackupManager
from rollback_system import RollbackSystem

class SecureUpdateInstaller:
    def __init__(self, config_path="/home/ubuntu/music_scheduler_update_system/config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.github_token = self.config['github']['token']
        self.repo_api_url = self.config['github']['repository_api_url']
        self.local_path = self.config['system']['local_path']
        self.db_path = self.config['system']['database_path']
        self.backup_path = self.config['system']['backup_path']
        
        # Setup logging
        log_dir = Path(self.config['system']['log_path'])
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / 'update_installer.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize managers
        self.backup_manager = BackupManager(config_path)
        self.rollback_system = RollbackSystem(config_path)
        
        # Security settings
        self.verify_signatures = self.config['security']['verify_signatures']
        self.allowed_branches = self.config['security']['allowed_branches']
        self.temp_dir = None
    
    def get_headers(self):
        """Get GitHub API headers with authentication"""
        return {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'MusicScheduler-SecureUpdater'
        }
    
    def validate_update_request(self, update_info: Dict) -> Tuple[bool, str]:
        """Validate update request for security"""
        try:
            # Check if branch is allowed
            branch = update_info.get('branch', 'main')
            if branch not in self.allowed_branches:
                return False, f"Branch '{branch}' not in allowed branches: {self.allowed_branches}"
            
            # Check if target version exists
            target_hash = update_info.get('target_hash')
            if not target_hash or len(target_hash) < 8:
                return False, "Invalid target hash provided"
            
            # Verify target hash exists in repository
            if not self.verify_commit_exists(target_hash):
                return False, f"Target commit {target_hash[:8]} does not exist in repository"
            
            # Check if we're not downgrading (unless explicitly allowed)
            if not update_info.get('allow_downgrade', False):
                current_hash = self.get_current_commit_hash()
                if current_hash and not self.is_newer_commit(current_hash, target_hash):
                    return False, "Cannot downgrade to older version without explicit permission"
            
            return True, "Validation successful"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def verify_commit_exists(self, commit_hash: str) -> bool:
        """Verify that commit exists in remote repository"""
        try:
            url = f"{self.repo_api_url}/commits/{commit_hash}"
            response = requests.get(url, headers=self.get_headers())
            return response.status_code == 200
        except:
            return False
    
    def get_current_commit_hash(self) -> Optional[str]:
        """Get current local commit hash"""
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
    
    def is_newer_commit(self, current_hash: str, target_hash: str) -> bool:
        """Check if target commit is newer than current"""
        try:
            # Get commit timestamps
            current_timestamp = self.get_commit_timestamp(current_hash)
            target_timestamp = self.get_commit_timestamp(target_hash)
            
            if current_timestamp and target_timestamp:
                return target_timestamp > current_timestamp
            
            return True  # Allow if we can't determine
        except:
            return True
    
    def get_commit_timestamp(self, commit_hash: str) -> Optional[datetime.datetime]:
        """Get commit timestamp from GitHub"""
        try:
            url = f"{self.repo_api_url}/commits/{commit_hash}"
            response = requests.get(url, headers=self.get_headers())
            
            if response.status_code == 200:
                commit_data = response.json()
                date_str = commit_data['commit']['author']['date']
                return datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            return None
        except:
            return None
    
    def download_update(self, commit_hash: str) -> Tuple[bool, str, Optional[str]]:
        """Download update archive from GitHub"""
        try:
            self.logger.info(f"Downloading update for commit {commit_hash[:8]}")
            
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix='music_scheduler_update_')
            
            # Download archive
            archive_url = f"https://github.com/{self.config['github']['owner']}/{self.config['github']['repo']}/archive/{commit_hash}.zip"
            
            response = requests.get(archive_url, headers=self.get_headers())
            response.raise_for_status()
            
            # Save archive
            archive_path = os.path.join(self.temp_dir, f'update_{commit_hash[:8]}.zip')
            with open(archive_path, 'wb') as f:
                f.write(response.content)
            
            # Verify download
            if not self.verify_download(archive_path):
                return False, "Download verification failed", None
            
            self.logger.info(f"Update downloaded successfully: {archive_path}")
            return True, "Download completed", archive_path
            
        except requests.RequestException as e:
            error_msg = f"Download failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Unexpected download error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def verify_download(self, archive_path: str) -> bool:
        """Verify downloaded archive integrity"""
        try:
            # Check if file exists and has content
            if not os.path.exists(archive_path) or os.path.getsize(archive_path) == 0:
                return False
            
            # Test zip file integrity
            with zipfile.ZipFile(archive_path, 'r') as zip_file:
                # Test the zip file
                result = zip_file.testzip()
                if result is not None:
                    self.logger.error(f"Corrupted file in archive: {result}")
                    return False
            
            # Additional security checks could go here
            # - Virus scanning
            # - Size limits
            # - Content validation
            
            return True
            
        except Exception as e:
            self.logger.error(f"Archive verification failed: {str(e)}")
            return False
    
    def extract_update(self, archive_path: str) -> Tuple[bool, str, Optional[str]]:
        """Extract update archive safely"""
        try:
            extract_dir = os.path.join(self.temp_dir, 'extracted')
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(archive_path, 'r') as zip_file:
                # Security check: prevent zip slip attacks
                for member in zip_file.namelist():
                    if os.path.isabs(member) or '..' in member:
                        return False, f"Unsafe path in archive: {member}", None
                
                # Extract all files
                zip_file.extractall(extract_dir)
            
            # Find the extracted directory (GitHub creates a subdirectory)
            extracted_contents = os.listdir(extract_dir)
            if len(extracted_contents) != 1 or not os.path.isdir(os.path.join(extract_dir, extracted_contents[0])):
                return False, "Unexpected archive structure", None
            
            source_dir = os.path.join(extract_dir, extracted_contents[0])
            
            self.logger.info(f"Update extracted to: {source_dir}")
            return True, "Extraction completed", source_dir
            
        except Exception as e:
            error_msg = f"Extraction failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def pre_install_checks(self, source_dir: str) -> Tuple[bool, str]:
        """Perform pre-installation checks"""
        try:
            # Check required files exist
            required_files = ['package.json', 'requirements.txt', 'app.py']  # Adjust based on your app
            for req_file in required_files:
                if not os.path.exists(os.path.join(source_dir, req_file)):
                    self.logger.warning(f"Required file missing: {req_file}")
            
            # Check for migration scripts
            migrations_dir = os.path.join(source_dir, 'migrations')
            if os.path.exists(migrations_dir):
                self.logger.info("Database migrations found")
            
            # Check disk space
            if not self.check_disk_space(source_dir):
                return False, "Insufficient disk space for installation"
            
            # Check permissions
            if not self.check_permissions():
                return False, "Insufficient permissions for installation"
            
            return True, "Pre-installation checks passed"
            
        except Exception as e:
            error_msg = f"Pre-installation check failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def check_disk_space(self, source_dir: str, buffer_gb: float = 1.0) -> bool:
        """Check if there's enough disk space"""
        try:
            # Calculate source size
            source_size = self.get_directory_size(source_dir)
            
            # Get available space
            stat = shutil.disk_usage(self.local_path)
            available_space = stat.free
            
            # Require source size + buffer
            required_space = source_size + (buffer_gb * 1024 * 1024 * 1024)
            
            self.logger.info(f"Disk space check: required {required_space}, available {available_space}")
            return available_space > required_space
            
        except Exception as e:
            self.logger.error(f"Disk space check failed: {str(e)}")
            return False
    
    def get_directory_size(self, path: str) -> int:
        """Get total size of directory"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    pass
        return total_size
    
    def check_permissions(self) -> bool:
        """Check if we have necessary permissions"""
        try:
            # Check write permissions on target directory
            if not os.access(self.local_path, os.W_OK):
                return False
            
            # Try creating a test file
            test_file = os.path.join(self.local_path, '.permission_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                return True
            except:
                return False
                
        except Exception:
            return False
    
    def create_pre_install_backup(self, commit_hash: str) -> Tuple[bool, str, Optional[str]]:
        """Create backup before installation"""
        try:
            backup_name = f"pre_update_{commit_hash[:8]}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            success, message, backup_path = self.backup_manager.create_backup(
                backup_name, 
                backup_type='pre_update',
                description=f"Backup before updating to {commit_hash[:8]}"
            )
            
            if success:
                self.logger.info(f"Pre-install backup created: {backup_path}")
                return True, "Backup created successfully", backup_path
            else:
                return False, f"Backup failed: {message}", None
                
        except Exception as e:
            error_msg = f"Backup creation failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def install_update(self, source_dir: str, backup_path: Optional[str] = None) -> Tuple[bool, str]:
        """Install the update"""
        try:
            self.logger.info("Starting update installation")
            
            # Stop services
            self.stop_services()
            
            # Create staging directory
            staging_dir = os.path.join(self.temp_dir, 'staging')
            shutil.copytree(source_dir, staging_dir)
            
            # Run pre-installation scripts
            self.run_pre_install_scripts(staging_dir)
            
            # Install dependencies
            self.install_dependencies(staging_dir)
            
            # Update application files
            self.update_application_files(staging_dir)
            
            # Run database migrations
            self.run_database_migrations(staging_dir)
            
            # Update configuration files
            self.update_configuration(staging_dir)
            
            # Run post-installation scripts
            self.run_post_install_scripts(staging_dir)
            
            # Start services
            self.start_services()
            
            # Verify installation
            if not self.verify_installation():
                # If verification fails, attempt rollback
                if backup_path:
                    self.logger.error("Installation verification failed, attempting rollback")
                    self.rollback_system.rollback_from_backup(backup_path)
                return False, "Installation verification failed"
            
            self.logger.info("Update installation completed successfully")
            return True, "Installation completed successfully"
            
        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            self.logger.error(error_msg)
            
            # Attempt rollback on failure
            if backup_path:
                try:
                    self.rollback_system.rollback_from_backup(backup_path)
                except Exception as rollback_error:
                    self.logger.error(f"Rollback also failed: {str(rollback_error)}")
            
            return False, error_msg
    
    def stop_services(self):
        """Stop application services"""
        try:
            # Stop your specific services here
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
        """Start application services"""
        try:
            services = ['music-scheduler', 'nginx']  # Adjust as needed
            
            for service in services:
                try:
                    subprocess.run(['sudo', 'systemctl', 'start', service], 
                                 check=True, capture_output=True)
                    self.logger.info(f"Started service: {service}")
                except subprocess.CalledProcessError:
                    self.logger.warning(f"Could not start service: {service}")
                    
        except Exception as e:
            self.logger.error(f"Error starting services: {str(e)}")
    
    def install_dependencies(self, source_dir: str):
        """Install application dependencies"""
        try:
            # Python dependencies
            requirements_file = os.path.join(source_dir, 'requirements.txt')
            if os.path.exists(requirements_file):
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', '-r', requirements_file
                ], check=True, cwd=source_dir)
                self.logger.info("Python dependencies installed")
            
            # Node.js dependencies (if applicable)
            package_json = os.path.join(source_dir, 'package.json')
            if os.path.exists(package_json):
                subprocess.run(['npm', 'install'], check=True, cwd=source_dir)
                self.logger.info("Node.js dependencies installed")
                
        except subprocess.CalledProcessError as e:
            raise Exception(f"Dependency installation failed: {str(e)}")
    
    def update_application_files(self, source_dir: str):
        """Update application files"""
        try:
            # List of files/directories to preserve during update
            preserve_paths = [
                'config/local.json',
                'data/',
                'logs/',
                'uploads/',
                '.env'
            ]
            
            # Create temporary backup of preserved files
            preserved_files = {}
            for preserve_path in preserve_paths:
                full_path = os.path.join(self.local_path, preserve_path)
                if os.path.exists(full_path):
                    temp_path = os.path.join(self.temp_dir, f'preserve_{preserve_path.replace("/", "_")}')
                    if os.path.isdir(full_path):
                        shutil.copytree(full_path, temp_path)
                    else:
                        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                        shutil.copy2(full_path, temp_path)
                    preserved_files[preserve_path] = temp_path
            
            # Remove old application files (excluding preserved ones)
            self.remove_old_files(preserve_paths)
            
            # Copy new files
            self.copy_new_files(source_dir, preserve_paths)
            
            # Restore preserved files
            for preserve_path, temp_path in preserved_files.items():
                full_path = os.path.join(self.local_path, preserve_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                if os.path.isdir(temp_path):
                    if os.path.exists(full_path):
                        shutil.rmtree(full_path)
                    shutil.copytree(temp_path, full_path)
                else:
                    shutil.copy2(temp_path, full_path)
            
            self.logger.info("Application files updated")
            
        except Exception as e:
            raise Exception(f"File update failed: {str(e)}")
    
    def remove_old_files(self, preserve_paths: List[str]):
        """Remove old application files"""
        for item in os.listdir(self.local_path):
            if item in ['.git', '.gitignore'] + preserve_paths:
                continue
            
            item_path = os.path.join(self.local_path, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            except Exception as e:
                self.logger.warning(f"Could not remove {item_path}: {str(e)}")
    
    def copy_new_files(self, source_dir: str, preserve_paths: List[str]):
        """Copy new application files"""
        for item in os.listdir(source_dir):
            if item in ['.git', '.gitignore'] + preserve_paths:
                continue
            
            source_path = os.path.join(source_dir, item)
            dest_path = os.path.join(self.local_path, item)
            
            try:
                if os.path.isdir(source_path):
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(source_path, dest_path)
            except Exception as e:
                self.logger.error(f"Could not copy {item}: {str(e)}")
                raise
    
    def run_database_migrations(self, source_dir: str):
        """Run database migrations"""
        try:
            migrations_dir = os.path.join(source_dir, 'migrations')
            if not os.path.exists(migrations_dir):
                return
            
            # Run migration script if it exists
            migration_script = os.path.join(migrations_dir, 'migrate.py')
            if os.path.exists(migration_script):
                subprocess.run([sys.executable, migration_script], check=True)
                self.logger.info("Database migrations completed")
                
        except subprocess.CalledProcessError as e:
            raise Exception(f"Database migration failed: {str(e)}")
    
    def run_pre_install_scripts(self, source_dir: str):
        """Run pre-installation scripts"""
        script_path = os.path.join(source_dir, 'scripts', 'pre_install.py')
        if os.path.exists(script_path):
            try:
                subprocess.run([sys.executable, script_path], check=True, cwd=source_dir)
                self.logger.info("Pre-install scripts completed")
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Pre-install script failed: {str(e)}")
    
    def run_post_install_scripts(self, source_dir: str):
        """Run post-installation scripts"""
        script_path = os.path.join(source_dir, 'scripts', 'post_install.py')
        if os.path.exists(script_path):
            try:
                subprocess.run([sys.executable, script_path], check=True, cwd=self.local_path)
                self.logger.info("Post-install scripts completed")
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Post-install script failed: {str(e)}")
    
    def update_configuration(self, source_dir: str):
        """Update configuration files"""
        try:
            # Handle configuration updates
            config_updates = os.path.join(source_dir, 'config', 'updates.json')
            if os.path.exists(config_updates):
                with open(config_updates, 'r') as f:
                    updates = json.load(f)
                
                # Apply configuration updates
                for update in updates:
                    self.apply_config_update(update)
                    
        except Exception as e:
            self.logger.warning(f"Configuration update failed: {str(e)}")
    
    def apply_config_update(self, update: Dict):
        """Apply a single configuration update"""
        # Implementation depends on your configuration system
        pass
    
    def verify_installation(self) -> bool:
        """Verify that installation was successful"""
        try:
            # Check if main application file exists
            main_app = os.path.join(self.local_path, 'app.py')  # Adjust as needed
            if not os.path.exists(main_app):
                return False
            
            # Try to import/run basic health check
            # This is application-specific
            
            # Check if services are running
            services = ['music-scheduler']  # Adjust as needed
            for service in services:
                try:
                    result = subprocess.run(['sudo', 'systemctl', 'is-active', service], 
                                          capture_output=True, text=True)
                    if result.stdout.strip() != 'active':
                        self.logger.error(f"Service {service} is not active")
                        return False
                except:
                    pass
            
            return True
            
        except Exception as e:
            self.logger.error(f"Installation verification error: {str(e)}")
            return False
    
    def record_update_history(self, update_info: Dict, status: str, error_msg: Optional[str] = None):
        """Record update in history database"""
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
                    'installation',
                    status,
                    update_info.get('current_version'),
                    update_info.get('target_version'),
                    update_info.get('current_hash'),
                    update_info.get('target_hash'),
                    update_info.get('backup_created', False),
                    update_info.get('backup_path'),
                    error_msg,
                    update_info.get('duration_seconds'),
                    update_info.get('initiated_by', 'system'),
                    update_info.get('started_at'),
                    datetime.datetime.now().isoformat(),
                    json.dumps(update_info.get('metadata', {}))
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to record update history: {str(e)}")
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.info("Temporary files cleaned up")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
    
    def full_update_process(self, update_request: Dict) -> Dict:
        """Complete update process with all security checks"""
        start_time = datetime.datetime.now()
        
        try:
            # Validate update request
            valid, validation_msg = self.validate_update_request(update_request)
            if not valid:
                return {
                    'success': False,
                    'error': f"Validation failed: {validation_msg}",
                    'stage': 'validation'
                }
            
            target_hash = update_request['target_hash']
            
            # Download update
            download_success, download_msg, archive_path = self.download_update(target_hash)
            if not download_success:
                return {
                    'success': False,
                    'error': download_msg,
                    'stage': 'download'
                }
            
            # Extract update
            extract_success, extract_msg, source_dir = self.extract_update(archive_path)
            if not extract_success:
                return {
                    'success': False,
                    'error': extract_msg,
                    'stage': 'extraction'
                }
            
            # Pre-installation checks
            checks_success, checks_msg = self.pre_install_checks(source_dir)
            if not checks_success:
                return {
                    'success': False,
                    'error': checks_msg,
                    'stage': 'pre_checks'
                }
            
            # Create backup
            backup_success, backup_msg, backup_path = self.create_pre_install_backup(target_hash)
            if not backup_success:
                return {
                    'success': False,
                    'error': backup_msg,
                    'stage': 'backup'
                }
            
            # Install update
            install_success, install_msg = self.install_update(source_dir, backup_path)
            if not install_success:
                return {
                    'success': False,
                    'error': install_msg,
                    'stage': 'installation',
                    'backup_path': backup_path
                }
            
            # Record success
            duration = (datetime.datetime.now() - start_time).total_seconds()
            self.record_update_history({
                'current_hash': self.get_current_commit_hash(),
                'target_hash': target_hash,
                'backup_created': True,
                'backup_path': backup_path,
                'duration_seconds': duration,
                'started_at': start_time.isoformat(),
                'initiated_by': update_request.get('initiated_by', 'system')
            }, 'success')
            
            return {
                'success': True,
                'message': 'Update completed successfully',
                'backup_path': backup_path,
                'duration_seconds': duration
            }
            
        except Exception as e:
            error_msg = f"Unexpected error during update: {str(e)}"
            self.logger.error(error_msg)
            
            # Record failure
            duration = (datetime.datetime.now() - start_time).total_seconds()
            self.record_update_history({
                'target_hash': update_request.get('target_hash'),
                'duration_seconds': duration,
                'started_at': start_time.isoformat(),
                'initiated_by': update_request.get('initiated_by', 'system')
            }, 'failed', error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'stage': 'unexpected_error'
            }
            
        finally:
            # Always cleanup temp files
            self.cleanup_temp_files()

if __name__ == "__main__":
    # Example usage
    installer = SecureUpdateInstaller()
    
    test_request = {
        'target_hash': 'abcdef123456',  # Replace with actual hash
        'branch': 'main',
        'initiated_by': 'admin'
    }
    
    result = installer.full_update_process(test_request)
    print(json.dumps(result, indent=2))
