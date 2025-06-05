#!/bin/bash

echo "Starting fix_react_build.sh logging at $(date)"
exec > >(tee -a /music_scheduler/logs/fix_react_build.log) 2>&1

echo "Debug: Logging initialized for fix_react_build.sh"

# Ensure we're in the correct directory
cd /music_scheduler

# Step 1: Fix the typo in setup_admin.sh for API_BASE_URL
echo "Fixing typo in API_BASE_URL in setup_admin.sh..."
sed -i "s|const API_BASE_URL = 'http://192.168.1.63}';|const API_BASE_URL = 'http://192.168.1.63';|" setup_admin.sh

# Verify the fix
echo "Verifying API_BASE_URL in setup_admin.sh..."
grep "API_BASE_URL" setup_admin.sh | grep "192.168.1.63" || { echo "Error: API_BASE_URL typo fix failed in setup_admin.sh"; exit 1; }
echo "API_BASE_URL typo fixed in setup_admin.sh"

# Step 2: Update fetch calls in setup_admin.sh and setup_instructor.sh to use API_BASE_URL
echo "Updating fetch calls in setup_admin.sh and setup_instructor.sh..."

for script in setup_admin.sh setup_instructor.sh; do
    # Extract the index.jsx content into a temporary file
    sed -n "/cat << 'EOF' > index.jsx/,/EOF/p" $script > temp_index.jsx

    # Remove the const U = "http://"; line
    sed -i "/const U = \"http:\/\/\";/d" temp_index.jsx

    # Replace fetch calls using ${U} with ${API_BASE_URL}
    sed -i "s|\`\\\${U}/|\`\\\${API_BASE_URL}/|g" temp_index.jsx

    # Replace the index.jsx creation section in the script with the updated version
    sed -i "/cat << 'EOF' > index.jsx/,/EOF/c\
echo \"Updating index.jsx...\"\
cat << 'EOF' > index.jsx\
$(cat temp_index.jsx)\
EOF" $script

    # Clean up temporary file
    rm temp_index.jsx
    echo "Updated fetch calls in $script"
done

# Step 3: Resolve Browserslist warning by updating Tailwind CSS and Browserslist database
echo "Updating Tailwind CSS and Browserslist database..."
npm install tailwindcss@latest --save-dev
npx update-browserslist-db@latest
echo "Tailwind CSS and Browserslist database updated"

# Step 4: Fix npm vulnerabilities
echo "Fixing npm vulnerabilities..."
npm audit fix --force
echo "npm vulnerabilities addressed"

# Step 5: Rebuild the application
echo "Clearing old build artifacts..."
rm -rf /music_scheduler/static/*

echo "Re-running setup_core.sh to rebuild the app..."
chmod +x setup_core.sh
./setup_core.sh

# Step 6: Identify the latest built JavaScript file
echo "Identifying the latest built JavaScript file..."
LATEST_JS_FILE=$(ls -t /music_scheduler/static/index-*.js | head -n 1)
if [ -z "$LATEST_JS_FILE" ]; then
    echo "Error: No built JavaScript file found in /music_scheduler/static/"
    exit 1
fi
echo "Latest JavaScript file: $LATEST_JS_FILE"

# Step 7: Verify the API_BASE_URL in the built JavaScript file
echo "Verifying API_BASE_URL in the built JavaScript file..."
cat "$LATEST_JS_FILE" | grep 'api/login' | grep '192.168.1.63' || { echo "Error: API_BASE_URL not correctly applied in the built JavaScript file"; exit 1; }
echo "API_BASE_URL correctly applied in the built JavaScript file"

echo "Fix complete! Check the logs for details: cat /music_scheduler/logs/fix_react_build.log"
echo "Please clear your browser cache and test the application by logging in as admin (Username: 'admin', Password: 'MusicU2025') and as instructor (Username: 'instructor1', Password: 'MusicU2025')."
