import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';

const AdminDashboard = ({ handleLogout, error, setError }) => {
  const [users, setUsers] = useState([]);
  const [students, setStudents] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [availability, setAvailability] = useState([]);
  const [timeOff, setTimeOff] = useState([]);
  const [instructorInstruments, setInstructorInstruments] = useState([]);
  const [newUser, setNewUser] = useState({ username: '', password: '', role: 'instructor' });
  const [newStudent, setNewStudent] = useState({ name: '', email: '', phone: '', instrument: '' });
  const [newLesson, setNewLesson] = useState({
    student_id: '',
    instructor_id: '',
    lesson_date: '',
    lesson_time: '',
    duration: '',
    instrument: '',
    reminder_enabled: false,
  });
  const [loadingLessons, setLoadingLessons] = useState(true);

  useEffect(() => {
    fetchUsers();
    fetchStudents();
    fetchLessons();
  }, []);

  useEffect(() => {
    if (newLesson.instructor_id) {
      fetchAvailability(newLesson.instructor_id);
      fetchTimeOff(newLesson.instructor_id);
      fetchInstructorInstruments(newLesson.instructor_id);
    } else {
      setInstructorInstruments([]);
      setNewLesson(prev => ({ ...prev, instrument: '' }));
    }
  }, [newLesson.instructor_id]);

  const fetchUsers = async () => {
    try {
      const res = await fetch('/api/users');
      const data = await res.json();
      setUsers(data.users || []);
    } catch (err) {
      setError('Failed to fetch users');
      console.error('Fetch users error:', err);
    }
  };

  const fetchStudents = async () => {
    try {
      const res = await fetch('/api/students');
      const data = await res.json();
      setStudents(data.students || []);
    } catch (err) {
      setError('Failed to fetch students');
      console.error('Fetch students error:', err);
    }
  };

  const fetchLessons = async () => {
    try {
      setLoadingLessons(true);
      const res = await fetch('/api/lessons');
      const data = await res.json();
      if (data.error) {
        throw new Error(data.error);
      }
      const validLessons = (data.lessons || []).filter(lesson => {
        const isValid = (
          lesson.lesson_date &&
          lesson.lesson_time &&
          lesson.duration &&
          lesson.student_name &&
          lesson.instructor_id
        );
        if (!isValid) {
          console.warn('Invalid lesson data:', lesson);
        }
        return isValid;
      });
      setLessons(validLessons);
    } catch (err) {
      setError('Failed to fetch lessons: ' + err.message);
      setLessons([]);
      console.error('Fetch lessons error:', err);
    } finally {
      setLoadingLessons(false);
    }
  };

  const fetchAvailability = async (instructorId) => {
    try {
      const res = await fetch(`/api/availability?instructor_id=${instructorId}`);
      const data = await res.json();
      if (data.error) {
        throw new Error(data.error);
      }
      setAvailability(data.availability || []);
    } catch (err) {
      setError('Failed to fetch availability: ' + err.message);
      setAvailability([]);
      console.error('Fetch availability error:', err);
    }
  };

  const fetchTimeOff = async (instructorId) => {
    try {
      const res = await fetch(`/api/time-off?instructor_id=${instructorId}`);
      const data = await res.json();
      if (data.error) {
        throw new Error(data.error);
      }
      setTimeOff(data.time_off || []);
    } catch (err) {
      setError('Failed to fetch time off: ' + err.message);
      setTimeOff([]);
      console.error('Fetch time off error:', err);
    }
  };

  const fetchInstructorInstruments = async (instructorId) => {
    try {
      const res = await fetch(`/api/instruments?instructor_id=${instructorId}`);
      const data = await res.json();
      if (data.error) {
        throw new Error(data.error);
      }
      setInstructorInstruments(data.instruments || []);
    } catch (err) {
      setError('Failed to fetch instructor instruments: ' + err.message);
      setInstructorInstruments([]);
      console.error('Fetch instructor instruments error:', err);
    }
  };

  const checkInstructorAvailability = () => {
    console.log('Checking instructor availability with lesson data:', newLesson);
    if (!newLesson.instructor_id || !newLesson.lesson_date || !newLesson.lesson_time || !newLesson.duration || !newLesson.instrument) {
      alert('Please fill in all required fields.');
      return false;
    }

    // Check if the lesson date and time are in the future
    const lessonDateTime = new Date(`${newLesson.lesson_date}T${newLesson.lesson_time}`);
    const currentTime = new Date();
    if (lessonDateTime <= currentTime) {
      alert('Cannot schedule a lesson in the past.');
      return false;
    }

    const lessonDate = lessonDateTime.toISOString().split('T')[0];
    const lessonDay = lessonDateTime.toLocaleString('en-US', { weekday: 'long' });
    const lessonTime = lessonDateTime.toTimeString().split(' ')[0].substring(0, 5);

    // Check if the instructor is on time off
    const isOnTimeOff = timeOff.some(slot => {
      const startDate = new Date(slot.start_date);
      const endDate = new Date(slot.end_date);
      return lessonDateTime >= startDate && lessonDateTime <= endDate;
    });

    if (isOnTimeOff) {
      alert(`Instructor is on time off on ${lessonDate}.`);
      return false;
    }

    // Check if the instructor is available on this day and time
    const isAvailable = availability.some(slot => {
      if (slot.day_of_week !== lessonDay) return false;
      const slotStart = slot.start_time.substring(0, 5);
      const slotEnd = slot.end_time.substring(0, 5);
      return lessonTime >= slotStart && lessonTime <= slotEnd;
    });

    if (!isAvailable) {
      alert(`Instructor is not available on ${lessonDay} at ${lessonTime}.`);
      return false;
    }

    return true;
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
      console.error('Add user error:', err);
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
        setNewStudent({ name: '', email: '', phone: '', instrument: '' });
        fetchStudents();
        setError('');
      } else {
        setError(data.error || 'Failed to add student');
      }
    } catch (err) {
      setError('Failed to add student');
      console.error('Add student error:', err);
    }
  };

  const handleAddLesson = async (e) => {
    e.preventDefault();
    try {
      if (!checkInstructorAvailability()) {
        return;
      }
      const lessonData = {
        student_id: parseInt(newLesson.student_id),
        instructor_id: parseInt(newLesson.instructor_id),
        lesson_date: newLesson.lesson_date,
        lesson_time: newLesson.lesson_time,
        duration: parseInt(newLesson.duration),
        instrument: newLesson.instrument,
        reminder_enabled: newLesson.reminder_enabled,
      };
      console.log('Sending lesson data:', lessonData);
      const res = await fetch('/api/lessons', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(lessonData),
      });
      const data = await res.json();
      console.log('Lesson creation response:', data);
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
        await fetchLessons();
        setError('');
        alert('Lesson added successfully!');
      } else {
        setError(data.error || 'Failed to add lesson');
        alert(data.error || 'Failed to add lesson');
      }
    } catch (err) {
      setError('Failed to add lesson: ' + err.message);
      console.error('Add lesson error:', err);
      alert('Failed to add lesson: ' + err.message);
    }
  };

  const handleStudentChange = (e) => {
    const studentId = e.target.value;
    setNewLesson(prev => ({ ...prev, student_id: studentId }));
  };

  const handleInstructorChange = (e) => {
    const instructorId = e.target.value;
    setNewLesson(prev => ({ ...prev, instructor_id: instructorId, instrument: '' }));
  };

  const handleInstrumentChange = (e) => {
    const instrument = e.target.value;
    setNewLesson(prev => ({ ...prev, instrument }));
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">Admin Dashboard</h1>
      <button onClick={handleLogout} className="bg-red-500 text-white p-2 rounded mb-4">Logout</button>
      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4" role="alert">
          <p>{error}</p>
        </div>
      )}

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
        <div>
          <label className="block">Instrument</label>
          <input
            type="text"
            value={newStudent.instrument}
            onChange={(e) => setNewStudent({ ...newStudent, instrument: e.target.value })}
            className="border p-2 w-full"
          />
        </div>
        <button type="submit" className="bg-blue-500 text-white p-2 rounded">Add Student</button>
      </form>
      <ul className="mb-4">
        {students.map(student => (
          <li key={student.id} className="border-b py-2">
            {student.name} (Email: {student.email || 'N/A'}, Phone: {student.phone || 'N/A'}, Instrument: {student.instrument || 'N/A'})
          </li>
        ))}
      </ul>

      <h2 className="text-2xl font-semibold mb-2">Schedule Lesson</h2>
      <form onSubmit={handleAddLesson} className="space-y-4 mb-4">
        <div>
          <label className="block">Student</label>
          <select
            value={newLesson.student_id}
            onChange={handleStudentChange}
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
            onChange={handleInstructorChange}
            className="border p-2 w-full"
          >
            <option value="">Select Instructor</option>
            {users.filter(u => u.role === 'instructor').map(user => (
              <option key={user.id} value={user.id}>{user.username}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block">Instrument</label>
          <select
            value={newLesson.instrument}
            onChange={handleInstrumentChange}
            className="border p-2 w-full"
            disabled={!newLesson.instructor_id || instructorInstruments.length === 0}
          >
            <option value="">Select Instrument</option>
            {instructorInstruments.map(item => (
              <option key={item.id} value={item.instrument}>{item.instrument}</option>
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

      <h2 className="text-2xl font-semibold mb-2">Lessons</h2>
      {loadingLessons ? (
        <p>Loading lessons...</p>
      ) : lessons.length > 0 ? (
        <ul className="mb-4">
          {lessons.map(lesson => (
            <li key={lesson.id} className="border-b py-2">
              <p><strong>Student:</strong> {lesson.student_name}</p>
              <p><strong>Date:</strong> {lesson.lesson_date}</p>
              <p><strong>Time:</strong> {lesson.lesson_time}</p>
              <p><strong>Duration:</strong> {lesson.duration} minutes</p>
              <p><strong>Instrument:</strong> {lesson.instrument}</p>
              <p><strong>Reminder Enabled:</strong> {lesson.reminder_enabled ? 'Yes' : 'No'}</p>
              <p><strong>Notes:</strong> {lesson.notes || 'None'}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p>No lessons scheduled.</p>
      )}
    </div>
  );
};

const InstructorDashboard = ({ handleLogout, error, setError }) => {
  const [lessons, setLessons] = useState([]);
  const [availability, setAvailability] = useState([]);
  const [timeOff, setTimeOff] = useState([]);
  const [instruments, setInstruments] = useState([]);
  const [newAvailability, setNewAvailability] = useState({ days_of_week: [], start_time: '', end_time: '' });
  const [newTimeOff, setNewTimeOff] = useState({ start_date: '', end_date: '' });
  const [newInstrument, setNewInstrument] = useState('');
  const [lessonNotes, setLessonNotes] = useState({});
  const [loadingLessons, setLoadingLessons] = useState(true);

  useEffect(() => {
    fetchLessons();
    fetchAvailability();
    fetchTimeOff();
    fetchInstruments();
  }, []);

  const fetchLessons = async () => {
    try {
      setLoadingLessons(true);
      const res = await fetch('/api/my-lessons');
      const data = await res.json();
      if (data.error) {
        throw new Error(data.error);
      }
      const validLessons = (data.lessons || []).filter(lesson => {
        const isValid = (
          lesson.lesson_date &&
          lesson.lesson_time &&
          lesson.duration &&
          lesson.student_name
        );
        if (!isValid) {
          console.warn('Invalid lesson data:', lesson);
        }
        return isValid;
      });
      setLessons(validLessons);
      // Initialize notes state
      const notesObj = {};
      validLessons.forEach(lesson => {
        notesObj[lesson.id] = lesson.notes || '';
      });
      setLessonNotes(notesObj);
    } catch (err) {
      setError('Failed to fetch lessons: ' + err.message);
      setLessons([]);
      console.error('Fetch lessons error:', err);
    } finally {
      setLoadingLessons(false);
    }
  };

  const fetchAvailability = async () => {
    try {
      const res = await fetch('/api/availability');
      const data = await res.json();
      setAvailability(data.availability || []);
    } catch (err) {
      setError('Failed to fetch availability');
      console.error('Fetch availability error:', err);
    }
  };

  const fetchTimeOff = async () => {
    try {
      const res = await fetch('/api/time-off');
      const data = await res.json();
      setTimeOff(data.time_off || []);
    } catch (err) {
      setError('Failed to fetch time off');
      console.error('Fetch time off error:', err);
    }
  };

  const fetchInstruments = async () => {
    try {
      const res = await fetch('/api/instruments');
      const data = await res.json();
      setInstruments(data.instruments || []);
    } catch (err) {
      setError('Failed to fetch instruments');
      console.error('Fetch instruments error:', err);
    }
  };

  const handleAddAvailability = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/availability', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newAvailability),
      });
      const data = await res.json();
      if (data.message) {
        setNewAvailability({ days_of_week: [], start_time: '', end_time: '' });
        fetchAvailability();
        setError('');
      } else {
        setError(data.error || 'Failed to add availability');
      }
    } catch (err) {
      setError('Failed to add availability');
      console.error('Add availability error:', err);
    }
  };

  const handleAddTimeOff = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/time-off', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTimeOff),
      });
      const data = await res.json();
      if (data.message) {
        setNewTimeOff({ start_date: '', end_date: '' });
        fetchTimeOff();
        setError('');
      } else {
        setError(data.error || 'Failed to add time off');
      }
    } catch (err) {
      setError('Failed to add time off');
      console.error('Add time off error:', err);
    }
  };

  const handleAddInstrument = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/instruments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instrument: newInstrument }),
      });
      const data = await res.json();
      if (data.message) {
        setNewInstrument('');
        fetchInstruments();
        setError('');
      } else {
        setError(data.error || 'Failed to add instrument');
      }
    } catch (err) {
      setError('Failed to add instrument');
      console.error('Add instrument error:', err);
    }
  };

  const handleDayChange = (e) => {
    const { value, checked } = e.target;
    setNewAvailability(prev => {
      const days = checked
        ? [...prev.days_of_week, value]
        : prev.days_of_week.filter(day => day !== value);
      return { ...prev, days_of_week: days };
    });
  };

  const handleNotesChange = (lessonId, notes) => {
    setLessonNotes(prev => ({
      ...prev,
      [lessonId]: notes
    }));
  };

  const saveNotes = async (lessonId) => {
    try {
      const res = await fetch('/api/lesson-notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lesson_id: lessonId, notes: lessonNotes[lessonId] }),
      });
      const data = await res.json();
      if (data.message) {
        fetchLessons();
        setError('');
        alert('Notes saved successfully!');
      } else {
        setError(data.error || 'Failed to save notes');
        alert(data.error || 'Failed to save notes');
      }
    } catch (err) {
      setError('Failed to save notes: ' + err.message);
      console.error('Save notes error:', err);
      alert('Failed to save notes: ' + err.message);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">Instructor Dashboard</h1>
      <button onClick={handleLogout} className="bg-red-500 text-white p-2 rounded mb-4">Logout</button>
      {error && <p className="text-red-500 mb-4">{error}</p>}

      <h2 className="text-2xl font-semibold mb-2">My Lessons</h2>
      {loadingLessons ? (
        <p>Loading lessons...</p>
      ) : lessons.length > 0 ? (
        <ul className="mb-4">
          {lessons.map(lesson => (
            <li key={lesson.id} className="border-b py-2">
              <p><strong>Student:</strong> {lesson.student_name}</p>
              <p><strong>Date:</strong> {lesson.lesson_date}</p>
              <p><strong>Time:</strong> {lesson.lesson_time}</p>
              <p><strong>Duration:</strong> {lesson.duration} minutes</p>
              <p><strong>Instrument:</strong> {lesson.instrument}</p>
              <div>
                <label className="block"><strong>Notes:</strong></label>
                <textarea
                  value={lessonNotes[lesson.id] || ''}
                  onChange={(e) => handleNotesChange(lesson.id, e.target.value)}
                  className="border p-2 w-full"
                  rows="3"
                  placeholder="Add notes for this lesson..."
                />
                <button
                  onClick={() => saveNotes(lesson.id)}
                  className="bg-blue-500 text-white p-2 rounded mt-2"
                >
                  Save Notes
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p>No lessons scheduled.</p>
      )}

      <h2 className="text-2xl font-semibold mb-2">Set Availability</h2>
      <form onSubmit={handleAddAvailability} className="space-y-4 mb-4">
        <div>
          <label className="block">Days of Week</label>
          {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map(day => (
            <label key={day} className="flex items-center">
              <input
                type="checkbox"
                value={day}
                checked={newAvailability.days_of_week.includes(day)}
                onChange={handleDayChange}
                className="mr-2"
              />
              {day}
            </label>
          ))}
        </div>
        <div>
          <label className="block">Start Time</label>
          <input
            type="time"
            value={newAvailability.start_time}
            onChange={(e) => setNewAvailability({ ...newAvailability, start_time: e.target.value })}
            className="border p-2 w-full"
          />
        </div>
        <div>
          <label className="block">End Time</label>
          <input
            type="time"
            value={newAvailability.end_time}
            onChange={(e) => setNewAvailability({ ...newAvailability, end_time: e.target.value })}
            className="border p-2 w-full"
          />
        </div>
        <button type="submit" className="bg-blue-500 text-white p-2 rounded">Add Availability</button>
      </form>
      <ul className="mb-4">
        {availability.map(slot => (
          <li key={slot.id} className="border-b py-2">
            {slot.day_of_week}: {slot.start_time} - {slot.end_time}
          </li>
        ))}
      </ul>

      <h2 className="text-2xl font-semibold mb-2">Request Time Off</h2>
      <form onSubmit={handleAddTimeOff} className="space-y-4 mb-4">
        <div>
          <label className="block">Start Date</label>
          <input
            type="date"
            value={newTimeOff.start_date}
            onChange={(e) => setNewTimeOff({ ...newTimeOff, start_date: e.target.value })}
            className="border p-2 w-full"
          />
        </div>
        <div>
          <label className="block">End Date</label>
          <input
            type="date"
            value={newTimeOff.end_date}
            onChange={(e) => setNewTimeOff({ ...newTimeOff, end_date: e.target.value })}
            className="border p-2 w-full"
          />
        </div>
        <button type="submit" className="bg-blue-500 text-white p-2 rounded">Request Time Off</button>
      </form>
      <ul className="mb-4">
        {timeOff.map(slot => (
          <li key={slot.id} className="border-b py-2">
            Time Off: {slot.start_date} to {slot.end_date}
          </li>
        ))}
      </ul>

      <h2 className="text-2xl font-semibold mb-2">Instruments I Teach</h2>
      <form onSubmit={handleAddInstrument} className="space-y-4 mb-4">
        <div>
          <label className="block">Instrument</label>
          <input
            type="text"
            value={newInstrument}
            onChange={(e) => setNewInstrument(e.target.value)}
            className="border p-2 w-full"
          />
        </div>
        <button type="submit" className="bg-blue-500 text-white p-2 rounded">Add Instrument</button>
      </form>
      <ul>
        {instruments.map(item => (
          <li key={item.id} className="border-b py-2">{item.instrument}</li>
        ))}
      </ul>
    </div>
  );
};

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [role, setRole] = useState(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    fetch('/api/check-auth')
      .then(res => res.json())
      .then(data => {
        setIsAuthenticated(data.authenticated);
        setRole(data.role);
      })
      .catch(err => setError('Failed to check authentication'));
  }, []);

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
    return <AdminDashboard handleLogout={handleLogout} error={error} setError={setError} />;
  }

  if (role === 'instructor') {
    return <InstructorDashboard handleLogout={handleLogout} error={error} setError={setError} />;
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
