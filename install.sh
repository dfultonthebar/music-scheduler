
#!/bin/bash

# Music Scheduler System - One-Click Installer
# This script installs and configures the complete music scheduler system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="music_scheduler"
DB_USER="music_user"
DB_PASS=$(openssl rand -base64 12 | tr -d "=+/" | cut -c1-12)
ADMIN_USER="admin"
ADMIN_PASS=$(openssl rand -base64 12 | tr -d "=+/" | cut -c1-12)
INSTALL_DIR="/opt/music-scheduler"
SERVICE_USER="music-scheduler"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Music Scheduler System Installer${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}This script should not be run as root for security reasons.${NC}"
   echo "Please run as a regular user with sudo privileges."
   exit 1
fi

# Check for sudo privileges
if ! sudo -n true 2>/dev/null; then
    echo -e "${YELLOW}This script requires sudo privileges. You may be prompted for your password.${NC}"
fi

# Detect OS
if [[ -f /etc/debian_version ]]; then
    OS="debian"
    PKG_MANAGER="apt"
elif [[ -f /etc/redhat-release ]]; then
    OS="redhat"
    PKG_MANAGER="yum"
else
    echo -e "${RED}Unsupported operating system. This installer supports Debian/Ubuntu and RHEL/CentOS.${NC}"
    exit 1
fi

echo -e "${GREEN}Detected OS: ${OS}${NC}"
echo

# Function to install packages
install_packages() {
    echo -e "${BLUE}Installing system packages...${NC}"
    if [[ $OS == "debian" ]]; then
        sudo apt update -y
        sudo apt install -y python3 python3-pip python3-venv mysql-server nginx curl wget git openssl
    else
        sudo yum update -y
        sudo yum install -y python3 python3-pip mysql-server nginx curl wget git openssl
    fi
    echo -e "${GREEN}✓ System packages installed${NC}"
}

# Function to setup MySQL
setup_mysql() {
    echo -e "${BLUE}Setting up MySQL database...${NC}"
    
    # Start MySQL service
    sudo systemctl start mysql
    sudo systemctl enable mysql
    
    # Create database and user
    sudo mysql -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME};"
    sudo mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';"
    sudo mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';"
    sudo mysql -e "FLUSH PRIVILEGES;"
    
    # Run database initialization script
    if [[ -f "scripts/db-init.sql" ]]; then
        sudo mysql ${DB_NAME} < scripts/db-init.sql
        echo -e "${GREEN}✓ Database schema initialized${NC}"
    fi
    
    echo -e "${GREEN}✓ MySQL configured${NC}"
}

# Function to setup application
setup_application() {
    echo -e "${BLUE}Setting up Music Scheduler application...${NC}"
    
    # Create service user
    if ! id "${SERVICE_USER}" &>/dev/null; then
        sudo useradd -r -s /bin/false -d ${INSTALL_DIR} ${SERVICE_USER}
    fi
    
    # Create installation directory
    sudo mkdir -p ${INSTALL_DIR}
    sudo cp -r . ${INSTALL_DIR}/
    sudo chown -R ${SERVICE_USER}:${SERVICE_USER} ${INSTALL_DIR}
    
    # Set up Python virtual environment
    cd ${INSTALL_DIR}
    sudo -u ${SERVICE_USER} python3 -m venv venv
    sudo -u ${SERVICE_USER} venv/bin/pip install --upgrade pip
    sudo -u ${SERVICE_USER} venv/bin/pip install -r requirements.txt
    
    # Create environment configuration
    sudo -u ${SERVICE_USER} tee .env > /dev/null <<EOF
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=mysql://${DB_USER}:${DB_PASS}@localhost/${DB_NAME}
MYSQL_HOST=localhost
MYSQL_DATABASE=${DB_NAME}
MYSQL_USERNAME=${DB_USER}
MYSQL_PASSWORD=${DB_PASS}
EOF
    
    echo -e "${GREEN}✓ Application installed${NC}"
}

# Function to create admin user
create_admin_user() {
    echo -e "${BLUE}Creating admin user...${NC}"
    
    cd ${INSTALL_DIR}
    sudo -u ${SERVICE_USER} venv/bin/python3 -c "
import sys
sys.path.insert(0, '.')
from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Create admin user if not exists
    admin = User.query.filter_by(username='${ADMIN_USER}').first()
    if not admin:
        admin = User(
            username='${ADMIN_USER}',
            email='admin@musicscheduler.local',
            password_hash=generate_password_hash('${ADMIN_PASS}'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created successfully')
    else:
        print('Admin user already exists')
"
    echo -e "${GREEN}✓ Admin user configured${NC}"
}

# Function to setup systemd service
setup_service() {
    echo -e "${BLUE}Setting up systemd service...${NC}"
    
    sudo cp scripts/music-scheduler.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable music-scheduler
    sudo systemctl start music-scheduler
    
    echo -e "${GREEN}✓ Systemd service installed and started${NC}"
}

# Function to setup nginx reverse proxy
setup_nginx() {
    echo -e "${BLUE}Setting up Nginx reverse proxy...${NC}"
    
    sudo tee /etc/nginx/sites-available/music-scheduler > /dev/null <<EOF
server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias ${INSTALL_DIR}/static;
        expires 30d;
    }
}
EOF

    # Enable the site
    sudo ln -sf /etc/nginx/sites-available/music-scheduler /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test and reload nginx
    sudo nginx -t && sudo systemctl reload nginx
    sudo systemctl enable nginx
    
    echo -e "${GREEN}✓ Nginx configured${NC}"
}

# Function to setup backup system
setup_backup() {
    echo -e "${BLUE}Setting up backup system...${NC}"
    
    # Make backup script executable
    chmod +x backup/backup.sh
    
    # Create systemd timer for backups
    sudo tee /etc/systemd/system/music-scheduler-backup.service > /dev/null <<EOF
[Unit]
Description=Music Scheduler Backup Service
After=mysql.service

[Service]
Type=oneshot
User=root
ExecStart=${INSTALL_DIR}/backup/backup.sh
EOF

    sudo tee /etc/systemd/system/music-scheduler-backup.timer > /dev/null <<EOF
[Unit]
Description=Run Music Scheduler Backup Daily
Requires=music-scheduler-backup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable music-scheduler-backup.timer
    sudo systemctl start music-scheduler-backup.timer
    
    echo -e "${GREEN}✓ Backup system configured${NC}"
}

# Function to display final information
display_info() {
    echo
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo
    echo -e "${YELLOW}System Information:${NC}"
    echo -e "  Installation Directory: ${INSTALL_DIR}"
    echo -e "  Database Name: ${DB_NAME}"
    echo -e "  Database User: ${DB_USER}"
    echo -e "  Database Password: ${DB_PASS}"
    echo
    echo -e "${YELLOW}Admin Credentials:${NC}"
    echo -e "  Username: ${ADMIN_USER}"
    echo -e "  Password: ${ADMIN_PASS}"
    echo
    echo -e "${YELLOW}Access URLs:${NC}"
    echo -e "  Web Interface: http://localhost"
    echo -e "  Direct App: http://localhost:5000"
    echo
    echo -e "${YELLOW}Service Management:${NC}"
    echo -e "  Status: sudo systemctl status music-scheduler"
    echo -e "  Start:  sudo systemctl start music-scheduler"
    echo -e "  Stop:   sudo systemctl stop music-scheduler"
    echo -e "  Logs:   sudo journalctl -u music-scheduler -f"
    echo
    echo -e "${BLUE}IMPORTANT: Save the database password and admin credentials!${NC}"
    echo
}

# Main installation process
main() {
    echo -e "${BLUE}Starting installation...${NC}"
    
    install_packages
    setup_mysql
    setup_application
    create_admin_user
    setup_service
    setup_nginx
    setup_backup
    display_info
    
    echo -e "${GREEN}Installation completed successfully!${NC}"
}

# Run main function
main "$@"
