from flask import Flask, request, jsonify, session
from flask_session import Session
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os
from dotenv import load_dotenv

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
    """User login endpoint"""
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Username and password required'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'message': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if user and bcrypt.check_password_hash(user['password'], password):
            session['user'] = {
                'username': username, 
                'role': user['role'], 
                'id': user['id']
            }
            return jsonify({
                'message': 'Login successful', 
                'role': user['role'],
                'user_id': user['id']
            }), 200
        else:
            return jsonify({'message': 'Invalid credentials'}), 401
            
    except Error as e:
        print(f"Login error: {e}")
        return jsonify({'message': 'Login failed'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users - admin only"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        return jsonify({'users': users}), 200
    except Error as e:
        print(f"Get users error: {e}")
        return jsonify({'error': 'Failed to fetch users'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/students', methods=['GET'])
def get_students():
    """Get all students"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*, u.username as created_by_username 
            FROM students s 
            LEFT JOIN users u ON s.created_by = u.id 
            ORDER BY s.created_at DESC
        """)
        students = cursor.fetchall()
        return jsonify({'students': students}), 200
    except Error as e:
        print(f"Get students error: {e}")
        return jsonify({'error': 'Failed to fetch students'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/lessons', methods=['GET'])
def get_lessons():
    """Get all lessons"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT l.*, 
                   s.name as student_name, s.email as student_email,
                   u.username as instructor_name
            FROM lessons l
            JOIN students s ON l.student_id = s.id
            JOIN users u ON l.instructor_id = u.id
            ORDER BY l.lesson_date DESC, l.lesson_time DESC
        """)
        lessons = cursor.fetchall()
        
        # Convert date and time objects to strings for JSON serialization
        for lesson in lessons:
            if lesson['lesson_date']:
                lesson['lesson_date'] = lesson['lesson_date'].strftime('%Y-%m-%d')
            if lesson['lesson_time']:
                lesson['lesson_time'] = str(lesson['lesson_time'])
            if lesson['created_at']:
                lesson['created_at'] = lesson['created_at'].isoformat()
        
        return jsonify({'lessons': lessons}), 200
    except Error as e:
        print(f"Get lessons error: {e}")
        return jsonify({'error': 'Failed to fetch lessons'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/availability', methods=['GET'])
def get_availability():
    """Get instructor availability"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    instructor_id = request.args.get('instructor_id')
    if not instructor_id:
        return jsonify({'error': 'instructor_id parameter required'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM instructor_availability 
            WHERE instructor_id = %s 
            ORDER BY FIELD(day_of_week, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
        """, (instructor_id,))
        availability = cursor.fetchall()
        
        # Convert time objects to strings
        for avail in availability:
            if avail['start_time']:
                avail['start_time'] = str(avail['start_time'])
            if avail['end_time']:
                avail['end_time'] = str(avail['end_time'])
            if avail['created_at']:
                avail['created_at'] = avail['created_at'].isoformat()
        
        return jsonify({'availability': availability}), 200
    except Error as e:
        print(f"Get availability error: {e}")
        return jsonify({'error': 'Failed to fetch availability'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/instructor-instruments', methods=['GET']) 
def get_instructor_instruments():
    """Get instruments for an instructor"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    instructor_id = request.args.get('instructor_id')
    if not instructor_id:
        return jsonify({'error': 'instructor_id parameter required'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM instructor_instruments WHERE instructor_id = %s", (instructor_id,))
        instruments = cursor.fetchall()
        return jsonify({'instruments': instruments}), 200
    except Error as e:
        print(f"Get instructor instruments error: {e}")
        return jsonify({'error': 'Failed to fetch instruments'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Ensure sessions directory exists
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    
    print("🎵 Music Scheduler Flask Backend")
    print(f"Database: {db_config['host']}/{db_config['database']}")
    print(f"Session dir: {app.config['SESSION_FILE_DIR']}")
    print("Starting development server...")
    
    app.run(
        debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true',
        host='0.0.0.0',
        port=5000
    )
