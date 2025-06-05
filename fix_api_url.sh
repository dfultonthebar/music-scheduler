#!/bin/bash

echo "Starting fix_api_url.sh logging at $(date)"
exec > >(tee -a /music_scheduler/logs/fix_api_url.log) 2>&1

echo "Debug: Logging initialized for fix_api_url.sh"

# Ensure we're in the correct directory
cd /music_scheduler

# Step 1: Verify and fix API_BASE_URL in setup_admin.sh and setup_instructor.sh
echo "Fixing API_BASE_URL in setup_admin.sh and setup_instructor.sh..."
for script in setup_admin.sh setup_instructor.sh; do
    # Extract the index.jsx content into a temporary file
    sed -n '/cat << '"'"'EOF'"'"' > index.jsx/,/EOF/p' $script > temp_index.jsx

    # Ensure API_BASE_URL is set to http://192.168.1.63
    sed -i 's/const API_BASE_URL = .*/const API_BASE_URL = '"'"'http:\/\/192.168.1.63'"'"';/' temp_index.jsx

    # Replace the index.jsx creation section in the script with the updated version
    sed -i '/cat << '"'"'EOF'"'"' > index.jsx/,/EOF/c\
echo "Updating index.jsx..."\
cat << '"'"'EOF'"'"' > index.jsx\
'"$(cat temp_index.jsx)"'\
EOF' $script

    # Clean up temporary file
    rm temp_index.jsx
    echo "Updated API_BASE_URL in $script"
done

# Step 2: Clear old build artifacts
echo "Clearing old build artifacts..."
rm -rf /music_scheduler/static/*

# Step 3: Rebuild the React app by re-running setup_admin.sh and setup_instructor.sh
echo "Re-running setup_admin.sh to rebuild the React app..."
chmod +x setup_admin.sh
./setup_admin.sh

echo "Re-running setup_instructor.sh to rebuild the React app..."
chmod +x setup_instructor.sh
./setup_instructor.sh

# Step 4: Verify Nginx configuration
echo "Verifying Nginx configuration..."
nginx -t
if [ $? -ne 0 ]; then
    echo "Nginx configuration test failed. Check /var/log/nginx/error.log"
    cat /var/log/nginx/error.log
    exit 1
fi

# Reload Nginx to apply any changes
systemctl reload nginx

# Step 5: Test the application
echo "Testing the application endpoint..."
curl -s -o /dev/null -w "%{http_code}" http://192.168.1.63
if [ $? -eq 0 ]; then
    echo "Application is accessible at http://192.168.1.63"
else
    echo "Failed to access the application at http://192.168.1.63. Check server logs."
    exit 1
fi

echo "Fix complete! Check the logs for details: cat /music_scheduler/logs/fix_api_url.log"
echo "Please test the application by logging in as admin (Username: 'admin', Password: 'MusicU2025') and adding a user."
