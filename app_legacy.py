from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

# Initialize App
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-this-in-prod'
# Use absolute path to avoid ambiguity
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'qcm.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Models ---

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    duration_minutes = db.Column(db.Integer, default=10) # Total duration (optional usage now)
    time_per_question = db.Column(db.Integer, default=30) # Seconds per question
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade="all, delete-orphan")
    submissions = db.relationship('Submission', backref='quiz', lazy=True, cascade="all, delete-orphan")

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    options = db.relationship('Option', backref='question', lazy=True, cascade="all, delete-orphan")

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- Routes ---

@app.route('/')
def home():
    return render_template('home.html') # Placeholder, need to create

@app.route('/teacher')
def teacher_dashboard():
    quizzes = Quiz.query.order_by(Quiz.created_at.desc()).all()
    return render_template('teacher_dashboard.html', quizzes=quizzes)

@app.route('/teacher/add_quiz', methods=['GET', 'POST'])
def add_quiz():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        duration_str = request.form.get('duration')
        time_per_q_str = request.form.get('time_per_question')
        
        duration = int(duration_str) if duration_str and duration_str.isdigit() else 10
        time_per_question = int(time_per_q_str) if time_per_q_str and time_per_q_str.isdigit() else 30
        
        new_quiz = Quiz(
            title=title, 
            description=description, 
            duration_minutes=duration,
            time_per_question=time_per_question
        )
        db.session.add(new_quiz)
        db.session.commit()
        
        # Determine how many questions were added by checking the form keys
        # The form sends questions in a structured way that Flask can't parse automatically into a list of dicts easily without some parsing logic
        # Or we can iterate based on hypothetical indices.
        # A simpler way given standard form submission:
        
        # Iterating through form data to find question blocks
        # We need to rely on the form structure: questions[index][text], questions[index][options][], questions[index][correct]
        
        data = request.form
        
        # Manual parsing of the complex form data
        # Let's group by question index
        questions_data = {}
        for key in data.keys():
            if key.startswith('questions['):
                # extract ID
                import re
                match = re.search(r'questions\[(\d+)\]\[(.*)\]', key)
                if match:
                    q_id = int(match.group(1))
                    field = match.group(2)
                    
                    if q_id not in questions_data:
                        questions_data[q_id] = {'options': []}
                    
                    if field == 'text':
                        questions_data[q_id]['text'] = data[key]
                    elif field == 'correct':
                        questions_data[q_id]['correct'] = int(data[key])
                    elif field == 'options[]':
                         # options[] comes as a list from Flask's request.form.getlist if we access it directly, 
                         # but here we are iterating keys. 
                         # let's skip options[] here and handle it separately below
                         pass

        # Handle options separately as they are lists
        for q_id in questions_data.keys():
            options = request.form.getlist(f'questions[{q_id}][options][]')
            questions_data[q_id]['options'] = options

        # Create Question and Option objects
        for q_id, q_data in questions_data.items():
            if 'text' in q_data and 'options' in q_data:
                new_question = Question(quiz_id=new_quiz.id, text=q_data['text'])
                db.session.add(new_question)
                db.session.commit() # Commit to get ID
                
                for i, opt_text in enumerate(q_data['options']):
                    is_correct = (i == q_data.get('correct'))
                    new_option = Option(question_id=new_question.id, text=opt_text, is_correct=is_correct)
                    db.session.add(new_option)
        
        db.session.commit()
        return redirect(url_for('teacher_dashboard'))

    return render_template('add_quiz.html')

@app.route('/teacher/quiz/delete/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    db.session.delete(quiz)
    db.session.commit()
    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/quiz/edit/<int:quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        quiz.title = request.form.get('title')
        quiz.description = request.form.get('description')
        
        duration_str = request.form.get('duration')
        time_per_q_str = request.form.get('time_per_question')
        
        quiz.duration_minutes = int(duration_str) if duration_str and duration_str.isdigit() else 10
        quiz.time_per_question = int(time_per_q_str) if time_per_q_str and time_per_q_str.isdigit() else 30
        
        # Delete existing questions to replace with new set
        # This is a simplification strategy since we don't track question-level stats nicely yet
        for question in quiz.questions:
            db.session.delete(question)
        
        # Re-add questions from form
        data = request.form
        questions_data = {}
        for key in data.keys():
            if key.startswith('questions['):
                import re
                match = re.search(r'questions\[(\d+)\]\[(.*)\]', key)
                if match:
                    q_idx = int(match.group(1))
                    field = match.group(2)
                    
                    if q_idx not in questions_data:
                        questions_data[q_idx] = {'options': []}
                    
                    if field == 'text':
                        questions_data[q_idx]['text'] = data[key]
                    elif field == 'correct':
                        questions_data[q_idx]['correct'] = int(data[key])

        for q_idx in questions_data.keys():
            # Form index might not match array index perfectly if deletions happened in JS, but we use keys
            # Options are lists
            options = request.form.getlist(f'questions[{q_idx}][options][]')
            questions_data[q_idx]['options'] = options

        for q_idx, q_data in questions_data.items():
            if 'text' in q_data and 'options' in q_data:
                new_question = Question(quiz_id=quiz.id, text=q_data['text'])
                db.session.add(new_question)
                db.session.commit() # Commit to get ID
                
                for i, opt_text in enumerate(q_data['options']):
                    # The radio value from form corresponds to index in the options list for that question
                    # We need to make sure we treat it correctly. 
                    # In add_quiz JS: value="${opt-1}" (0, 1, 2, 3)
                    # In edit_quiz Jinja: value="{{ loop.index0 }}"
                    is_correct = (i == q_data.get('correct'))
                    new_option = Option(question_id=new_question.id, text=opt_text, is_correct=is_correct)
                    db.session.add(new_option)

        db.session.commit()
        return redirect(url_for('teacher_dashboard'))

    return render_template('edit_quiz.html', quiz=quiz)

@app.route('/teacher/quiz/<int:quiz_id>/results')
def view_results(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    submissions = Submission.query.filter_by(quiz_id=quiz_id).order_by(Submission.submitted_at.desc()).all()
    return render_template('view_results.html', quiz=quiz, submissions=submissions)

@app.route('/student/join/<int:quiz_id>', methods=['GET', 'POST'])
def student_join(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            session['student_name'] = name
            # Store quiz_id in session to verify they joined correctly or just rely on URL
            return redirect(url_for('take_quiz', quiz_id=quiz.id))
    return render_template('student_join_quiz.html', quiz=quiz)

@app.route('/student/quiz/<int:quiz_id>')
def take_quiz(quiz_id):
    if 'student_name' not in session:
        return redirect(url_for('student_join', quiz_id=quiz_id))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('quiz_take.html', quiz=quiz)

@app.route('/student/submit/<int:quiz_id>', methods=['POST'])
def student_submit(quiz_id):
    if 'student_name' not in session:
        return redirect(url_for('student_join', quiz_id=quiz_id))
        
    quiz = Quiz.query.get_or_404(quiz_id)
    student_name = session['student_name']
    
    score = 0
    max_score = len(quiz.questions)
    
    for question in quiz.questions:
        selected_option_id = request.form.get(f'q_{question.id}')
        if selected_option_id:
            selected_option = Option.query.get(int(selected_option_id))
            if selected_option and selected_option.is_correct:
                score += 1
                
    # Save submission
    submission = Submission(
        quiz_id=quiz_id,
        student_name=student_name,
        score=score,
        max_score=max_score
    )
    db.session.add(submission)
    db.session.commit()
    
    # Clear session if needed, but keeping name might be useful
    return render_template('student_result.html', score=score, max_score=max_score, student_name=student_name)


if __name__ == '__main__':
    app.run(debug=True)
