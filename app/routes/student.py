from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models import Quiz, Question, Option, Submission, Classroom, StudentAnswer, Achievement, UserAchievement

bp = Blueprint('student', __name__)

@bp.route('/join/<string:access_code>', methods=['GET', 'POST'])
def join(access_code):
    quiz = Quiz.query.filter_by(access_code=access_code).first()
    if not quiz:
        flash('Quiz not found. Please verify the access code.', 'error')
        return redirect(url_for('main.home'))
    
    # Validation Rules
    now = datetime.utcnow()
    if quiz.start_time and now < quiz.start_time:
        flash(f'This quiz will not be available until {quiz.start_time.strftime("%m/%d/%Y, %H:%M")}', 'error')
        return redirect(url_for('main.home'))
    if quiz.end_time and now > quiz.end_time:
        flash(f'This quiz closed on {quiz.end_time.strftime("%m/%d/%Y, %H:%M")}', 'error')
        return redirect(url_for('main.home'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            existing_sub = Submission.query.filter_by(quiz_id=quiz.id, student_name=name).first()
            if existing_sub:
                flash('A submission with this name already exists for this quiz.', 'error')
                return redirect(url_for('student.join', access_code=quiz.access_code))
            session['student_name'] = name
            return redirect(url_for('student.take_quiz', access_code=quiz.access_code))
            
    if current_user.is_authenticated and current_user.role == 'student':
        # Check if already submitted and handle recurrence
        existing_sub = Submission.query.filter_by(quiz_id=quiz.id, user_id=current_user.id).order_by(Submission.submitted_at.desc()).first()
        
        if existing_sub:
            pattern = getattr(quiz, 'recurrence_pattern', 'none')
            can_retake = False
            
            if pattern == 'daily':
                if existing_sub.submitted_at.date() < now.date(): can_retake = True
            elif pattern == 'weekly':
                if existing_sub.submitted_at.isocalendar()[1] != now.isocalendar()[1] or existing_sub.submitted_at.year != now.year: can_retake = True
            elif pattern == 'monthly':
                if existing_sub.submitted_at.month != now.month or existing_sub.submitted_at.year != now.year: can_retake = True
                
            if not can_retake:
                flash(f'You have already completed the quiz "{quiz.title}". You cannot take it again right now.', 'error')
                return redirect(url_for('student.dashboard'))
                
        return redirect(url_for('student.take_quiz', access_code=quiz.access_code))
        
    return render_template('student_join_quiz.html', quiz=quiz)

@bp.route('/')
@login_required
def dashboard():
    if current_user.role != 'student':
        flash('Access Denied', 'error')
        return redirect(url_for('main.home'))
        
    submissions = Submission.query.filter_by(user_id=current_user.id).order_by(Submission.submitted_at.desc()).all()
    
    # Store latest submission per quiz for logic
    latest_submission_for_quiz = {}
    for sub in submissions:
        if sub.quiz_id not in latest_submission_for_quiz:
            latest_submission_for_quiz[sub.quiz_id] = sub
            
    pending_class_quizzes = []
    now = datetime.utcnow()
    
    for classroom in current_user.classrooms:
        for quiz in classroom.quizzes:
            can_take = False
            
            if quiz.id not in latest_submission_for_quiz:
                can_take = True
            else:
                last_sub = latest_submission_for_quiz[quiz.id]
                pattern = getattr(quiz, 'recurrence_pattern', 'none')
                
                if pattern == 'daily':
                    if last_sub.submitted_at.date() < now.date(): can_take = True
                elif pattern == 'weekly':
                    if last_sub.submitted_at.isocalendar()[1] != now.isocalendar()[1] or last_sub.submitted_at.year != now.year: can_take = True
                elif pattern == 'monthly':
                    if last_sub.submitted_at.month != now.month or last_sub.submitted_at.year != now.year: can_take = True
            
            # Additional validity check
            if can_take:
                if quiz.start_time and now < quiz.start_time: can_take = False
                if quiz.end_time and now > quiz.end_time: can_take = False
                
            if can_take:
                if not any(item['quiz'].id == quiz.id for item in pending_class_quizzes):
                    pending_class_quizzes.append({
                        'quiz': quiz,
                        'classroom_name': classroom.name
                    })
                
    # Calculate Competency Radar by Category and Tag
    student_answers = StudentAnswer.query.join(Submission).filter(Submission.user_id == current_user.id).all()
    
    category_stats = {}
    tag_stats = {}
    
    for answer in student_answers:
        question = Question.query.get(answer.question_id)
        if not question:
            continue
            
        # Category tracking
        if question.category:
            cat_name = question.category.name
            if cat_name not in category_stats:
                category_stats[cat_name] = {'correct': 0, 'total': 0}
            category_stats[cat_name]['total'] += 1
            if answer.is_correct:
                category_stats[cat_name]['correct'] += 1
                
        # Tag tracking
        for tag in question.tags:
            tag_name = tag.name
            if tag_name not in tag_stats:
                tag_stats[tag_name] = {'correct': 0, 'total': 0}
            tag_stats[tag_name]['total'] += 1
            if answer.is_correct:
                tag_stats[tag_name]['correct'] += 1
                
    radar_labels = []
    radar_scores = []
    for cat_name, stats in category_stats.items():
        radar_labels.append(cat_name)
        radar_scores.append(round((stats['correct'] / stats['total']) * 100))
        
    radar_data = {
        'labels': radar_labels,
        'scores': radar_scores
    }
    
    tag_radar_labels = []
    tag_radar_scores = []
    for tag_name, stats in tag_stats.items():
        tag_radar_labels.append(tag_name)
        tag_radar_scores.append(round((stats['correct'] / stats['total']) * 100))
        
    tag_radar_data = {
        'labels': tag_radar_labels,
        'scores': tag_radar_scores
    }
    
    # Fetch earned achievements for Trophy Case
    earned_achievements = []
    if current_user.achievements:
        for ua in current_user.achievements:
            ach = Achievement.query.get(ua.achievement_id)
            if ach:
                earned_achievements.append(ach)
                
    return render_template('student_dashboard.html', submissions=submissions, pending_class_quizzes=pending_class_quizzes, radar_data=radar_data, tag_radar_data=tag_radar_data, earned_achievements=earned_achievements)

@bp.route('/join_class', methods=['POST'])
@login_required
def join_class():
    if current_user.role != 'student':
        abort(403)
        
    class_code = request.form.get('class_code')
    if class_code:
        classroom = Classroom.query.filter_by(class_code=class_code.strip()).first()
        if classroom:
            if current_user not in classroom.students:
                classroom.students.append(current_user)
                db.session.commit()
                flash(f'Successfully joined {classroom.name}!', 'success')
            else:
                flash(f'You are already enrolled in {classroom.name}.', 'info')
        else:
            flash('Invalid Class Code.', 'error')
            
    return redirect(url_for('student.dashboard'))

@bp.route('/quiz/<string:access_code>')
def take_quiz(access_code):
    if not current_user.is_authenticated and 'student_name' not in session:
        return redirect(url_for('student.join', access_code=access_code))
    
    quiz = Quiz.query.filter_by(access_code=access_code).first()
    if not quiz:
        flash('Quiz not found.', 'error')
        return redirect(url_for('main.home'))
    
    if current_user.is_authenticated and current_user.role == 'student':
        existing_sub = Submission.query.filter_by(quiz_id=quiz.id, user_id=current_user.id).first()
        if existing_sub:
            flash(f'You have already completed the quiz "{quiz.title}". You cannot take it again.', 'error')
            return redirect(url_for('student.dashboard'))
    elif 'student_name' in session:
        existing_sub = Submission.query.filter_by(quiz_id=quiz.id, student_name=session['student_name']).first()
        if existing_sub:
            flash(f'A submission under the name "{session["student_name"]}" already exists for the quiz "{quiz.title}". You cannot take it again.', 'error')
            session.pop('student_name', None)
            return redirect(url_for('main.home'))

    return render_template('quiz_take.html', quiz=quiz, is_practice=False)

@bp.route('/practice/<string:access_code>')
def practice_quiz(access_code):
    if not current_user.is_authenticated and 'student_name' not in session:
        return redirect(url_for('student.join', access_code=access_code))
        
    quiz = Quiz.query.filter_by(access_code=access_code).first()
    if not quiz:
        flash('Quiz not found.', 'error')
        return redirect(url_for('main.home'))
    return render_template('quiz_take.html', quiz=quiz, is_practice=True)

@bp.route('/submit/<string:access_code>', methods=['POST'])
def submit(access_code):
    if not current_user.is_authenticated and 'student_name' not in session:
        return redirect(url_for('student.join', access_code=access_code))
        
    quiz = Quiz.query.filter_by(access_code=access_code).first_or_404()
    
    if current_user.is_authenticated:
        student_name = current_user.username
        user_id = current_user.id
        existing_sub = Submission.query.filter_by(quiz_id=quiz.id, user_id=current_user.id).first()
    else:
        student_name = session['student_name']
        user_id = None
        existing_sub = Submission.query.filter_by(quiz_id=quiz.id, student_name=student_name).first()
        
    if existing_sub:
        flash('You have already submitted this quiz.', 'error')
        if current_user.is_authenticated and current_user.role == 'student':
            return redirect(url_for('student.dashboard'))
        else:
            session.pop('student_name', None)
            return redirect(url_for('main.home'))
    
    score = 0
    max_score = len(quiz.questions)
    
    try:
        tab_switches = int(request.form.get('tab_switches', 0))
    except ValueError:
        tab_switches = 0
    
    submission = Submission(
        quiz_id=quiz.id,
        user_id=user_id,
        student_name=student_name,
        score=0, # Will update after loop
        max_score=max_score,
        tab_switches=tab_switches
    )
    db.session.add(submission)
    db.session.flush() # Get submission ID
    
    for question in quiz.questions:
        is_correct = False
        selected_option_id = None
        text_answer = None

        if question.question_type == 'multiple':
            selected_option_ids = request.form.getlist(f'q_{question.id}')
            correct_options = [str(o.id) for o in question.options if o.is_correct]
            if set(selected_option_ids) == set(correct_options) and len(correct_options) > 0:
                is_correct = True
                score += 1
            # For simplicity in storing, we just store the first selected if any, or leave null for multiple. 
            # In a robust system, we might need a StudentAnswerOption join table for multiple.
            if selected_option_ids:
                selected_option_id = int(selected_option_ids[0])

        elif question.question_type == 'text':
            text_answer = request.form.get(f'q_{question.id}')
            # Manual grading expected
            
        elif question.question_type == 'ordering':
            # The client will pass a comma-separated list of ordered Option IDs
            order_str = request.form.get(f'q_{question.id}_order')
            if order_str:
                selected_order = [int(x) for x in order_str.split(',') if x.isdigit()]
                correct_order = [o.id for o in question.options] # The DB order is the correct order for ordering questions
                
                # Grading logic: Full point only if exact sequence? Let's check exact sequence for simplicity/strictness
                if selected_order == correct_order:
                    is_correct = True
                    score += 1
                
                import json
                student_answer_json = json.dumps(selected_order)

        elif question.question_type == 'matching':
            # Client passes individual matching connections via hidden inputs or similar mapping:
            # e.g., mapping left option ID to right item text/ID.
            # We stored `Item::|::Match` in option text.
            correct_pairs = {str(o.id): o.text.split('::|::')[1] if '::|::' in o.text else '' for o in question.options}
            
            student_pairs = {}
            correct_count = 0
            for opt in question.options:
                # The form should map OptionID -> matched string text
                student_match = request.form.get(f'q_{question.id}_match_{opt.id}', '')
                student_pairs[str(opt.id)] = student_match
                if student_match == correct_pairs.get(str(opt.id)):
                    correct_count += 1
                    
            if correct_count == len(question.options) and len(question.options) > 0:
                is_correct = True
                score += 1
                
            import json
            student_answer_json = json.dumps(student_pairs)

        else:
            selected_id_str = request.form.get(f'q_{question.id}')
            if selected_id_str:
                selected_option_id = int(selected_id_str)
                selected_option = Option.query.get(selected_option_id)
                if selected_option and selected_option.is_correct:
                    is_correct = True
                    score += 1
        
        # Save the student's answer
        student_answer = StudentAnswer(
            submission_id=submission.id,
            question_id=question.id,
            selected_option_id=selected_option_id,
            text_answer=text_answer,
            json_answer=student_answer_json if 'student_answer_json' in locals() else None,
            is_correct=is_correct
        )
        db.session.add(student_answer)
                
    submission.score = score
    db.session.commit()
    
    # Award XP
    if current_user.is_authenticated and current_user.role == 'student':
        base_xp = 10
        score_xp = score * 5
        streak_bonus = (current_user.current_streak or 0) * 2
        total_xp_earned = base_xp + score_xp + streak_bonus
        current_user.xp = (current_user.xp or 0) + total_xp_earned
        db.session.commit()
        flash(f'You earned {total_xp_earned} XP! (Base: {base_xp}, Score: {score_xp}, Streak Bonus: {streak_bonus})', 'success')
        
    # Award Achievements
    if current_user.is_authenticated and current_user.role == 'student':
        awarded_badges = []
        achievements = Achievement.query.all()
        user_achievements = [ua.achievement_id for ua in current_user.achievements]
        
        # Need to check sub count BEFORE this one since we just added it, or use count <= 1
        sub_count = Submission.query.filter_by(user_id=current_user.id).count()
        
        if score == max_score and max_score > 0:
            a = next((a for a in achievements if a.condition_type == 'perfect_score'), None)
            if a and a.id not in user_achievements:
                db.session.add(UserAchievement(user_id=current_user.id, achievement_id=a.id))
                awarded_badges.append(a)
                
        if sub_count == 1:
            a = next((a for a in achievements if a.condition_type == 'first_quiz'), None)
            if a and a.id not in user_achievements:
                db.session.add(UserAchievement(user_id=current_user.id, achievement_id=a.id))
                awarded_badges.append(a)
                
        if sub_count == 5:
            a = next((a for a in achievements if a.condition_type == 'five_quizzes'), None)
            if a and a.id not in user_achievements:
                db.session.add(UserAchievement(user_id=current_user.id, achievement_id=a.id))
                awarded_badges.append(a)
                
        if awarded_badges:
            db.session.commit()
            for b in awarded_badges:
                flash(f'Achievement Unlocked: {b.icon_url} {b.name}', 'success')
    
    leaderboard = None
    if quiz.show_leaderboard:
        from sqlalchemy import desc
        leaderboard = Submission.query.filter_by(quiz_id=quiz.id).order_by(desc(Submission.score), Submission.submitted_at).limit(10).all()
    
    return render_template('student_result.html', score=score, max_score=max_score, student_name=student_name, show_results=quiz.show_results, show_leaderboard=quiz.show_leaderboard, leaderboard=leaderboard)

@bp.route('/live/join', methods=['GET', 'POST'])
def join_live():
    if request.method == 'POST':
        pin = request.form.get('pin')
        name = request.form.get('name')
        
        if current_user.is_authenticated:
            name = current_user.username
            
        if not pin or not name:
            flash('Please provide both PIN and Name', 'error')
            return redirect(url_for('student.join_live'))
            
        from app.models import LiveSession
        session_obj = LiveSession.query.filter_by(pin=pin, is_active=True).first()
        if not session_obj:
            flash('Invalid PIN or active session not found', 'error')
            return redirect(url_for('main.home'))
            
        session['live_name'] = name
        return redirect(url_for('student.play_live', pin=pin))
        
    return render_template('student_live_join.html')

@bp.route('/live/play/<string:pin>')
def play_live(pin):
    name = session.get('live_name')
    if current_user.is_authenticated:
        name = current_user.username
        
    if not name:
        flash('Please enter your name to join', 'error')
        return redirect(url_for('student.join_live'))
        
    from app.models import LiveSession
    session_obj = LiveSession.query.filter_by(pin=pin, is_active=True).first()
    if not session_obj:
        flash('Session no longer active or invalid PIN', 'error')
        return redirect(url_for('main.home'))
        
    return render_template('student_live_play.html', pin=pin, name=name)
