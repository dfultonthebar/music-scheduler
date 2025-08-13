
# Music Scheduler System

A comprehensive Flask-based web application for managing music events, venues, artists, and bookings. This system provides an intuitive interface for scheduling concerts, managing venues, tracking artists, and handling customer bookings.

## ✨ Features

- **Event Management**: Create, edit, and manage music events with detailed scheduling
- **Venue Management**: Maintain venue information, capacity, and contact details
- **Artist Management**: Track artist information, genres, and contact details
- **Booking System**: Handle customer bookings with payment tracking
- **User Management**: Admin and user roles with secure authentication
- **Backup System**: Automated daily backups with configurable retention
- **Production Ready**: Systemd service with Nginx reverse proxy

## 🚀 One-Click Installation

The easiest way to install the Music Scheduler System is using our automated installer:

```bash
curl -fsSL https://raw.githubusercontent.com/dfultonthebar/music-scheduler/main/install.sh | bash
```

Or clone and run manually:

```bash
git clone https://github.com/dfultonthebar/music-scheduler.git
cd music-scheduler
chmod +x install.sh
./install.sh
```

### What the installer does:

1. **System Dependencies**: Installs Python 3, MySQL, Nginx, and other required packages
2. **Database Setup**: Creates MySQL database, user, and initializes schema
3. **Application Setup**: Configures Python virtual environment and installs dependencies
4. **Service Configuration**: Sets up systemd service for automatic startup
5. **Web Server**: Configures Nginx reverse proxy for production deployment
6. **Backup System**: Sets up automated daily backups with systemd timers
7. **Admin Account**: Creates initial admin user with secure credentials

## 📋 System Requirements

- **Operating System**: Ubuntu 18.04+, Debian 9+, CentOS 7+, or RHEL 7+
- **Memory**: 1GB RAM minimum, 2GB recommended
- **Storage**: 5GB available space
- **Network**: Internet connection for package downloads

## 🔧 Manual Installation

If you prefer to install manually or need custom configuration:

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv mysql-server nginx git

# CentOS/RHEL
sudo yum install python3 python3-pip mysql-server nginx git
```

### Database Setup

```bash
# Start MySQL service
sudo systemctl start mysql
sudo systemctl enable mysql

# Create database and user
sudo mysql
```

```sql
CREATE DATABASE music_scheduler;
CREATE USER 'music_user'@'localhost' IDENTIFIED BY 'secure_password_here';
GRANT ALL PRIVILEGES ON music_scheduler.* TO 'music_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Application Setup

```bash
# Clone repository
git clone https://github.com/dfultonthebar/music-scheduler.git
cd music-scheduler

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Initialize database
mysql music_scheduler < scripts/db-init.sql

# Run application
python app.py
```

## 🖥️ Usage

After installation, access the system at:

- **Web Interface**: `http://your-server-ip` (if using Nginx)
- **Direct Access**: `http://your-server-ip:5000` (Flask development server)

### Default Admin Credentials

The installer creates an admin account with randomly generated credentials. Check the installer output for the login details, or check the systemd logs:

```bash
sudo journalctl -u music-scheduler --since="1 hour ago" | grep -i admin
```

## 🛠️ Configuration

### Environment Variables

Edit `/opt/music-scheduler/.env` for production or `.env` for development:

```bash
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
DATABASE_URL=mysql://user:password@localhost/music_scheduler
MYSQL_HOST=localhost
MYSQL_DATABASE=music_scheduler
MYSQL_USERNAME=music_user
MYSQL_PASSWORD=your-password-here
```

### Service Management

```bash
# Check service status
sudo systemctl status music-scheduler

# Start/Stop/Restart service
sudo systemctl start music-scheduler
sudo systemctl stop music-scheduler
sudo systemctl restart music-scheduler

# View logs
sudo journalctl -u music-scheduler -f
```

### Backup Management

```bash
# Check backup status
sudo systemctl status music-scheduler-backup.timer

# Run manual backup
sudo /opt/music-scheduler/backup/backup.sh

# View backup logs
sudo journalctl -u music-scheduler-backup

# List current backups
ls -la /var/backups/music-scheduler/
```

## 📊 Database Schema

The system uses the following main tables:

- **users**: User accounts and authentication
- **venues**: Venue information and capacity
- **artists**: Artist profiles and contact details
- **events**: Event scheduling and details
- **bookings**: Customer bookings and payments
- **settings**: System configuration

## 🔒 Security Features

- **Password Hashing**: Uses bcrypt for secure password storage
- **Session Management**: Secure Flask session handling
- **SQL Injection Protection**: Parameterized queries throughout
- **Service Isolation**: Runs as dedicated system user
- **File Permissions**: Restricted access to configuration files
- **Backup Encryption**: Compressed backup files with restricted access

## 🔧 Troubleshooting

### Common Issues

1. **Service won't start**:
   ```bash
   sudo systemctl status music-scheduler
   sudo journalctl -u music-scheduler --no-pager
   ```

2. **Database connection errors**:
   - Check MySQL service: `sudo systemctl status mysql`
   - Verify credentials in `.env` file
   - Test database connection: `mysql -u music_user -p music_scheduler`

3. **Permission errors**:
   ```bash
   sudo chown -R music-scheduler:music-scheduler /opt/music-scheduler
   ```

4. **Port conflicts**:
   - Check if port 5000 is in use: `sudo netstat -tlnp | grep :5000`
   - Modify port in `app.py` if needed

### Log Files

- **Application logs**: `sudo journalctl -u music-scheduler`
- **Nginx logs**: `/var/log/nginx/access.log` and `/var/log/nginx/error.log`
- **MySQL logs**: `/var/log/mysql/error.log`
- **Backup logs**: `sudo journalctl -u music-scheduler-backup`

## 📚 API Documentation

The system provides a RESTful API for integration with other systems. Key endpoints include:

- `GET /api/events` - List all events
- `POST /api/events` - Create new event
- `GET /api/venues` - List all venues
- `POST /api/bookings` - Create new booking

(Full API documentation available in the application interface)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:

- **Issues**: Create a GitHub issue
- **Documentation**: Check this README and inline documentation
- **Logs**: Always include relevant log output when reporting issues

## 🔄 Updates and Maintenance

### Updating the Application

```bash
cd /opt/music-scheduler
sudo -u music-scheduler git pull origin main
sudo -u music-scheduler venv/bin/pip install -r requirements.txt
sudo systemctl restart music-scheduler
```

### Database Maintenance

```bash
# Backup before maintenance
sudo /opt/music-scheduler/backup/backup.sh

# Optimize database
mysql -u music_user -p music_scheduler -e "OPTIMIZE TABLE events, bookings, venues, artists;"
```

### System Health Checks

```bash
# Check all services
sudo systemctl status music-scheduler mysql nginx

# Check disk space
df -h

# Check backup status
ls -la /var/backups/music-scheduler/
```

---

**Music Scheduler System** - Streamline your music event management with ease! 🎵
