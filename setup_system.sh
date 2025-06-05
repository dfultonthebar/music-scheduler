#!/bin/bash
# Define SERVER_IP at the start of the script
SERVER_IP="192.168.1.63"
echo "Debug: SERVER_IP set to $SERVER_IP"
# System setup script for music lesson scheduler on Debian 12

# Exit on error, but we'll disable this temporarily for specific sections
set -e

# Load VM_IP from vm_ip.env
if [ -f "/home/musicu/vm_ip.env" ]; then
    source /home/musicu/vm_ip.env
else
    echo "Error: vm_ip.env not found. Please run configure_ip.sh first."
    exit 1
fi

# Configuration
SERVER_IP="$VM_IP"
DOMAIN_NAME="musicu.local"

# Create logs directory
echo "Creating logs directory..."
sudo mkdir -p /music_scheduler/logs
sudo chown $USER:$USER /music_scheduler/logs
sudo chmod 755 /music_scheduler/logs

# Log output to a file in the logs directory
echo "Starting setup_system.sh logging at $(date)"
exec > >(tee -a /music_scheduler/logs/setup_system.log) 2>&1

# Verify logging is working
echo "Debug: Logging initialized for setup_system.sh"

# Ensure the system is up to date, including kernel
echo "Upgrading the distribution, including kernel..."
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install linux-image-amd64 -y

# Clean up unused packages and fix broken dependencies
echo "Cleaning up unused packages and fixing broken dependencies..."
sudo apt-get autoremove -y
sudo apt-get autoclean
sudo dpkg --configure -a
sudo apt-get install -f -y

# Stop any existing web servers
echo "Stopping existing web servers..."
sudo systemctl stop nginx || true
sudo systemctl stop apache2 || true
sudo systemctl disable apache2 || true
sudo killall nginx || true
sudo killall apache2 || true

# Check for port 80 conflicts
echo "Checking for port 80 conflicts..."
if sudo netstat -tuln | grep -q ':80 '; then
    echo "Port 80 is still in use. Identifying service..."
    sudo netstat -tulnp | grep ':80 '
    echo "Error: Port 80 still in use after stopping services. Please free port 80 and retry."
    exit 1
else
    echo "Port 80 is free."
fi

# Purge existing Nginx installations to avoid conflicts
echo "Purging existing Nginx installations..."
sudo apt-get purge -y nginx nginx-common nginx-full || true
sudo rm -rf /etc/nginx /var/log/nginx /var/lib/nginx
sudo apt-get autoremove -y

# Install dependencies (includes libcrypt-dev, Node.js/npm for frontend, and Twilio for SMS)
echo "Installing system dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv curl mariadb-server ufw net-tools wget libcrypt1 libcrypt-dev gunicorn jq nodejs npm avahi-daemon avahi-utils coreutils apparmor apparmor-utils apparmor-profiles

# Ensure libcrypt.so.1 is correctly placed
echo "Ensuring libcrypt.so.1 is correctly placed..."
set +e
LIBCRYPT_PATH=$(find /lib /usr/lib -name libcrypt.so.1 2>/dev/null || true)
echo "LIBCRYPT_PATH result: $LIBCRYPT_PATH"
if [ -z "$LIBCRYPT_PATH" ]; then
    echo "libcrypt.so.1 not found. Reinstalling libcrypt1..."
    sudo apt-get install --reinstall libcrypt1 -y
    LIBCRYPT_PATH=$(find /lib /usr/lib -name libcrypt.so.1 2>/dev/null || true)
    echo "LIBCRYPT_PATH after reinstall: $LIBCRYPT_PATH"
fi

if [ -z "$LIBCRYPT_PATH" ]; then
    echo "Error: libcrypt.so.1 still not found after reinstalling libcrypt1."
    echo "Listing available libcrypt files for debugging:"
    find /lib /usr/lib -name "libcrypt*" 2>/dev/null || true
    exit 1
fi

if [ -f "/lib/x86_64-linux-gnu/libcrypt.so.1" ]; then
    echo "libcrypt.so.1 is already in /lib/x86_64-linux-gnu/, skipping copy."
else
    echo "Copying libcrypt.so.1 to /lib/x86_64-linux-gnu/..."
    LIBCRYPT_SO=$(find $(dirname "$LIBCRYPT_PATH") -name "libcrypt.so.1.*" 2>/dev/null | head -n 1)
    if [ -z "$LIBCRYPT_SO" ]; then
        echo "Error: Could not find libcrypt.so.1.* in $(dirname "$LIBCRYPT_PATH")."
        exit 1
    fi
    sudo cp "$LIBCRYPT_SO" /lib/x86_64-linux-gnu/
    sudo ln -sf "/lib/x86_64-linux-gnu/$(basename "$LIBCRYPT_SO")" /lib/x86_64-linux-gnu/libcrypt.so.1
fi

set -e

# Update ldconfig and verify library path
echo "Updating ldconfig..."
sudo /sbin/ldconfig

echo "Verifying library path in ldconfig..."
if ! /sbin/ldconfig -p | grep -q "libcrypt.so.1.*=>.*\/lib\/x86_64-linux-gnu\/libcrypt.so.1"; then
    echo "Error: libcrypt.so.1 not in ldconfig cache at expected path /lib/x86_64-linux-gnu/libcrypt.so.1."
    /sbin/ldconfig -p
    exit 1
fi
echo "libcrypt.so.1 is in ldconfig cache at /lib/x86_64-linux-gnu/libcrypt.so.1."

# Install Nginx
echo "Installing Nginx..."
sudo apt-get install -y nginx || {
    echo "Nginx installation failed. Checking dependencies..."
    sudo apt-get install -f -y
    sudo apt-get install nginx -y || {
        echo "Nginx installation still failed. Exiting."
        exit 1
    }
}

# Verify Nginx can run
echo "Verifying Nginx binary..."
/usr/sbin/nginx -V || {
    echo "Nginx binary failed to run. Check for missing libraries."
    ldd /usr/sbin/nginx
    exit 1
}

# Start and enable Nginx to ensure it works
echo "Starting and enabling Nginx..."
sudo systemctl start nginx || {
    echo "Failed to start Nginx. Checking status and logs..."
    sudo systemctl status nginx
    journalctl -u nginx.service -n 50
    exit 1
}
sudo systemctl enable nginx
echo "Nginx installed and running."

# Verify Node.js version
echo "Verifying Node.js version..."
node_version=$(node -v | cut -d'v' -f2)
if [[ "${node_version%%.*}" -lt 14 ]]; then
    echo "Error: Node.js version 14 or higher required, found $node_version"
    exit 1
fi
echo "Node.js version $node_version is compatible"

# Create /music_scheduler directory
echo "Creating /music_scheduler directory..."
sudo mkdir -p /music_scheduler/static
sudo mkdir -p /music_scheduler/backups
sudo chown -R $USER:$USER /music_scheduler
sudo chmod -R 755 /music_scheduler
cd /music_scheduler

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install Python packages (including Twilio for SMS)
echo "Installing Python packages..."
pip install flask==2.0.3 flask-cors==3.0.10 pyjwt==2.6.0 werkzeug==2.0.3 mysql-connector-python==8.0.33 gunicorn==20.1.0 bcrypt==4.1.2 twilio==9.3.3

# Set permissions for the next script and run it
echo "Setting permissions for setup_database.sh and running it..."
if [ ! -f "setup_database.sh" ]; then
    echo "Error: setup_database.sh not found in /music_scheduler. Please ensure all setup scripts are in the correct directory."
    exit 1
fi
chmod +x setup_database.sh
./setup_database.sh

echo "System setup complete! Check the setup log for details: cat /music_scheduler/logs/setup_system.log"
