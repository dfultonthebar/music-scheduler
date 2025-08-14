#!/bin/bash

# Music Scheduler Update System - Installation Script
# This script installs and sets up the Music Scheduler Update System

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

print_info "Starting Music Scheduler Update System installation..."

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
    print_success "Dependencies installed successfully"
else
    print_error "requirements.txt file not found!"
    exit 1
fi

# Check if database schema file exists
if [ -f "database_schema.sql" ]; then
    print_info "Database schema file found"
else
    print_warning "database_schema.sql file not found. Some features may not work properly."
fi

# Check if config file exists
if [ -f "config.json" ]; then
    print_info "Configuration file found"
else
    print_warning "config.json file not found. You may need to create configuration."
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

# Final verification
print_info "Verifying installation..."

# Test import of requests module
python3 -c "import requests; print('requests module imported successfully')" 2>/dev/null
if [ $? -eq 0 ]; then
    print_success "All dependencies verified successfully"
else
    print_error "Failed to import required modules"
    exit 1
fi

print_success "Installation completed successfully!"
print_info "To use the system:"
print_info "1. Activate the virtual environment: source venv/bin/activate"
print_info "2. Configure your settings in config.json"
print_info "3. Run the desired Python scripts"

print_info "Installation finished. The Music Scheduler Update System is ready to use."
