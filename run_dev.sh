#!/bin/bash

# Music Scheduler Development Server Runner
# This script starts both Flask backend and React frontend for development

set -e

PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/venv"
PID_FILE="$PROJECT_DIR/.dev_pids"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🎵 Music Scheduler Development Server${NC}"
echo "==============================================="

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping development servers...${NC}"
    if [ -f "$PID_FILE" ]; then
        while read pid; do
            if ps -p $pid > /dev/null 2>&1; then
                echo "Stopping process $pid"
                kill $pid 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    echo -e "${GREEN}Development servers stopped.${NC}"
    exit 0
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ Virtual environment not found. Please run './setup_dev.sh' first.${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Environment file not found. Please run './setup_dev.sh' first.${NC}"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${RED}❌ Node modules not found. Please run './setup_dev.sh' first.${NC}"
    exit 1
fi

echo -e "${YELLOW}🔧 Activating Python virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

echo -e "${YELLOW}🗄️  Checking database connection...${NC}"
# Test database connection
python3 -c "
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'music_user'),
        password=os.getenv('DB_PASSWORD', 'music_pass'),
        database=os.getenv('DB_NAME', 'music_scheduler')
    )
    if conn.is_connected():
        print('✓ Database connection successful')
        conn.close()
    else:
        print('✗ Database connection failed')
        exit(1)
except Exception as e:
    print(f'✗ Database connection error: {e}')
    exit(1)
" || {
    echo -e "${RED}❌ Database connection failed. Please check your MySQL service and configuration.${NC}"
    exit 1
}

echo -e "${YELLOW}🚀 Starting Flask backend server...${NC}"
# Start Flask backend in background
FLASK_APP=app.py FLASK_ENV=development python3 -m flask run --host=0.0.0.0 --port=5000 > flask.log 2>&1 &
FLASK_PID=$!
echo $FLASK_PID >> "$PID_FILE"

# Wait a moment for Flask to start
sleep 2

# Check if Flask started successfully
if ! ps -p $FLASK_PID > /dev/null; then
    echo -e "${RED}❌ Flask failed to start. Check flask.log for errors.${NC}"
    tail -10 flask.log
    exit 1
fi

echo -e "${GREEN}✓ Flask backend started (PID: $FLASK_PID) at http://localhost:5000${NC}"

# Test Flask health
echo -e "${YELLOW}🔍 Testing Flask backend...${NC}"
sleep 3
if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Flask backend is responding${NC}"
else
    echo -e "${YELLOW}⚠️  Flask backend health check failed (this is normal if no /api/health endpoint exists)${NC}"
fi

echo -e "${YELLOW}⚡ Starting React/Vite frontend server...${NC}"
# Start React/Vite frontend in background
npm run dev > vite.log 2>&1 &
VITE_PID=$!
echo $VITE_PID >> "$PID_FILE"

# Wait a moment for Vite to start
sleep 3

# Check if Vite started successfully
if ! ps -p $VITE_PID > /dev/null; then
    echo -e "${RED}❌ Vite failed to start. Check vite.log for errors.${NC}"
    tail -10 vite.log
    exit 1
fi

echo -e "${GREEN}✓ React frontend started (PID: $VITE_PID)${NC}"

# Wait for Vite to fully start and get the port
sleep 5

echo ""
echo -e "${GREEN}🎉 Development environment is ready!${NC}"
echo "============================================="
echo -e "${GREEN}📱 Frontend:${NC} http://localhost:3000"
echo -e "${GREEN}🔧 Backend:${NC}  http://localhost:5000" 
echo -e "${GREEN}📋 API:${NC}      http://localhost:5000/api/"
echo ""
echo -e "${YELLOW}📊 Test Accounts:${NC}"
echo "  👤 Admin: admin / admin123"
echo "  👨‍🏫 Instructor: john_instructor / instructor123" 
echo "  👩‍🏫 Instructor: jane_instructor / instructor123"
echo ""
echo -e "${YELLOW}📁 Logs:${NC}"
echo "  🐍 Flask: flask.log"
echo "  ⚡ Vite: vite.log"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo "  • Press Ctrl+C to stop all servers"
echo "  • Backend changes require restart"
echo "  • Frontend changes are hot-reloaded"
echo "  • Check logs if you encounter issues"
echo ""
echo -e "${GREEN}Servers are running... Press Ctrl+C to stop.${NC}"

# Keep script running and show live logs
tail -f flask.log &
TAIL_PID=$!
echo $TAIL_PID >> "$PID_FILE"

# Wait for user interruption
while true; do
    sleep 1
done
