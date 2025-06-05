#!/bin/bash

echo "Starting setup_admin.sh logging at $(date)"
exec > >(tee -a /music_scheduler/logs/setup_admin.log) 2>&1

echo "Debug: Logging initialized for setup_admin.sh"

# Update index.jsx with AdminDashboard
echo "Updating index.jsx with AdminDashboard..."
cat > /music_scheduler/src/index.jsx << 'EOF'
import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import { Calendar, dateFnsLocalizer } from 'react-big-calendar';
import format from 'date-fns/format';
import parse from 'date-fns/parse';
import startOfWeek from 'date-fns/startOfWeek';
import getDay from 'date-fns/getDay';
import 'react-big-calendar/lib/css/react-big-calendar.css';

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
});

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [role, setRole] = useState(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [users, setUsers] = useState([]);
  const [students, setStudents] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [newUser, setNewUser] = useState({ username: '', password: '', role: 'instructor' });
  const [newStudent, setNewStudent] = useState({ name: '', email: '', phone: '' });
  const [newLesson, setNewLesson] = useState({
    student_id: '',
    instructor_id: '',
    lesson_date: '',
    lesson_time: '',
    duration: '',
    instrument: '',
    reminder_enabled: false,
  });
  const [error, setError] = useState('');

  useEffect(() => {
    fetch('/api/check-auth')
      .then(res => res.json())
      .then(data => {
        setIsAuthenticated(data.authenticated);
        setRole(data.role);
        if (data.authenticated && data.role === 'admin') {
          fetchUsers();
          fetchStudents();
          fetchLessons();
        }
      })
      .catch(err => setError('Failed to check authentication'));
  }, []);

  const fetchUsers = async () => {
    try {
      const res = await fetch('/api/users');
      const data = await res.json();
      setUsers(data.users);
    } catch (err) {
      setError('Failed to fetch users');
    }
  };

  const fetchStudents = async () => {
    try {
      const res = await fetch('/api/students');
      const data = await res.json();
      setStudents(data.students);
    } catch (err) {
      setError('Failed to fetch students');
    }
  };

  const fetchLessons = async () => {
    try {
      const res = await fetch('/api/lessons');
      const data = await res.json();
      setLessons(data.lessons.map(lesson => ({
        ...lesson,
        start: new Date(`${lesson.lesson_date}T${lesson.lesson_time}`),
        end: new Date(new Date(`${lesson.lesson_date}T${lesson.lesson_time}`).getTime() + lesson.duration * 60000),
        title: `${lesson.student_name} - ${lesson.instrument}`,
      })));
    } catch (err) {
      setError('Failed to fetch lessons');
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (data.authenticated) {
        setIsAuthenticated(true);
        setRole(data.role);
        setError('');
        if (data.role === 'admin') {
          fetchUsers();
          fetchStudents();
          fetchLessons();
        }
      } else {
        setError('Invalid credentials');
      }
    } catch (err) {
      setError('Failed to login');
    }
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/logout', { method: 'POST' });
      setIsAuthenticated(false);
      setRole(null);
    } catch (err) {
      setError('Failed to logout');
    }
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newUser),
      });
      const data = await res.json();
      if (data.message) {
        setNewUser({ username: '', password: '', role: 'instructor' });
        fetchUsers();
        setError('');
      } else {
        setError(data.error || 'Failed to add user');
      }
    } catch (err) {
      setError('Failed to add user');
    }
  };

  const handleAddStudent = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/students', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newStudent),
      });
      const data = await res.json();
      if (data.message) {
        setNewStudent({ name: '', email: '', phone: '' });
        fetchStudents();
        setError('');
      } else {
        setError(data.error || 'Failed to add student');
      }
    } catch (err) {
      setError('Failed to add student');
    }
  };

  const handleAddLesson = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/lessons', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newLesson),
      });
      const data = await res.json();
      if (data.message) {
        setNewLesson({
          student_id: '',
          instructor_id: '',
          lesson_date: '',
          lesson_time: '',
          duration: '',
          instrument: '',
          reminder_enabled: false,
        });
        fetchLessons();
        setError('');
      } else {
        setError(data.error || 'Failed to add lesson');
      }
    } catch (err) {
      setError('Failed to add lesson');
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto p-4">
        <h1 className="text-3xl font-bold mb-4">Music Lesson Scheduler</h1>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="border p-2 w-full"
            />
          </div>
          <div>
            <label className="block">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="border p-2 w-full"
            />
          </div>
          <button type="submit" className="bg-blue-500 text-white p-2 rounded">Login</button>
          {error && <p className="text-red-500">{error}</p>}
        </form>
      </div>
    );
  }

  if (role === 'admin') {
    return (
      <div className="container mx-auto p-4">
        <h1 className="text-3xl font-bold mb-4">Admin Dashboard</h1>
        <button onClick={handleLogout} className="bg-red-500 text-white p-2 rounded mb-4">Logout</button>
        {error && <p className="text-red-500 mb-4">{error}</p>}

        <h2 className="text-2xl font-semibold mb-2">Manage Users</h2>
        <form onSubmit={handleAddUser} className="space-y-4 mb-4">
          <div>
            <label className="block">Username</label>
            <input
              type="text"
              value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
              className="border p-2 w-full"
            />
          </div>
          <div>
            <label className="block">Password</label>
            <input
              type="password"
              value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
              className="border p-2 w-full"
            />
          </div>
          <div>
            <label className="block">Role</label>
            <select
              value={newUser.role}
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
              className="border p-2 w-full"
            >
              <option value="admin">Admin</option>
              <option value="instructor">Instructor</option>
            </select>
          </div>
          <button type="submit" className="bg-blue-500 text-white p-2 rounded">Add User</button>
        </form>
        <ul className="mb-4">
          {users.map(user => (
            <li key={user.id} className="border-b py-2">{user.username} ({user.role})</li>
          ))}
        </ul>

        <h2 className="text-2xl font-semibold mb-2">Manage Students</h2>
        <form onSubmit={handleAddStudent} className="space-y-4 mb-4">
          <div>
            <label className="block">Name</label>
            <input
              type="text"
              value={newStudent.name}
              onChange={(e) => setNewStudent({ ...newStudent, name: e.target.value })}
              className="border p-2 w-full"
            />
          </div>
          <div>
            <label className="block">Email</label>
            <input
              type="email"
              value={newStudent.email}
              onChange={(e) => setNewStudent({ ...newStudent, email: e.target.value })}
              className="border p-2 w-full"
            />
          </div>
          <div>
            <label className="block">Phone</label>
            <input
              type="text"
              value={newStudent.phone}
              onChange={(e) => setNewStudent({ ...newStudent, phone: e.target.value })}
              className="border p-2 w-full"
            />
          </div>
          <button type="submit" className="bg-blue-500 text-white p-2 rounded">Add Student</button>
        </form>
        <ul className="mb-4">
          {students.map(student => (
            <li key={student.id} className="border-b py-2">
              {student.name} (Email: {student.email || 'N/A'}, Phone: {student.phone || 'N/A'})
            </li>
          ))}
        </ul>

        <h2 className="text-2xl font-semibold mb-2">Schedule Lesson</h2>
        <form onSubmit={handleAddLesson} className="space-y-4 mb-4">
          <div>
            <label className="block">Student</label>
            <select
              value={newLesson.student_id}
              onChange={(e) => setNewLesson({ ...newLesson, student_id: e.target.value })}
              className="border p-2 w-full"
            >
              <option value="">Select Student</option>
              {students.map(student => (
                <option key={student.id} value={student.id}>{student.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block">Instructor</label>
            <select
              value={newLesson.instructor_id}
              onChange={(e) => setNewLesson({ ...newLesson, instructor_id: e.target.value })}
              className="border p-2 w-full"
            >
              <option value="">Select Instructor</option>
              {users.filter(u => u.role === 'instructor').map(user => (
                <option key={user.id} value={user.id}>{user.username}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block">Date</label>
            <input
              type="date"
              value={newLesson.lesson_date}
              onChange={(e) => setNewLesson({ ...newLesson, lesson_date: e.target.value })}
              className="border p-2 w-full"
            />
          </div>
          <div>
            <label className="block">Time</label>
            <input
              type="time"
              value={newLesson.lesson_time}
              onChange={(e) => setNewLesson({ ...newLesson, lesson_time: e.target.value })}
              className="border p-2 w-full"
            />
          </div>
          <div>
            <label className="block">Duration (minutes)</label>
            <input
              type="number"
              value={newLesson.duration}
              onChange={(e) => setNewLesson({ ...newLesson, duration: e.target.value })}
              className="border p-2 w-full"
            />
          </div>
          <div>
            <label className="block">Instrument</label>
            <input
              type="text"
              value={newLesson.instrument}
              onChange={(e) => setNewLesson({ ...newLesson, instrument: e.target.value })}
              className="border p-2 w-full"
            />
          </div>
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={newLesson.reminder_enabled}
                onChange={(e) => setNewLesson({ ...newLesson, reminder_enabled: e.target.checked })}
                className="mr-2"
              />
              Send Reminder
            </label>
          </div>
          <button type="submit" className="bg-blue-500 text-white p-2 rounded">Add Lesson</button>
        </form>

        <h2 className="text-2xl font-semibold mb-2">Lesson Calendar</h2>
        <Calendar
          localizer={localizer}
          events={lessons}
          startAccessor="start"
          endAccessor="end"
          style={{ height: 500 }}
          className="mb-4"
        />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">Music Lesson Scheduler</h1>
      <p>Welcome, {username}! Your role: {role}</p>
      <button onClick={handleLogout} className="bg-red-500 text-white p-2 rounded mt-4">Logout</button>
      {error && <p className="text-red-500">{error}</p>}
    </div>
  );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
EOF

# Create index.html for Vite
echo "Recreating index.html for Vite..."
cat > /music_scheduler/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Music Lesson Scheduler</title>
  <link rel="stylesheet" href="/static/tailwind.css">
  <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/index.jsx"></script>
</body>
</html>
EOF

# Rebuild React app with AdminDashboard
echo "Rebuilding React app with AdminDashboard..."
cd /music_scheduler
npm install react-big-calendar date-fns@2.30.0
npm run build

# Rebuild Tailwind CSS
echo "Rebuilding Tailwind CSS..."
npx tailwindcss -i /music_scheduler/src/index.css -o /music_scheduler/static/tailwind.css --minify
if [ -f /music_scheduler/static/tailwind.css ]; then
  echo "tailwind.css successfully rebuilt."
  ls -l /music_scheduler/static/tailwind.css
else
  echo "Error: tailwind.css not created."
  exit 1
fi

# Remove incorrect index.html from /music_scheduler/
echo "Removing incorrect index.html from /music_scheduler/..."
rm -f /music_scheduler/index.html

echo "Admin setup complete! Check the setup log for details: cat /music_scheduler/logs/setup_admin.log"
