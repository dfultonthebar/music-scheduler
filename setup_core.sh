#!/bin/bash

echo "Starting setup_core.sh logging at $(date)"
exec > >(tee -a /music_scheduler/logs/setup_core.log) 2>&1

echo "Debug: Logging initialized for setup_core.sh"

# Check for and resolve port conflicts on port 8000 with retries
echo "Checking for processes using port 8000..."
for ATTEMPT in {1..3}; do
    PORT_CHECK=$(lsof -i :8000 -t)
    if [ -n "$PORT_CHECK" ]; then
        echo "Port 8000 is in use by PID(s): $PORT_CHECK (Attempt $ATTEMPT/3)"
        echo "Killing processes using port 8000..."
        for PID in $PORT_CHECK; do
            kill -9 $PID
            if [ $? -eq 0 ]; then
                echo "Killed process $PID"
            else
                echo "Error: Failed to kill process $PID"
                exit 1
            fi
        done
        sleep 2  # Wait for the port to be freed
    else
        echo "Port 8000 is free."
        break
    fi
    if [ $ATTEMPT -eq 3 ] && [ -n "$(lsof -i :8000 -t)" ]; then
        echo "Error: Port 8000 still in use after 3 attempts."
        exit 1
    fi
done

# Verify port is free
echo "Verifying port 8000 is free..."
if lsof -i :8000 -t > /dev/null; then
    echo "Error: Port 8000 is still in use after attempting to free it."
    exit 1
else
    echo "Port 8000 is now free."
fi

# Set executable permissions for all sub-scripts
echo "Setting executable permissions for all sub-scripts..."
chmod +x /music_scheduler/setup_database.sh
chmod +x /music_scheduler/setup_backend.sh
chmod +x /music_scheduler/setup_frontend.sh
chmod +x /music_scheduler/setup_config.sh
chmod +x /music_scheduler/setup_admin.sh
chmod +x /music_scheduler/setup_instructor.sh
chmod +x /music_scheduler/setup_services.sh
chmod +x /music_scheduler/fix_permissions.sh

# Move backup files to the backups directory
echo "Moving backup files to /music_scheduler/backups..."
for file in /music_scheduler/*.bak_*; do
    if [ -f "$file" ]; then
        mv "$file" /music_scheduler/backups/
    fi
done

# Run each setup script in sequence
echo "Running setup_database.sh..."
/music_scheduler/setup_database.sh

echo "Running setup_backend.sh..."
/music_scheduler/setup_backend.sh

echo "Running setup_frontend.sh..."
/music_scheduler/setup_frontend.sh

echo "Setting up database backup..."
mkdir -p /music_scheduler/db_backups

echo "Setting permissions for setup_config.sh and running it..."
chmod +x /music_scheduler/setup_config.sh
/music_scheduler/setup_config.sh

echo "Setting permissions for setup_admin.sh and running it..."
chmod +x /music_scheduler/setup_admin.sh
/music_scheduler/setup_admin.sh

echo "Setting permissions for setup_instructor.sh and running it..."
chmod +x /music_scheduler/setup_instructor.sh
/music_scheduler/setup_instructor.sh

echo "Running setup_services.sh..."
/music_scheduler/setup_services.sh

echo "Running fix_permissions.sh..."
/music_scheduler/fix_permissions.sh

# Verify installation
echo "Verifying installation..."
if systemctl is-active --quiet nginx; then
    echo "Nginx is running."
else
    echo "Error: Nginx is not running."
    journalctl -u nginx -n 20 --no-pager
    exit 1
fi

if systemctl is-active --quiet music_scheduler_gunicorn; then
    echo "Gunicorn is running."
else
    echo "Error: Gunicorn is not running."
    journalctl -u music_scheduler_gunicorn -n 20 --no-pager
    exit 1
fi

# Test the application endpoint
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://192.168.1.63)
if [ "$HTTP_STATUS" -eq 200 ]; then
    echo "${HTTP_STATUS}Application is accessible at http://192.168.1.63"
else
    echo "Error: Application is not accessible at http://192.168.1.63 (HTTP Status: $HTTP_STATUS)"
    exit 1
fi

echo "Core setup complete! Check the setup log for details: cat /music_scheduler/logs/setup_core.log"
