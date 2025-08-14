/**
 * Music Scheduler Update Management JavaScript
 * Handles all frontend interactions for the update system
 */

class UpdateManager {
    constructor() {
        this.apiBaseUrl = '/api/updates'; // Adjust based on your API structure
        this.currentStatus = 'checking';
        this.updateCheckInterval = null;
        this.progressInterval = null;
        
        this.init();
    }
    
    init() {
        this.bindEventListeners();
        this.loadInitialData();
        this.startPeriodicChecks();
    }
    
    bindEventListeners() {
        // Main action buttons
        document.getElementById('check-updates-btn')?.addEventListener('click', () => this.checkForUpdates());
        document.getElementById('view-changelog-btn')?.addEventListener('click', () => this.showChangelog());
        document.getElementById('download-update-btn')?.addEventListener('click', () => this.downloadUpdate());
        document.getElementById('install-update-btn')?.addEventListener('click', () => this.installUpdate());
        
        // Modal controls
        document.getElementById('changelog-close')?.addEventListener('click', () => this.closeModal('changelog-modal'));
        document.getElementById('changelog-cancel')?.addEventListener('click', () => this.closeModal('changelog-modal'));
        document.getElementById('proceed-download')?.addEventListener('click', () => this.proceedWithDownload());
        
        // Backup actions
        document.getElementById('create-backup-btn')?.addEventListener('click', () => this.createBackup());
        document.getElementById('view-backups-btn')?.addEventListener('click', () => this.viewBackups());
        
        // Settings
        document.getElementById('save-settings-btn')?.addEventListener('click', () => this.saveSettings());
        document.getElementById('refresh-history-btn')?.addEventListener('click', () => this.refreshHistory());
        
        // History filter
        document.getElementById('history-filter')?.addEventListener('change', (e) => this.filterHistory(e.target.value));
        
        // Confirmation modal
        document.getElementById('confirm-cancel')?.addEventListener('click', () => this.closeModal('confirmation-modal'));
        document.getElementById('confirm-ok')?.addEventListener('click', () => this.confirmAction());
        
        // Auto-backup toggle
        document.getElementById('auto-backup-toggle')?.addEventListener('change', (e) => this.toggleAutoBackup(e.target.checked));
    }
    
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadSystemInfo(),
                this.loadNotifications(),
                this.loadUpdateHistory(),
                this.loadSettings()
            ]);
            
            // Initial update check
            await this.checkForUpdates();
            
        } catch (error) {
            this.showError('Failed to load initial data: ' + error.message);
        }
    }
    
    async loadSystemInfo() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/system-info`);
            const data = await response.json();
            
            document.getElementById('current-version').textContent = data.current_version?.substring(0, 8) || 'Unknown';
            document.getElementById('last-updated').textContent = data.last_updated || 'Never';
            document.getElementById('update-branch').textContent = data.branch || 'main';
            document.getElementById('last-check').textContent = data.last_check || 'Never';
            document.getElementById('last-backup').textContent = data.last_backup || 'None';
            
        } catch (error) {
            console.error('Error loading system info:', error);
        }
    }
    
    async loadNotifications() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/notifications`);
            const notifications = await response.json();
            
            const notificationsContainer = document.getElementById('update-notifications');
            const notificationsList = document.getElementById('notifications-list');
            
            if (notifications.length > 0) {
                notificationsContainer.style.display = 'block';
                notificationsList.innerHTML = notifications.map(notification => 
                    this.createNotificationElement(notification)
                ).join('');
            } else {
                notificationsContainer.style.display = 'none';
            }
            
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }
    
    createNotificationElement(notification) {
        const severityClass = `notification-${notification.severity}`;
        const timeAgo = this.getTimeAgo(notification.created_at);
        
        return `
            <div class="notification ${severityClass}" data-id="${notification.id}">
                <div class="notification-header">
                    <h4>${notification.title}</h4>
                    <span class="notification-time">${timeAgo}</span>
                    <button class="notification-close" onclick="updateManager.dismissNotification(${notification.id})">×</button>
                </div>
                <div class="notification-body">
                    <p>${notification.message}</p>
                    ${notification.requires_action ? '<div class="notification-actions"></div>' : ''}
                </div>
            </div>
        `;
    }
    
    async checkForUpdates(showLoading = true) {
        if (showLoading) {
            this.setStatus('checking', 'Checking for updates...');
            document.getElementById('check-updates-btn').disabled = true;
        }
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/check`, { method: 'POST' });
            const result = await response.json();
            
            this.handleUpdateCheckResult(result);
            
        } catch (error) {
            this.setStatus('error', 'Failed to check for updates');
            this.showError('Update check failed: ' + error.message);
        } finally {
            document.getElementById('check-updates-btn').disabled = false;
        }
    }
    
    handleUpdateCheckResult(result) {
        const availableUpdates = document.getElementById('available-updates');
        
        switch (result.status) {
            case 'up_to_date':
                this.setStatus('up-to-date', 'System is up to date');
                availableUpdates.style.display = 'none';
                break;
                
            case 'updates_available':
                this.setStatus('updates-available', `${result.commit_count} updates available`);
                this.showAvailableUpdates(result);
                availableUpdates.style.display = 'block';
                break;
                
            case 'error':
                this.setStatus('error', result.message);
                availableUpdates.style.display = 'none';
                break;
                
            default:
                this.setStatus('unknown', 'Unknown status');
        }
        
        // Update last check time
        document.getElementById('last-check').textContent = 'Just now';
    }
    
    showAvailableUpdates(updateInfo) {
        document.getElementById('current-hash').textContent = updateInfo.current_version.hash.substring(0, 8);
        document.getElementById('available-hash').textContent = updateInfo.remote_version.hash.substring(0, 8);
        document.getElementById('commit-count').textContent = updateInfo.commit_count;
        
        const latestCommit = document.getElementById('latest-commit');
        latestCommit.innerHTML = `
            <p><strong>${updateInfo.remote_version.message}</strong></p>
            <p><small>By ${updateInfo.remote_version.author} on ${new Date(updateInfo.remote_version.date).toLocaleDateString()}</small></p>
        `;
        
        // Store update info for later use
        this.currentUpdateInfo = updateInfo;
    }
    
    async showChangelog() {
        if (!this.currentUpdateInfo) {
            this.showError('No update information available');
            return;
        }
        
        const changelogContent = document.getElementById('changelog-content');
        changelogContent.innerHTML = '<div class="loading">Loading changelog...</div>';
        
        this.showModal('changelog-modal');
        
        try {
            const commits = this.currentUpdateInfo.new_commits || [];
            
            changelogContent.innerHTML = commits.map((commit, index) => `
                <div class="commit-item">
                    <div class="commit-header">
                        <span class="commit-number">#${index + 1}</span>
                        <span class="commit-hash">${commit.sha?.substring(0, 8) || 'N/A'}</span>
                        <span class="commit-date">${new Date(commit.commit.author.date).toLocaleDateString()}</span>
                    </div>
                    <div class="commit-message">${commit.commit.message}</div>
                    <div class="commit-author">By ${commit.commit.author.name}</div>
                </div>
            `).join('');
            
        } catch (error) {
            changelogContent.innerHTML = '<div class="error">Failed to load changelog</div>';
        }
    }
    
    async downloadUpdate() {
        if (!this.currentUpdateInfo) {
            this.showError('No update information available');
            return;
        }
        
        const confirmed = await this.showConfirmation(
            'Download Update',
            'This will download the latest update files. Continue?'
        );
        
        if (!confirmed) return;
        
        this.showProgress('Downloading update...', 0);
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    version: this.currentUpdateInfo.remote_version.hash 
                })
            });
            
            if (!response.ok) throw new Error('Download failed');
            
            // Simulate progress for demo
            await this.simulateProgress(5000);
            
            this.hideProgress();
            document.getElementById('install-update-btn').disabled = false;
            this.showSuccess('Update downloaded successfully');
            
        } catch (error) {
            this.hideProgress();
            this.showError('Download failed: ' + error.message);
        }
    }
    
    async installUpdate() {
        const confirmed = await this.showConfirmation(
            'Install Update',
            'This will install the downloaded update. A backup will be created automatically. The system may be briefly unavailable. Continue?'
        );
        
        if (!confirmed) return;
        
        this.showProgress('Installing update...', 0);
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/install`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    version: this.currentUpdateInfo.remote_version.hash,
                    create_backup: document.getElementById('auto-backup-toggle').checked
                })
            });
            
            if (!response.ok) throw new Error('Installation failed');
            
            // Monitor installation progress
            await this.monitorInstallation();
            
        } catch (error) {
            this.hideProgress();
            this.showError('Installation failed: ' + error.message);
        }
    }
    
    async monitorInstallation() {
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const progressLog = document.getElementById('progress-log');
        
        const steps = [
            'Creating backup...',
            'Downloading files...',
            'Validating update...',
            'Installing update...',
            'Updating database...',
            'Restarting services...',
            'Verifying installation...'
        ];
        
        for (let i = 0; i < steps.length; i++) {
            progressText.textContent = steps[i];
            progressFill.style.width = `${((i + 1) / steps.length) * 100}%`;
            
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';
            logEntry.textContent = `✓ ${steps[i]}`;
            progressLog.appendChild(logEntry);
            
            // Simulate step duration
            await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 1000));
        }
        
        this.hideProgress();
        this.showSuccess('Update installed successfully! System is now up to date.');
        
        // Refresh data
        setTimeout(() => {
            this.loadInitialData();
        }, 2000);
    }
    
    async loadUpdateHistory() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/history`);
            const history = await response.json();
            
            const historyList = document.getElementById('update-history-list');
            
            if (history.length === 0) {
                historyList.innerHTML = '<div class="no-data">No update history available</div>';
                return;
            }
            
            historyList.innerHTML = history.map(item => this.createHistoryItem(item)).join('');
            
        } catch (error) {
            console.error('Error loading update history:', error);
            document.getElementById('update-history-list').innerHTML = '<div class="error">Failed to load history</div>';
        }
    }
    
    createHistoryItem(item) {
        const statusClass = `status-${item.status}`;
        const statusIcon = this.getStatusIcon(item.status);
        const duration = item.duration_seconds ? `${item.duration_seconds}s` : 'N/A';
        
        return `
            <div class="history-item ${statusClass}" data-type="${item.update_type}">
                <div class="history-icon">${statusIcon}</div>
                <div class="history-content">
                    <div class="history-header">
                        <span class="history-type">${item.update_type.replace('_', ' ')}</span>
                        <span class="history-date">${new Date(item.started_at).toLocaleString()}</span>
                    </div>
                    <div class="history-details">
                        <span class="history-version">${item.version_from?.substring(0, 8) || 'N/A'} → ${item.version_to?.substring(0, 8) || 'N/A'}</span>
                        <span class="history-duration">${duration}</span>
                        <span class="history-user">${item.initiated_by}</span>
                    </div>
                    ${item.error_message ? `<div class="history-error">${item.error_message}</div>` : ''}
                </div>
                ${item.rollback_available && item.status === 'success' ? 
                    `<button class="btn btn-small rollback-btn" onclick="updateManager.rollbackToVersion('${item.version_to}')">Rollback</button>` : ''
                }
            </div>
        `;
    }
    
    getStatusIcon(status) {
        const icons = {
            'success': '✅',
            'failed': '❌',
            'in_progress': '⏳',
            'cancelled': '⚠️'
        };
        return icons[status] || '❓';
    }
    
    // Utility methods
    setStatus(status, message) {
        this.currentStatus = status;
        const indicator = document.getElementById('status-indicator');
        const text = document.getElementById('status-text');
        
        indicator.className = `status-indicator status-${status}`;
        text.textContent = message;
    }
    
    showModal(modalId) {
        document.getElementById(modalId).style.display = 'flex';
    }
    
    closeModal(modalId) {
        document.getElementById(modalId).style.display = 'none';
    }
    
    showProgress(message, progress) {
        const progressContainer = document.getElementById('update-progress');
        const progressText = document.getElementById('progress-text');
        const progressFill = document.getElementById('progress-fill');
        
        progressContainer.style.display = 'block';
        progressText.textContent = message;
        progressFill.style.width = `${progress}%`;
    }
    
    hideProgress() {
        document.getElementById('update-progress').style.display = 'none';
        document.getElementById('progress-log').innerHTML = '';
    }
    
    async simulateProgress(duration) {
        const steps = 20;
        const stepDuration = duration / steps;
        
        for (let i = 0; i <= steps; i++) {
            const progress = (i / steps) * 100;
            document.getElementById('progress-fill').style.width = `${progress}%`;
            await new Promise(resolve => setTimeout(resolve, stepDuration));
        }
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('toast-show');
        }, 100);
        
        setTimeout(() => {
            toast.classList.remove('toast-show');
            setTimeout(() => container.removeChild(toast), 300);
        }, 3000);
    }
    
    showSuccess(message) {
        this.showToast(message, 'success');
    }
    
    showError(message) {
        this.showToast(message, 'error');
    }
    
    showWarning(message) {
        this.showToast(message, 'warning');
    }
    
    async showConfirmation(title, message) {
        return new Promise((resolve) => {
            document.getElementById('confirm-title').textContent = title;
            document.getElementById('confirm-message').textContent = message;
            
            this.confirmationCallback = resolve;
            this.showModal('confirmation-modal');
        });
    }
    
    confirmAction() {
        if (this.confirmationCallback) {
            this.confirmationCallback(true);
            this.confirmationCallback = null;
        }
        this.closeModal('confirmation-modal');
    }
    
    getTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffDays > 0) return `${diffDays} days ago`;
        if (diffHours > 0) return `${diffHours} hours ago`;
        return 'Just now';
    }
    
    // Event handlers
    async dismissNotification(notificationId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/notifications/${notificationId}/dismiss`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const notification = document.querySelector(`[data-id="${notificationId}"]`);
                if (notification) {
                    notification.remove();
                }
            }
        } catch (error) {
            this.showError('Failed to dismiss notification');
        }
    }
    
    async createBackup() {
        const confirmed = await this.showConfirmation(
            'Create Backup',
            'Create a backup of the current system state?'
        );
        
        if (!confirmed) return;
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/backup`, { method: 'POST' });
            if (response.ok) {
                this.showSuccess('Backup created successfully');
                this.loadSystemInfo(); // Refresh backup info
            }
        } catch (error) {
            this.showError('Failed to create backup: ' + error.message);
        }
    }
    
    viewBackups() {
        // Navigate to backups page or show backup modal
        window.location.href = '#backups';
    }
    
    async saveSettings() {
        const settings = {
            email_notifications: document.getElementById('email-notifications').checked,
            auto_check: document.getElementById('auto-check').checked,
            notification_frequency: document.getElementById('notification-frequency').value,
            backup_retention: parseInt(document.getElementById('backup-retention').value)
        };
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/settings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });
            
            if (response.ok) {
                this.showSuccess('Settings saved successfully');
            }
        } catch (error) {
            this.showError('Failed to save settings: ' + error.message);
        }
    }
    
    async loadSettings() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/settings`);
            const settings = await response.json();
            
            document.getElementById('email-notifications').checked = settings.email_notifications;
            document.getElementById('auto-check').checked = settings.auto_check;
            document.getElementById('notification-frequency').value = settings.notification_frequency;
            document.getElementById('backup-retention').value = settings.backup_retention;
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }
    
    refreshHistory() {
        this.loadUpdateHistory();
    }
    
    filterHistory(type) {
        const historyItems = document.querySelectorAll('.history-item');
        
        historyItems.forEach(item => {
            if (type === 'all' || item.dataset.type === type || 
                (type === 'successful' && item.classList.contains('status-success')) ||
                (type === 'failed' && item.classList.contains('status-failed'))) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }
    
    async rollbackToVersion(version) {
        const confirmed = await this.showConfirmation(
            'Rollback System',
            `Are you sure you want to rollback to version ${version.substring(0, 8)}? This will revert all changes made after this version.`
        );
        
        if (!confirmed) return;
        
        try {
            this.showProgress('Rolling back system...', 0);
            
            const response = await fetch(`${this.apiBaseUrl}/rollback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ version })
            });
            
            if (response.ok) {
                await this.simulateProgress(3000);
                this.hideProgress();
                this.showSuccess('System rolled back successfully');
                setTimeout(() => this.loadInitialData(), 2000);
            }
        } catch (error) {
            this.hideProgress();
            this.showError('Rollback failed: ' + error.message);
        }
    }
    
    toggleAutoBackup(enabled) {
        // Update backend setting
        this.saveSettings();
        this.showSuccess(enabled ? 'Auto-backup enabled' : 'Auto-backup disabled');
    }
    
    proceedWithDownload() {
        this.closeModal('changelog-modal');
        this.downloadUpdate();
    }
    
    startPeriodicChecks() {
        // Check for updates every hour
        this.updateCheckInterval = setInterval(() => {
            this.checkForUpdates(false);
        }, 60 * 60 * 1000);
    }
    
    stopPeriodicChecks() {
        if (this.updateCheckInterval) {
            clearInterval(this.updateCheckInterval);
        }
    }
}

// Initialize update manager when page loads
let updateManager;
document.addEventListener('DOMContentLoaded', () => {
    updateManager = new UpdateManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (updateManager) {
        updateManager.stopPeriodicChecks();
    }
});
