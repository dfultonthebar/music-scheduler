from flask import Flask, request, jsonify, session, render_template, redirect, url_for, flash
from flask_session import Session
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os
from dotenv import load_dotenv
from email_service import EmailService

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration from environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'd0f33f212484b6776da8332afe37bee7')
app.config['SESSION_TYPE'] = os.getenv('SESSION_TYPE', 'filesystem')
app.config['SESSION_FILE_DIR'] = os.getenv('SESSION_FILE_DIR', './sessions')
app.config['SESSION_FILE_THRESHOLD'] = 500
app.config['SESSION_FILE_MODE'] = 0o660

# Enable CORS for React frontend
CORS(app, supports_credentials=True, origins=["http://localhost:3000", "http://52.34.76.202:3000"])

# Initialize extensions
Session(app)
bcrypt = Bcrypt(app)

# Database configuration from environment variables
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'music_user'), 
    'password': os.getenv('DB_PASSWORD', 'music_pass'),
    'database': os.getenv('DB_NAME', 'music_scheduler')
}

# Initialize email service
email_service = EmailService(db_config)

def get_db_connection():
    """Get database connection with error handling"""
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify the API is running"""
    try:
        connection = get_db_connection()
        if connection and connection.is_connected():
            connection.close()
            return jsonify({
                'status': 'healthy',
                'message': 'API is running and database is connected',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'message': 'Database connection failed',
                'timestamp': datetime.now().isoformat()
            }), 503
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Health check failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

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
            cursor.execute("SELECT id, username, role, email, phone FROM users")
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

@app.route('/api/instructors-missing-contact', methods=['GET'])
def get_instructors_missing_contact():
    """Get instructors who are missing email or phone information"""
    if session.get('user', {}).get('role') != 'admin':
        return jsonify({'error': 'Unauthorized - Admin access required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, username, email, phone 
            FROM users 
            WHERE role = 'instructor' 
            AND (email IS NULL OR email = '' OR phone IS NULL OR phone = '')
        """)
        instructors = cursor.fetchall()
        return jsonify({'instructors': instructors}), 200
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/instructors/<int:instructor_id>/contact', methods=['PUT'])
def update_instructor_contact(instructor_id):
    """Update instructor contact information"""
    import re
    
    if session.get('user', {}).get('role') != 'admin':
        return jsonify({'error': 'Unauthorized - Admin access required'}), 403
    
    data = request.get_json()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    
    if not email or not phone:
        return jsonify({'error': 'Email and phone are required'}), 400
    
    # Validate email format
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    if not email_pattern.match(email):
        return jsonify({'error': 'Please enter a valid email address'}), 400
    
    # Validate phone format (basic validation - should have at least 10 digits)
    phone_digits = re.sub(r'\D', '', phone)  # Remove non-digits
    if len(phone_digits) < 10:
        return jsonify({'error': 'Please enter a valid phone number (at least 10 digits)'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Check if instructor exists and is actually an instructor
        cursor.execute("SELECT id, role FROM users WHERE id = %s", (instructor_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'Instructor not found'}), 404
        if user['role'] != 'instructor':
            return jsonify({'error': 'User is not an instructor'}), 400
        
        # Check if email already exists for another user
        cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (email, instructor_id))
        if cursor.fetchone():
            return jsonify({'error': 'Email address already exists in the system'}), 400
        
        # Update instructor contact information
        cursor.execute(
            "UPDATE users SET email = %s, phone = %s WHERE id = %s",
            (email, phone, instructor_id)
        )
        connection.commit()
        
        return jsonify({'message': 'Contact information updated successfully'}), 200
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/users/<int:user_id>/password', methods=['PUT'])
def change_user_password(user_id):
    """Admin-only endpoint to change any user's password"""
    if session.get('user', {}).get('role') != 'admin':
        return jsonify({'error': 'Unauthorized - Admin access required'}), 403
    
    data = request.get_json()
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    # Validate password input
    if not new_password or not confirm_password:
        return jsonify({'error': 'Password and confirmation are required'}), 400
    
    if new_password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verify user exists
        cursor.execute("SELECT id, username, role FROM users WHERE id = %s", (user_id,))
        target_user = cursor.fetchone()
        
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Hash the new password
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        # Update the password
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_id))
        connection.commit()
        
        # Log the password change for audit trail
        admin_username = session['user']['username']
        current_time = datetime.now()
        log_password_change(admin_username, target_user['username'], current_time)
        
        return jsonify({
            'message': f'Password updated successfully for user {target_user["username"]}',
            'username': target_user['username']
        }), 200
        
    except Error as e:
        print(f"Database error during password change: {e}")
        return jsonify({'error': 'Failed to update password due to server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/all-users', methods=['GET'])
def get_all_system_users():
    """Get all users including students for password management"""
    if session.get('user', {}).get('role') != 'admin':
        return jsonify({'error': 'Unauthorized - Admin access required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get users from users table
        cursor.execute("SELECT id, username, role, 'user' as user_type FROM users ORDER BY username")
        users = cursor.fetchall()
        
        # Get students (they can also have passwords changed if needed)
        cursor.execute("SELECT id, name as username, 'student' as role, 'student' as user_type FROM students ORDER BY name")
        students = cursor.fetchall()
        
        # Combine and return all users
        all_users = users + students
        return jsonify({'users': all_users}), 200
        
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

def log_password_change(admin_username, target_username, timestamp):
    """Log password changes for audit trail"""
    try:
        log_message = f"[{timestamp.isoformat()}] Admin '{admin_username}' changed password for user '{target_username}'\n"
        
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Write to audit log
        with open('logs/password_changes.log', 'a') as log_file:
            log_file.write(log_message)
            
        print(f"Password change logged: Admin {admin_username} changed password for {target_username}")
        
    except Exception as e:
        print(f"Failed to log password change: {e}")
        # Don't fail the password change if logging fails

def prepare_lesson_notification_data(lesson_id, cursor):
    """Prepare lesson data for email notifications"""
    try:
        cursor.execute("""
            SELECT 
                l.id as lesson_id, l.lesson_date, l.lesson_time, l.duration, l.instrument, l.notes,
                s.name as student_name, s.email as student_email,
                u.username as instructor_name, u.email as instructor_email
            FROM lessons l
            JOIN students s ON l.student_id = s.id
            JOIN users u ON l.instructor_id = u.id
            WHERE l.id = %s
        """, (lesson_id,))
        
        lesson = cursor.fetchone()
        if not lesson:
            return None
        
        # Convert lesson_time to readable format
        lesson_time = parse_time_to_12h(lesson['lesson_time']) if lesson['lesson_time'] else 'TBD'
        
        # Format lesson date
        lesson_date = lesson['lesson_date'].strftime('%A, %B %d, %Y') if lesson['lesson_date'] else 'TBD'
        
        return {
            'lesson_id': lesson['lesson_id'],
            'student_name': lesson['student_name'],
            'student_email': lesson['student_email'],
            'instructor_name': lesson['instructor_name'],
            'instructor_email': lesson['instructor_email'],
            'lesson_date': lesson_date,
            'lesson_time': lesson_time,
            'duration': lesson['duration'] or 60,
            'instrument': lesson['instrument'] or 'Music',
            'lesson_notes': lesson['notes'] or ''
        }
        
    except Exception as e:
        print(f"Error preparing lesson notification data: {e}")
        return None

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
                cursor.execute("""
                    SELECT l.id, l.student_id, l.instructor_id, l.lesson_date, l.lesson_time, l.duration, l.instrument,
                           l.reminder_enabled, l.notes, s.name AS student_name
                    FROM lessons l
                    JOIN students s ON l.student_id = s.id
                """)
                lessons = cursor.fetchall()
                
                # Convert lesson_time to 12-hour format for display
                for lesson in lessons:
                    if lesson.get('lesson_time'):
                        lesson['lesson_time'] = parse_time_to_12h(lesson['lesson_time'])
                
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
            lesson_id = cursor.lastrowid
            connection.commit()
            
            # Send email notifications
            try:
                lesson_data = prepare_lesson_notification_data(lesson_id, cursor)
                if lesson_data:
                    email_service.send_lesson_notification(lesson_data, 'confirmation')
            except Exception as e:
                print(f"Email notification failed: {e}")
            
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
        cursor.execute("""
            SELECT l.id, l.student_id, l.instructor_id, l.lesson_date, l.lesson_time, l.duration, l.instrument,
                   l.reminder_enabled, l.notes, s.name AS student_name
            FROM lessons l
            JOIN students s ON l.student_id = s.id
            WHERE l.instructor_id = %s
        """, (user_id,))
        lessons = cursor.fetchall()
        
        # Convert lesson_time to 12-hour format for display
        for lesson in lessons:
            if lesson.get('lesson_time'):
                lesson['lesson_time'] = parse_time_to_12h(lesson['lesson_time'])
        
        return jsonify({'lessons': lessons}), 200
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

def parse_time_to_24h(time_str):
    """Convert time string to 24-hour format for MySQL TIME type"""
    if not time_str:
        return None
    
    time_str = time_str.strip().lower()
    
    # If already in 24-hour format (HH:MM or HH:MM:SS), return as is
    if ':' in time_str and ('am' not in time_str and 'pm' not in time_str):
        parts = time_str.split(':')
        if len(parts) == 2:
            return f"{time_str}:00"  # Add seconds
        return time_str
    
    try:
        from datetime import datetime
        # Parse 12-hour format with AM/PM
        if 'am' in time_str or 'pm' in time_str:
            # Handle formats like "1:30pm", "1:30 pm", "1pm"
            time_str = time_str.replace(' ', '')
            
            # Add :00 for minutes if not present (e.g., "1pm" -> "1:00pm")
            if ':' not in time_str:
                time_str = time_str.replace('am', ':00am').replace('pm', ':00pm')
            
            # Parse and convert to 24-hour format
            time_obj = datetime.strptime(time_str, '%I:%M%p')
            return time_obj.strftime('%H:%M:%S')
        
        # Fallback - assume it's already in correct format
        return time_str
        
    except ValueError as e:
        print(f"Time parsing error: {e} for time_str: {time_str}")
        return None

def parse_time_to_12h(time_str):
    """Convert 24-hour format time to 12-hour format for display"""
    if not time_str:
        return None
    
    try:
        from datetime import datetime
        
        # Handle both string and timedelta objects
        if hasattr(time_str, 'total_seconds'):
            # Convert timedelta to time string
            total_seconds = int(time_str.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            time_str = f"{hours:02d}:{minutes:02d}:00"
        
        time_str = str(time_str).strip()
        
        # Parse time string and convert to 12-hour format
        if ':' in time_str:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            
            # Convert to 12-hour format
            if hours == 0:
                return f"12:{minutes:02d} AM"
            elif hours < 12:
                return f"{hours}:{minutes:02d} AM"
            elif hours == 12:
                return f"12:{minutes:02d} PM"
            else:
                return f"{hours-12}:{minutes:02d} PM"
        
        return time_str
        
    except (ValueError, AttributeError) as e:
        print(f"Time conversion error: {e} for time_str: {time_str}")
        return str(time_str)  # Return original if conversion fails

def convert_day_name_to_number(day_name):
    """Convert day name to number (0=Monday, 6=Sunday)"""
    if isinstance(day_name, int):
        return day_name
    
    day_mapping = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    return day_mapping.get(day_name.lower(), None)

def convert_day_number_to_name(day_number):
    """Convert day number to day name (0=Monday, 6=Sunday)"""
    if day_number is None:
        return None
    
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    if 0 <= day_number <= 6:
        return day_names[day_number]
    return None

@app.route('/api/availability', methods=['GET', 'POST'])
def manage_availability():
    # Check if user is logged in
    if 'user' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    if session['user']['role'] != 'instructor':
        return jsonify({'error': 'Instructor role required'}), 403
        
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        user_id = session['user']['id']
        
        if request.method == 'GET':
            cursor.execute("SELECT id, day_of_week, start_time, end_time FROM availability WHERE instructor_id = %s", (user_id,))
            availability = cursor.fetchall()
            
            # Convert times to 12-hour format and add day names
            for item in availability:
                if item.get('start_time'):
                    item['start_time'] = parse_time_to_12h(item['start_time'])
                if item.get('end_time'):
                    item['end_time'] = parse_time_to_12h(item['end_time'])
                # Add day name for display
                item['day_name'] = convert_day_number_to_name(item['day_of_week'])
            
            return jsonify({'availability': availability}), 200
            
        elif request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
                
            days = data.get('days_of_week', [])
            start_time = data.get('start_time')
            end_time = data.get('end_time')
            
            if not days or not start_time or not end_time:
                return jsonify({'error': 'Missing required fields: days_of_week, start_time, end_time'}), 400
            
            # Convert times to 24-hour format
            start_time_24h = parse_time_to_24h(start_time)
            end_time_24h = parse_time_to_24h(end_time)
            
            if not start_time_24h or not end_time_24h:
                return jsonify({'error': 'Invalid time format. Use format like "1:30pm" or "13:30"'}), 400
            
            inserted_count = 0
            for day in days:
                day_num = convert_day_name_to_number(day)
                if day_num is None:
                    continue
                    
                # Check if availability already exists for this day and time
                cursor.execute(
                    "SELECT id FROM availability WHERE instructor_id = %s AND day_of_week = %s AND start_time = %s AND end_time = %s",
                    (user_id, day_num, start_time_24h, end_time_24h)
                )
                if cursor.fetchone():
                    continue  # Skip if already exists
                    
                cursor.execute(
                    "INSERT INTO availability (instructor_id, day_of_week, start_time, end_time) VALUES (%s, %s, %s, %s)",
                    (user_id, day_num, start_time_24h, end_time_24h)
                )
                inserted_count += 1
            
            connection.commit()
            return jsonify({
                'message': f'Availability added successfully. {inserted_count} time slots added.',
                'inserted_count': inserted_count
            }), 201
            
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/availability/<int:availability_id>', methods=['PUT', 'DELETE'])
def edit_availability(availability_id):
    """Edit or delete a specific availability slot"""
    if 'user' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    if session['user']['role'] != 'instructor':
        return jsonify({'error': 'Instructor role required'}), 403
        
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        user_id = session['user']['id']
        
        if request.method == 'PUT':
            # Update availability slot
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
                
            day_of_week = data.get('day_of_week')
            start_time = data.get('start_time')
            end_time = data.get('end_time')
            
            if not all([day_of_week is not None, start_time, end_time]):
                return jsonify({'error': 'Missing required fields: day_of_week, start_time, end_time'}), 400
            
            # Convert day name to number if needed
            day_num = convert_day_name_to_number(day_of_week)
            if day_num is None:
                return jsonify({'error': 'Invalid day of week'}), 400
            
            # Convert times to 24-hour format
            start_time_24h = parse_time_to_24h(start_time)
            end_time_24h = parse_time_to_24h(end_time)
            
            if not start_time_24h or not end_time_24h:
                return jsonify({'error': 'Invalid time format. Use format like "1:30pm" or "13:30"'}), 400
            
            # Check if the availability belongs to the current user
            cursor.execute("SELECT instructor_id FROM availability WHERE id = %s", (availability_id,))
            result = cursor.fetchone()
            if not result or result['instructor_id'] != user_id:
                return jsonify({'error': 'Availability slot not found or unauthorized'}), 404
            
            # Update the availability slot
            cursor.execute(
                "UPDATE availability SET day_of_week = %s, start_time = %s, end_time = %s WHERE id = %s AND instructor_id = %s",
                (day_num, start_time_24h, end_time_24h, availability_id, user_id)
            )
            connection.commit()
            
            return jsonify({'message': 'Availability updated successfully'}), 200
            
        elif request.method == 'DELETE':
            # Delete availability slot
            # Check if the availability belongs to the current user
            cursor.execute("SELECT instructor_id FROM availability WHERE id = %s", (availability_id,))
            result = cursor.fetchone()
            if not result or result['instructor_id'] != user_id:
                return jsonify({'error': 'Availability slot not found or unauthorized'}), 404
            
            cursor.execute("DELETE FROM availability WHERE id = %s AND instructor_id = %s", (availability_id, user_id))
            connection.commit()
            
            return jsonify({'message': 'Availability deleted successfully'}), 200
            
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500
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

@app.route('/api/instructor/students', methods=['GET'])
def get_instructor_students():
    """Get students assigned to the current instructor for lesson scheduling"""
    if 'user' not in session or session['user']['role'] != 'instructor':
        return jsonify({'error': 'Instructor authentication required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        instructor_id = session['user']['id']
        
        # Only return students assigned to this instructor
        cursor.execute("""
            SELECT s.id, s.name, s.email, s.phone, s.instrument
            FROM students s
            JOIN instructor_student_assignments a ON s.id = a.student_id
            WHERE a.instructor_id = %s
            ORDER BY s.name
        """, (instructor_id,))
        
        students = cursor.fetchall()
        return jsonify({'students': students}), 200
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/instructor/lessons', methods=['GET', 'POST'])
def instructor_lesson_management():
    """Handle instructor lesson scheduling"""
    if 'user' not in session or session['user']['role'] != 'instructor':
        return jsonify({'error': 'Instructor authentication required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        user_id = session['user']['id']
        
        if request.method == 'GET':
            # Get lessons for this instructor
            cursor.execute("""
                SELECT l.id, l.student_id, l.instructor_id, l.lesson_date, l.lesson_time, l.duration, l.instrument,
                       l.reminder_enabled, l.notes, s.name AS student_name, s.email AS student_email
                FROM lessons l
                JOIN students s ON l.student_id = s.id
                WHERE l.instructor_id = %s
                ORDER BY l.lesson_date DESC, l.lesson_time DESC
            """, (user_id,))
            lessons = cursor.fetchall()
            
            # Convert lesson_time to 12-hour format for display
            for lesson in lessons:
                if lesson.get('lesson_time'):
                    lesson['lesson_time'] = parse_time_to_12h(lesson['lesson_time'])
            
            return jsonify({'lessons': lessons}), 200
            
        elif request.method == 'POST':
            # Schedule a new lesson
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
                
            student_id = data.get('student_id')
            lesson_date = data.get('lesson_date')
            lesson_time = data.get('lesson_time')
            duration = data.get('duration', 60)  # Default 60 minutes
            instrument = data.get('instrument')
            reminder_enabled = data.get('reminder_enabled', True)
            notes = data.get('notes', '')
            
            if not all([student_id, lesson_date, lesson_time, instrument]):
                return jsonify({'error': 'Missing required fields: student_id, lesson_date, lesson_time, instrument'}), 400
            
            # Convert time to 24-hour format
            lesson_time_24h = parse_time_to_24h(lesson_time)
            if not lesson_time_24h:
                return jsonify({'error': 'Invalid time format. Use format like "1:30pm" or "13:30"'}), 400
            
            # Check if student is assigned to this instructor
            cursor.execute("""
                SELECT s.id FROM students s
                JOIN instructor_student_assignments a ON s.id = a.student_id
                WHERE s.id = %s AND a.instructor_id = %s
            """, (student_id, user_id))
            if not cursor.fetchone():
                return jsonify({'error': 'Student not found or not assigned to you. Please contact admin to assign students.'}), 404
            
            # Insert new lesson
            cursor.execute(
                """
                INSERT INTO lessons (student_id, instructor_id, lesson_date, lesson_time, duration, instrument, reminder_enabled, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (student_id, user_id, lesson_date, lesson_time_24h, duration, instrument, reminder_enabled, notes)
            )
            lesson_id = cursor.lastrowid
            connection.commit()
            
            # Send email notifications
            try:
                lesson_data = prepare_lesson_notification_data(lesson_id, cursor)
                if lesson_data:
                    email_service.send_lesson_notification(lesson_data, 'confirmation')
            except Exception as e:
                print(f"Email notification failed: {e}")
            
            return jsonify({'message': 'Lesson scheduled successfully'}), 201
            
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/instructor/lessons/<int:lesson_id>', methods=['PUT', 'DELETE'])
def edit_instructor_lesson(lesson_id):
    """Edit or delete a lesson"""
    if 'user' not in session or session['user']['role'] != 'instructor':
        return jsonify({'error': 'Instructor authentication required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        user_id = session['user']['id']
        
        # Check if lesson exists and belongs to this instructor
        cursor.execute("SELECT * FROM lessons WHERE id = %s AND instructor_id = %s", (lesson_id, user_id))
        lesson = cursor.fetchone()
        if not lesson:
            return jsonify({'error': 'Lesson not found or unauthorized'}), 404
        
        if request.method == 'PUT':
            # Update lesson
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Get fields to update
            lesson_date = data.get('lesson_date', lesson['lesson_date'])
            lesson_time = data.get('lesson_time')
            duration = data.get('duration', lesson['duration'])
            instrument = data.get('instrument', lesson['instrument'])
            reminder_enabled = data.get('reminder_enabled', lesson['reminder_enabled'])
            notes = data.get('notes', lesson['notes'])
            
            # Convert time to 24-hour format if provided
            if lesson_time:
                lesson_time_24h = parse_time_to_24h(lesson_time)
                if not lesson_time_24h:
                    return jsonify({'error': 'Invalid time format. Use format like "1:30pm" or "13:30"'}), 400
            else:
                lesson_time_24h = lesson['lesson_time']
            
            # Update lesson
            cursor.execute(
                """
                UPDATE lessons 
                SET lesson_date = %s, lesson_time = %s, duration = %s, instrument = %s, reminder_enabled = %s, notes = %s
                WHERE id = %s AND instructor_id = %s
                """,
                (lesson_date, lesson_time_24h, duration, instrument, reminder_enabled, notes, lesson_id, user_id)
            )
            connection.commit()
            
            # Send email notifications for update
            try:
                lesson_data = prepare_lesson_notification_data(lesson_id, cursor)
                if lesson_data:
                    email_service.send_lesson_notification(lesson_data, 'update')
            except Exception as e:
                print(f"Email notification failed: {e}")
            
            return jsonify({'message': 'Lesson updated successfully'}), 200
            
        elif request.method == 'DELETE':
            # Get lesson data before deletion for cancellation notification
            lesson_data = prepare_lesson_notification_data(lesson_id, cursor)
            
            # Delete lesson
            cursor.execute("DELETE FROM lessons WHERE id = %s AND instructor_id = %s", (lesson_id, user_id))
            connection.commit()
            
            # Send cancellation email notifications
            try:
                if lesson_data:
                    email_service.send_lesson_notification(lesson_data, 'cancellation')
            except Exception as e:
                print(f"Email notification failed: {e}")
            
            return jsonify({'message': 'Lesson deleted successfully'}), 200
            
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

# Role-based access control decorators

def require_instructor():
    """Decorator to require instructor role"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            if 'user' not in session or session['user']['role'] != 'instructor':
                return redirect(url_for('login_page'))
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

def require_admin():
    """Decorator to require admin role"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            if 'user' not in session or session['user']['role'] != 'admin':
                return redirect(url_for('login_page'))
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# Web Interface Routes

@app.route('/')
def index():
    """Redirect to appropriate dashboard based on user role"""
    if 'user' in session:
        if session['user']['role'] == 'admin':
            return redirect(url_for('dashboard'))
        elif session['user']['role'] == 'instructor':
            return redirect(url_for('instructor_dashboard'))
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """Handle login form"""
    if request.method == 'GET':
        return render_template('login.html')
    
    # Handle form submission
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return render_template('login.html', error='Please fill in all fields')
    
    connection = get_db_connection()
    if not connection:
        return render_template('login.html', error='Database connection failed')
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if user and bcrypt.check_password_hash(user['password'], password):
            session['user'] = {'username': username, 'role': user['role'], 'id': user['id']}
            
            # Role-based redirect
            if user['role'] == 'admin':
                return redirect(url_for('dashboard'))
            elif user['role'] == 'instructor':
                return redirect(url_for('instructor_dashboard'))
            else:
                return render_template('login.html', error='Invalid user role')
        else:
            return render_template('login.html', error='Invalid username or password')
            
    except Error as e:
        print(f"Database error: {e}")
        return render_template('login.html', error='Login failed due to server error')
    finally:
        cursor.close()
        connection.close()

@app.route('/dashboard', methods=['GET', 'POST'])
@require_admin()
def dashboard():
    """Admin dashboard"""
    
    if request.method == 'GET':
        return render_template('dashboard.html', session=session)
    
    # Handle form submissions
    action = request.form.get('action')
    
    if action == 'add_user':
        return handle_add_user()
    elif action == 'add_student':
        return handle_add_student()
    
    return render_template('dashboard.html', session=session, error='Invalid action')

def handle_add_user():
    """Handle adding a new user"""
    import re
    
    username = request.form.get('user_username')
    password = request.form.get('user_password')
    role = request.form.get('user_role')
    email = request.form.get('user_email', '').strip()
    phone = request.form.get('user_phone', '').strip()
    
    if not all([username, password, role]):
        return render_template('dashboard.html', session=session, error='Please fill in all user fields')
    
    if role not in ['admin', 'instructor']:
        return render_template('dashboard.html', session=session, error='Invalid role selected')
    
    # Validate instructor requirements
    if role == 'instructor':
        if not email:
            return render_template('dashboard.html', session=session, error='Email is required for instructor accounts')
        if not phone:
            return render_template('dashboard.html', session=session, error='Phone number is required for instructor accounts')
        
        # Validate email format
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            return render_template('dashboard.html', session=session, error='Please enter a valid email address')
        
        # Validate phone format (basic validation - should have at least 10 digits)
        phone_digits = re.sub(r'\D', '', phone)  # Remove non-digits
        if len(phone_digits) < 10:
            return render_template('dashboard.html', session=session, error='Please enter a valid phone number (at least 10 digits)')
    
    connection = get_db_connection()
    if not connection:
        return render_template('dashboard.html', session=session, error='Database connection failed')
    
    try:
        cursor = connection.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return render_template('dashboard.html', session=session, error='Username already exists')
        
        # Check if email already exists for instructors
        if role == 'instructor' and email:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return render_template('dashboard.html', session=session, error='Email address already exists in the system')
        
        # Add new user with contact information
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        if role == 'instructor':
            cursor.execute(
                "INSERT INTO users (username, password, role, email, phone) VALUES (%s, %s, %s, %s, %s)",
                (username, hashed_password, role, email, phone)
            )
        else:
            cursor.execute(
                "INSERT INTO users (username, password, role, email, phone) VALUES (%s, %s, %s, %s, %s)",
                (username, hashed_password, role, email if email else None, phone if phone else None)
            )
        
        connection.commit()
        
        success_message = f'User {username} added successfully'
        if role == 'instructor':
            success_message += f' with contact information (Email: {email}, Phone: {phone})'
        
        return render_template('dashboard.html', session=session, success=success_message)
        
    except Error as e:
        print(f"Database error: {e}")
        return render_template('dashboard.html', session=session, error='Failed to add user due to server error')
    finally:
        cursor.close()
        connection.close()

def handle_add_student():
    """Handle adding a new student"""
    name = request.form.get('student_name')
    email = request.form.get('student_email')
    phone = request.form.get('student_phone')
    instrument = request.form.get('student_instrument')
    
    if not all([name, email, phone, instrument]):
        return render_template('dashboard.html', session=session, error='Please fill in all student fields')
    
    connection = get_db_connection()
    if not connection:
        return render_template('dashboard.html', session=session, error='Database connection failed')
    
    try:
        cursor = connection.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM students WHERE email = %s", (email,))
        if cursor.fetchone():
            return render_template('dashboard.html', session=session, error='Student with this email already exists')
        
        # Add new student
        cursor.execute(
            "INSERT INTO students (name, email, phone, instrument) VALUES (%s, %s, %s, %s)",
            (name, email, phone, instrument)
        )
        connection.commit()
        
        return render_template('dashboard.html', session=session, success=f'Student {name} added successfully')
        
    except Error as e:
        print(f"Database error: {e}")
        return render_template('dashboard.html', session=session, error='Failed to add student due to server error')
    finally:
        cursor.close()
        connection.close()

@app.route('/logout')
def logout_page():
    """Handle logout"""
    session.pop('user', None)
    return redirect(url_for('login_page'))

# Instructor Routes

@app.route('/instructor')
@require_instructor()
def instructor_dashboard():
    """Instructor dashboard"""
    return render_template('instructor_dashboard.html', session=session)

@app.route('/instructor/lessons')
@require_instructor()
def instructor_lessons():
    """Instructor lessons page"""
    return render_template('instructor_lessons.html', session=session)

@app.route('/instructor/availability', methods=['GET', 'POST'])
@require_instructor()
def instructor_availability():
    """Instructor availability management"""
    if request.method == 'GET':
        return render_template('instructor_availability.html', session=session)
    
    # Handle form submissions
    action = request.form.get('action')
    
    if action == 'add_availability':
        return handle_add_availability()
    elif action == 'add_time_off':
        return handle_add_time_off()
    
    return render_template('instructor_availability.html', session=session, error='Invalid action')

def handle_add_availability():
    """Handle adding instructor availability"""
    days_of_week = request.form.getlist('days_of_week')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    
    if not all([days_of_week, start_time, end_time]):
        return render_template('instructor_availability.html', session=session, error='Please fill in all availability fields')
    
    # Check if user is logged in and is an instructor
    if 'user' not in session or session['user']['role'] != 'instructor':
        return render_template('instructor_availability.html', session=session, error='Instructor authentication required')
    
    # Convert times to 24-hour format
    start_time_24h = parse_time_to_24h(start_time)
    end_time_24h = parse_time_to_24h(end_time)
    
    if not start_time_24h or not end_time_24h:
        return render_template('instructor_availability.html', session=session, error='Invalid time format. Use format like "1:30pm" or "13:30"')
    
    connection = get_db_connection()
    if not connection:
        return render_template('instructor_availability.html', session=session, error='Database connection failed')
    
    try:
        cursor = connection.cursor()
        user_id = session['user']['id']
        
        inserted_count = 0
        # Add availability for each selected day
        for day in days_of_week:
            day_num = convert_day_name_to_number(day)
            if day_num is None:
                continue
                
            # Check if availability already exists for this day and time
            cursor.execute(
                "SELECT id FROM availability WHERE instructor_id = %s AND day_of_week = %s AND start_time = %s AND end_time = %s",
                (user_id, day_num, start_time_24h, end_time_24h)
            )
            if cursor.fetchone():
                continue  # Skip if already exists
                
            cursor.execute(
                "INSERT INTO availability (instructor_id, day_of_week, start_time, end_time) VALUES (%s, %s, %s, %s)",
                (user_id, day_num, start_time_24h, end_time_24h)
            )
            inserted_count += 1
        
        connection.commit()
        message = f'Availability added successfully. {inserted_count} time slots added.'
        return render_template('instructor_availability.html', session=session, success=message)
        
    except Error as e:
        print(f"Database error: {e}")
        return render_template('instructor_availability.html', session=session, error=f'Failed to add availability: {str(e)}')
    except Exception as e:
        print(f"Server error: {e}")
        return render_template('instructor_availability.html', session=session, error=f'Server error: {str(e)}')
    finally:
        cursor.close()
        connection.close()

def handle_add_time_off():
    """Handle adding instructor time off"""
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    if not all([start_date, end_date]):
        return render_template('instructor_availability.html', session=session, error='Please fill in all time off fields')
    
    # Validate that start date is not after end date
    if start_date > end_date:
        return render_template('instructor_availability.html', session=session, error='Start date cannot be after end date')
    
    connection = get_db_connection()
    if not connection:
        return render_template('instructor_availability.html', session=session, error='Database connection failed')
    
    try:
        cursor = connection.cursor()
        user_id = session['user']['id']
        
        # Check for overlapping time off
        cursor.execute(
            "SELECT id FROM time_off WHERE instructor_id = %s AND ((start_date <= %s AND end_date >= %s) OR (start_date <= %s AND end_date >= %s))",
            (user_id, start_date, start_date, end_date, end_date)
        )
        if cursor.fetchone():
            return render_template('instructor_availability.html', session=session, error='Time off overlaps with existing time off period')
        
        cursor.execute(
            "INSERT INTO time_off (instructor_id, start_date, end_date) VALUES (%s, %s, %s)",
            (user_id, start_date, end_date)
        )
        connection.commit()
        
        return render_template('instructor_availability.html', session=session, success='Time off added successfully')
        
    except Error as e:
        print(f"Database error: {e}")
        return render_template('instructor_availability.html', session=session, error='Failed to add time off due to server error')
    finally:
        cursor.close()
        connection.close()

@app.route('/api/valid-time-slots', methods=['GET'])
def get_valid_time_slots():
    """Get valid time slots for scheduling based on availability and time-off"""
    if 'user' not in session or session['user']['role'] != 'instructor':
        return jsonify({'error': 'Instructor authentication required'}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        instructor_id = session['user']['id']
        
        # Get query parameters
        date = request.args.get('date')
        duration = request.args.get('duration', 60, type=int)
        
        if not date:
            return jsonify({'error': 'Date parameter is required'}), 400
        
        # Get day of week for the requested date
        from datetime import datetime
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_of_week = date_obj.weekday()
            # Convert Python weekday (Monday=0) to our system (Sunday=0)
            day_of_week = (day_of_week + 1) % 7
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Check if date is in time-off period
        cursor.execute(
            "SELECT id FROM time_off WHERE instructor_id = %s AND %s BETWEEN start_date AND end_date",
            (instructor_id, date)
        )
        if cursor.fetchone():
            return jsonify({'valid_slots': [], 'message': 'Date is during time-off period'}), 200
        
        # Get availability for this day of week
        cursor.execute(
            "SELECT start_time, end_time FROM availability WHERE instructor_id = %s AND day_of_week = %s",
            (instructor_id, day_of_week)
        )
        availability_slots = cursor.fetchall()
        
        if not availability_slots:
            return jsonify({'valid_slots': [], 'message': 'No availability set for this day'}), 200
        
        # Get existing lessons for this date
        cursor.execute(
            "SELECT lesson_time, duration FROM lessons WHERE instructor_id = %s AND lesson_date = %s",
            (instructor_id, date)
        )
        existing_lessons = cursor.fetchall()
        
        # Generate valid time slots
        valid_slots = []
        
        try:
            for slot in availability_slots:
                start_time = slot['start_time']
                end_time = slot['end_time']
                
                # Convert to minutes for easier calculation
                start_minutes = time_to_minutes(start_time)
                end_minutes = time_to_minutes(end_time)
                
                # Generate possible time slots within this availability window
                current_minutes = start_minutes
                while current_minutes + duration <= end_minutes:
                    slot_start = minutes_to_time(current_minutes)
                    slot_end = minutes_to_time(current_minutes + duration)
                    
                    # Check if this slot conflicts with existing lessons
                    conflicts = False
                    for lesson in existing_lessons:
                        lesson_start = time_to_minutes(lesson['lesson_time'])
                        lesson_end = lesson_start + lesson['duration']
                        
                        # Check for overlap
                        if not (current_minutes + duration <= lesson_start or current_minutes >= lesson_end):
                            conflicts = True
                            break
                    
                    if not conflicts:
                        valid_slots.append({
                            'time': parse_time_to_12h(slot_start),
                            'end_time': parse_time_to_12h(slot_end),
                            'duration': duration
                        })
                    
                    # Move to next 15-minute slot
                    current_minutes += 15
        except Exception as slot_error:
            print(f"Error generating time slots: {slot_error}")
            print(f"Availability slots: {availability_slots}")
            print(f"Existing lessons: {existing_lessons}")
            return jsonify({'error': f'Error processing time slots: {str(slot_error)}'}), 500
        
        return jsonify({'valid_slots': valid_slots}), 200
        
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        cursor.close()
        connection.close()

def time_to_minutes(time_obj):
    """Convert time string (HH:MM:SS) or time object to minutes since midnight"""
    if isinstance(time_obj, str):
        parts = time_obj.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    else:
        # Handle datetime.time object from database
        from datetime import time
        if isinstance(time_obj, time):
            return time_obj.hour * 60 + time_obj.minute
        else:
            # Handle timedelta objects (if any)
            if hasattr(time_obj, 'seconds'):
                return time_obj.seconds // 60
            return 0

def minutes_to_time(minutes):
    """Convert minutes since midnight to time string (HH:MM:SS)"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}:00"

@app.route('/instructor/schedule')
@require_instructor()
def instructor_schedule():
    """Instructor lesson scheduling page"""
    return render_template('instructor_schedule.html', session=session)

@app.route('/instructor/students')
@require_instructor()
def instructor_students():
    """Instructor students page"""
    return render_template('instructor_students.html', session=session)

@app.route('/admin/calendar')
def admin_calendar():
    """Admin calendar view page"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect('/login')
    return render_template('admin_calendar.html', session=session)

@app.route('/admin/assignments')
def admin_assignments():
    """Admin assignment management page"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect('/login')
    return render_template('admin_assignments.html', session=session)

@app.route('/admin/email-settings')
def admin_email_settings():
    """Admin email settings page"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect('/login')
    return render_template('admin_email_settings.html', session=session)

# ============ INSTRUCTOR-STUDENT ASSIGNMENT API ENDPOINTS ============

@app.route('/api/admin/assignments', methods=['GET', 'POST'])
def manage_assignments():
    """Admin endpoint for managing instructor-student assignments"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Get all current assignments with instructor and student names
            cursor.execute("""
                SELECT 
                    a.id, a.instructor_id, a.student_id, a.assigned_date,
                    u.username as instructor_name,
                    s.name as student_name,
                    s.instrument as student_instrument
                FROM instructor_student_assignments a
                JOIN users u ON a.instructor_id = u.id
                JOIN students s ON a.student_id = s.id
                ORDER BY u.username, s.name
            """)
            assignments = cursor.fetchall()
            
            # Also get all instructors and students for the interface
            cursor.execute("SELECT id, username FROM users WHERE role = 'instructor' ORDER BY username")
            instructors = cursor.fetchall()
            
            cursor.execute("SELECT id, name, instrument FROM students ORDER BY name")
            students = cursor.fetchall()
            
            return jsonify({
                'assignments': assignments,
                'instructors': instructors,
                'students': students
            }), 200
            
        elif request.method == 'POST':
            data = request.get_json()
            instructor_id = data.get('instructor_id')
            student_id = data.get('student_id')
            
            if not instructor_id or not student_id:
                return jsonify({'error': 'Both instructor_id and student_id are required'}), 400
            
            # Check if assignment already exists
            cursor.execute(
                "SELECT id FROM instructor_student_assignments WHERE instructor_id = %s AND student_id = %s",
                (instructor_id, student_id)
            )
            if cursor.fetchone():
                return jsonify({'error': 'Assignment already exists'}), 409
            
            # Create new assignment
            cursor.execute(
                """INSERT INTO instructor_student_assignments 
                   (instructor_id, student_id, assigned_by_admin_id) 
                   VALUES (%s, %s, %s)""",
                (instructor_id, student_id, session['user']['id'])
            )
            connection.commit()
            
            return jsonify({'message': 'Assignment created successfully'}), 201
            
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/assignments/<int:assignment_id>', methods=['DELETE'])
def delete_assignment(assignment_id):
    """Delete an instructor-student assignment"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM instructor_student_assignments WHERE id = %s", (assignment_id,))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Assignment not found'}), 404
            
        connection.commit()
        return jsonify({'message': 'Assignment deleted successfully'}), 200
        
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/assignments/bulk', methods=['POST'])
def bulk_assign_students():
    """Bulk assign multiple students to an instructor"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor()
        data = request.get_json()
        instructor_id = data.get('instructor_id')
        student_ids = data.get('student_ids', [])
        
        if not instructor_id or not student_ids:
            return jsonify({'error': 'instructor_id and student_ids are required'}), 400
        
        success_count = 0
        for student_id in student_ids:
            try:
                cursor.execute(
                    """INSERT IGNORE INTO instructor_student_assignments 
                       (instructor_id, student_id, assigned_by_admin_id) 
                       VALUES (%s, %s, %s)""",
                    (instructor_id, student_id, session['user']['id'])
                )
                if cursor.rowcount > 0:
                    success_count += 1
            except Error:
                continue
        
        connection.commit()
        return jsonify({
            'message': f'{success_count} assignments created successfully',
            'success_count': success_count
        }), 200
        
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        cursor.close()
        connection.close()

# ============ MODIFIED INSTRUCTOR ENDPOINTS FOR RESTRICTED ACCESS ============

@app.route('/api/instructor/assigned-students', methods=['GET'])
def get_instructor_assigned_students():
    """Get students assigned to the current instructor"""
    if 'user' not in session or session['user']['role'] != 'instructor':
        return jsonify({'error': 'Instructor authentication required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        instructor_id = session['user']['id']
        
        cursor.execute("""
            SELECT s.id, s.name, s.email, s.phone, s.instrument
            FROM students s
            JOIN instructor_student_assignments a ON s.id = a.student_id
            WHERE a.instructor_id = %s
            ORDER BY s.name
        """, (instructor_id,))
        
        students = cursor.fetchall()
        return jsonify({'students': students}), 200
        
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        cursor.close()
        connection.close()

# ============ ADMIN CALENDAR API ENDPOINTS ============

@app.route('/api/admin/calendar-data', methods=['GET'])
def get_admin_calendar_data():
    """Get all calendar data for admin view (lessons, availability, time-off)"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get all lessons with instructor and student info
        cursor.execute("""
            SELECT 
                l.id, l.lesson_date, l.lesson_time, l.duration, l.instrument, l.notes,
                s.name as student_name,
                u.username as instructor_name,
                'lesson' as event_type
            FROM lessons l
            JOIN students s ON l.student_id = s.id
            JOIN users u ON l.instructor_id = u.id
            ORDER BY l.lesson_date, l.lesson_time
        """)
        lessons = cursor.fetchall()
        
        # Convert lesson times to readable format
        for lesson in lessons:
            if lesson.get('lesson_time'):
                lesson['lesson_time'] = parse_time_to_12h(lesson['lesson_time'])
        
        # Get instructor availability
        cursor.execute("""
            SELECT 
                a.id, a.day_of_week, a.start_time, a.end_time,
                u.username as instructor_name,
                'availability' as event_type
            FROM availability a
            JOIN users u ON a.instructor_id = u.id
            ORDER BY u.username, a.day_of_week, a.start_time
        """)
        availability = cursor.fetchall()
        
        # Convert availability times and add day names
        for item in availability:
            if item.get('start_time'):
                item['start_time'] = parse_time_to_12h(item['start_time'])
            if item.get('end_time'):
                item['end_time'] = parse_time_to_12h(item['end_time'])
            item['day_name'] = convert_day_number_to_name(item['day_of_week'])
        
        # Get instructor time-off
        cursor.execute("""
            SELECT 
                t.id, t.start_date, t.end_date,
                u.username as instructor_name,
                'time_off' as event_type
            FROM time_off t
            JOIN users u ON t.instructor_id = u.id
            ORDER BY u.username, t.start_date
        """)
        time_off = cursor.fetchall()
        
        # Get all instructors for filtering
        cursor.execute("SELECT id, username FROM users WHERE role = 'instructor' ORDER BY username")
        instructors = cursor.fetchall()
        
        # Get all students for filtering
        cursor.execute("SELECT id, name, instrument FROM students ORDER BY name")
        students = cursor.fetchall()
        
        return jsonify({
            'lessons': lessons,
            'availability': availability,
            'time_off': time_off,
            'instructors': instructors,
            'students': students
        }), 200
        
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/calendar-data/filtered', methods=['GET'])
def get_filtered_calendar_data():
    """Get filtered calendar data based on instructor or date range"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        instructor_id = request.args.get('instructor_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Build base lessons query with optional filters
        lessons_query = """
            SELECT 
                l.id, l.lesson_date, l.lesson_time, l.duration, l.instrument, l.notes,
                s.name as student_name,
                u.username as instructor_name,
                'lesson' as event_type
            FROM lessons l
            JOIN students s ON l.student_id = s.id
            JOIN users u ON l.instructor_id = u.id
        """
        
        lessons_conditions = []
        lessons_params = []
        
        if instructor_id:
            lessons_conditions.append("l.instructor_id = %s")
            lessons_params.append(instructor_id)
        
        if start_date:
            lessons_conditions.append("l.lesson_date >= %s")
            lessons_params.append(start_date)
            
        if end_date:
            lessons_conditions.append("l.lesson_date <= %s")
            lessons_params.append(end_date)
        
        if lessons_conditions:
            lessons_query += " WHERE " + " AND ".join(lessons_conditions)
        
        lessons_query += " ORDER BY l.lesson_date, l.lesson_time"
        
        cursor.execute(lessons_query, lessons_params)
        lessons = cursor.fetchall()
        
        # Convert lesson times to readable format
        for lesson in lessons:
            if lesson.get('lesson_time'):
                lesson['lesson_time'] = parse_time_to_12h(lesson['lesson_time'])
        
        return jsonify({'lessons': lessons}), 200
        
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        cursor.close()
        connection.close()

# ============ EMAIL NOTIFICATION API ENDPOINTS ============

@app.route('/api/admin/email/smtp-config', methods=['GET', 'POST'])
def manage_smtp_config():
    """Admin endpoint for managing SMTP configuration"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    if request.method == 'GET':
        # Get current SMTP configuration (without password)
        config = email_service.get_smtp_config()
        if config:
            # Remove password from response for security
            config.pop('smtp_password', None)
            return jsonify({'config': config}), 200
        else:
            return jsonify({'config': None}), 200
    
    elif request.method == 'POST':
        data = request.get_json()
        required_fields = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'from_email', 'from_name']
        
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Validate security type
        if data.get('smtp_security') not in ['NONE', 'STARTTLS', 'SSL']:
            data['smtp_security'] = 'STARTTLS'
        
        result = email_service.save_smtp_config(data)
        if result['success']:
            return jsonify({'message': result['message']}), 200
        else:
            return jsonify({'error': result['error']}), 500

@app.route('/api/admin/email/test-smtp', methods=['POST'])
def test_smtp_connection():
    """Test SMTP connection with provided configuration"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    data = request.get_json()
    required_fields = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password']
    
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields for SMTP test'}), 400
    
    result = email_service.test_smtp_connection(data)
    return jsonify(result), 200 if result['success'] else 400

@app.route('/api/admin/email/templates', methods=['GET'])
def get_email_templates():
    """Get all email templates for admin management"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    templates = email_service.get_all_templates()
    return jsonify({'templates': templates}), 200

@app.route('/api/admin/email/templates/<template_name>', methods=['PUT'])
def update_email_template(template_name):
    """Update a specific email template"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    data = request.get_json()
    if not data or 'subject' not in data or 'body' not in data:
        return jsonify({'error': 'Subject and body are required'}), 400
    
    result = email_service.update_email_template(template_name, data['subject'], data['body'])
    if result['success']:
        return jsonify({'message': result['message']}), 200
    else:
        return jsonify({'error': result['error']}), 400

@app.route('/api/admin/email/logs', methods=['GET'])
def get_email_logs():
    """Get email activity logs for admin review"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    limit = request.args.get('limit', 100, type=int)
    logs = email_service.get_email_logs(limit)
    return jsonify({'logs': logs}), 200

@app.route('/api/admin/email/send-test', methods=['POST'])
def send_test_email():
    """Send a test email to verify configuration"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    data = request.get_json()
    test_email = data.get('test_email')
    
    if not test_email:
        return jsonify({'error': 'Test email address is required'}), 400
    
    # Send test email
    result = email_service.send_email(
        test_email,
        "Music Scheduler - Test Email",
        """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c3e50; text-align: center;">🎵 Test Email</h2>
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <p>Hello!</p>
                <p>This is a test email from the Music Scheduler system to verify that your email configuration is working correctly.</p>
                <p>If you received this email, your SMTP settings are properly configured! 🎉</p>
                <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
                <p style="color: #666; font-size: 12px;">This is an automated test message from the Music Scheduler system.</p>
            </div>
        </div>
        """,
        "test_email"
    )
    
    return jsonify(result), 200 if result['success'] else 400

@app.route('/api/admin/email/service-status', methods=['GET'])
def get_email_service_status():
    """Get email service enabled/disabled status"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    result = email_service.get_email_service_status()
    return jsonify(result), 200 if result['success'] else 400

@app.route('/api/admin/email/service-toggle', methods=['POST'])
def toggle_email_service():
    """Enable or disable email service"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    data = request.get_json()
    enabled = data.get('enabled')
    
    if enabled is None:
        return jsonify({'error': 'enabled parameter is required'}), 400
    
    # Set the service status
    result = email_service.set_email_service_enabled(enabled, session['user']['username'])
    return jsonify(result), 200 if result['success'] else 400

# ========================
# USER DELETION API ENDPOINTS
# ========================

@app.route('/api/admin/users/<int:user_id>/deletion-impact', methods=['GET'])
def get_user_deletion_impact(user_id):
    """Get information about what data will be affected when deleting a user"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    # Prevent admin from checking deletion impact on themselves
    if user_id == session['user']['id']:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get user information
        cursor.execute("SELECT id, username, role, email, phone FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        impact = {
            'user': user,
            'lessons': {'count': 0, 'future_count': 0, 'past_count': 0},
            'assignments': {'count': 0, 'students': []},
            'availability': {'count': 0, 'slots': []},
            'recommendations': []
        }
        
        if user['role'] == 'instructor':
            # Check lessons (both future and past)
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN lesson_date >= CURDATE() THEN 1 ELSE 0 END) as future,
                       SUM(CASE WHEN lesson_date < CURDATE() THEN 1 ELSE 0 END) as past
                FROM lessons WHERE instructor_id = %s
            """, (user_id,))
            lesson_counts = cursor.fetchone()
            
            impact['lessons'] = {
                'count': lesson_counts['total'] or 0,
                'future_count': lesson_counts['future'] or 0,
                'past_count': lesson_counts['past'] or 0
            }
            
            # Check instructor-student assignments
            cursor.execute("""
                SELECT s.id, s.name, s.email, s.instrument 
                FROM students s
                JOIN instructor_student_assignments isa ON s.id = isa.student_id
                WHERE isa.instructor_id = %s
            """, (user_id,))
            assigned_students = cursor.fetchall()
            
            impact['assignments'] = {
                'count': len(assigned_students),
                'students': assigned_students or []
            }
            
            # Check availability slots
            cursor.execute("""
                SELECT id, day_of_week, start_time, end_time 
                FROM availability WHERE instructor_id = %s
            """, (user_id,))
            availability_slots = cursor.fetchall()
            
            # Convert day numbers to names for display
            for slot in availability_slots:
                slot['day_name'] = convert_day_number_to_name(slot['day_of_week'])
                slot['start_time'] = parse_time_to_12h(slot['start_time'])
                slot['end_time'] = parse_time_to_12h(slot['end_time'])
            
            impact['availability'] = {
                'count': len(availability_slots),
                'slots': availability_slots or []
            }
            
            # Generate recommendations
            if impact['lessons']['future_count'] > 0:
                impact['recommendations'].append({
                    'type': 'warning',
                    'message': f"This instructor has {impact['lessons']['future_count']} future lessons that will be cancelled"
                })
            
            if impact['assignments']['count'] > 0:
                impact['recommendations'].append({
                    'type': 'info', 
                    'message': f"{impact['assignments']['count']} students will lose their instructor assignment"
                })
            
            if impact['lessons']['past_count'] > 0:
                impact['recommendations'].append({
                    'type': 'info',
                    'message': f"{impact['lessons']['past_count']} historical lesson records will be preserved for audit purposes"
                })
        
        return jsonify({'success': True, 'impact': impact}), 200
        
    except Error as e:
        print(f"Database error in deletion impact check: {e}")
        return jsonify({'error': 'Failed to check deletion impact'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/students/<int:student_id>/deletion-impact', methods=['GET'])  
def get_student_deletion_impact(student_id):
    """Get information about what data will be affected when deleting a student"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get student information
        cursor.execute("SELECT id, name, email, phone, instrument FROM students WHERE id = %s", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        impact = {
            'student': student,
            'lessons': {'count': 0, 'future_count': 0, 'past_count': 0},
            'assignments': {'count': 0, 'instructors': []},
            'recommendations': []
        }
        
        # Check lessons (both future and past)
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN lesson_date >= CURDATE() THEN 1 ELSE 0 END) as future,
                   SUM(CASE WHEN lesson_date < CURDATE() THEN 1 ELSE 0 END) as past
            FROM lessons WHERE student_id = %s
        """, (student_id,))
        lesson_counts = cursor.fetchone()
        
        impact['lessons'] = {
            'count': lesson_counts['total'] or 0,
            'future_count': lesson_counts['future'] or 0,
            'past_count': lesson_counts['past'] or 0
        }
        
        # Check instructor assignments
        cursor.execute("""
            SELECT u.id, u.username, u.email 
            FROM users u
            JOIN instructor_student_assignments isa ON u.id = isa.instructor_id
            WHERE isa.student_id = %s AND u.role = 'instructor'
        """, (student_id,))
        assigned_instructors = cursor.fetchall()
        
        impact['assignments'] = {
            'count': len(assigned_instructors),
            'instructors': assigned_instructors or []
        }
        
        # Generate recommendations
        if impact['lessons']['future_count'] > 0:
            impact['recommendations'].append({
                'type': 'warning',
                'message': f"This student has {impact['lessons']['future_count']} future lessons that will be cancelled"
            })
        
        if impact['lessons']['past_count'] > 0:
            impact['recommendations'].append({
                'type': 'info',
                'message': f"{impact['lessons']['past_count']} historical lesson records will be preserved for audit purposes"
            })
        
        return jsonify({'success': True, 'impact': impact}), 200
        
    except Error as e:
        print(f"Database error in student deletion impact check: {e}")
        return jsonify({'error': 'Failed to check deletion impact'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/users/<int:user_id>/delete', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user account and handle all related data"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    # Prevent admin from deleting themselves
    if user_id == session['user']['id']:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    data = request.get_json() or {}
    deletion_reason = data.get('reason', 'No reason provided')
    force_delete = data.get('force', False)  # For bypassing some safety checks
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get user information before deletion
        cursor.execute("SELECT id, username, role, email, phone FROM users WHERE id = %s", (user_id,))
        user_to_delete = cursor.fetchone()
        
        if not user_to_delete:
            return jsonify({'error': 'User not found'}), 404
        
        # Set up transaction handling
        connection.autocommit = False  # Disable autocommit for transaction
        
        deletion_summary = {
            'user': user_to_delete,
            'lessons_cancelled': 0,
            'lessons_archived': 0, 
            'assignments_removed': 0,
            'availability_removed': 0,
            'affected_students': []
        }
        
        # Create audit record
        cursor.execute("""
            INSERT INTO user_deletion_audit 
            (deleted_user_id, deleted_username, deleted_user_role, deleted_user_type,
             deleted_by_admin_id, deleted_by_admin_username, deletion_reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, user_to_delete['username'], user_to_delete['role'], 'user',
            session['user']['id'], session['user']['username'], deletion_reason
        ))
        audit_id = cursor.lastrowid
        
        if user_to_delete['role'] == 'instructor':
            # Handle future lessons - cancel them
            cursor.execute("""
                SELECT l.id, l.student_id, s.name as student_name, s.email as student_email,
                       l.lesson_date, l.lesson_time, l.instrument
                FROM lessons l
                JOIN students s ON l.student_id = s.id
                WHERE l.instructor_id = %s AND l.lesson_date >= CURDATE()
            """, (user_id,))
            future_lessons = cursor.fetchall()
            
            # Cancel future lessons and log affected data
            for lesson in future_lessons:
                # Send cancellation notification if email service is enabled
                try:
                    lesson_data = {
                        'lesson_id': lesson['id'],
                        'student_name': lesson['student_name'],
                        'student_email': lesson['student_email'],
                        'instructor_name': user_to_delete['username'],
                        'instructor_email': user_to_delete['email'],
                        'lesson_date': lesson['lesson_date'].strftime('%A, %B %d, %Y') if lesson['lesson_date'] else 'TBD',
                        'lesson_time': parse_time_to_12h(lesson['lesson_time']) if lesson['lesson_time'] else 'TBD',
                        'instrument': lesson['instrument'] or 'Music'
                    }
                    email_service.send_lesson_notification(lesson_data, 'cancellation')
                except Exception as e:
                    print(f"Failed to send cancellation email for lesson {lesson['id']}: {e}")
                
                # Log affected lesson data
                cursor.execute("""
                    INSERT INTO deletion_affected_data 
                    (deletion_audit_id, affected_table, affected_record_id, affected_record_data, action_taken)
                    VALUES (%s, %s, %s, %s, %s)
                """, (audit_id, 'lessons', lesson['id'], str(lesson), 'cancelled'))
                
                deletion_summary['affected_students'].append({
                    'id': lesson['student_id'], 
                    'name': lesson['student_name']
                })
            
            # Delete future lessons
            cursor.execute("DELETE FROM lessons WHERE instructor_id = %s AND lesson_date >= CURDATE()", (user_id,))
            deletion_summary['lessons_cancelled'] = cursor.rowcount
            
            # Count past lessons that will remain for audit
            cursor.execute("SELECT COUNT(*) as count FROM lessons WHERE instructor_id = %s AND lesson_date < CURDATE()", (user_id,))
            past_lessons_result = cursor.fetchone()
            deletion_summary['lessons_archived'] = past_lessons_result['count'] if past_lessons_result else 0
            
            # Remove instructor-student assignments
            cursor.execute("SELECT student_id FROM instructor_student_assignments WHERE instructor_id = %s", (user_id,))
            assigned_students = cursor.fetchall()
            
            for assignment in assigned_students:
                cursor.execute("""
                    INSERT INTO deletion_affected_data 
                    (deletion_audit_id, affected_table, affected_record_id, affected_record_data, action_taken)
                    VALUES (%s, %s, %s, %s, %s)
                """, (audit_id, 'instructor_student_assignments', assignment['student_id'], str(assignment), 'deleted'))
            
            cursor.execute("DELETE FROM instructor_student_assignments WHERE instructor_id = %s", (user_id,))
            deletion_summary['assignments_removed'] = cursor.rowcount
            
            # Remove availability slots
            cursor.execute("SELECT COUNT(*) as count FROM availability WHERE instructor_id = %s", (user_id,))
            availability_count = cursor.fetchone()
            deletion_summary['availability_removed'] = availability_count['count'] if availability_count else 0
            
            cursor.execute("DELETE FROM availability WHERE instructor_id = %s", (user_id,))
        
        # Soft delete the user account instead of hard delete
        cursor.execute("""
            UPDATE users SET 
                is_deleted = 1, 
                deleted_at = NOW(), 
                deleted_by = %s 
            WHERE id = %s
        """, (session['user']['id'], user_id))
        
        # Update audit record with summary counts
        cursor.execute("""
            UPDATE user_deletion_audit SET 
            affected_lessons_count = %s,
            affected_assignments_count = %s, 
            affected_availability_count = %s,
            related_data_summary = %s
            WHERE id = %s
        """, (
            deletion_summary['lessons_cancelled'] + deletion_summary['lessons_archived'],
            deletion_summary['assignments_removed'],
            deletion_summary['availability_removed'],
            str(deletion_summary),
            audit_id
        ))
        
        # Commit transaction
        connection.commit()
        
        return jsonify({
            'success': True, 
            'message': f'User {user_to_delete["username"]} deleted successfully',
            'summary': deletion_summary
        }), 200
        
    except Error as e:
        # Rollback transaction on error
        connection.rollback()
        print(f"Database error during user deletion: {e}")
        return jsonify({'error': 'Failed to delete user due to database error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/students/<int:student_id>/delete', methods=['DELETE'])
def delete_student(student_id):
    """Delete a student account and handle all related data"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    data = request.get_json() or {}
    deletion_reason = data.get('reason', 'No reason provided')
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get student information before deletion
        cursor.execute("SELECT id, name, email, phone, instrument FROM students WHERE id = %s", (student_id,))
        student_to_delete = cursor.fetchone()
        
        if not student_to_delete:
            return jsonify({'error': 'Student not found'}), 404
        
        # Set up transaction handling
        connection.autocommit = False  # Disable autocommit for transaction
        
        deletion_summary = {
            'student': student_to_delete,
            'lessons_cancelled': 0,
            'lessons_archived': 0,
            'assignments_removed': 0,
            'affected_instructors': []
        }
        
        # Create audit record
        cursor.execute("""
            INSERT INTO user_deletion_audit 
            (deleted_user_id, deleted_username, deleted_user_role, deleted_user_type,
             deleted_by_admin_id, deleted_by_admin_username, deletion_reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            student_id, student_to_delete['name'], 'student', 'student',
            session['user']['id'], session['user']['username'], deletion_reason
        ))
        audit_id = cursor.lastrowid
        
        # Handle future lessons - cancel them and notify instructors
        cursor.execute("""
            SELECT l.id, l.instructor_id, u.username as instructor_name, u.email as instructor_email,
                   l.lesson_date, l.lesson_time, l.instrument
            FROM lessons l
            JOIN users u ON l.instructor_id = u.id
            WHERE l.student_id = %s AND l.lesson_date >= CURDATE()
        """, (student_id,))
        future_lessons = cursor.fetchall()
        
        # Cancel future lessons and send notifications
        for lesson in future_lessons:
            try:
                lesson_data = {
                    'lesson_id': lesson['id'],
                    'student_name': student_to_delete['name'],
                    'student_email': student_to_delete['email'],
                    'instructor_name': lesson['instructor_name'],
                    'instructor_email': lesson['instructor_email'],
                    'lesson_date': lesson['lesson_date'].strftime('%A, %B %d, %Y') if lesson['lesson_date'] else 'TBD',
                    'lesson_time': parse_time_to_12h(lesson['lesson_time']) if lesson['lesson_time'] else 'TBD',
                    'instrument': lesson['instrument'] or 'Music'
                }
                email_service.send_lesson_notification(lesson_data, 'cancellation')
            except Exception as e:
                print(f"Failed to send cancellation email for lesson {lesson['id']}: {e}")
            
            # Log affected lesson data
            cursor.execute("""
                INSERT INTO deletion_affected_data 
                (deletion_audit_id, affected_table, affected_record_id, affected_record_data, action_taken)
                VALUES (%s, %s, %s, %s, %s)
            """, (audit_id, 'lessons', lesson['id'], str(lesson), 'cancelled'))
            
            deletion_summary['affected_instructors'].append({
                'id': lesson['instructor_id'],
                'name': lesson['instructor_name']
            })
        
        # Delete future lessons
        cursor.execute("DELETE FROM lessons WHERE student_id = %s AND lesson_date >= CURDATE()", (student_id,))
        deletion_summary['lessons_cancelled'] = cursor.rowcount
        
        # Count past lessons that will remain for audit
        cursor.execute("SELECT COUNT(*) as count FROM lessons WHERE student_id = %s AND lesson_date < CURDATE()", (student_id,))
        past_lessons_result = cursor.fetchone()
        deletion_summary['lessons_archived'] = past_lessons_result['count'] if past_lessons_result else 0
        
        # Remove instructor-student assignments
        cursor.execute("DELETE FROM instructor_student_assignments WHERE student_id = %s", (student_id,))
        deletion_summary['assignments_removed'] = cursor.rowcount
        
        # Delete the student account
        cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
        
        # Update audit record with summary  
        cursor.execute("""
            UPDATE user_deletion_audit SET 
            affected_lessons_count = %s,
            affected_assignments_count = %s,
            related_data_summary = %s
            WHERE id = %s
        """, (
            deletion_summary['lessons_cancelled'] + deletion_summary['lessons_archived'],
            deletion_summary['assignments_removed'], 
            str(deletion_summary),
            audit_id
        ))
        
        # Commit transaction
        connection.commit()
        
        return jsonify({
            'success': True,
            'message': f'Student {student_to_delete["name"]} deleted successfully',
            'summary': deletion_summary
        }), 200
        
    except Error as e:
        # Rollback transaction on error
        connection.rollback()
        print(f"Database error during student deletion: {e}")
        return jsonify({'error': 'Failed to delete student due to database error'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/users/bulk-delete', methods=['POST'])
def bulk_delete_users():
    """Delete multiple users at once"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    student_ids = data.get('student_ids', [])
    deletion_reason = data.get('reason', 'Bulk deletion - No reason provided')
    
    if not user_ids and not student_ids:
        return jsonify({'error': 'No users or students selected for deletion'}), 400
    
    # Prevent admin from deleting themselves
    if session['user']['id'] in user_ids:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    results = {
        'success': True,
        'deleted_users': [],
        'deleted_students': [],
        'errors': [],
        'total_processed': 0
    }
    
    # Delete users
    for user_id in user_ids:
        try:
            # Make a request to single user deletion endpoint
            response = delete_user(user_id)
            response_data = response[0].get_json()
            
            if response_data.get('success'):
                results['deleted_users'].append({
                    'id': user_id,
                    'message': response_data.get('message', 'Deleted successfully')
                })
            else:
                results['errors'].append({
                    'type': 'user',
                    'id': user_id,
                    'error': response_data.get('error', 'Unknown error')
                })
                results['success'] = False
                
        except Exception as e:
            results['errors'].append({
                'type': 'user', 
                'id': user_id,
                'error': f'Deletion failed: {str(e)}'
            })
            results['success'] = False
    
    # Delete students  
    for student_id in student_ids:
        try:
            response = delete_student(student_id)
            response_data = response[0].get_json()
            
            if response_data.get('success'):
                results['deleted_students'].append({
                    'id': student_id,
                    'message': response_data.get('message', 'Deleted successfully')
                })
            else:
                results['errors'].append({
                    'type': 'student',
                    'id': student_id, 
                    'error': response_data.get('error', 'Unknown error')
                })
                results['success'] = False
                
        except Exception as e:
            results['errors'].append({
                'type': 'student',
                'id': student_id,
                'error': f'Deletion failed: {str(e)}'
            })
            results['success'] = False
    
    results['total_processed'] = len(results['deleted_users']) + len(results['deleted_students']) + len(results['errors'])
    
    return jsonify(results), 200 if results['success'] else 207  # 207 = Multi-Status

@app.route('/api/admin/deletion-audit', methods=['GET'])
def get_deletion_audit_log():
    """Get audit log of all user deletions"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        offset = (page - 1) * per_page
        
        # Get audit records with pagination
        cursor.execute("""
            SELECT * FROM user_deletion_audit 
            ORDER BY deleted_at DESC 
            LIMIT %s OFFSET %s
        """, (per_page, offset))
        
        audit_records = cursor.fetchall()
        
        # Get total count for pagination
        cursor.execute("SELECT COUNT(*) as total FROM user_deletion_audit")
        total_count = cursor.fetchone()['total']
        
        return jsonify({
            'success': True,
            'audit_records': audit_records,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        }), 200
        
    except Error as e:
        print(f"Database error in deletion audit: {e}")
        return jsonify({'error': 'Failed to retrieve audit log'}), 500
    finally:
        cursor.close()
        connection.close()

# Backup and Restore Routes
@app.route('/admin/backup-restore')
def admin_backup_restore():
    """Admin page for database backup and restore operations"""
    if session.get('user', {}).get('role') != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('login'))
    return render_template('admin_backup_restore.html')

@app.route('/api/admin/backups', methods=['GET'])
def list_backups():
    """List all available database backups"""
    if session.get('user', {}).get('role') != 'admin':
        return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
    
    import os
    import subprocess
    
    try:
        backup_dir = 'database_backups'
        backups = []
        
        if os.path.exists(backup_dir):
            for filename in os.listdir(backup_dir):
                if filename.endswith(('.sql', '.sql.gz')):
                    filepath = os.path.join(backup_dir, filename)
                    stat = os.stat(filepath)
                    backups.append({
                        'filename': filename,
                        'size': os.path.getsize(filepath),
                        'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'path': filepath
                    })
        
        # Sort by creation time, newest first
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({'backups': backups}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to list backups: {str(e)}'}), 500

@app.route('/api/admin/backup/create', methods=['POST'])
def create_backup():
    """Create a new database backup"""
    if session.get('user', {}).get('role') != 'admin':
        return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
    
    import subprocess
    import os
    
    try:
        # Run backup script
        script_path = os.path.join(os.getcwd(), 'scripts', 'backup_db.sh')
        
        if not os.path.exists(script_path):
            return jsonify({'error': 'Backup script not found'}), 500
            
        result = subprocess.run([script_path], capture_output=True, text=True, cwd='scripts')
        
        if result.returncode == 0:
            # Log the backup creation
            admin_username = session['user']['username']
            current_time = datetime.now()
            
            # You might want to log this to your audit system
            print(f"[{current_time.isoformat()}] Admin '{admin_username}' created database backup")
            
            return jsonify({
                'message': 'Backup created successfully',
                'output': result.stdout
            }), 200
        else:
            return jsonify({
                'error': 'Backup creation failed',
                'details': result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to create backup: {str(e)}'}), 500

@app.route('/api/admin/backup/download/<filename>')
def download_backup(filename):
    """Download a backup file"""
    if session.get('user', {}).get('role') != 'admin':
        return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
    
    import os
    from flask import send_file
    
    try:
        backup_dir = 'database_backups'
        filepath = os.path.join(backup_dir, filename)
        
        # Security check - ensure filename is safe and exists
        if not os.path.exists(filepath) or not filename.endswith(('.sql', '.sql.gz')):
            return jsonify({'error': 'Backup file not found'}), 404
            
        # Log the download
        admin_username = session['user']['username']
        current_time = datetime.now()
        print(f"[{current_time.isoformat()}] Admin '{admin_username}' downloaded backup: {filename}")
        
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    except Exception as e:
        return jsonify({'error': f'Failed to download backup: {str(e)}'}), 500

@app.route('/api/admin/backup/upload', methods=['POST'])
def upload_backup():
    """Upload a backup file for restoration"""
    if session.get('user', {}).get('role') != 'admin':
        return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
    
    import os
    from werkzeug.utils import secure_filename
    
    try:
        if 'backup_file' not in request.files:
            return jsonify({'error': 'No backup file provided'}), 400
            
        file = request.files['backup_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        # Validate file extension
        if not file.filename.endswith(('.sql', '.sql.gz')):
            return jsonify({'error': 'Invalid file type. Only .sql and .sql.gz files are allowed'}), 400
            
        # Secure filename
        filename = secure_filename(file.filename)
        
        # Create uploads directory if it doesn't exist
        upload_dir = 'uploaded_backups'
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # Log the upload
        admin_username = session['user']['username']
        current_time = datetime.now()
        print(f"[{current_time.isoformat()}] Admin '{admin_username}' uploaded backup: {filename}")
        
        return jsonify({
            'message': 'Backup file uploaded successfully',
            'filename': filename,
            'path': filepath
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to upload backup: {str(e)}'}), 500

@app.route('/api/admin/backup/restore', methods=['POST'])
def restore_backup():
    """Restore database from backup file"""
    if session.get('user', {}).get('role') != 'admin':
        return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
    
    import subprocess
    import os
    
    try:
        data = request.get_json()
        backup_path = data.get('backup_path')
        
        if not backup_path:
            return jsonify({'error': 'Backup path is required'}), 400
            
        # Security check - ensure path exists and is safe
        if not os.path.exists(backup_path):
            return jsonify({'error': 'Backup file not found'}), 404
            
        # Run restore script
        script_path = os.path.join(os.getcwd(), 'scripts', 'restore_db.sh')
        
        if not os.path.exists(script_path):
            return jsonify({'error': 'Restore script not found'}), 500
            
        # Note: For security, this endpoint requires manual confirmation
        # In a production environment, you might want additional safeguards
        
        result = subprocess.run([script_path, backup_path], 
                              capture_output=True, text=True, cwd='scripts',
                              input='YES\n')  # Auto-confirm for API call
        
        if result.returncode == 0:
            # Log the restore operation
            admin_username = session['user']['username']
            current_time = datetime.now()
            
            # You might want to log this to your audit system
            print(f"[{current_time.isoformat()}] Admin '{admin_username}' restored database from: {backup_path}")
            
            return jsonify({
                'message': 'Database restored successfully',
                'output': result.stdout
            }), 200
        else:
            return jsonify({
                'error': 'Database restore failed',
                'details': result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to restore backup: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
