
#!/usr/bin/env python3
"""
Music Scheduler Web Application
Main Flask application for scheduling and managing music playlists
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import sqlite3
import json
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

app = Flask(__name__)
app.secret_key = 'music_scheduler_secret_key_change_in_production'

# Configuration
DATABASE_PATH = 'music_scheduler.db'
scheduler = BackgroundScheduler()
scheduler.start()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database with music scheduler schema"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.executescript('''
            -- Music Scheduler Database Schema
            
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS music_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                artist TEXT NOT NULL,
                album TEXT,
                duration INTEGER, -- in seconds
                file_path TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                track_id INTEGER NOT NULL,
                order_position INTEGER DEFAULT 0,
                FOREIGN KEY (playlist_id) REFERENCES playlists (id) ON DELETE CASCADE,
                FOREIGN KEY (track_id) REFERENCES music_tracks (id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                playlist_id INTEGER NOT NULL,
                schedule_type TEXT NOT NULL CHECK (schedule_type IN ('daily', 'weekly', 'monthly', 'once')),
                schedule_time TIME NOT NULL,
                schedule_day TEXT, -- for weekly: monday, tuesday, etc. For monthly: 1-31
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_run TIMESTAMP,
                next_run TIMESTAMP,
                FOREIGN KEY (playlist_id) REFERENCES playlists (id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS schedule_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER NOT NULL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'skipped')),
                error_message TEXT,
                tracks_played INTEGER DEFAULT 0,
                FOREIGN KEY (schedule_id) REFERENCES schedules (id) ON DELETE CASCADE
            );
            
            -- Insert sample data
            INSERT OR IGNORE INTO playlists (id, name, description) VALUES
                (1, 'Morning Mix', 'Energetic music to start the day'),
                (2, 'Afternoon Chill', 'Relaxing tunes for afternoon'),
                (3, 'Evening Classics', 'Classical music for evening wind-down');
                
            INSERT OR IGNORE INTO music_tracks (id, title, artist, album, duration) VALUES
                (1, 'Good Morning Sunshine', 'The Energizers', 'Wake Up Album', 210),
                (2, 'Coffee Break Blues', 'Chill Masters', 'Afternoon Vibes', 185),
                (3, 'Sunset Serenade', 'Classical Ensemble', 'Evening Collection', 240),
                (4, 'Productivity Boost', 'Focus Band', 'Work Tunes', 195),
                (5, 'Relaxation Station', 'Ambient Artists', 'Chill Out', 300);
                
            INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id, order_position) VALUES
                (1, 1, 1), (1, 4, 2),
                (2, 2, 1), (2, 5, 2),
                (3, 3, 1);
                
            INSERT OR IGNORE INTO schedules (id, name, playlist_id, schedule_type, schedule_time, is_active) VALUES
                (1, 'Daily Morning Music', 1, 'daily', '08:00', TRUE),
                (2, 'Afternoon Break', 2, 'daily', '14:00', TRUE),
                (3, 'Evening Wind Down', 3, 'daily', '18:00', TRUE);
        ''')
        conn.commit()

@app.route('/')
def index():
    """Home page showing dashboard"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        
        # Get playlist count
        playlist_count = conn.execute('SELECT COUNT(*) as count FROM playlists').fetchone()['count']
        
        # Get track count  
        track_count = conn.execute('SELECT COUNT(*) as count FROM music_tracks').fetchone()['count']
        
        # Get active schedule count
        schedule_count = conn.execute('SELECT COUNT(*) as count FROM schedules WHERE is_active = 1').fetchone()['count']
        
        # Get recent schedule logs
        recent_logs = conn.execute('''
            SELECT sl.*, s.name as schedule_name, p.name as playlist_name
            FROM schedule_logs sl
            JOIN schedules s ON sl.schedule_id = s.id
            JOIN playlists p ON s.playlist_id = p.id
            ORDER BY sl.executed_at DESC
            LIMIT 5
        ''').fetchall()
        
        return render_template('index.html', 
                             playlist_count=playlist_count,
                             track_count=track_count, 
                             schedule_count=schedule_count,
                             recent_logs=recent_logs)

@app.route('/playlists')
def playlists():
    """View all playlists"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        playlists = conn.execute('''
            SELECT p.*, COUNT(pt.track_id) as track_count
            FROM playlists p
            LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
            GROUP BY p.id
            ORDER BY p.name
        ''').fetchall()
        
        return render_template('playlists.html', playlists=playlists)

@app.route('/playlists/<int:playlist_id>')
def playlist_detail(playlist_id):
    """View playlist details and tracks"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        
        playlist = conn.execute('SELECT * FROM playlists WHERE id = ?', (playlist_id,)).fetchone()
        if not playlist:
            flash('Playlist not found', 'error')
            return redirect(url_for('playlists'))
            
        tracks = conn.execute('''
            SELECT mt.*, pt.order_position
            FROM music_tracks mt
            JOIN playlist_tracks pt ON mt.id = pt.track_id
            WHERE pt.playlist_id = ?
            ORDER BY pt.order_position
        ''', (playlist_id,)).fetchall()
        
        return render_template('playlist_detail.html', playlist=playlist, tracks=tracks)

@app.route('/schedules')
def schedules():
    """View all schedules"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        schedules = conn.execute('''
            SELECT s.*, p.name as playlist_name
            FROM schedules s
            JOIN playlists p ON s.playlist_id = p.id
            ORDER BY s.schedule_time
        ''').fetchall()
        
        return render_template('schedules.html', schedules=schedules)

@app.route('/api/schedules/<int:schedule_id>/toggle', methods=['POST'])
def toggle_schedule(schedule_id):
    """Toggle schedule active status"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        schedule = conn.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,)).fetchone()
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
            
        new_status = not bool(schedule[6])  # is_active is at index 6
        conn.execute('UPDATE schedules SET is_active = ? WHERE id = ?', (new_status, schedule_id))
        conn.commit()
        
        return jsonify({'success': True, 'active': new_status})

@app.route('/api/execute_schedule/<int:schedule_id>', methods=['POST']) 
def execute_schedule(schedule_id):
    """Manually execute a schedule"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        
        # Get schedule and playlist info
        schedule_info = conn.execute('''
            SELECT s.*, p.name as playlist_name
            FROM schedules s
            JOIN playlists p ON s.playlist_id = p.id
            WHERE s.id = ?
        ''', (schedule_id,)).fetchone()
        
        if not schedule_info:
            return jsonify({'error': 'Schedule not found'}), 404
            
        # Get tracks in playlist
        tracks = conn.execute('''
            SELECT COUNT(*) as count
            FROM playlist_tracks pt
            WHERE pt.playlist_id = ?
        ''', (schedule_info['playlist_id'],)).fetchone()
        
        # Log the execution
        conn.execute('''
            INSERT INTO schedule_logs (schedule_id, status, tracks_played)
            VALUES (?, ?, ?)
        ''', (schedule_id, 'success', tracks['count']))
        
        # Update last run
        conn.execute('UPDATE schedules SET last_run = ? WHERE id = ?', 
                    (datetime.now().isoformat(), schedule_id))
        conn.commit()
        
        logger.info(f"Executed schedule: {schedule_info['name']}")
        return jsonify({
            'success': True, 
            'message': f"Executed playlist '{schedule_info['playlist_name']}' with {tracks['count']} tracks"
        })

if __name__ == '__main__':
    init_db()
    print("🎵 Music Scheduler starting up...")
    print("📊 Dashboard available at: http://localhost:5000")
    print("🎶 Access your music scheduling interface now!")
    app.run(host='0.0.0.0', port=5000, debug=True)
