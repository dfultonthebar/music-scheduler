import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import Calendar from 'react-calendar';
import './src/index.css';

const API_BASE_URL = 'http://192.168.1.63';

const InstructorDashboard = ({ token }) => {
  const [students, setStudents] = useState([]);
  const [availability, setAvailability] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [newAvailability, setNewAvailability] = useState({ day_of_week: '', start_time: '', end_time: '' });
  const [lessonForm, setLessonForm] = useState({
    student_id: '',
    instructor_id: '',
    instrument: '',
    date_time: '',
    duration: '',
    notes: ''
  });
  const [selectedDate, setSelectedDate] = useState(new Date());

  useEffect(() => {
    (async () => {
      try {
        const studentsResponse = await fetch(`${API_BASE_URL}/api/my_students`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const availabilityResponse = await fetch(`${API_BASE_URL}/api/instructor_availability`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const lessonsResponse = await fetch(`${API_BASE_URL}/api/lessons`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        setStudents(await studentsResponse.json());
        setAvailability(await availabilityResponse.json());
        setLessons(await lessonsResponse.json());
      } catch (error) {
        console.error('Error fetching data:', error);
        alert('Error fetching data: ' + error.message);
      }
    })();
  }, [token]);

  const handleAddAvailability = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/instructor_availability`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(newAvailability)
      });
      const result = await response.json();
      alert(result.message);
      setAvailability([...availability, newAvailability]);
      setNewAvailability({ day_of_week: '', start_time: '', end_time: '' });
    } catch (error) {
      console.error('Error adding availability:', error);
      alert('Error adding availability: ' + error.message);
    }
  };

  const handleDeleteAvailability = async (id) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/instructor_availability`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ id })
      });
      const result = await response.json();
      alert(result.message);
      setAvailability(availability.filter(slot => slot.id !== id));
    } catch (error) {
      console.error('Error deleting availability:', error);
      alert('Error deleting availability: ' + error.message);
    }
  };

  const handleAddLesson = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/lessons`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(lessonForm)
      });
      const result = await response.json();
      if (result.error) {
        alert(result.error);
      } else {
        alert(result.message);
        setLessons([...lessons, { ...lessonForm, student_name: students.find(s => s.id === lessonForm.student_id)?.name }]);
        setLessonForm({ student_id: '', instructor_id: '', instrument: '', date_time: '', duration: '', notes: '' });
      }
    } catch (error) {
      console.error('Error scheduling lesson:', error);
      alert('Error scheduling lesson: ' + error.message);
    }
  };

  const handleEditLesson = async (lesson) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/lessons`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ lesson })
      });
      const result = await response.json();
      if (result.error) {
        alert(result.error);
      } else {
        alert(result.message);
        setLessons(lessons.map(l => l.id === lesson.id ? { ...lesson, student_name: students.find(s => s.id === lesson.student_id)?.name } : l));
      }
    } catch (error) {
      console.error('Error updating lesson:', error);
      alert('Error updating lesson: ' + error.message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    window.location.reload();
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl mb-4">Instructor Dashboard</h1>
      <button onClick={handleLogout} className="bg-red-500 text-white p-2 rounded mb-4">Log Out</button>

      <h2 className="text-xl mb-2">My Students</h2>
      <table className="w-full mb-4 border-collapse border">
        <thead>
          <tr>
            <th className="border p-2">Name</th>
            <th className="border p-2">Instrument</th>
            <th className="border p-2">Cell Phone</th>
            <th className="border p-2">Email</th>
          </tr>
        </thead>
        <tbody>
          {students.map(student => (
            <tr key={student.id}>
              <td className="border p-2">{student.name}</td>
              <td className="border p-2">{student.instrument}</td>
              <td className="border p-2">{student.cell_phone}</td>
              <td className="border p-2">{student.email}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="text-xl mb-2">My Availability</h2>
      <table className="w-full mb-4 border-collapse border">
        <thead>
          <tr>
            <th className="border p-2">Day of Week</th>
            <th className="border p-2">Start Time</th>
            <th className="border p-2">End Time</th>
            <th className="border p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {availability.map(slot => (
            <tr key={slot.id}>
              <td className="border p-2">{slot.day_of_week}</td>
              <td className="border p-2">{slot.start_time}</td>
              <td className="border p-2">{slot.end_time}</td>
              <td className="border p-2">
                <button onClick={() => handleDeleteAvailability(slot.id)} className="bg-red-500 text-white p-1 rounded">Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="text-xl mb-2">Add Availability</h2>
      <div className="mb-4">
        <select value={newAvailability.day_of_week} onChange={(e) => setNewAvailability({ ...newAvailability, day_of_week: e.target.value })} className="border p-2 mr-2">
          <option value="">Select Day</option>
          <option value="Monday">Monday</option>
          <option value="Tuesday">Tuesday</option>
          <option value="Wednesday">Wednesday</option>
          <option value="Thursday">Thursday</option>
          <option value="Friday">Friday</option>
          <option value="Saturday">Saturday</option>
          <option value="Sunday">Sunday</option>
        </select>
        <input type="time" value={newAvailability.start_time} onChange={(e) => setNewAvailability({ ...newAvailability, start_time: e.target.value })} className="border p-2 mr-2" />
        <input type="time" value={newAvailability.end_time} onChange={(e) => setNewAvailability({ ...newAvailability, end_time: e.target.value })} className="border p-2 mr-2" />
        <button onClick={handleAddAvailability} className="bg-green-500 text-white p-2 rounded">Add Availability</button>
      </div>

      <h2 className="text-xl mb-2">Schedule Lesson</h2>
      <div className="mb-4">
        <select value={lessonForm.student_id} onChange={(e) => setLessonForm({ ...lessonForm, student_id: e.target.value })} className="border p-2 mr-2">
          <option value="">Select Student</option>
          {students.map(student => (
            <option key={student.id} value={student.id}>{student.name}</option>
          ))}
        </select>
        <input type="text" placeholder="Instrument" value={lessonForm.instrument} onChange={(e) => setLessonForm({ ...lessonForm, instrument: e.target.value })} className="border p-2 mr-2" />
        <input type="datetime-local" value={lessonForm.date_time} onChange={(e) => setLessonForm({ ...lessonForm, date_time: e.target.value })} className="border p-2 mr-2" />
        <input type="number" placeholder="Duration (hours)" value={lessonForm.duration} onChange={(e) => setLessonForm({ ...lessonForm, duration: e.target.value })} className="border p-2 mr-2" />
        <input type="text" placeholder="Notes" value={lessonForm.notes} onChange={(e) => setLessonForm({ ...lessonForm, notes: e.target.value })} className="border p-2 mr-2" />
        <button onClick={handleAddLesson} className="bg-green-500 text-white p-2 rounded">Schedule Lesson</button>
      </div>

      <h2 className="text-xl mb-2">My Lessons</h2>
      <Calendar
        onChange={setSelectedDate}
        value={selectedDate}
        tileClassName={({ date }) => {
          const lessonDates = lessons.map(lesson => new Date(lesson.date_time).toDateString());
          return lessonDates.includes(date.toDateString()) ? 'bg-blue-200' : null;
        }}
      />
      <table className="w-full mt-4 border-collapse border">
        <thead>
          <tr>
            <th className="border p-2">Student</th>
            <th className="border p-2">Instrument</th>
            <th className="border p-2">Date/Time</th>
            <th className="border p-2">Duration</th>
            <th className="border p-2">Notes</th>
            <th className="border p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {lessons.filter(lesson => new Date(lesson.date_time).toDateString() === selectedDate.toDateString()).map(lesson => (
            <tr key={lesson.id}>
              <td className="border p-2">{lesson.student_name}</td>
              <td className="border p-2">{lesson.instrument}</td>
              <td className="border p-2">{lesson.date_time}</td>
              <td className="border p-2">{lesson.duration}</td>
              <td className="border p-2">{lesson.notes}</td>
              <td className="border p-2">
                <button onClick={() => {
                  const updatedLesson = { ...lesson };
                  updatedLesson.student_id = prompt('Student ID:', lesson.student_id) || lesson.student_id;
                  updatedLesson.instrument = prompt('Instrument:', lesson.instrument) || lesson.instrument;
                  updatedLesson.date_time = prompt('Date/Time (YYYY-MM-DDTHH:MM):', lesson.date_time) || lesson.date_time;
                  updatedLesson.duration = prompt('Duration (hours):', lesson.duration) || lesson.duration;
                  updatedLesson.notes = prompt('Notes:', lesson.notes) || lesson.notes;
                  handleEditLesson(updatedLesson);
                }} className="bg-yellow-500 text-white p-1 rounded">Edit</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const App = () => {
  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role');

  if (!token || role !== 'instructor') {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');

    const handleLogin = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        if (data.token) {
          localStorage.setItem('token', data.token);
          localStorage.setItem('role', data.role);
          window.location.reload();
        } else {
          alert(data.error);
        }
      } catch (error) {
        console.error('Error during login:', error);
        alert('Error during login: ' + error.message);
      }
    };

    return (
      <div className="p-6">
        <h1 className="text-2xl mb-4">Login</h1>
        <input type="text" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} className="border p-2 mb-2 w-full" />
        <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} className="border p-2 mb-2 w-full" />
        <button onClick={handleLogin} className="bg-blue-500 text-white p-2 rounded">Login</button>
      </div>
    );
  }

  return <InstructorDashboard token={token} />;
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
