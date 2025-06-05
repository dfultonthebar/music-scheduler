#!/bin/bash

echo "Starting update_fixes.sh logging at $(date)"
exec > >(tee -a /music_scheduler/logs/update_fixes.log) 2>&1

echo "Debug: Logging initialized for update_fixes.sh"

# Ensure we're in the correct directory
cd /music_scheduler

# Step 1: Update setup_system.sh to define SERVER_IP
echo "Updating setup_system.sh to define SERVER_IP..."
if ! grep -q "SERVER_IP=\"192.168.1.63\"" setup_system.sh; then
    # Add SERVER_IP definition after the shebang
    sed -i '2i\
# Define SERVER_IP at the start of the script\
SERVER_IP="192.168.1.63"\
echo "Debug: SERVER_IP set to $SERVER_IP"' setup_system.sh
    echo "SERVER_IP definition added to setup_system.sh"
else
    echo "SERVER_IP already defined in setup_system.sh"
fi

# Step 2: Update setup_database.sh to add email field to users table
echo "Updating setup_database.sh to add email field to users table..."
# Replace the users table creation to include email field
sed -i '/CREATE TABLE IF NOT EXISTS users/,/);/c\
CREATE TABLE IF NOT EXISTS users (\
    id INT AUTO_INCREMENT PRIMARY KEY,\
    username VARCHAR(255) NOT NULL UNIQUE,\
    password VARCHAR(255) NOT NULL,\
    email VARCHAR(255),\
    role ENUM('"'"'admin'"'"', '"'"'instructor'"'"') NOT NULL\
);' setup_database.sh

# Also update the reset table creation if placeholder hash is detected
sed -i '/CREATE TABLE users/,/);/c\
    CREATE TABLE users (\
        id INT AUTO_INCREMENT PRIMARY KEY,\
        username VARCHAR(255) NOT NULL UNIQUE,\
        password VARCHAR(255) NOT NULL,\
        email VARCHAR(255),\
        role ENUM('"'"'admin'"'"', '"'"'instructor'"'"') NOT NULL\
    );' setup_database.sh

# Update the initial data insertion to include email
sed -i '/INSERT INTO users (username, password, role) VALUES ('"'"'admin'"'"', '"'"'$ADMIN_HASH'"'"', '"'"'admin'"'"');/c\
INSERT INTO users (username, password, email, role) VALUES ('"'"'admin'"'"', '"'"'$ADMIN_HASH'"'"', '"'"'admin@example.com'"'"', '"'"'admin'"'"');' setup_database.sh

sed -i '/INSERT INTO users (username, password, role) VALUES ('"'"'instructor1'"'"', '"'"'$INSTRUCTOR_HASH'"'"', '"'"'instructor'"'"');/c\
INSERT INTO users (username, password, email, role) VALUES ('"'"'instructor1'"'"', '"'"'$INSTRUCTOR_HASH'"'"', '"'"'instructor1@example.com'"'"', '"'"'instructor'"'"');' setup_database.sh

sed -i '/INSERT INTO instructors (name, user_id, cell_phone) VALUES ('"'"'Instructor One'"'"', (SELECT id FROM users WHERE username = '"'"'instructor1'"'"'), '"'"'+1234567890'"'"');/c\
INSERT INTO instructors (name, user_id, cell_phone, email) VALUES ('"'"'Instructor One'"'"', (SELECT id FROM users WHERE username = '"'"'instructor1'"'"'), '"'"'+1234567890'"'"', '"'"'instructor1@example.com'"'"');' setup_database.sh

echo "Email field added to users table in setup_database.sh"

# Step 3: Update setup_core.sh to fix timedelta serialization and handle email in /api/users
echo "Updating setup_core.sh to fix timedelta serialization and handle email in /api/users..."
# Extract the app.py creation section and modify it
# First, extract the app.py content into a temporary file
sed -n '/cat << '"'"'EOF'"'"' > app.py/,/EOF/p' setup_core.sh > temp_app.py

# Fix the manage_users endpoint to handle email
sed -i '/def manage_users():/,/def manage_students():/ {
    /username = data.get('"'"'username'"'"')/a\
        cell_phone = data.get('"'"'cell_phone'"'"')\
        email = data.get('"'"'email'"'"')
    s/cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, '"'"'instructor'"'"')", (username, hashed_password))/cursor.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, '"'"'instructor'"'"')", (username, hashed_password, email))/
    s/cursor.execute("INSERT INTO instructors (name, user_id, cell_phone) VALUES (%s, %s, %s)", (name, user_id, cell_phone))/cursor.execute("INSERT INTO instructors (name, user_id, cell_phone, email) VALUES (%s, %s, %s, %s)", (name, user_id, cell_phone, email))/
    /user_id = data.get('"'"'id'"'"')/a\
        cell_phone = data.get('"'"'cell_phone'"'"')\
        email = data.get('"'"'email'"'"')
    s/cursor.execute("UPDATE users SET username = %s WHERE id = %s AND role = '"'"'instructor'"'"'", (username, user_id))/cursor.execute("UPDATE users SET username = %s, email = %s WHERE id = %s AND role = '"'"'instructor'"'"'", (username, email, user_id))/
    s/cursor.execute("UPDATE instructors SET name = %s, cell_phone = %s WHERE user_id = %s", (name, cell_phone, user_id))/cursor.execute("UPDATE instructors SET name = %s, cell_phone = %s, email = %s WHERE user_id = %s", (name, cell_phone, email, user_id))/
    s/SELECT u.id, u.username, u.role, i.name, i.cell_phone/SELECT u.id, u.username, u.role, u.email, i.name, i.cell_phone/
}' temp_app.py

# Fix the manage_students endpoint to handle email
sed -i '/def manage_students():/,/def my_students():/ {
    s/cursor.execute("INSERT INTO students (name, instrument, cell_phone) VALUES (%s, %s, %s)", (data\['"'"'name'"'"'\], data\['"'"'instrument'"'"'\], data.get('"'"'cell_phone'"'"')))/cursor.execute("INSERT INTO students (name, instrument, cell_phone, email) VALUES (%s, %s, %s, %s)", (data\['"'"'name'"'"'\], data\['"'"'instrument'"'"'\], data.get('"'"'cell_phone'"'"'), data.get('"'"'email'"'"')))/
    /student_id = data.get('"'"'id'"'"')/a\
        cell_phone = data.get('"'"'cell_phone'"'"')\
        email = data.get('"'"'email'"'"')
    s/SET name = %s, instrument = %s, cell_phone = %s/SET name = %s, instrument = %s, cell_phone = %s, email = %s/
    s/(name, instrument, cell_phone, student_id)/(name, instrument, cell_phone, email, student_id)/
}' temp_app.py

# Fix the manage_availability endpoint to handle timedelta serialization
sed -i '/def manage_availability():/,/def manage_lessons():/ {
    /cursor.execute("SELECT \* FROM instructor_availability WHERE instructor_id = %s", (instructor_id,))/a\
            # Convert start_time and end_time to strings to fix JSON serialization\
            for slot in availability:\
                slot['"'"'start_time'"'"'] = str(slot['"'"'start_time'"'"'])\
                slot['"'"'end_time'"'"'] = str(slot['"'"'end_time'"'"'])
}' temp_app.py

# Replace the app.py creation section in setup_core.sh with the updated version
sed -i '/cat << '"'"'EOF'"'"' > app.py/,/EOF/c\
echo "Creating app.py..."\
cat << '"'"'EOF'"'"' > app.py\
'"$(cat temp_app.py)"'\
EOF' setup_core.sh

# Clean up temporary file
rm temp_app.py
echo "Updated app.py in setup_core.sh to handle email and fix timedelta serialization"

# Step 4: Update setup_admin.sh to hardcode API_BASE_URL and align user/student forms
echo "Updating setup_admin.sh to hardcode API_BASE_URL and align user/student forms..."
# Extract the index.jsx content into a temporary file
sed -n '/cat << '"'"'EOF'"'"' > index.jsx/,/EOF/p' setup_admin.sh > temp_index.jsx

# Hardcode API_BASE_URL
sed -i 's/const API_BASE_URL = '"'"'http:\/\/${SERVER_IP}'"'"';/const API_BASE_URL = '"'"'http:\/\/192.168.1.63'"'"';/' temp_index.jsx

# Update AdminDashboard to align user and student forms
# Add email to newUser state
sed -i '/const \[newUser, setNewUser\] = useState({ username: '"'"''"'"', password: '"'"''"'"', name: '"'"''"'"', cell_phone: '"'"''"'"' });/c\
  const [newUser, setNewUser] = useState({ username: '"'"''"'"', password: '"'"''"'"', name: '"'"''"'"', cell_phone: '"'"''"'"', email: '"'"''"'"' });' temp_index.jsx

# Add email to newStudent state
sed -i '/const \[newStudent, setNewStudent\] = useState({ name: '"'"''"'"', instrument: '"'"''"'"', cell_phone: '"'"''"'"' });/c\
  const [newStudent, setNewStudent] = useState({ name: '"'"''"'"', instrument: '"'"''"'"', cell_phone: '"'"''"'"', email: '"'"''"'"' });' temp_index.jsx

# Update editUser to include email
sed -i '/setEditingUser({ id: user.id, username: user.username, name: user.name, cell_phone: user.cell_phone || '"'"''"'"' });/c\
    setEditingUser({ id: user.id, username: user.username, name: user.name, cell_phone: user.cell_phone || '"'"''"'"', email: user.email || '"'"''"'"' });' temp_index.jsx

# Update editStudent to include email
sed -i '/setEditingStudent({/,/});/c\
    setEditingStudent({\
      id: student.id,\
      name: student.name,\
      instrument: student.instrument,\
      cell_phone: student.cell_phone || '"'"''"'"',\
      email: student.email || '"'"''"'"'\
    });' temp_index.jsx

# Update the user form in editing mode
sed -i '/{editingUser ? (/,/Cancel/ {
    /<input/a\
          <input\
            type="email"\
            name="email"\
            placeholder="Email"\
            value={editingUser.email}\
            onChange={handleEditUserChange}\
            className="border p-2 mr-2"\
          />
}' temp_index.jsx

# Update the user form in adding mode
sed -i '/<div className="mb-4">/,/Add User/ {
    /<input.*cell_phone.*>/a\
          <input\
            type="email"\
            name="email"\
            placeholder="Email"\
            value={newUser.email}\
            onChange={handleUserChange}\
            className="border p-2 mr-2"\
          />
}' temp_index.jsx

# Update the student form in editing mode
sed -i '/{editingStudent ? (/,/Cancel/ {
    /<input.*cell_phone.*>/a\
          <input\
            type="email"\
            name="email"\
            placeholder="Email"\
            value={editingStudent.email}\
            onChange={handleEditStudentChange}\
            className="border p-2 mr-2"\
          />
}' temp_index.jsx

# Update the student form in adding mode
sed -i '/<div className="mb-4">/,/Add Student/ {
    /<input.*cell_phone.*>/a\
          <input\
            type="email"\
            name="email"\
            placeholder="Email"\
            value={newStudent.email}\
            onChange={handleStudentChange}\
            className="border p-2 mr-2"\
          />
}' temp_index.jsx

# Update the user list display to show email
sed -i 's/{user.cell_phone ? ` - ${user.cell_phone}` : '"'"''"'"'}/{user.cell_phone ? ` - ${user.cell_phone}` : '"'"''"'"'} {user.email ? ` - ${user.email}` : '"'"''"'"'}/' temp_index.jsx

# Update the student list display to show email
sed -i 's/{student.cell_phone ? ` - ${student.cell_phone}` : '"'"''"'"'}/{student.cell_phone ? ` - ${student.cell_phone}` : '"'"''"'"'} {student.email ? ` - ${student.email}` : '"'"''"'"'}/' temp_index.jsx

# Replace the index.jsx creation section in setup_admin.sh with the updated version
sed -i '/cat << '"'"'EOF'"'"' > index.jsx/,/EOF/c\
echo "Updating index.jsx with AdminDashboard..."\
cat << '"'"'EOF'"'"' > index.jsx\
'"$(cat temp_index.jsx)"'\
EOF' setup_admin.sh

# Clean up temporary file
rm temp_index.jsx
echo "Updated index.jsx in setup_admin.sh to hardcode API_BASE_URL and align user/student forms"

# Step 5: Update setup_instructor.sh to hardcode API_BASE_URL (InstructorDashboard doesn’t have user/student forms)
echo "Updating setup_instructor.sh to hardcode API_BASE_URL..."
# Extract the index.jsx content into a temporary file
sed -n '/cat << '"'"'EOF'"'"' > index.jsx/,/EOF/p' setup_instructor.sh > temp_index.jsx

# Hardcode API_BASE_URL
sed -i 's/const API_BASE_URL = '"'"'http:\/\/${SERVER_IP}'"'"';/const API_BASE_URL = '"'"'http:\/\/192.168.1.63'"'"';/' temp_index.jsx

# Replace the index.jsx creation section in setup_instructor.sh with the updated version
sed -i '/cat << '"'"'EOF'"'"' > index.jsx/,/EOF/c\
echo "Updating index.jsx with InstructorDashboard..."\
cat << '"'"'EOF'"'"' > index.jsx\
'"$(cat temp_index.jsx)"'\
EOF' setup_instructor.sh

# Clean up temporary file
rm temp_index.jsx
echo "Updated index.jsx in setup_instructor.sh to hardcode API_BASE_URL"

# Step 6: Set execute permissions for all scripts
echo "Setting execute permissions for all setup scripts..."
chmod +x setup_system.sh setup_database.sh setup_core.sh setup_config.sh setup_admin.sh setup_instructor.sh

# Step 7: Clear the static directory for a clean build
echo "Clearing static directory for a clean build..."
rm -rf /music_scheduler/static/*

# Step 8: Re-run the setup process
echo "Re-running the setup process to apply changes..."
./setup_system.sh

# Step 9: Monitor the setup process
echo "Monitoring the setup process..."
tail -f /music_scheduler/logs/setup_system.log &
tail -f /music_scheduler/logs/setup_database.log &
tail -f /music_scheduler/logs/setup_core.log &
tail -f /music_scheduler/logs/setup_config.log &
tail -f /music_scheduler/logs/setup_admin.log &
tail -f /music_scheduler/logs/setup_instructor.log &

echo "Update complete! Check the logs for details: /music_scheduler/logs/*.log"
