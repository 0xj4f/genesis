-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS genesis;
USE genesis;

-- Create the 'users' table if it doesn't exist
CREATE TABLE IF NOT EXISTS users (
    id CHAR(36) NOT NULL PRIMARY KEY,
    username VARCHAR(150) NOT NULL UNIQUE,
    email VARCHAR(254) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    oauth_provider VARCHAR(50),
    oauth_id VARCHAR(100)
);

-- Create the 'profiles' table if it doesn't exist
CREATE TABLE IF NOT EXISTS profiles (
    user_id CHAR(36) NOT NULL PRIMARY KEY,
    first_name VARCHAR(30),
    last_name VARCHAR(30),
    phone_number VARCHAR(20),
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(56),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

