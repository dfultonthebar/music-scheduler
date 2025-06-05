#!/bin/bash

echo "Starting fix_final_issues.sh logging at $(date)"
exec > >(tee -a /music_scheduler/logs/fix_final_issues.log) 2>&1

echo "Debug: Logging initialized for fix_final_issues.sh"

# Ensure we're in the correct directory
cd /music_scheduler

# Step 1: Clear npm cache and rebuild dependencies
echo "Clearing npm cache and rebuilding dependencies..."
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
echo "Dependencies rebuilt"

# Step 2: Run npm audit fix to address vulnerabilities
echo "Running npm audit fix to address vulnerabilities..."
npm audit fix
echo "npm vulnerabilities addressed"

# Step 3: Fix API_BASE_URL in setup_admin.sh and setup_instructor.sh
echo "Fixing API_BASE_URL in setup_admin.sh and setup_instructor.sh..."
for script in setup_admin.sh setup_instructor.sh; do
    # Extract the index.jsx content into a temporary file
    sed -n '/cat << '"'"'EOF'"'"' > index.jsx/,/EOF/p' $script > temp_index.jsx

    # Replace API_BASE_URL placeholder with the correct URL, using a more robust pattern
    sed -i "s/const API_BASE_URL = 'http:\/\/\${SERVER_IP}';/const API_BASE_URL = 'http:\/\/192.168.1.63';/" temp_index.jsx

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

# Step 4: Fix timedelta serialization in setup_core.sh
echo "Fixing timedelta serialization in setup_core.sh..."
# Extract the app.py content into a temporary file
sed -n '/cat << '"'"'EOF'"'"' > app.py/,/EOF/p' setup_core.sh > temp_app.py

# Add the fix for timedelta serialization in manage_availability with corrected formatting
sed -i '/cursor.execute("SELECT \* FROM instructor_availability WHERE instructor_id = %s", (instructor_id,))/a\
            # Convert start_time and end_time to strings to fix JSON serialization\n            for slot in availability:\n                slot["start_time"] = str(slot["start_time"])\n                slot["end_time"] = str(slot["end_time"])' temp_app.py

# Replace the app.py creation section in setup_core.sh with the updated version
sed -i '/cat << '"'"'EOF'"'"' > app.py/,/EOF/c\
echo "Creating app.py..."\
cat << '"'"'EOF'"'"' > app.py\
'"$(cat temp_app.py)"'\
EOF' setup_core.sh

# Clean up temporary file
rm temp_app.py
echo "Updated setup_core.sh with timedelta serialization fix"

# Step 5: Clear old build artifacts
echo "Clearing old build artifacts..."
rm -rf /music_scheduler/static/*

# Step 6: Re-run setup_core.sh to rebuild the app
echo "Re-running setup_core.sh to apply changes..."
chmod +x setup_core.sh
./setup_core.sh

# Step 7: Create favicon.ico placeholder (in case it was cleared)
echo "Creating favicon.ico placeholder in static directory..."
echo -n "" > /music_scheduler/static/favicon.ico
chown root:www-data /music_scheduler/static/favicon.ico
chmod 660 /music_scheduler/static/favicon.ico
echo "favicon.ico created and permissions set"

# Step 8: Verify the favicon exists
echo "Verifying favicon.ico exists..."
if [ -f /music_scheduler/static/favicon.ico ]; then
    echo "favicon.ico exists in /music_scheduler/static/"
else
    echo "Error: favicon.ico was not created. Check the setup_core.sh script."
    exit 1
fi

# Step 9: Verify the application
echo "Testing the application endpoint..."
status_code=$(curl -s -o /dev/null -w "%{http_code}" http://192.168.1.63)
if [ "$status_code" -eq 200 ]; then
    echo "Application is accessible at http://192.168.1.63"
else
    echo "Failed to access the application at http://192.168.1.63. Status code: $status_code. Check server logs."
    exit 1
fi

echo "Fix complete! Check the logs for details: cat /music_scheduler/logs/fix_final_issues.log"
echo "Please clear your browser cache and test the application by logging in as admin (Username: 'admin', Password: 'MusicU2025') and as instructor (Username: 'instructor1', Password: 'MusicU2025')."
