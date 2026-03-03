# QCM Platform Documentation

This document provides a detailed overview of the application's architecture, database schema, and core routing structure.

## 🏗️ Architecture

The QCM Platform is built using the **Flask** web framework and follows a standard monolithic application pattern using Blueprints for modularity.

### Directory Structure
```text
qcm/
├── app/
│   ├── __init__.py       # Factory pattern: create_app()
│   ├── models.py         # SQLAlchemy database models
│   ├── events.py         # SocketIO event handlers for Live Quizzes
│   ├── routes/           # Application Blueprints
│   │   ├── main.py       # Public & general routes
│   │   ├── auth.py       # Login, Register, Logout
│   │   ├── admin.py      # Admin & Secretary dashboard
│   │   ├── teacher.py    # Teacher dashboard, Quiz & Classroom management
│   │   ├── student.py    # Student dashboard & Quiz execution
│   │   └── messages.py   # Internal inbox messaging system
│   ├── static/           # CSS, JS, Images (Custom Design System styling)
│   ├── templates/        # Jinja2 HTML templates
│   └── translations/     # Flask-Babel .po and .mo files for i18n
├── migrations/           # Alembic database migrations (Flask-Migrate)
├── venv/                 # Python virtual environment
├── .env                  # Environment variables
├── config.py             # Configuration classes (Development, Production)
├── requirements.txt      # Python dependencies
└── run.py                # Main application entry point (runs SocketIO)
```

## 🗄️ Database Schema (SQLAlchemy)

The application uses a relational database (SQLite by default) with the following core entities:

### 1. Users & Authentication
* **User**: The central entity. Includes fields for `username`, `password_hash`, `role` (admin, secretary, teacher, student), and gamification fields (`xp`, `current_streak`).

### 2. Educational Content
* **Classroom**: Created by teachers. Contains `name` and `class_code`. Belongs to a Teacher, has many Students (Many-to-Many), and has many Quizzes (Many-to-Many).
* **Quiz**: Represents an assessment. Contains `title`, `description`, `duration_minutes`, `start_time`, `end_time`, `recurrence_pattern`, and access control settings (`randomize_questions`, `show_results`, `show_leaderboard`).
* **Question**: Belongs to a Quiz or the general Question Bank (`is_bank=True`). Supports types: `single`, `multiple`, `true_false`, `text`, `matching`, and `ordering`.
* **Option**: Belongs to a Question. Defines the text and whether `is_correct` is true.

### 3. Question Bank Organizers
* **Category**: Broad subject groupings created by Teachers.
* **Tag**: Specific keywords/topics assigned to Questions (Many-to-Many).

### 4. Student Tracking & Evaluation
* **Submission**: Represents a student's attempt at a Quiz. Tracks `score`, `max_score`, `student_name` (for guests), `user_id` (for logged-in students), and `tab_switches` (basic anti-cheat).
* **StudentAnswer**: Granular record of what a student answered for a specific Question during a Submission.

### 5. Gamification
* **Achievement**: Static badges defined in the system (e.g., "Perfect Score", "First Quiz").
* **UserAchievement**: Join table tracking when a User earned a specific Achievement.

### 6. Communication
* **Message**: Internal mail system. Tracks `sender_id`, `receiver_id`, `subject`, `content`, and read/deleted statuses.

### 7. Real-time (Live Quizzes)
* **LiveSession**: Represents an active, synchronous Kahoot-style game. Tracks the `pin` and `current_question_index`.
* **LiveParticipant**: Users joined to a `LiveSession` waiting for the teacher to advance questions.

## 🛣️ Core Routes & Blueprints

### `auth` Blueprint (`/auth`)
* `GET/POST /login`: Authenticate users.
* `GET/POST /register`: Create new student/teacher accounts.
* `GET /logout`: Terminate session.

### `teacher` Blueprint (`/teacher`)
* `GET /`: Main dashboard. Overview of quizzes, active classrooms, and at-risk students. Dashboard includes performance charts (Chart.js) and competency radar analysis.
* `GET/POST /add_quiz`: Form to create a new quiz. Logic handles importing bank questions or creating ad-hoc questions (with multiple types).
* `GET/POST /question_bank`: Central hub to CRUD Categories, Tags, and reusable Questions.
* `GET/POST /classrooms`: Create a classroom and generate a join `class_code`.
* `GET /classrooms/<id>`: Manage a specific classroom (assign/unassign quizzes, remove students).
* `GET /quiz/<id>/results`: View all submissions for a quiz.
* `GET /quiz/<id>/export_results`: Download a `.csv` of student scores.
* `POST /import_quiz`: Upload a `.csv` to mass-generate a Quiz and Questions.

### `student` Blueprint (`/student` and root)
* `GET /`: Dashboard showing assigned quizzes pending to be taken, personal competency radar charts, and unlocked achievements (Trophy Case).
* `POST /join_class`: Enter a teacher's `class_code` to enroll.
* `GET /join/<access_code>`: The entry point for taking a quiz. Handles anonymous (guest) name entry or logged-in user validation. Restricts based on Quiz `start_time`, `end_time`, and `recurrence_pattern`.
* `GET /quiz/<access_code>`: The UI for taking the actual quiz. Includes a countdown timer and tab-switching detection.
* `POST /submit/<access_code>`: The grading engine. Processes answers based on question type (`single`, `multiple`, `matching`, etc.), calculates score, awards XP and Achievements, and saves the Submission to the DB.
* `GET/POST /live/join`: Join a Kahoot-style game using a PIN.

### `admin` Blueprint (`/admin`)
* `GET /`: View global system statistics (total users, active teachers, total submissions).
* `GET/POST /user/new`, `/user/<id>/edit`, `/user/<id>/delete`: CRUD interface for managing system users.

### `messages` Blueprint (`/messages`)
* `GET /`: View inbox.
* `GET /sent`: View sent items.
* `GET/POST /compose`: Send a new message to another user.
* `GET /<id>`: Read a specific message and optionally reply.

## 📡 Real-Time Live Quizzes (SocketIO)

Live sessions are managed via `app/events.py`.
* **Teacher Flow**: `start_live_session` → `next_question` → `end_session`
* **Student Flow**: `join_live_session` → `submit_live_answer`
* Data is emitted to specific SocketIO rooms (identified by the session `pin`).

## 🌍 Internationalization (i18n)
The application leverages **Flask-Babel**. Text across the application templates and backend flashes are wrapped with `_()` or `gettext()`.
Users can switch languages via a global dropdown, which stores their preference in the Flask `session['lang']`. Re-compile translations using standard Babel commands if `.po` files are updated.
