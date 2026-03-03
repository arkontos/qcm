# QCM Platform

A comprehensive, real-time Quiz and Classroom Management Web Application built with Python and Flask.

## 📖 Description
QCM Platform is an interactive web-based educational tool designed to bridge the gap between teachers and students. It allows educators to create detailed quizzes, manage classrooms, maintain a centralized question bank, and even host live interactive quizzes (like Kahoot). Students can join classes, take practice or assigned quizzes, track their progress, and earn gamified achievements. 

Administrators have full visibility into the system, managing users (teachers, students, secretaries) and platform statistics.

## ✨ Features

### For Teachers
* **Quiz Creation**: Mix and match multiple-choice, true/false, open-ended, ordering, and matching questions.
* **Question Bank**: Centralized repository for questions categorized by topic and tags for easy reuse.
* **Live Sessions**: Host real-time synchronous quizzes with a PIN, controlling the pace of questions while students answer on their devices.
* **Classroom Management**: Group students into classrooms, assign specific quizzes, and monitor collective progress.
* **Analytics**: Detailed score breakdowns, radar charts for competency tracking, and identification of at-risk students.
* **Import/Export**: Easily import quizzes from CSV files and export student results.

### For Students
* **Interactive Quizzes**: Take assigned or practice quizzes with real-time feedback.
* **Gamification**: Earn XP, build streaks, and unlock achievements/badges for milestones (e.g., perfect scores, quick finishes).
* **Dashboard**: Track personal performance through competency radar charts (by category and tag).
* **Live Play**: Join live teacher-hosted quizzes using a simple PIN.

### General & Admin
* **Role-Based Access**: Specialized dashboards for Admins, Secretaries, Teachers, and Students.
* **Messaging System**: Built-in inbox for internal communication between users.
* **Multi-language Support**: English and French localized UI (via Flask-Babel).
* **Responsive Design**: Beautiful, mobile-friendly interface built with modern CSS and JavaScript.

## 🛠️ Technologies Used
* **Backend**: Python 3.13, Flask
* **Database**: SQLite (via Flask-SQLAlchemy & Alembic for migrations)
* **Authentication**: Flask-Login, Werkzeug Security
* **Real-time**: Flask-SocketIO (for live quizzes)
* **Frontend**: HTML5, Vanilla CSS (Custom Design System), Vanilla JavaScript, Chart.js
* **Containerization**: Docker & Docker Compose

## 🚀 Getting Started

### Prerequisites
Make sure you have the following installed:
* Python 3.10+
* Git
* (Optional) Docker and Docker Compose

### Standard Installation (Local Development)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/qcm.git
   cd qcm
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-super-secret-key-here
   FLASK_APP=run.py
   FLASK_DEBUG=1
   ```

5. **Initialize the Database**
   ```bash
   flask db upgrade
   ```
   *Note: The application will automatically seed a default admin user (`admin` / `password`) and default achievements on the first run.*

6. **Compile Translations (Optional but recommended)**
   ```bash
   pybabel compile -d app/translations
   ```

7. **Run the Application**
   Because we use SocketIO, it's recommended to run using the custom runner:
   ```bash
   python run.py
   ```
   The app will be available at `http://127.0.0.1:5000`.

### Docker Installation

If you prefer using Docker:

1. **Build and start the containers**
   ```bash
   docker-compose up -d --build
   ```
2. **Access the application**
   Open your browser and navigate to `http://localhost:5000`.

## 📚 Documentation
For an in-depth look at the database schema, application architecture, and routing structure, please see [DOCUMENTATION.md](DOCUMENTATION.md).

## 🤝 Contributing
1. Fork the repository
2. Create a new feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
