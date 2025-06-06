from flask import Flask, request, jsonify, session
from flask_session import Session
from flask_bcrypt import Bcrypt
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'd0f33f212484b6776da8332afe37bee7'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = '/music_scheduler/sessions'
app.config['SESSION_FILE_THRESHOLD'] = 500
app.config['SESSION_FILE_MODE'] = 0o660
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
                cursor.execute("""
                    SELECT l.id, l.student_id, l.instructor_id, l.lesson_date, l.lesson_time, l.duration, l.instrument,
                           l.reminder_enabled, l.notes, s.name AS student_name
                    FROM lessons l
                    JOIN students s ON l.student_id = s.id
                """)
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
        cursor.execute("""
            SELECT l.id, l.student_id, l.instructor_id, l.lesson_date, l.lesson_time, l.duration, l.instrument,
                   l.reminder_enabled, l.notes, s.name AS student_name
            FROM lessons l
            JOIN students s ON l.student_id = s.id
            WHERE l.instructor_id = %s
        """, (user_id,))
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
    app.run(debug=True, host='0.0.0.0', port=8000)
