# 🎵 Music Scheduler

A comprehensive Flask-based music lesson scheduling application with MySQL database integration. Features a modern tabbed admin interface for managing users, students, lessons, and system configuration.

## ✨ Features

### 📊 Admin Dashboard
- **Tabbed Interface**: Modern admin dashboard with three main tabs
  - **Dashboard**: User management, email service status, student management
  - **Backup & Restore**: Database backup creation, automatic backups, restore functionality
  - **Settings**: Email configuration (SMTP), system settings

### 👥 User Management
- Admin and Instructor user roles
- Student registration and management
- Secure password hashing with bcrypt
- Session-based authentication

### 📅 Scheduling System  
- Lesson scheduling and management
- Instructor availability tracking
- Calendar integration
- Time-off management for instructors

### 📧 Email Notifications
- Configurable SMTP settings
- Email notifications for lessons
- Service status monitoring
- Email template management

### 💾 Backup System
- Manual database backup creation
- Automated daily backups with systemd timers
- Backup upload and restore functionality
- Backup history and management

### 🔒 Security Features
- Session-based authentication
- Secure password storage
- Environment variable configuration
- Dedicated system user for deployment

## 🛠 Tech Stack

- **Backend**: Flask 2.3.3 with Python 3
- **Database**: MySQL with mysql-connector-python
- **Frontend**: Server-side rendered Jinja2 templates
- **Authentication**: Flask-Bcrypt + Flask-Session
- **Deployment**: Systemd service + Nginx reverse proxy
- **Backup**: Custom backup scripts with systemd timers

## 📋 Prerequisites

- **Operating System**: Ubuntu/Debian or RHEL/CentOS
- **Python**: Python 3.7+ with pip and venv
- **Database**: MySQL Server 5.7+
- **Web Server**: Nginx (configured automatically)
- **Permissions**: Sudo access for installation

## 🚀 Quick Install

### One-Click Installation
```bash
git clone <repository-url>
cd music-scheduler
chmod +x install.sh
./install.sh
```

The installation script will:
1. Install system packages (Python3, MySQL, Nginx)
2. Set up MySQL database with random credentials
3. Create Python virtual environment and install dependencies
4. Configure systemd service for the Flask app
5. Set up Nginx reverse proxy
6. Configure automatic backup system
7. Create admin user with random password

### Manual Installation

#### 1. Clone Repository
```bash
git clone <repository-url>
cd music-scheduler
```

#### 2. Install System Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv mysql-server nginx

# RHEL/CentOS
sudo yum install python3 python3-pip mysql-server nginx
```

#### 3. Set Up Database
```bash
sudo systemctl start mysql
sudo systemctl enable mysql
sudo mysql -e "CREATE DATABASE music_scheduler;"
sudo mysql -e "CREATE USER 'music_user'@'localhost' IDENTIFIED BY 'your_password';"
sudo mysql -e "GRANT ALL PRIVILEGES ON music_scheduler.* TO 'music_user'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"
```

#### 4. Configure Application
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env with your database credentials
```

#### 5. Initialize Database
```bash
python3 -c "
from app import app, get_db_connection
import mysql.connector

# Run database initialization
# Add your initialization code here
"
```

#### 6. Start Application
```bash
# Development mode
python3 app.py

# Production mode (after setting up systemd service)
sudo systemctl start music-scheduler
```

## 🎯 Usage

### Access the Application
- **Web Interface**: http://localhost (via Nginx)
- **Direct Access**: http://localhost:5000 (Flask development server)

### Default Admin Credentials
After installation, check the installer output for:
- **Username**: admin
- **Password**: [randomly generated - shown in installer output]

### Admin Dashboard Features

#### 📊 Dashboard Tab
- **Email Service Status**: Monitor and toggle email notifications
- **Add New User**: Create admin or instructor accounts
- **Add New Student**: Register new students with contact information

#### 💾 Backup & Restore Tab  
- **Create Backup**: Generate database backups manually
- **Automatic Backups**: Set up daily automated backups (2:00 AM)
- **Restore Database**: Upload and restore from backup files
- **Available Backups**: Browse, download, and restore from existing backups

#### ⚙️ Settings Tab
- **Email Service Control**: Enable/disable email notifications system-wide
- **Email Configuration**: Configure SMTP settings for notifications
  - SMTP Server and Port
  - Authentication credentials  
  - From email address

### Instructor Features
- **Dashboard**: View assigned students and upcoming lessons
- **Availability**: Set weekly availability and time-off periods
- **Lessons**: Manage lesson schedules and add notes
- **Students**: View student contact information and history

## 🔧 Configuration

### Environment Variables (.env)
```env
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
DB_HOST=localhost
DB_USER=music_user
DB_PASSWORD=your_db_password
DB_NAME=music_scheduler
SESSION_TYPE=filesystem
SESSION_FILE_DIR=./sessions
```

### Database Configuration
The application connects to MySQL using credentials from environment variables. The database schema is automatically initialized on first run.

### Email Configuration
Configure SMTP settings through the Settings tab in the admin dashboard:
- Supports Gmail, Outlook, and other SMTP providers
- Requires app passwords for Gmail
- Email notifications can be enabled/disabled system-wide

## 🛠 Service Management

### Systemd Service (Production)
```bash
# Service status
sudo systemctl status music-scheduler

# Start/stop/restart
sudo systemctl start music-scheduler
sudo systemctl stop music-scheduler
sudo systemctl restart music-scheduler

# View logs
sudo journalctl -u music-scheduler -f
```

### Nginx Configuration
The installer sets up Nginx as a reverse proxy:
```nginx
server {
    listen 80;
    server_name localhost;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /static {
        alias /opt/music-scheduler/static;
        expires 30d;
    }
}
```

## 💾 Backup System

### Automatic Backups
- **Schedule**: Daily at 2:00 AM via systemd timer
- **Location**: `/opt/music-scheduler/database_backups/`
- **Format**: Compressed SQL dumps (`*.sql.gz`)
- **Retention**: Configurable (default: 30 days)

### Manual Backup
```bash
# Create backup via web interface (Backup & Restore tab)
# Or via command line:
cd /opt/music-scheduler
./backup/backup.sh
```

### Restore Process
1. Access **Backup & Restore** tab in admin dashboard
2. **Upload** backup file or select from available backups
3. Click **Restore Database** (⚠️ This replaces all current data)
4. Restart the application service

## 📁 Project Structure

```
music-scheduler/
├── app.py                  # Main Flask application
├── email_service.py        # Email service functionality
├── requirements.txt        # Python dependencies
├── install.sh             # One-click installation script
├── .env                   # Environment configuration
├── README.md              # This file
├── templates/             # Flask Jinja2 templates
│   ├── base.html         # Base template
│   ├── dashboard.html    # Admin dashboard (tabbed interface)
│   ├── login.html        # Login page
│   ├── instructor_*.html # Instructor templates
│   └── admin_*.html      # Admin templates
├── static/               # Static assets
│   └── favicon.ico       # Application icon
├── scripts/              # System scripts
│   ├── db-init.sql      # Database initialization
│   ├── backup_db.sh     # Database backup script
│   ├── restore_db.sh    # Database restore script
│   └── music-scheduler.service # Systemd service file
├── backup/               # Backup system
│   └── backup.sh         # Main backup script
├── database_backups/     # Database backup storage
├── uploaded_backups/     # User-uploaded backup files
├── logs/                 # Application logs
├── sessions/             # Flask session storage
├── docs/                 # Additional documentation
└── venv/                 # Python virtual environment
```

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Error
```bash
# Check MySQL service
sudo systemctl status mysql

# Check credentials in .env file
cat .env | grep DB_

# Test database connection
mysql -u music_user -p music_scheduler
```

#### Permission Errors
```bash
# Fix file permissions
sudo chown -R music-scheduler:music-scheduler /opt/music-scheduler
sudo chmod +x /opt/music-scheduler/install.sh
```

#### Service Won't Start
```bash
# Check service logs
sudo journalctl -u music-scheduler -f

# Check Flask app directly
cd /opt/music-scheduler
source venv/bin/activate
python3 app.py
```

#### Email Not Working
1. Check SMTP settings in Settings tab
2. Verify email service is enabled (toggle in Dashboard/Settings)
3. Check firewall settings for SMTP ports
4. For Gmail: Use app passwords, not regular passwords

### Log Files
- **Application logs**: `/opt/music-scheduler/logs/`
- **System service logs**: `sudo journalctl -u music-scheduler`
- **Nginx logs**: `/var/log/nginx/error.log`
- **MySQL logs**: `/var/log/mysql/error.log`

## 🔒 Security Considerations

### Production Deployment
- Change default admin password immediately
- Use strong, unique passwords for database users
- Configure firewall to restrict database access
- Enable HTTPS with SSL certificates
- Regular security updates for system packages
- Monitor access logs for suspicious activity

### Database Security
- Database user has minimal required privileges
- Passwords stored with bcrypt hashing
- Session data stored securely in filesystem
- Environment variables for sensitive configuration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review application logs for error details

---

**Built with Flask 🚀 | Designed for Music Schools 🎵**
