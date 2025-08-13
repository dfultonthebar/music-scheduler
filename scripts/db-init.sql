
-- Music Scheduler Database Schema
-- This script initializes the database schema for the music scheduler system

-- Create users table if it doesn't exist
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

-- Create venues table
CREATE TABLE IF NOT EXISTS venues (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    address TEXT,
    capacity INT,
    contact_email VARCHAR(120),
    contact_phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

-- Create artists table
CREATE TABLE IF NOT EXISTS artists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    genre VARCHAR(100),
    contact_email VARCHAR(120),
    contact_phone VARCHAR(20),
    bio TEXT,
    website VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

-- Create events table
CREATE TABLE IF NOT EXISTS events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    venue_id INT,
    artist_id INT,
    event_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME,
    ticket_price DECIMAL(10, 2),
    max_capacity INT,
    current_bookings INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'scheduled',
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (venue_id) REFERENCES venues(id) ON DELETE SET NULL,
    FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Create bookings table
CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    customer_name VARCHAR(200) NOT NULL,
    customer_email VARCHAR(120) NOT NULL,
    customer_phone VARCHAR(20),
    tickets_count INT DEFAULT 1,
    total_amount DECIMAL(10, 2),
    booking_status VARCHAR(20) DEFAULT 'confirmed',
    payment_status VARCHAR(20) DEFAULT 'pending',
    booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Create settings table for system configuration
CREATE TABLE IF NOT EXISTS settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    description VARCHAR(255),
    updated_by INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Insert default system settings
INSERT INTO settings (setting_key, setting_value, description) VALUES
('app_name', 'Music Scheduler', 'Application name displayed in UI'),
('currency', 'USD', 'Default currency for pricing'),
('timezone', 'America/New_York', 'Default timezone for events'),
('max_booking_days_advance', '90', 'Maximum days in advance for bookings'),
('email_notifications', 'true', 'Enable email notifications'),
('backup_retention_days', '30', 'Number of days to keep backups')
ON DUPLICATE KEY UPDATE setting_value=setting_value;

-- Create indexes for better performance
CREATE INDEX idx_events_date ON events(event_date);
CREATE INDEX idx_events_venue ON events(venue_id);
CREATE INDEX idx_events_artist ON events(artist_id);
CREATE INDEX idx_bookings_event ON bookings(event_id);
CREATE INDEX idx_bookings_customer ON bookings(customer_email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- Create a view for event details with venue and artist information
CREATE OR REPLACE VIEW event_details AS
SELECT 
    e.id,
    e.title,
    e.description,
    e.event_date,
    e.start_time,
    e.end_time,
    e.ticket_price,
    e.max_capacity,
    e.current_bookings,
    e.status,
    v.name AS venue_name,
    v.address AS venue_address,
    a.name AS artist_name,
    a.genre AS artist_genre,
    u.username AS created_by_username
FROM events e
LEFT JOIN venues v ON e.venue_id = v.id
LEFT JOIN artists a ON e.artist_id = a.id
LEFT JOIN users u ON e.created_by = u.id;

-- Create a view for booking summary
CREATE OR REPLACE VIEW booking_summary AS
SELECT 
    b.id,
    b.customer_name,
    b.customer_email,
    b.tickets_count,
    b.total_amount,
    b.booking_status,
    b.payment_status,
    b.booking_date,
    e.title AS event_title,
    e.event_date,
    e.start_time,
    v.name AS venue_name
FROM bookings b
JOIN events e ON b.event_id = e.id
LEFT JOIN venues v ON e.venue_id = v.id;

-- Insert some sample data for testing (optional)
-- You can remove this section if you don't want sample data

-- Sample venues
INSERT INTO venues (name, address, capacity, contact_email, contact_phone) VALUES
('The Grand Theater', '123 Main St, Music City, MC 12345', 500, 'bookings@grandtheater.com', '555-0001'),
('Riverside Concert Hall', '456 River Rd, Music City, MC 12345', 1200, 'events@riverside.com', '555-0002'),
('Intimate Jazz Club', '789 Jazz Ave, Music City, MC 12345', 150, 'info@jazzclub.com', '555-0003')
ON DUPLICATE KEY UPDATE name=name;

-- Sample artists
INSERT INTO artists (name, genre, contact_email, contact_phone, bio, website) VALUES
('The Harmony Collective', 'Indie Folk', 'booking@harmonycollective.com', '555-1001', 'An indie folk band known for their harmonious melodies and storytelling.', 'https://harmonycollective.com'),
('Electric Pulse', 'Electronic', 'contact@electricpulse.com', '555-1002', 'Electronic music duo creating atmospheric soundscapes.', 'https://electricpulse.com'),
('Jazz Masters Quartet', 'Jazz', 'bookings@jazzmasters.com', '555-1003', 'Traditional and contemporary jazz quartet with 20+ years experience.', 'https://jazzmasters.com')
ON DUPLICATE KEY UPDATE name=name;

-- Database schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(10) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_version (version) VALUES ('1.0.0');

-- Grant necessary privileges (this will be handled by the installer script)
-- The installer script will create a dedicated database user with appropriate permissions
