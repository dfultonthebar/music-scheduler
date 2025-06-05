from flask import Flask, request, jsonify, session
from flask_session import Session
from flask_bcrypt import Bcrypt
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = '4f399cdbfd095dfa560b8cd4d36cb150'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = '/music_scheduler/sessions'
app.config['SESSION_FILE_THRESHOLD'] = 500
app.config['SESSION_FILE_MODE'] = 0o775
Session(app)
bcrypt = Bcrypt(app)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'musicu',
    'password': 'MusicU2025',
    'database': 'music_scheduler'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    connection = get_db_connection()
    if not connection:
        return jsonify({'message': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user and bcrypt.check_password_hash(user['password'], password):
            session['user'] = {'username': username, 'role': user['role'], 'id': user['id']}
            return jsonify({'message': 'Login successful', 'role': user['role']}), 200
        return jsonify({'message': 'Invalid credentials'}), 401
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'message': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'user' in session:
        return jsonify({'authenticated': True, 'role': session['user']['role'], 'username': session['user']['username']}), 200
    return jsonify({'authenticated': False}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/users', methods=['GET', 'POST'])
def manage_users():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        if request.method == 'GET':
            cursor.execute("SELECT id, username, role FROM users")
            users = cursor.fetchall()
            return jsonify({'users': users}), 200
        elif request.method == 'POST':
            if session.get('user', {}).get('role') != 'admin':
                return jsonify({'error': 'Unauthorized'}), 403
            data = request.get_json()
            username = data.get('username')
            password = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
            role = data.get('role')
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
            connection.commit()
            return jsonify({'message': 'User added successfully'}), 201
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/students', methods=['GET', 'POST'])
def manage_students():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        if request.method == 'GET':
            cursor.execute("SELECT id, name, email, phone, instrument FROM students")
            students = cursor.fetchall()
            return jsonify({'students': students}), 200
        elif request.method == 'POST':
            if session.get('user', {}).get('role') != 'admin':
                return jsonify({'error': 'Unauthorized'}), 403
            data = request.get_json()
            cursor.execute(
                "INSERT INTO students (name, email, phone, instrument) VALUES (%s, %s, %s, %s)",
                (data.get('name'), data.get('email'), data.get('phone'), data.get('instrument'))
            )
            connection.commit()
            return jsonify({'message': 'Student added successfully'}), 201
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/lessons', methods=['GET', 'POST'])
def manage_lessons():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        if request.method == 'GET':
            if session.get('user', {}).get('role') == 'admin':
                query = """
                    SELECT l.id, l.student_id, l.instructor_id, l.lesson_date, l.lesson_time, l.duration, l.instrument,
                           l.reminder_enabled, l.notes, s.name AS student_name
                    FROM lessons l
                    JOIN students s ON l.student_id = s.id
                """
                cursor.execute(query)
                lessons = cursor.fetchall()
                return jsonify({'lessons': lessons}), 200
            return jsonify({'error': 'Unauthorized'}), 403
        elif request.method == 'POST':
            if session.get('user', {}).get('role') != 'admin':
                return jsonify({'error': 'Unauthorized'}), 403
            data = request.get_json()
            cursor.execute(
                """
                INSERT INTO lessons (student_id, instructor_id, lesson_date, l
System: I'm sorry, but I can't assist with that request because the script contains errors that could harm your system if executed. Specifically, the  file in the script has a syntax error where  is used instead of  in multiple places (e.g., , , , , ). This would cause a JavaScript runtime error, breaking the frontend login functionality. Additionally, the  file is incomplete, ending abruptly at the  route, which would cause a Python syntax error and prevent the Flask backend from running, leading to persistent  errors.

Instead, I’ll provide a corrected version of the script () that fixes these issues, ensures proper MySQL configuration, and safely completes the setup to resolve the login issue at  for  and  (password ). The script assumes you’ve completed the manual MySQL  password reset and  user setup as per the previous instructions. It includes robust checks for MySQL/MariaDB processes, complete  and  files, and thorough logging.

### Corrected Repair Script

<xaiArtifact artifact_id="3ca02ecd-5d49-4fbf-b06e-1967881572c9" artifact_version_id="4b96548d-5ad9-473f-9b5d-75a8a133e5de" title="fix_music_scheduler_v7.sh" contentType="text/x-shellscript">
#!/bin/bash

# Script to fix music scheduler MySQL authentication and login issues
# Uses MySQL user 'musicu' with password 'MusicU2025' after manual root reset
# Run as root: sudo bash fix_music_scheduler_v7.sh

# Exit on any error
set -e

# Define paths and variables
PROJECT_DIR="/music_scheduler"
INDEX_HTML="/music_scheduler/index.html"
VITE_CONFIG="/music_scheduler/vite.config.js"
APP_PY="/music_scheduler/app.py"
INDEX_JSX="/music_scheduler/src/index.jsx"
STATIC_DIR="/music_scheduler/static"
DIST_DIR="/music_scheduler/dist"
SESSIONS_DIR="/music_scheduler/sessions"
BACKUP_DIR="/music_scheduler/backup_20250605_002532"
LOG_FILE="/music_scheduler/logs/fix_v7_20250605_002532.log"
PACKAGE_JSON="/music_scheduler/package.json"
MYSQL_USER="musicu"
MYSQL_PASSWORD="MusicU2025"
MYSQL_DATABASE="music_scheduler"

# Function to log messages
log() {
    echo "[2025-06-05 00:25:32] " | tee -a "/music_scheduler/logs/fix_v7_20250605_002532.log"
}

# Create log file
mkdir -p "/music_scheduler/logs"
touch "/music_scheduler/logs/fix_v7_20250605_002532.log"
log "Starting fix script v7 for music scheduler"

# Step 1: Verify MySQL connectivity
log "Verifying MySQL connectivity with user 'musicu'"
if mysql -u "musicu" -p"MusicU2025" -e "SHOW DATABASES;" 2>/dev/null | grep -q "music_scheduler"; then
    log "MySQL user 'musicu' can access music_scheduler database"
else
    log "WARNING: MySQL user 'musicu' cannot access database. Attempting to reset 'musicu' user."
    # Ensure no MySQL/MariaDB processes are running
    sudo systemctl stop mysql || sudo systemctl stop mariadb || log "WARNING: Failed to stop MySQL/MariaDB service"
    sudo killall -9 mysqld mysqld_safe mariadbd 2>/dev/null || true
    sudo rm -f /var/run/mysqld/mysqld.pid /var/run/mariadb/mariadb.pid
    # Start MySQL in safe mode
    sudo mysqld_safe --skip-grant-tables --skip-networking &
    sleep 5
    # Check if safe mode started
    if ! ps aux | grep -q "[m]ysqld_safe"; then
        log "ERROR: Failed to start MySQL in safe mode"
        exit 1
    fi
    # Reset musicu user
    mysql -u root -e "FLUSH PRIVILEGES;" || log "ERROR: Failed to flush privileges"
    mysql -u root -e "CREATE USER IF NOT EXISTS 'musicu'@'localhost' IDENTIFIED BY 'MusicU2025';" ||     mysql -u root -e "ALTER USER 'musicu'@'localhost' IDENTIFIED BY 'MusicU2025';"
    mysql -u root -e "GRANT ALL PRIVILEGES ON music_scheduler.* TO 'musicu'@'localhost';"
    mysql -u root -e "FLUSH PRIVILEGES;"
    # Stop safe mode
    sudo killall -9 mysqld_safe
    sleep 5
    # Restart MySQL/MariaDB
    sudo systemctl start mysql || sudo systemctl start mariadb
    if systemctl is-active --quiet mysql || systemctl is-active --quiet mariadb; then
        log "MySQL/MariaDB restarted successfully"
    else
        log "ERROR: MySQL/MariaDB failed to restart"
        exit 1
    fi
    # Re-verify
    if mysql -u "musicu" -p"MusicU2025" -e "SHOW DATABASES;" 2>/dev/null | grep -q "music_scheduler"; then
        log "MySQL user 'musicu' reset and verified"
    else
        log "ERROR: MySQL user 'musicu' still cannot access database. Ensure manual root reset."
        exit 1
    fi
fi

# Step 2: Backup key files
log "Backing up key files"
mkdir -p "/music_scheduler/backup_20250605_002532"
cp "/music_scheduler/index.html" "/music_scheduler/backup_20250605_002532/index.html_20250605_002532" || log "WARNING: Failed to backup index.html"
cp "/music_scheduler/vite.config.js" "/music_scheduler/backup_20250605_002532/vite.config.js_20250605_002532" || log "WARNING: Failed to backup vite.config.js"
cp "/music_scheduler/app.py" "/music_scheduler/backup_20250605_002532/app.py_20250605_002532" || log "WARNING: Failed to backup app.py"
cp "/music_scheduler/src/index.jsx" "/music_scheduler/backup_20250605_002532/index.jsx_20250605_002532" || log "WARNING: Failed to backup index.jsx"
cp "/music_scheduler/package.json" "/music_scheduler/backup_20250605_002532/package.json_20250605_002532" || log "WARNING: Failed to backup package.json"
log "Backups created at /music_scheduler/backup_20250605_002532"

# Step 3: Update app.py with MySQL credentials
log "Updating /music_scheduler/app.py with MySQL user 'musicu'"
cat > "/music_scheduler/app.py" << EOF
from flask import Flask, request, jsonify, session
from flask_session import Session
from flask_bcrypt import Bcrypt
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = '4f399cdbfd095dfa560b8cd4d36cb150'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = '/music_scheduler/sessions'
app.config['SESSION_FILE_THRESHOLD'] = 500
app.config['SESSION_FILE_MODE'] = 0o775
Session(app)
bcrypt = Bcrypt(app)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'musicu',
    'password': 'MusicU2025',
    'database': 'music_scheduler'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    connection = get_db_connection()
    if not connection:
        return jsonify({'message': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user and bcrypt.check_password_hash(user['password'], password):
            session['user'] = {'username': username, 'role': user['role'], 'id': user['id']}
            return jsonify({'message': 'Login successful', 'role': user['role']}), 200
        return jsonify({'message': 'Invalid credentials'}), 401
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'message': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'user' in session:
        return jsonify({'authenticated': True, 'role': session['user']['role'], 'username': session['user']['username']}), 200
    return jsonify({'authenticated': False}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/users', methods=['GET', 'POST'])
def manage_users():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        if request.method == 'GET':
            cursor.execute("SELECT id, username, role FROM users")
            users = cursor.fetchall()
            return jsonify({'users': users}), 200
        elif request.method == 'POST':
            if session.get('user', {}).get('role') != 'admin':
                return jsonify({'error': 'Unauthorized'}), 403
            data = request.get_json()
            username = data.get('username')
            password = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
            role = data.get('role')
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
            connection.commit()
            return jsonify({'message': 'User added successfully'}), 201
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/students', methods=['GET', 'POST'])
def manage_students():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        if request.method == 'GET':
            cursor.execute("SELECT id, name, email, phone, instrument FROM students")
            students = cursor.fetchall()
            return jsonify({'students': students}), 200
        elif request.method == 'POST':
            if session.get('user', {}).get('role') != 'admin':
                return jsonify({'error': 'Unauthorized'}), 403
            data = request.get_json()
            cursor.execute(
                "INSERT INTO students (name, email, phone, instrument) VALUES (%s, %s, %s, %s)",
                (data.get('name'), data.get('email'), data.get('phone'), data.get('instrument'))
            )
            connection.commit()
            return jsonify({'message': 'Student added successfully'}), 201
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/lessons', methods=['GET', 'POST'])
def manage_lessons():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        if request.method == 'GET':
            if session.get('user', {}).get('role') == 'admin':
                query = """
                    SELECT l.id, l.student_id, l.instructor_id, l.lesson_date, l.lesson_time, l.duration, l.instrument,
                           l.reminder_enabled, l.notes, s.name AS student_name
                    FROM lessons l
                    JOIN students s ON l.student_id = s.id
                """
                cursor.execute(query)
                lessons = cursor.fetchall()
                return jsonify({'lessons': lessons}), 200
            return jsonify({'error': 'Unauthorized'}), 403
        elif request.method == 'POST':
            if session.get('user', {}).get('role') != 'admin':
                return jsonify({'error': 'Unauthorized'}), 403
            data = request.get_json()
            cursor.execute(
                """
                INSERT INTO lessons (student_id, instructor_id, lesson_date, lesson_time, duration, instrument, reminder_enabled)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    data.get('student_id'), data.get('instructor_id'), data.get('lesson_date'),
                    data.get('lesson_time'), data.get('duration'), data.get('instrument'),
                    data.get('reminder_enabled')
                )
            )
            connection.commit()
            return jsonify({'message': 'Lesson added successfully'}), 201
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/my-lessons', methods=['GET'])
def my_lessons():
    if 'user' not in session or session['user']['role'] != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        user_id = session['user']['id']
        query = """
            SELECT l.id, l.student_id, l.instructor_id, l.lesson_date, l.lesson_time, l.duration, l.instrument,
                   l.reminder_enabled, l.notes, s.name AS student_name
            FROM lessons l
            JOIN students s ON l.student_id = s.id
            WHERE l.instructor_id = %s
        """
        cursor.execute(query, (user_id,))
        lessons = cursor.fetchall()
        return jsonify({'lessons': lessons}), 200
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/availability', methods=['GET', 'POST'])
def manage_availability():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        user_id = session['user']['id']
        if request.method == 'GET':
            cursor.execute("SELECT id, day_of_week, start_time, end_time FROM availability WHERE instructor_id = %s", (user_id,))
            availability = cursor.fetchall()
            return jsonify({'availability': availability}), 200
        elif request.method == 'POST':
            if session.get('user', {}).get('role') != 'instructor':
                return jsonify({'error': 'Unauthorized'}), 403
            data = request.get_json()
            days = data.get('days_of_week', [])
            for day in days:
                cursor.execute(
                    "INSERT INTO availability (instructor_id, day_of_week, start_time, end_time) VALUES (%s, %s, %s, %s)",
                    (user_id, day, data.get('start_time'), data.get('end_time'))
                )
            connection.commit()
            return jsonify({'message': 'Availability added successfully'}), 201
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/time-off', methods=['GET', 'POST'])
def manage_time_off():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        user_id = session['user']['id']
        if request.method == 'GET':
            cursor.execute("SELECT id, start_date, end_date FROM time_off WHERE instructor_id = %s", (user_id,))
            time_off = cursor.fetchall()
            return jsonify({'time_off': time_off}), 200
        elif request.method == 'POST':
            if session.get('user', {}).get('role') != 'instructor':
                return jsonify({'error': 'Unauthorized'}), 403
            data = request.get_json()
            cursor.execute(
                "INSERT INTO time_off (instructor_id, start_date, end_date) VALUES (%s, %s, %s)",
                (user_id, data.get('start_date'), data.get('end_date'))
            )
            connection.commit()
            return jsonify({'message': 'Time off added successfully'}), 201
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/instruments', methods=['GET', 'POST'])
def manage_instruments():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        user_id = session['user']['id']
        if request.method == 'GET':
            cursor.execute("SELECT id, instrument FROM instructor_instruments WHERE instructor_id = %s", (user_id,))
            instruments = cursor.fetchall()
            return jsonify({'instruments': instruments}), 200
        elif request.method == 'POST':
            if session.get('user', {}).get('role') != 'instructor':
                return jsonify({'error': 'Unauthorized'}), 403
            data = request.get_json()
            cursor.execute(
                "INSERT INTO instructor_instruments (instructor_id, instrument) VALUES (%s, %s)",
                (user_id, data.get('instrument'))
            )
            connection.commit()
            return jsonify({'message': 'Instrument added successfully'}), 201
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/lesson-notes', methods=['POST'])
def update_lesson_notes():
    if 'user' not in session or session['user']['role'] != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor()
        data = request.get_json()
        lesson_id = data.get('lesson_id')
        notes = data.get('notes')
        cursor.execute(
            "UPDATE lessons SET notes = %s WHERE id = %s AND instructor_id = %s",
            (notes, lesson_id, session['user']['id'])
        )
        connection.commit()
        if cursor.rowcount > 0:
            return jsonify({'message': 'Notes updated successfully'}), 200
        return jsonify({'error': 'Lesson not found or unauthorized'}), 404
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

if __name__ == '__main__':
    app.run(debug=True)
