#!/bin/bash

# Music Scheduler Web Application - Installation Script
# This script installs and sets up the Music Scheduler Web Application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

print_info "🎵 Starting Music Scheduler Web Application installation..."

# Check if Python 3 is installed
if ! command_exists python3; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.8"

# Compare versions (simple version comparison for major.minor)
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python $PYTHON_VERSION detected. Python $REQUIRED_VERSION or higher is required."
    exit 1
fi

print_success "Python $PYTHON_VERSION detected"

# Check if pip is installed
if ! command_exists pip3; then
    print_error "pip3 is not installed. Please install pip3."
    exit 1
fi

print_success "pip3 is available"

# Create virtual environment if it doesn't exist
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    print_info "Installing Python dependencies from requirements.txt..."
    pip install -r requirements.txt
    print_success "Dependencies installed successfully (Flask, APScheduler, etc.)"
else
    print_error "requirements.txt file not found!"
    exit 1
fi

# Check if main application exists
if [ -f "app.py" ]; then
    print_info "Music Scheduler application found"
    chmod +x app.py
else
    print_error "app.py file not found! This is the main web application."
    exit 1
fi

# Create templates directory if it doesn't exist
if [ ! -d "templates" ]; then
    print_warning "templates directory not found. Creating it..."
    mkdir -p templates
fi

# Create logs directory if it doesn't exist
if [ ! -d "logs" ]; then
    print_info "Creating logs directory..."
    mkdir -p logs
    print_success "Logs directory created"
fi

# Set executable permissions for Python files
print_info "Setting executable permissions..."
chmod +x *.py

# Initialize database
print_info "Initializing music scheduler database..."
python3 -c "
import sys
sys.path.append('.')
from app import init_db
init_db()
print('Database initialized with sample data')
"
print_success "Database initialized successfully"

# Final verification
print_info "Verifying installation..."

# Test import of required modules
python3 -c "
try:
    import flask
    import apscheduler
    import sqlite3
    print('✓ Flask web framework')
    print('✓ APScheduler for task scheduling')
    print('✓ SQLite3 for database')
    print('All required modules imported successfully')
except ImportError as e:
    print(f'Failed to import: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    print_success "All dependencies verified successfully"
else
    print_error "Failed to import required modules"
    exit 1
fi

print_success "🎉 Installation completed successfully!"
echo ""
print_info "🎵 Music Scheduler Web Application is ready!"
print_info "📊 Dashboard: http://localhost:5000"
print_info "🎶 Features: Playlist management, Music scheduling, Dashboard"
echo ""
print_info "To start the web application:"
print_info "1. Activate the virtual environment: source venv/bin/activate"
print_info "2. Run the application: python3 app.py"
print_info "3. Open your browser to: http://localhost:5000"
echo ""
print_info "🚀 Starting the web application now..."

# Start the web application
nohup python3 app.py > logs/app.log 2>&1 &
APP_PID=$!

# Wait a moment for the server to start
sleep 3

# Check if the server is running
if curl -s http://localhost:5000 > /dev/null 2>&1; then
    print_success "🎉 Music Scheduler web application is now running!"
    print_success "🌐 Access your music scheduler at: http://localhost:5000"
    print_info "📋 Process ID: $APP_PID"
    print_info "📝 Logs available at: logs/app.log"
    echo ""
    print_info "To stop the application: kill $APP_PID"
else
    print_error "Failed to start web application. Check logs/app.log for details."
    kill $APP_PID 2>/dev/null || true
    exit 1
fi
