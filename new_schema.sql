CREATE DATABASE IF NOT EXISTS ecoeat_2;
USE ecoeat_2;

-- Drop tables in reverse order of foreign key dependencies to prevent errors
DROP TABLE IF EXISTS Review;
DROP TABLE IF EXISTS `Order`;
DROP TABLE IF EXISTS Blind_Box;
DROP TABLE IF EXISTS Store;
DROP TABLE IF EXISTS Student;

-- 1. Student Table
CREATE TABLE Student (
    SID INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    student_number VARCHAR(50) UNIQUE NOT NULL,
    acc_balance DECIMAL(10, 2) DEFAULT 0.00 CHECK (acc_balance >= 0),
    eco_points INT DEFAULT 0
);

-- 2. Store (Vendor) Table
CREATE TABLE Store (
    store_ID INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    rating DECIMAL(3, 2) DEFAULT 0.00
);

-- 3. Blind Box Table
CREATE TABLE Blind_Box (
    box_ID INT AUTO_INCREMENT PRIMARY KEY,
    store_ID INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    originalPrice DECIMAL(10, 2) NOT NULL,
    flashPrice DECIMAL(10, 2) NOT NULL,
    stockQuantity INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    pickUpDeadline TIME NOT NULL,
    FOREIGN KEY (store_ID) REFERENCES Store(store_ID) ON DELETE CASCADE
);

-- 4. Order Table
CREATE TABLE `Order` (
    order_ID INT AUTO_INCREMENT PRIMARY KEY,
    SID INT NOT NULL,
    box_ID INT NOT NULL,
    status ENUM('Pending', 'Claimed', 'Canceled') DEFAULT 'Pending',
    pickup_code VARCHAR(10) NOT NULL,
    order_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (SID) REFERENCES Student(SID) ON DELETE CASCADE,
    -- We use RESTRICT here to prevent the "Vendor Delete Crash" we patched earlier!
    FOREIGN KEY (box_ID) REFERENCES Blind_Box(box_ID) ON DELETE RESTRICT 
);

-- 5. Review Table (1:1 Relationship with Order)
CREATE TABLE Review (
    review_ID INT AUTO_INCREMENT PRIMARY KEY,
    order_ID INT UNIQUE NOT NULL, -- The UNIQUE keyword enforces the 1:1 constraint
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_ID) REFERENCES `Order`(order_ID) ON DELETE CASCADE
);

SELECT * from student;