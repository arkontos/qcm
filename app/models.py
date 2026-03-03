from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Association table for Question and Tag (Many-to-Many)
question_tags = db.Table('question_tags',
    db.Column('question_id', db.Integer, db.ForeignKey('question.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# Association table for Classroom and Student (Many-to-Many)
classroom_students = db.Table('classroom_students',
    db.Column('classroom_id', db.Integer, db.ForeignKey('classroom.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# Association table for Classroom and Quiz (Many-to-Many)
classroom_quizzes = db.Table('classroom_quizzes',
    db.Column('classroom_id', db.Integer, db.ForeignKey('classroom.id'), primary_key=True),
    db.Column('quiz_id', db.Integer, db.ForeignKey('quiz.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='teacher', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Email Confirmation
    email_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    confirmation_code = db.Column(db.String(6), nullable=True)
    
    # Gamification Fields
    xp = db.Column(db.Integer, default=0)
    current_streak = db.Column(db.Integer, default=0)
    last_login_date = db.Column(db.Date, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    access_code = db.Column(db.String(10), unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    duration_minutes = db.Column(db.Integer, default=10) # Total duration (optional usage now)
    time_per_question = db.Column(db.Integer, default=30) # Seconds per question
    start_time = db.Column(db.DateTime, nullable=True) # Valid from Date
    end_time = db.Column(db.DateTime, nullable=True) # Valid until Date
    randomize_questions = db.Column(db.Boolean, default=False)
    show_results = db.Column(db.Boolean, default=True)
    show_leaderboard = db.Column(db.Boolean, default=True)
    recurrence_pattern = db.Column(db.String(50), default='none') # e.g., 'none', 'daily', 'weekly'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade="all, delete-orphan")
    submissions = db.relationship('Submission', backref='quiz', lazy=True, cascade="all, delete-orphan")

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=True) # Now nullable for bank questions
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Owner of the bank question
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    text = db.Column(db.String(500), nullable=False)
    question_type = db.Column(db.String(50), default='single') # 'single', 'multiple', 'true_false', 'text'
    media_url = db.Column(db.String(500), nullable=True)
    is_bank = db.Column(db.Boolean, default=False)
    options = db.relationship('Option', backref='question', lazy=True, cascade="all, delete-orphan")
    tags = db.relationship('Tag', secondary=question_tags, lazy='subquery', backref=db.backref('questions', lazy=True))
    category = db.relationship('Category', backref='questions', lazy=True)

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    media_url = db.Column(db.String(500), nullable=True) # Supported added for Audio/Video/Image per option
    is_correct = db.Column(db.Boolean, default=False)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Optional for guests vs logged-in
    student_name = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    tab_switches = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.relationship('StudentAnswer', backref='submission', lazy=True, cascade="all, delete-orphan")

class StudentAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('option.id'), nullable=True) # Nullable for text answers
    text_answer = db.Column(db.String(1000), nullable=True) # For open-ended questions
    json_answer = db.Column(db.String(1000), nullable=True) # Used for matching / ordering pairs arrays
    is_correct = db.Column(db.Boolean, default=False)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(20), default='#3B82F6') # Hex color for UI
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    teacher = db.relationship('User', backref='taught_classes')
    class_code = db.Column(db.String(10), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    students = db.relationship('User', secondary=classroom_students, lazy='subquery', backref=db.backref('classrooms', lazy=True))
    quizzes = db.relationship('Quiz', secondary=classroom_quizzes, lazy='subquery', backref=db.backref('classrooms', lazy=True))

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    icon_url = db.Column(db.String(255), nullable=True)
    condition_type = db.Column(db.String(50), nullable=False) # e.g., 'perfect_score', 'first_quiz'

class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('achievements', lazy=True))
    achievement = db.relationship('Achievement')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    parent_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)
    deleted_by_sender = db.Column(db.Boolean, default=False, server_default='0')
    deleted_by_receiver = db.Column(db.Boolean, default=False, server_default='0')
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy=True))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy=True))
    replies = db.relationship('Message', backref=db.backref('parent', remote_side=[id]), lazy=True, cascade="all, delete-orphan")

class LiveSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pin = db.Column(db.String(10), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    current_question_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    quiz = db.relationship('Quiz', backref='live_sessions')
    teacher = db.relationship('User', backref='live_sessions')
    participants = db.relationship('LiveParticipant', backref='session', lazy=True, cascade="all, delete-orphan")

class LiveParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('live_session.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, default=0)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
