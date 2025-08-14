#!/usr/bin/env python3
"""
GitHub Update Checker for Music Scheduler
Checks GitHub repository for new commits and updates
"""

import requests
import json
import datetime
import subprocess
import os
import logging
from pathlib import Path

class GitHubUpdateChecker:
    def __init__(self, config_path="/home/ubuntu/music_scheduler_update_system/config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.github_token = self.config['github']['token']
        self.repo_api_url = self.config['github']['repository_api_url']
        self.local_path = self.config['system']['local_path']
        
        # Setup logging
        log_dir = Path(self.config['system']['log_path'])
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / 'update_checker.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def get_headers(self):
        """Get GitHub API headers with authentication"""
        return {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'MusicScheduler-AutoUpdater'
        }
    
    def get_remote_version(self):
        """Get the latest commit hash from remote repository"""
        try:
            url = f"{self.repo_api_url}/commits"
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            
            commits = response.json()
            if commits:
                latest_commit = commits[0]
                return {
                    'hash': latest_commit['sha'],
                    'message': latest_commit['commit']['message'],
                    'date': latest_commit['commit']['author']['date'],
                    'author': latest_commit['commit']['author']['name']
                }
            return None
        except Exception as e:
            self.logger.error(f"Error getting remote version: {str(e)}")
            return None
    
    def get_local_version(self):
        """Get the current local commit hash"""
        try:
            if not os.path.exists(self.local_path):
                self.logger.warning("Local repository path does not exist")
                return None
            
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.local_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {
                    'hash': result.stdout.strip(),
                    'date': self.get_local_commit_date()
                }
            else:
                self.logger.error(f"Error getting local version: {result.stderr}")
                return None
        except Exception as e:
            self.logger.error(f"Error getting local version: {str(e)}")
            return None
    
    def get_local_commit_date(self):
        """Get the date of the current local commit"""
        try:
            result = subprocess.run(
                ['git', 'show', '-s', '--format=%ci', 'HEAD'],
                cwd=self.local_path,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None
    
    def get_commits_between(self, local_hash, remote_hash):
        """Get list of commits between local and remote versions"""
        try:
            url = f"{self.repo_api_url}/compare/{local_hash}...{remote_hash}"
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            
            comparison = response.json()
            return comparison.get('commits', [])
        except Exception as e:
            self.logger.error(f"Error getting commit comparison: {str(e)}")
            return []
    
    def check_for_updates(self):
        """Main method to check for updates"""
        self.logger.info("Starting update check...")
        
        remote_version = self.get_remote_version()
        local_version = self.get_local_version()
        
        if not remote_version:
            self.logger.error("Could not get remote version")
            return {
                'status': 'error',
                'message': 'Could not connect to GitHub repository'
            }
        
        if not local_version:
            self.logger.warning("No local repository found - first time setup needed")
            return {
                'status': 'setup_needed',
                'remote_version': remote_version,
                'message': 'Local repository not found - initial setup required'
            }
        
        # Compare versions
        if remote_version['hash'] == local_version['hash']:
            self.logger.info("System is up to date")
            return {
                'status': 'up_to_date',
                'current_version': local_version,
                'message': 'No updates available'
            }
        
        # Get commits between versions
        commits = self.get_commits_between(local_version['hash'], remote_version['hash'])
        
        self.logger.info(f"Updates available: {len(commits)} new commits")
        
        return {
            'status': 'updates_available',
            'current_version': local_version,
            'remote_version': remote_version,
            'new_commits': commits,
            'commit_count': len(commits),
            'message': f'{len(commits)} new commits available for update'
        }
    
    def get_release_info(self):
        """Get latest release information if available"""
        try:
            url = f"{self.repo_api_url}/releases/latest"
            response = requests.get(url, headers=self.get_headers())
            
            if response.status_code == 200:
                release = response.json()
                return {
                    'tag_name': release['tag_name'],
                    'name': release['name'],
                    'body': release['body'],
                    'published_at': release['published_at'],
                    'assets': release.get('assets', [])
                }
        except Exception as e:
            self.logger.debug(f"No release info available: {str(e)}")
        
        return None

if __name__ == "__main__":
    checker = GitHubUpdateChecker()
    result = checker.check_for_updates()
    print(json.dumps(result, indent=2))
