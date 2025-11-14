DROP TABLE IF EXISTS Registrations, Exams, Courses, Buildings,
Locations, Users, Majors, Departments, Roles, Professors, Timeslots;

-- 1. Roles
CREATE TABLE Roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

-- 2. Departments
CREATE TABLE Departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- 3. Majors
CREATE TABLE Majors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department_id INT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES Departments(id)
);

-- 4. Users
CREATE TABLE Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    nshe_id VARCHAR(10),
    employee_id VARCHAR(15),
    password_hash VARCHAR(255) NOT NULL,
    role_id INT NOT NULL,
    department_id INT,
    major_id INT,
    status ENUM('Active','Inactive') DEFAULT 'Active',
    FOREIGN KEY (role_id) REFERENCES Roles(id),
    FOREIGN KEY (department_id) REFERENCES Departments(id),
    FOREIGN KEY (major_id) REFERENCES Majors(id),
    CHECK (
        (role_id = 2 AND email LIKE '%@student.csn.edu')
        OR
        (role_id = 1 AND email LIKE '%@csn.edu')
    )
);

-- 5. Professors
CREATE TABLE Professors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- 6. Locations
CREATE TABLE Locations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- 7. Buildings
CREATE TABLE Buildings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location_id INT NOT NULL,
    FOREIGN KEY (location_id) REFERENCES Locations(id)
);

-- 8. Courses
CREATE TABLE Courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_code VARCHAR(20) NOT NULL,
    course_name VARCHAR(150) NOT NULL,
    department_id INT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES Departments(id)
);

-- 9. Timeslots
CREATE TABLE Timeslots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL
);

-- 10. Exams
CREATE TABLE Exams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_type VARCHAR(255) NOT NULL,
    course_id INT NOT NULL,
    exam_date DATE NOT NULL,
    exam_time TIME,
    location_id INT NOT NULL,
    building_id INT NOT NULL,
    capacity INT DEFAULT 20,
    professor_id INT,
    timeslot_id INT,
    FOREIGN KEY (course_id) REFERENCES Courses(id),
    FOREIGN KEY (location_id) REFERENCES Locations(id),
    FOREIGN KEY (building_id) REFERENCES Buildings(id),
    FOREIGN KEY (professor_id) REFERENCES Professors(id) ON DELETE SET NULL,
    FOREIGN KEY (timeslot_id) REFERENCES Timeslots(id) ON DELETE SET NULL
);

-- 11. Registrations
CREATE TABLE Registrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    registration_id VARCHAR(10) UNIQUE,
    exam_id INT NOT NULL,
    user_id INT NOT NULL,
    timeslot_id INT,
    location_id INT,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('Active','Canceled') DEFAULT 'Active',
    UNIQUE(exam_id, user_id),
    FOREIGN KEY (exam_id) REFERENCES Exams(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- 12. Exam Locations
CREATE TABLE Exam_Locations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_id INT NOT NULL,
    location_id INT NOT NULL,
    capacity INT NOT NULL DEFAULT 20,
    UNIQUE KEY (exam_id, location_id),
    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
);
