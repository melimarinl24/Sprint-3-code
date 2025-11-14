USE er_system;

-- DROP old tables safely (if re-running)
DROP TABLE IF EXISTS Registrations, Exams, Courses, Buildings, 
Locations, Users, Majors, Departments, Roles, Professors;

-- =============================================================
-- 1. Roles
-- =============================================================
CREATE TABLE Roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

-- =============================================================
-- 2. Departments
-- =============================================================
CREATE TABLE Departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- =============================================================
-- 3. Majors
-- =============================================================
CREATE TABLE Majors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department_id INT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES Departments(id)
);

-- =============================================================
-- 4. Users (students + faculty)
-- =============================================================
CREATE TABLE Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    nshe_id VARCHAR(10) NULL,
    employee_id VARCHAR(15) NULL,
    role_id INT NOT NULL,
    department_id INT NULL,
    major_id INT NULL,
    password_hash VARCHAR(255) NULL,
    FOREIGN KEY (role_id) REFERENCES Roles(id),
    FOREIGN KEY (department_id) REFERENCES Departments(id),
    FOREIGN KEY (major_id) REFERENCES Majors(id)
);

-- =============================================================
-- 5. Professors
-- =============================================================
CREATE TABLE Professors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(50) NULL,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- =============================================================
-- 6. Locations
-- =============================================================
CREATE TABLE Locations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- =============================================================
-- 7. Buildings
-- =============================================================
CREATE TABLE Buildings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location_id INT NOT NULL,
    FOREIGN KEY (location_id) REFERENCES Locations(id)
);

-- =============================================================
-- 8. Courses
-- =============================================================
CREATE TABLE Courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_code VARCHAR(20) NOT NULL,
    course_name VARCHAR(150) NOT NULL,
    department_id INT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES Departments(id)
);

-- =============================================================
-- 9. Exams
-- =============================================================
CREATE TABLE Exams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_type VARCHAR(255) NOT NULL,
    course_id INT NOT NULL,
    exam_date DATE NOT NULL,
    exam_time TIME NULL,
    location_id INT NOT NULL,
    building_id INT NOT NULL,
    capacity INT NOT NULL DEFAULT 20,
    professor_id INT NULL,
    FOREIGN KEY (course_id) REFERENCES Courses(id),
    FOREIGN KEY (location_id) REFERENCES Locations(id),
    FOREIGN KEY (building_id) REFERENCES Buildings(id),
    FOREIGN KEY (professor_id) REFERENCES Professors(id) ON DELETE SET NULL
);

-- =============================================================
-- 10. Registrations
-- =============================================================
CREATE TABLE Registrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    registration_id VARCHAR(10) UNIQUE NOT NULL,
    exam_id INT NOT NULL,
    user_id INT NOT NULL,
    registration_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('Active','Canceled') DEFAULT 'Active',
    UNIQUE(exam_id, user_id),
    FOREIGN KEY(exam_id) REFERENCES Exams(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- =============================================================
-- 11. SEED DATA
-- =============================================================

INSERT INTO Roles (name) VALUES
('faculty'),
('student');

INSERT INTO Departments (name) VALUES
('Computer and Information Technology'),
('Mathematics'),
('Business Administration'),
('Health Sciences'),
('Engineering Technology');

INSERT INTO Majors (name, department_id) VALUES
('Computer Science', 1),
('Information Systems', 1),
('Mathematics', 2),
('Business Management', 3),
('Nursing', 4),
('Electronics Engineering', 5);

INSERT INTO Locations (name) VALUES
('North Las Vegas'),
('West Charleston'),
('Henderson');

INSERT INTO Buildings (name, location_id) VALUES
('Building B', 1),
('Building D', 2),
('Building A', 3);

INSERT INTO Courses (course_code, course_name, department_id) VALUES
('CS135', 'Introduction to Programming', 1),
('CS202', 'Computer Science I', 1),
('MATH120', 'Fundamentals of College Mathematics', 2),
('BUS101', 'Principles of Management', 3),
('NURS101', 'Foundations of Nursing Practice', 4),
('ET131', 'Basic Electronics I', 5);

-- =============================================================
-- 12. SEED USERS (faculty + students)
-- =============================================================
INSERT INTO Users (name, email, phone, nshe_id, employee_id, role_id, department_id, major_id)
VALUES
('Bart Simpson', 'bart.e10001@csn.edu', '765-000-0000', NULL, 'E10001', 1, 1, 1),
('Velma Dinkley', '2044992200@student.csn.edu', '123-456-7890', '2044992200', NULL, 2, 1, 2),
('Patrick Star', '2009991000@student.csn.edu', '908-765-5454', '2009991000', NULL, 2, 3, 4);

-- =============================================================
-- 13. SEED PROFESSOR (link faculty user)
-- =============================================================
INSERT INTO Professors (user_id, title)
SELECT id, 'Prof.' FROM Users WHERE employee_id = 'E10001';

-- =============================================================
-- 14. SEED EXAMS (linked with professors)
-- =============================================================
INSERT INTO Exams (exam_type, course_id, exam_date, exam_time, location_id, building_id, capacity, professor_id)
VALUES
('Midterm Exam', 1, '2025-11-15', '09:00:00', 1, 1, 20, 1),
('Final Exam', 2, '2025-12-10', '13:00:00', 2, 2, 20, 1),
('Math Test', 3, '2025-11-20', '10:00:00', 3, 3, 20, NULL);

-- =============================================================
-- 15. SEED REGISTRATIONS
-- =============================================================
INSERT INTO Registrations (registration_id, exam_id, user_id)
VALUES
('CSN001', 1, 2),
('CSN002', 2, 3);

-- =============================================================
-- 16. TRIGGERS
-- =============================================================
DELIMITER $$

-- Registration ID auto-generator
CREATE TRIGGER id_generator
BEFORE INSERT ON Registrations 
FOR EACH ROW 
BEGIN
    DECLARE next_id INT;
    SELECT AUTO_INCREMENT INTO next_id
    FROM information_schema.tables
    WHERE table_name = 'Registrations'
      AND table_schema = DATABASE();
    IF NEW.registration_id IS NULL OR NEW.registration_id = '' THEN
        SET NEW.registration_id = CONCAT('CSN', LPAD(next_id, 3, '0'));
    END IF;
END$$

-- Email format validator
CREATE TRIGGER check_email_format
BEFORE INSERT ON Users
FOR EACH ROW
BEGIN
    DECLARE role_name VARCHAR(50);
    SELECT name INTO role_name FROM Roles WHERE id = NEW.role_id;

    IF role_name = 'student' AND NEW.email NOT LIKE '%@student.csn.edu' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Invalid email: Students must use @student.csn.edu';
    END IF;

    IF role_name = 'faculty' AND NEW.email NOT LIKE '%@csn.edu' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Invalid email: Faculty must use @csn.edu';
    END IF;
END$$

DELIMITER ;

-- =============================================================
-- 17. TEST QUERIES
-- =============================================================
SELECT * FROM Users;
SELECT * FROM Professors;
SELECT * FROM Exams;
SELECT * FROM Registrations;
