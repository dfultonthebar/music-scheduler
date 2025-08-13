#!/bin/bash

# Music Scheduler Development Environment Setup
# This script sets up a complete development environment for the Flask + React music scheduler

set -e  # Exit on error

PROJECT_DIR="$(pwd)"
LOG_FILE="$PROJECT_DIR/setup.log"
VENV_DIR="$PROJECT_DIR/venv"
DB_NAME="music_scheduler"
DB_USER="music_user"
DB_PASS="music_pass"

echo "=== Music Scheduler Development Environment Setup ===" | tee "$LOG_FILE"
echo "Started at: $(date)" | tee -a "$LOG_FILE"
echo "Project directory: $PROJECT_DIR" | tee -a "$LOG_FILE"

# Function to log and execute commands
log_exec() {
    echo "Executing: $*" | tee -a "$LOG_FILE"
    "$@" 2>&1 | tee -a "$LOG_FILE"
}

# Function to check command success
check_success() {
    if [ $? -eq 0 ]; then
        echo "✓ $1 successful" | tee -a "$LOG_FILE"
    else
        echo "✗ $1 failed" | tee -a "$LOG_FILE"
        exit 1
    fi
}

echo "" | tee -a "$LOG_FILE"
echo "Step 1: Installing system dependencies..." | tee -a "$LOG_FILE"

# Update package list
log_exec sudo apt-get update
check_success "Package list update"

# Install system dependencies
log_exec sudo apt-get install -y python3 python3-venv python3-pip python3-dev build-essential nodejs npm mysql-server mysql-client libmysqlclient-dev pkg-config
check_success "System dependencies installation"

echo "" | tee -a "$LOG_FILE"
echo "Step 2: Setting up Python virtual environment..." | tee -a "$LOG_FILE"

# Create virtual environment
log_exec python3 -m venv "$VENV_DIR"
check_success "Virtual environment creation"

# Activate virtual environment and install Python packages
source "$VENV_DIR/bin/activate"
check_success "Virtual environment activation"

echo "" | tee -a "$LOG_FILE"
echo "Step 3: Creating requirements.txt..." | tee -a "$LOG_FILE"

# Create requirements.txt with all needed packages
cat > requirements.txt << EOF
Flask==2.3.3
Flask-Session==0.5.0
Flask-Bcrypt==1.0.1
mysql-connector-python==8.1.0
python-dotenv==1.0.0
flask-cors==4.0.0
EOF

echo "Created requirements.txt with Flask dependencies" | tee -a "$LOG_FILE"

# Install Python requirements
log_exec pip install --upgrade pip
log_exec pip install -r requirements.txt
check_success "Python requirements installation"

echo "" | tee -a "$LOG_FILE"
echo "Step 4: Setting up Node.js dependencies..." | tee -a "$LOG_FILE"

# Install Node.js dependencies
if [ -f "package.json" ]; then
    log_exec npm install
    check_success "Node.js dependencies installation"
else
    echo "Warning: package.json not found, skipping npm install" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "Step 5: Setting up MySQL database..." | tee -a "$LOG_FILE"

# Start MySQL service
log_exec sudo systemctl start mysql
log_exec sudo systemctl enable mysql
check_success "MySQL service start"

# Create database and user (using temporary SQL file for security)
TEMP_SQL=$(mktemp)
cat > "$TEMP_SQL" << EOF
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\`;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
EOF

# Execute SQL commands
log_exec sudo mysql -u root < "$TEMP_SQL"
rm "$TEMP_SQL"
check_success "Database and user creation"

echo "" | tee -a "$LOG_FILE"
echo "Step 6: Creating database schema..." | tee -a "$LOG_FILE"

# Create database schema
SCHEMA_SQL=$(mktemp)
cat > "$SCHEMA_SQL" << EOF
USE \`$DB_NAME\`;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'instructor') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(255),
    instrument VARCHAR(255),
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS lessons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    instructor_id INT,
    lesson_date DATE NOT NULL,
    lesson_time TIME NOT NULL,
    duration INT NOT NULL,
    instrument VARCHAR(255) NOT NULL,
    reminder_enabled BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (instructor_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS instructor_availability (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instructor_id INT,
    day_of_week ENUM('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday') NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instructor_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS instructor_time_off (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instructor_id INT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instructor_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS instructor_instruments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instructor_id INT,
    instrument VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instructor_id) REFERENCES users(id) ON DELETE CASCADE
);
EOF

log_exec mysql -u "$DB_USER" -p"$DB_PASS" < "$SCHEMA_SQL"
rm "$SCHEMA_SQL"
check_success "Database schema creation"

echo "" | tee -a "$LOG_FILE"
echo "Step 7: Inserting test data..." | tee -a "$LOG_FILE"

# Insert test data
# First, create hashed password using Python
HASHED_PASSWORD=$(python3 -c "
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()
print(bcrypt.generate_password_hash('admin123').decode('utf-8'))
")

HASHED_INSTRUCTOR_PASSWORD=$(python3 -c "
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()
print(bcrypt.generate_password_hash('instructor123').decode('utf-8'))
")

# Insert test data
TEST_DATA_SQL=$(mktemp)
cat > "$TEST_DATA_SQL" << EOF
USE \`$DB_NAME\`;

-- Insert test users
INSERT IGNORE INTO users (username, password, role) VALUES 
('admin', '$HASHED_PASSWORD', 'admin'),
('john_instructor', '$HASHED_INSTRUCTOR_PASSWORD', 'instructor'),
('jane_instructor', '$HASHED_INSTRUCTOR_PASSWORD', 'instructor');

-- Get user IDs for foreign key references
SET @admin_id = (SELECT id FROM users WHERE username = 'admin');
SET @john_id = (SELECT id FROM users WHERE username = 'john_instructor');  
SET @jane_id = (SELECT id FROM users WHERE username = 'jane_instructor');

-- Insert test students
INSERT IGNORE INTO students (name, email, phone, instrument, created_by) VALUES
('Emma Watson', 'emma@example.com', '555-0101', 'Piano', @admin_id),
('Liam Johnson', 'liam@example.com', '555-0102', 'Guitar', @admin_id),
('Olivia Brown', 'olivia@example.com', '555-0103', 'Violin', @admin_id),
('Noah Davis', 'noah@example.com', '555-0104', 'Drums', @admin_id),
('Ava Wilson', 'ava@example.com', '555-0105', 'Piano', @admin_id);

-- Insert instructor instruments
INSERT IGNORE INTO instructor_instruments (instructor_id, instrument) VALUES
(@john_id, 'Piano'),
(@john_id, 'Guitar'),
(@jane_id, 'Violin'),
(@jane_id, 'Piano');

-- Insert instructor availability (John - Mon, Wed, Fri)
INSERT IGNORE INTO instructor_availability (instructor_id, day_of_week, start_time, end_time) VALUES
(@john_id, 'Monday', '09:00:00', '17:00:00'),
(@john_id, 'Wednesday', '09:00:00', '17:00:00'),
(@john_id, 'Friday', '09:00:00', '17:00:00');

-- Insert instructor availability (Jane - Tue, Thu, Sat)  
INSERT IGNORE INTO instructor_availability (instructor_id, day_of_week, start_time, end_time) VALUES
(@jane_id, 'Tuesday', '10:00:00', '18:00:00'),
(@jane_id, 'Thursday', '10:00:00', '18:00:00'),
(@jane_id, 'Saturday', '09:00:00', '15:00:00');

-- Insert some test lessons (next week)
INSERT IGNORE INTO lessons (student_id, instructor_id, lesson_date, lesson_time, duration, instrument, reminder_enabled) VALUES
((SELECT id FROM students WHERE name = 'Emma Watson'), @john_id, DATE_ADD(CURDATE(), INTERVAL 7 DAY), '10:00:00', 60, 'Piano', true),
((SELECT id FROM students WHERE name = 'Liam Johnson'), @john_id, DATE_ADD(CURDATE(), INTERVAL 9 DAY), '14:00:00', 45, 'Guitar', false),
((SELECT id FROM students WHERE name = 'Olivia Brown'), @jane_id, DATE_ADD(CURDATE(), INTERVAL 8 DAY), '11:00:00', 60, 'Violin', true);
EOF

log_exec mysql -u "$DB_USER" -p"$DB_PASS" < "$TEST_DATA_SQL"
rm "$TEST_DATA_SQL"
check_success "Test data insertion"

echo "" | tee -a "$LOG_FILE"
echo "Step 8: Creating environment configuration..." | tee -a "$LOG_FILE"

# Create .env file for Flask
cat > .env << EOF
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=dev_secret_key_change_in_production

# Database Configuration
DB_HOST=localhost
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS
DB_NAME=$DB_NAME

# Session Configuration
SESSION_TYPE=filesystem
SESSION_FILE_DIR=./sessions
EOF

echo "Created .env file with development configuration" | tee -a "$LOG_FILE"

# Create sessions directory
mkdir -p sessions
check_success "Sessions directory creation"

echo "" | tee -a "$LOG_FILE"
echo "Step 9: Updating application configuration..." | tee -a "$LOG_FILE"

# Create backup of original app.py
if [ ! -f app.py.backup ]; then
    cp app.py app.py.backup
    echo "Created backup of original app.py" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "Development environment setup completed successfully!" | tee -a "$LOG_FILE"
echo "Completed at: $(date)" | tee -a "$LOG_FILE"

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Summary:"
echo "  • Python virtual environment: $VENV_DIR"
echo "  • Database: $DB_NAME"
echo "  • Database user: $DB_USER"  
echo "  • Database password: $DB_PASS"
echo ""
echo "👤 Test accounts created:"
echo "  • Admin: username='admin', password='admin123'"
echo "  • Instructor: username='john_instructor', password='instructor123'"
echo "  • Instructor: username='jane_instructor', password='instructor123'"
echo ""
echo "🗄️ Test data includes:"
echo "  • 5 sample students"
echo "  • 2 instructors with availability and instruments"
echo "  • 3 sample lessons scheduled for next week"
echo ""
echo "🚀 Next steps:"
echo "  1. Run './run_dev.sh' to start the application"
echo "  2. Open http://localhost:3000 for frontend"
echo "  3. Backend API will be available at http://localhost:5000"
echo ""
echo "📁 Check setup.log for detailed logs"
