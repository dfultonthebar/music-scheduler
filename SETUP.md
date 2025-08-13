# Music Scheduler - Development Environment Setup

A comprehensive Flask + React music lesson scheduling application with MySQL database.

## 🎯 Overview

**Music Scheduler** is a full-stack web application for managing music lessons, students, instructors, and scheduling. The application features:

- **Backend**: Flask REST API with MySQL database
- **Frontend**: React with Vite, Calendar component, and Tailwind CSS
- **Authentication**: Session-based auth with bcrypt password hashing
- **Features**: User management, student management, lesson scheduling, instructor availability

## 📋 Prerequisites

Before setting up the development environment, ensure you have:

- **Ubuntu/Debian Linux** (tested on Ubuntu)
- **Root/sudo access** (for installing system packages)
- **Internet connection** (for downloading packages)

The setup script will automatically install:
- Python 3 and pip
- Node.js and npm
- MySQL server
- Required development tools

## 🚀 Quick Start (One-Command Setup)

1. **Clone and navigate to the project:**
   ```bash
   cd ~/music-scheduler
   ```

2. **Run the setup script:**
   ```bash
   chmod +x setup_dev.sh
   ./setup_dev.sh
   ```

3. **Start the development servers:**
   ```bash
   chmod +x run_dev.sh  
   ./run_dev.sh
   ```

4. **Access the application:**
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:5000
   - **Health Check**: http://localhost:5000/api/health

## 🔧 Detailed Setup

### 1. System Dependencies Installation

The setup script installs the following system packages:
```bash
# Core development tools
python3 python3-venv python3-pip python3-dev build-essential

# Node.js and npm
nodejs npm

# MySQL database server
mysql-server mysql-client libmysqlclient-dev pkg-config
```

### 2. Python Environment Setup

- Creates isolated virtual environment in `./venv/`
- Installs Python dependencies:
  - Flask 2.3.3
  - Flask-Session 0.5.0
  - Flask-Bcrypt 1.0.1
  - mysql-connector-python 8.1.0
  - python-dotenv 1.0.0
  - flask-cors 4.0.0

### 3. Frontend Dependencies

- Installs Node.js dependencies from `package.json`:
  - React 18.2.0
  - React Calendar 6.0.0
  - Vite 6.3.5
  - Tailwind CSS 3.4.1
  - Development tools

### 4. Database Setup

Creates MySQL database with:
- **Database**: `music_scheduler`
- **User**: `music_user`
- **Password**: `music_pass`
- **Full schema** with proper foreign key relationships

### 5. Test Data

The setup script creates comprehensive test data:

**Test Accounts:**
- **Admin**: `admin` / `admin123`
- **Instructors**: 
  - `john_instructor` / `instructor123`
  - `jane_instructor` / `instructor123`

**Sample Data:**
- 5 sample students with contact information
- Instructor availability schedules
- Instrument assignments for instructors
- 3 sample lessons scheduled for next week

## 🗄️ Database Schema

### Tables Overview

1. **users** - System users (admin, instructors)
2. **students** - Music lesson students
3. **lessons** - Scheduled lessons
4. **instructor_availability** - Weekly availability patterns
5. **instructor_time_off** - Time-off periods
6. **instructor_instruments** - Instruments taught by instructors

### Relationships

```
users (admin/instructors)
├── created students
├── scheduled lessons (as instructors)
├── availability schedules
├── time-off periods
└── taught instruments

students
└── booked lessons

lessons
├── belongs to student
└── assigned to instructor
```

## 🔧 Configuration Files

### Environment Variables (`.env`)
```bash
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=dev_secret_key_change_in_production

# Database Configuration  
DB_HOST=localhost
DB_USER=music_user
DB_PASSWORD=music_pass
DB_NAME=music_scheduler

# Session Configuration
SESSION_TYPE=filesystem
SESSION_FILE_DIR=./sessions
```

### Vite Configuration (`vite.config.js`)
```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
```

## 🚦 Running the Application

### Development Servers

The `run_dev.sh` script starts both backend and frontend:

```bash
./run_dev.sh
```

This will:
1. ✅ Check prerequisites (venv, .env, node_modules)
2. ✅ Test database connection
3. 🚀 Start Flask backend on http://localhost:5000
4. ⚡ Start React frontend on http://localhost:3000
5. 📊 Display connection info and test accounts
6. 📁 Show live logs from both servers

### Manual Starting

**Backend only:**
```bash
source venv/bin/activate
FLASK_APP=app.py python3 -m flask run --port=5000
```

**Frontend only:**
```bash
npm run dev
```

### Stopping Servers

Press `Ctrl+C` in the terminal running `run_dev.sh` to stop all servers.

## 🔍 API Endpoints

### Authentication
- `POST /api/login` - User login
- `POST /api/logout` - User logout

### Data Endpoints
- `GET /api/health` - Health check
- `GET /api/users` - List all users (admin only)
- `GET /api/students` - List all students
- `GET /api/lessons` - List all lessons
- `GET /api/availability?instructor_id=X` - Get instructor availability
- `GET /api/instructor-instruments?instructor_id=X` - Get instructor instruments

### Example API Call
```bash
# Health check
curl http://localhost:5000/api/health

# Login  
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

## 🎨 Frontend Features

### Admin Dashboard
- **User Management**: View all system users
- **Student Management**: Add, view, edit students
- **Lesson Scheduling**: Create and manage lessons
- **Calendar Integration**: Visual lesson calendar
- **Instructor Management**: Availability and instruments

### React Components
- **Login Component**: Session-based authentication
- **AdminDashboard**: Main admin interface  
- **Calendar**: React-Calendar integration
- **Forms**: Student/lesson creation forms

## 🛠️ Development Tools

### Logging
- **Flask logs**: `flask.log`
- **Vite logs**: `vite.log`
- **Setup logs**: `setup.log`

### Development Features
- **Hot Reload**: Frontend changes are automatically reloaded
- **Debug Mode**: Flask runs with debug=True
- **CORS**: Frontend-backend communication enabled
- **Session Management**: Filesystem-based sessions

## 🐛 Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check MySQL service
sudo systemctl status mysql
sudo systemctl start mysql

# Verify database exists
mysql -u music_user -p music_pass -e "SHOW DATABASES;"
```

**Port Already in Use**
```bash
# Kill processes on ports 3000/5000
sudo lsof -ti:3000 | xargs kill -9
sudo lsof -ti:5000 | xargs kill -9
```

**Python Virtual Environment Issues**
```bash
# Recreate virtual environment
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Node.js Dependencies Issues**
```bash
# Clean install dependencies
rm -rf node_modules package-lock.json
npm install
```

### Checking Services

**Backend Health:**
```bash
curl http://localhost:5000/api/health
```

**Frontend Accessibility:**
```bash
curl -I http://localhost:3000
```

**Database Connection:**
```bash
mysql -u music_user -p'music_pass' music_scheduler -e "SELECT COUNT(*) FROM users;"
```

### Log Analysis

**Check Flask errors:**
```bash
tail -f flask.log
```

**Check Vite errors:**  
```bash
tail -f vite.log
```

**Check setup issues:**
```bash
tail -50 setup.log
```

## 🔒 Security Notes

### Development vs Production

**⚠️ This setup is for DEVELOPMENT only!**

The following should be changed for production:
- Database credentials (currently `music_user`/`music_pass`)
- Flask secret key
- CORS origins (currently allows localhost:3000)
- Session configuration
- Debug mode (currently enabled)

### Secure Production Setup

For production deployment:
1. Use environment-specific credentials
2. Enable HTTPS/TLS
3. Use production-grade session storage (Redis/database)
4. Configure proper CORS origins
5. Use a production WSGI server (Gunicorn)
6. Set up proper nginx reverse proxy

## 📚 Project Structure

```
music-scheduler/
├── app.py              # Flask backend application
├── vite.config.js      # Vite frontend configuration
├── package.json        # Node.js dependencies
├── requirements.txt    # Python dependencies
├── .env               # Environment configuration
├── setup_dev.sh       # Development setup script
├── run_dev.sh         # Development server runner
├── SETUP.md           # This documentation
├── venv/              # Python virtual environment
├── sessions/          # Flask session storage
├── node_modules/      # Node.js dependencies
├── src/               # React source code
│   ├── index.jsx      # Main React component
│   ├── index.css      # Styling
│   └── main.jsx       # React entry point
└── logs/              # Application logs
    ├── flask.log      # Backend logs
    ├── vite.log       # Frontend logs
    └── setup.log      # Setup script logs
```

## 🎯 Next Steps

1. **Explore the Admin Dashboard** at http://localhost:3000
2. **Test API endpoints** using the provided test accounts
3. **Review the codebase** in `src/index.jsx` and `app.py`
4. **Customize the application** for your specific needs
5. **Add new features** following the existing patterns

## 🤝 Contributing

To contribute to this project:
1. Follow the existing code patterns
2. Test changes with the provided test accounts
3. Update documentation as needed
4. Ensure both frontend and backend work together

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the log files (`flask.log`, `vite.log`, `setup.log`)
3. Verify all services are running (`run_dev.sh` output)
4. Test the health endpoint: http://localhost:5000/api/health

---

**🎵 Happy coding with Music Scheduler! 🎵**
