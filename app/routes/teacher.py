from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask_login import login_required, current_user
from app import db
from app.models import Quiz, Question, Option, Submission, User, Category, Tag, Classroom, StudentAnswer

bp = Blueprint('teacher', __name__)

@bp.before_request
@login_required
def require_login():
    if current_user.role not in ['teacher', 'admin', 'secretary']:
        flash("You do not have permission to access that area.", "error")
        return redirect(url_for('main.home'))

@bp.route('/')
def dashboard():
    if current_user.role == 'admin' or current_user.role == 'secretary':
        return redirect(url_for('admin.dashboard'))
        
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '')
    
    query = Quiz.query.filter_by(teacher_id=current_user.id)
    if search:
        query = query.filter(Quiz.title.ilike(f'%{search}%') | Quiz.access_code.ilike(f'%{search}%'))
        
    pagination = query.order_by(Quiz.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    quizzes = pagination.items
    
    total_quizzes = Quiz.query.filter_by(teacher_id=current_user.id).count()
    teacher_quizzes_all = Quiz.query.filter_by(teacher_id=current_user.id).all()
    teacher_quiz_ids = [q.id for q in teacher_quizzes_all]
    
    total_subs = Submission.query.filter(Submission.quiz_id.in_(teacher_quiz_ids)).count() if teacher_quiz_ids else 0
    total_classrooms = Classroom.query.filter_by(teacher_id=current_user.id).count()
    
    # Calculate At-Risk students & Unique Students
    at_risk_students = []
    teacher_students = set()
    for c in current_user.classrooms:
        for s in c.students:
            teacher_students.add(s)
            
    total_students = len(teacher_students)
    overall_total_score = 0
    overall_max_score = 0
    
    for student in teacher_students:
        student_subs = Submission.query.filter(Submission.quiz_id.in_(teacher_quiz_ids), Submission.user_id == student.id).all() if teacher_quiz_ids else []
        if student_subs:
            total_s = sum(s.score for s in student_subs)
            total_m = sum(s.max_score for s in student_subs)
            overall_total_score += total_s
            overall_max_score += total_m
            
            if total_m > 0:
                avg = (total_s / total_m) * 100
                if avg < 50:
                    at_risk_students.append({
                        'student': student,
                        'average': round(avg, 1),
                        'attempts': len(student_subs)
                    })
    at_risk_students.sort(key=lambda x: x['average'])
    
    overall_average = round((overall_total_score / overall_max_score) * 100, 1) if overall_max_score > 0 else 0
    
    # Quiz Performance Data for Charts
    chart_data = []
    tag_stats = {}
    
    for q in teacher_quizzes_all:
        subs = Submission.query.filter_by(quiz_id=q.id).all()
        if subs:
            q_total = sum(s.score for s in subs)
            q_max = sum(s.max_score for s in subs)
            avg = round((q_total / q_max) * 100, 1) if q_max > 0 else 0
            chart_data.append({
                'title': q.title,
                'submissions': len(subs),
                'average': avg
            })
            
            # Aggregate tags for all submissions of this quiz
            for sub in subs:
                for ans in sub.answers:
                    q_obj = Question.query.get(ans.question_id)
                    if q_obj:
                        for tg in q_obj.tags:
                            if tg.name not in tag_stats:
                                tag_stats[tg.name] = {'correct': 0, 'total': 0}
                            tag_stats[tg.name]['total'] += 1
                            if ans.is_correct:
                                tag_stats[tg.name]['correct'] += 1
                                
    # Format tag data for Radar Chart
    tag_radar_labels = []
    tag_radar_scores = []
    for tg_name, stats in tag_stats.items():
        tag_radar_labels.append(tg_name)
        tag_radar_scores.append(round((stats['correct'] / stats['total']) * 100))
        
    tag_radar_data = {
        'labels': tag_radar_labels,
        'scores': tag_radar_scores
    }
    
    return render_template('teacher_dashboard.html', quizzes=quizzes, pagination=pagination, search=search, target_user=current_user, 
                           total_quizzes=total_quizzes, total_subs=total_subs, at_risk_students=at_risk_students,
                           total_classrooms=total_classrooms, total_students=total_students, overall_average=overall_average,
                           chart_data=chart_data, tag_radar_data=tag_radar_data)

@bp.route('/user/<int:user_id>/quizzes')
def user_quizzes(user_id):
    if current_user.role not in ['admin', 'secretary'] and current_user.id != user_id:
        abort(403)
    
    target_user = User.query.get_or_404(user_id)
    if target_user.role != 'teacher':
        flash('Invalid teacher profile.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '')
    
    query = Quiz.query.filter_by(teacher_id=user_id)
    if search:
        query = query.filter(Quiz.title.ilike(f'%{search}%') | Quiz.access_code.ilike(f'%{search}%'))
        
    pagination = query.order_by(Quiz.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    quizzes = pagination.items
    
    total_quizzes = Quiz.query.filter_by(teacher_id=user_id).count()
    teacher_quizzes_all = Quiz.query.filter_by(teacher_id=user_id).all()
    teacher_quiz_ids = [q.id for q in teacher_quizzes_all]
    
    total_subs = Submission.query.filter(Submission.quiz_id.in_(teacher_quiz_ids)).count() if teacher_quiz_ids else 0
    total_classrooms = Classroom.query.filter_by(teacher_id=user_id).count()
    
    # Calculate At-Risk students for the target_user (teacher)
    at_risk_students = []
    teacher_students = set()
    for c in target_user.classrooms:
        for s in c.students:
            teacher_students.add(s)
            
    total_students = len(teacher_students)
    overall_total_score = 0
    overall_max_score = 0
            
    for student in teacher_students:
        student_subs = Submission.query.filter(Submission.quiz_id.in_(teacher_quiz_ids), Submission.user_id == student.id).all() if teacher_quiz_ids else []
        if student_subs:
            total_s = sum(s.score for s in student_subs)
            total_m = sum(s.max_score for s in student_subs)
            overall_total_score += total_s
            overall_max_score += total_m
            if total_m > 0:
                avg = (total_s / total_m) * 100
                if avg < 50:
                    at_risk_students.append({
                        'student': student,
                        'average': round(avg, 1),
                        'attempts': len(student_subs)
                    })
    at_risk_students.sort(key=lambda x: x['average'])
    
    overall_average = round((overall_total_score / overall_max_score) * 100, 1) if overall_max_score > 0 else 0
    
    # Quiz Performance Data for Charts
    chart_data = []
    tag_stats = {}
    
    for q in teacher_quizzes_all:
        subs = Submission.query.filter_by(quiz_id=q.id).all()
        if subs:
            q_total = sum(s.score for s in subs)
            q_max = sum(s.max_score for s in subs)
            avg = round((q_total / q_max) * 100, 1) if q_max > 0 else 0
            chart_data.append({
                'title': q.title,
                'submissions': len(subs),
                'average': avg
            })
            
            # Aggregate tags for all submissions of this quiz
            for sub in subs:
                for ans in sub.answers:
                    q_obj = Question.query.get(ans.question_id)
                    if q_obj:
                        for tg in q_obj.tags:
                            if tg.name not in tag_stats:
                                tag_stats[tg.name] = {'correct': 0, 'total': 0}
                            tag_stats[tg.name]['total'] += 1
                            if ans.is_correct:
                                tag_stats[tg.name]['correct'] += 1
                                
    # Format tag data for Radar Chart
    tag_radar_labels = []
    tag_radar_scores = []
    for tg_name, stats in tag_stats.items():
        tag_radar_labels.append(tg_name)
        tag_radar_scores.append(round((stats['correct'] / stats['total']) * 100))
        
    tag_radar_data = {
        'labels': tag_radar_labels,
        'scores': tag_radar_scores
    }
    
    return render_template('teacher_dashboard.html', quizzes=quizzes, pagination=pagination, search=search, target_user=target_user, 
                           total_quizzes=total_quizzes, total_subs=total_subs, at_risk_students=at_risk_students,
                           total_classrooms=total_classrooms, total_students=total_students, overall_average=overall_average,
                           chart_data=chart_data, tag_radar_data=tag_radar_data)

@bp.route('/add_quiz', methods=['GET', 'POST'])
@bp.route('/user/<int:user_id>/add_quiz', methods=['GET', 'POST'])
def add_quiz(user_id=None):
    if current_user.role == 'secretary':
        abort(403)
        
    if user_id:
        if current_user.role != 'admin':
            abort(403)
        target_id = user_id
    else:
        target_id = current_user.id

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        duration_str = request.form.get('duration')
        time_per_q_str = request.form.get('time_per_question')
        
        duration = int(duration_str) if duration_str and duration_str.isdigit() else 10
        time_per_question = int(time_per_q_str) if time_per_q_str and time_per_q_str.isdigit() else 30
        
        from datetime import datetime
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M') if start_time_str else None
        end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M') if end_time_str else None
        
        randomize_questions = request.form.get('randomize_questions') == 'true'
        show_results = request.form.get('show_results') == 'true'
        show_leaderboard = request.form.get('show_leaderboard') == 'true'
        recurrence_pattern = request.form.get('recurrence_pattern', 'none')
        
        import string, random
        access_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

        new_quiz = Quiz(
            title=title, 
            description=description, 
            duration_minutes=duration,
            time_per_question=time_per_question,
            start_time=start_time,
            end_time=end_time,
            randomize_questions=randomize_questions,
            show_results=show_results,
            show_leaderboard=show_leaderboard,
            recurrence_pattern=recurrence_pattern,
            teacher_id=target_id,
            access_code=access_code
        )
        db.session.add(new_quiz)
        db.session.commit()
        
        bank_count = request.form.get('bank_count', type=int)
        if bank_count and bank_count > 0:
            bank_cat = request.form.get('bank_category', type=int)
            bank_tag = request.form.get('bank_tag', type=int)
            
            # Since the global pool may be intended to span the application, 
            # we query globally. However, if category or tag is passed, 
            # it will effectively scope down. 
            # Let's keep it restricted to current teacher's bank for complete safety 
            # and better ownership mapping as per schema implementations.
            bq_query = Question.query.filter_by(is_bank=True, teacher_id=current_user.id)
            if bank_cat:
                bq_query = bq_query.filter_by(category_id=bank_cat)
            if bank_tag:
                 bq_query = bq_query.filter(Question.tags.any(id=bank_tag))
                 
            available_qs = bq_query.all()
            if available_qs:
                import random
                selected_qs = random.sample(available_qs, min(bank_count, len(available_qs)))
                for q in selected_qs:
                    cloned_q = Question(
                        quiz_id=new_quiz.id,
                        text=q.text,
                        question_type=q.question_type,
                        media_url=q.media_url,
                        is_bank=False
                    )
                    db.session.add(cloned_q)
                    db.session.flush()
                    
                    for opt in q.options:
                        cloned_opt = Option(question_id=cloned_q.id, text=opt.text, is_correct=opt.is_correct)
                        db.session.add(cloned_opt)
                db.session.commit()
        
        questions_data = {}
        import re
        for key in request.form.keys():
            match = re.search(r'questions\[(\d+)\]', key)
            if match:
                q_id = int(match.group(1))
                if q_id not in questions_data:
                    q_type = request.form.get(f'questions[{q_id}][type]', 'single')
                    corrects = request.form.getlist(f'questions[{q_id}][correct][]') if q_type == 'multiple' else [request.form.get(f'questions[{q_id}][correct]')]
                    
                    questions_data[q_id] = {
                        'text': request.form.get(f'questions[{q_id}][text]', ''),
                        'type': q_type,
                        'media_url': request.form.get(f'questions[{q_id}][media_url]', ''),
                        'options': request.form.getlist(f'questions[{q_id}][options][]'),
                        'options_media': request.form.getlist(f'questions[{q_id}][options_media][]'),
                        'matches': request.form.getlist(f'questions[{q_id}][matches][]') if q_type == 'matching' else [],
                        'correct': [int(c) for c in corrects if c and c.isdigit()]
                    }

        for q_id, q_data in questions_data.items():
            if q_data['text']:
                new_question = Question(
                    quiz_id=new_quiz.id, 
                    text=q_data['text'],
                    question_type=q_data['type'],
                    media_url=q_data['media_url']
                )
                db.session.add(new_question)
                db.session.flush()
                
                if q_data['type'] != 'text':
                    for i, opt_text in enumerate(q_data['options']):
                        is_correct = False
                        final_text = opt_text
                        
                        if q_data['type'] == 'matching':
                            # Append the matching pair with a delimiter
                            match_text = q_data['matches'][i] if i < len(q_data['matches']) else ""
                            final_text = f"{opt_text}::|::{match_text}"
                            is_correct = True # Matching items are inherently their own correct pairs
                        elif q_data['type'] == 'ordering':
                            is_correct = True # Ordering items are correct based on their position
                        else:
                            is_correct = (i in q_data['correct'])
                            
                        opt_media_url = q_data.get('options_media', [])[i] if i < len(q_data.get('options_media', [])) else None
                        new_option = Option(question_id=new_question.id, text=final_text, is_correct=is_correct, media_url=opt_media_url)
                        db.session.add(new_option)
        
        db.session.commit()
        if user_id:
            return redirect(url_for('teacher.user_quizzes', user_id=target_id))
        return redirect(url_for('teacher.dashboard'))

    categories = Category.query.filter_by(teacher_id=target_id).all()
    tags = Tag.query.filter_by(teacher_id=target_id).all()
    return render_template('add_quiz.html', target_id=target_id, categories=categories, tags=tags)

@bp.route('/quiz/delete/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    if current_user.role == 'secretary':
        abort(403)
        
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.teacher_id != current_user.id and current_user.role != 'admin':
        abort(403)
        
    teacher_id = quiz.teacher_id
    db.session.delete(quiz)
    db.session.commit()
    
    if current_user.role == 'admin':
        return redirect(url_for('teacher.user_quizzes', user_id=teacher_id))
    return redirect(url_for('teacher.dashboard'))

@bp.route('/quiz/edit/<int:quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    if current_user.role == 'secretary':
        abort(403)
        
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.teacher_id != current_user.id and current_user.role != 'admin':
        abort(403)
        
    if request.method == 'POST':
        quiz.title = request.form.get('title')
        quiz.description = request.form.get('description')
        
        duration_str = request.form.get('duration')
        time_per_q_str = request.form.get('time_per_question')
        
        quiz.duration_minutes = int(duration_str) if duration_str and duration_str.isdigit() else 10
        quiz.time_per_question = int(time_per_q_str) if time_per_q_str and time_per_q_str.isdigit() else 30
        
        from datetime import datetime
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        quiz.start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M') if start_time_str else None
        quiz.end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M') if end_time_str else None
        
        quiz.randomize_questions = request.form.get('randomize_questions') == 'true'
        quiz.show_results = request.form.get('show_results') == 'true'
        quiz.show_leaderboard = request.form.get('show_leaderboard') == 'true'
        quiz.recurrence_pattern = request.form.get('recurrence_pattern', 'none')
        
        for question in quiz.questions:
            db.session.delete(question)
        
        questions_data = {}
        import re
        for key in request.form.keys():
            match = re.search(r'questions\[(\d+)\]', key)
            if match:
                q_id = int(match.group(1))
                if q_id not in questions_data:
                    q_type = request.form.get(f'questions[{q_id}][type]', 'single')
                    corrects = request.form.getlist(f'questions[{q_id}][correct][]') if q_type == 'multiple' else [request.form.get(f'questions[{q_id}][correct]')]
                    
                    questions_data[q_id] = {
                        'text': request.form.get(f'questions[{q_id}][text]', ''),
                        'type': q_type,
                        'media_url': request.form.get(f'questions[{q_id}][media_url]', ''),
                        'options': request.form.getlist(f'questions[{q_id}][options][]'),
                        'options_media': request.form.getlist(f'questions[{q_id}][options_media][]'),
                        'matches': request.form.getlist(f'questions[{q_id}][matches][]') if q_type == 'matching' else [],
                        'correct': [int(c) for c in corrects if c and c.isdigit()]
                    }

        for q_id, q_data in questions_data.items():
            if q_data['text']:
                new_question = Question(
                    quiz_id=quiz.id, 
                    text=q_data['text'],
                    question_type=q_data['type'],
                    media_url=q_data['media_url']
                )
                db.session.add(new_question)
                db.session.flush()
                
                if q_data['type'] != 'text':
                    for i, opt_text in enumerate(q_data['options']):
                        is_correct = False
                        final_text = opt_text
                        
                        if q_data['type'] == 'matching':
                            match_text = q_data['matches'][i] if i < len(q_data['matches']) else ""
                            final_text = f"{opt_text}::|::{match_text}"
                            is_correct = True
                        elif q_data['type'] == 'ordering':
                            is_correct = True
                        else:
                            is_correct = (i in q_data['correct'])
                            
                        opt_media_url = q_data.get('options_media', [])[i] if i < len(q_data.get('options_media', [])) else None
                        new_option = Option(question_id=new_question.id, text=final_text, is_correct=is_correct, media_url=opt_media_url)
                        db.session.add(new_option)

        db.session.commit()
        if current_user.role == 'admin':
            return redirect(url_for('teacher.user_quizzes', user_id=quiz.teacher_id))
        return redirect(url_for('teacher.dashboard'))

    return render_template('edit_quiz.html', quiz=quiz)

@bp.route('/quiz/<int:quiz_id>/results')
def view_results(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.teacher_id != current_user.id and current_user.role not in ['admin', 'secretary']:
        abort(403)
    submissions = Submission.query.filter_by(quiz_id=quiz_id).order_by(Submission.submitted_at.desc()).all()
    return render_template('view_results.html', quiz=quiz, submissions=submissions)

@bp.route('/quiz/<int:quiz_id>/export_results')
def export_results(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.teacher_id != current_user.id and current_user.role not in ['admin', 'secretary']:
        abort(403)
        
    import io
    import csv
    from flask import make_response
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Student Name', 'Score', 'Max Score', 'Status', 'Tab Switches', 'Submission Date'])
    
    submissions = Submission.query.filter_by(quiz_id=quiz_id).order_by(Submission.submitted_at.desc()).all()
    for sub in submissions:
        status = 'Passed' if (sub.max_score > 0 and sub.score / sub.max_score >= 0.5) else 'Failed'
        cw.writerow([
            sub.student_name, 
            sub.score, 
            sub.max_score, 
            status,
            sub.tab_switches,
            sub.submitted_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=quiz_{quiz.id}_results.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@bp.route('/import_quiz', methods=['POST'])
@bp.route('/user/<int:user_id>/import_quiz', methods=['POST'])
def import_csv(user_id=None):
    if current_user.role == 'secretary':
        abort(403)
        
    if user_id:
        if current_user.role != 'admin':
            abort(403)
        target_id = user_id
    else:
        target_id = current_user.id
        
    if 'csv_file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('teacher.dashboard'))
        
    file = request.files['csv_file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('teacher.dashboard'))
        
    if file and file.filename.endswith('.csv'):
        import csv
        import io
        import string, random
        
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        
        try:
            headers = next(csv_input, None)
            if not headers:
                raise ValueError("Empty CSV file")
                
            title = headers[0] if len(headers) > 0 else "Imported Quiz"
            description = headers[1] if len(headers) > 1 else ""
            duration = int(headers[2]) if len(headers) > 2 and headers[2].isdigit() else 10
            time_per_q = int(headers[3]) if len(headers) > 3 and headers[3].isdigit() else 30
            
            access_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            
            new_quiz = Quiz(
                title=title, 
                description=description, 
                duration_minutes=duration,
                time_per_question=time_per_q,
                teacher_id=target_id,
                access_code=access_code
            )
            db.session.add(new_quiz)
            db.session.flush()
            
            for row in csv_input:
                if len(row) < 4:
                    continue 
                    
                q_text = row[0]
                q_type = row[1] if row[1] in ['single', 'multiple', 'true_false', 'text'] else 'single'
                q_media = row[2]
                
                new_question = Question(quiz_id=new_quiz.id, text=q_text, question_type=q_type, media_url=q_media)
                db.session.add(new_question)
                db.session.flush()
                
                if q_type != 'text':
                    options_len = len(row) - 4
                    correct_idx_str = row[-1]
                    correct_indices = [int(x) for x in correct_idx_str.split('|') if x.isdigit()] if q_type == 'multiple' else ([int(correct_idx_str)] if correct_idx_str.isdigit() else [0])
                    
                    for i in range(3, 3 + options_len):
                        opt_text = row[i]
                        if not opt_text.strip(): continue
                        is_correct = (i - 3) in correct_indices
                        new_option = Option(question_id=new_question.id, text=opt_text, is_correct=is_correct)
                        db.session.add(new_option)
                        
            db.session.commit()
            flash('Quiz imported successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing CSV: {str(e)}', 'error')
            
    else:
        flash('Invalid file format. Please upload a CSV.', 'error')
        
    if user_id:
        return redirect(url_for('teacher.user_quizzes', user_id=target_id))
    return redirect(url_for('teacher.dashboard'))

@bp.route('/question_bank', methods=['GET', 'POST'])
def question_bank():
    if current_user.role == 'secretary':
        abort(403)
        
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_category':
            name = request.form.get('name')
            if name:
                cat = Category(name=name, teacher_id=current_user.id)
                db.session.add(cat)
                db.session.commit()
                flash('Category added.', 'success')
                
        elif action == 'add_tag':
            name = request.form.get('name')
            if name:
                import random
                # Generate a random hex color, avoiding colors that are too light (to ensure readable white/light text)
                r = lambda: random.randint(0, 200)
                color = '#%02X%02X%02X' % (r(), r(), r())
                
                tag = Tag(name=name, color=color, teacher_id=current_user.id)
                db.session.add(tag)
                db.session.commit()
                flash('Tag added.', 'success')
                
        elif action == 'add_question':
            text = request.form.get('text')
            q_type = request.form.get('question_type', 'single')
            category_id = request.form.get('category_id')
            media_url = request.form.get('media_url')
            tag_ids = request.form.getlist('tags')
            
            if text:
                new_q = Question(
                    text=text,
                    question_type=q_type,
                    is_bank=True,
                    teacher_id=current_user.id,
                    category_id=int(category_id) if category_id else None,
                    media_url=media_url
                )
                db.session.add(new_q)
                db.session.flush()
                
                for tag_id in tag_ids:
                    tag = Tag.query.get(int(tag_id))
                    if tag:
                        new_q.tags.append(tag)
                        
                if q_type != 'text':
                    options = request.form.getlist('options[]')
                    options_media = request.form.getlist('options_media[]')
                    matches_list = request.form.getlist('matches[]')
                    
                    corrects = request.form.getlist('correct[]') if q_type == 'multiple' else [request.form.get('correct')]
                    
                    for i, opt_text in enumerate(options):
                        has_match = q_type == 'matching' and i < len(matches_list) and matches_list[i].strip()
                        if opt_text.strip() or has_match:
                            final_text = opt_text
                            if q_type == 'matching' and i < len(matches_list):
                                final_text = f"{opt_text}::|::{matches_list[i]}"
                                
                            is_correct = str(i) in corrects if q_type not in ['matching', 'ordering'] else True
                            opt_media_url = options_media[i] if i < len(options_media) else None
                            
                            new_opt = Option(question_id=new_q.id, text=final_text, is_correct=is_correct, media_url=opt_media_url)
                            db.session.add(new_opt)
                            
                db.session.commit()
                flash('Bank question added.', 'success')
                
        elif action == 'delete_question':
            q_id = request.form.get('question_id')
            q = Question.query.get(q_id)
            if q and q.teacher_id == current_user.id:
                db.session.delete(q)
                db.session.commit()
                flash('Question deleted.', 'success')
                
        elif action == 'delete_category':
            c_id = request.form.get('category_id')
            c = Category.query.get(c_id)
            if c and c.teacher_id == current_user.id:
                db.session.delete(c)
                db.session.commit()
                flash('Category deleted.', 'success')
                
        elif action == 'delete_tag':
            t_id = request.form.get('tag_id')
            t = Tag.query.get(t_id)
            if t and t.teacher_id == current_user.id:
                db.session.delete(t)
                db.session.commit()
                flash('Tag deleted.', 'success')
                
        return redirect(url_for('teacher.question_bank'))
        
    categories = Category.query.filter_by(teacher_id=current_user.id).all()
    tags = Tag.query.filter_by(teacher_id=current_user.id).all()
    
    # Filtering
    cat_filter = request.args.get('category_id', type=int)
    tag_filter = request.args.get('tag_id', type=int)
    page = request.args.get('page', 1, type=int)
    
    query = Question.query.filter_by(is_bank=True, teacher_id=current_user.id)
    if cat_filter:
        query = query.filter_by(category_id=cat_filter)
    if tag_filter:
        query = query.filter(Question.tags.any(id=tag_filter))
        
    pagination = query.order_by(Question.id.desc()).paginate(page=page, per_page=10, error_out=False)
    questions = pagination.items
    
    return render_template('question_bank.html', categories=categories, tags=tags, questions=questions, pagination=pagination, current_cat=cat_filter, current_tag=tag_filter)


@bp.route('/classrooms', methods=['GET', 'POST'])
def classrooms():
    if current_user.role == 'secretary':
        abort(403)
        
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            import string, random
            class_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            new_class = Classroom(name=name, teacher_id=current_user.id, class_code=class_code)
            db.session.add(new_class)
            db.session.commit()
            flash(f'Classroom "{name}" created with code {class_code}', 'success')
        return redirect(url_for('teacher.classrooms'))
        
    classes = Classroom.query.filter_by(teacher_id=current_user.id).order_by(Classroom.created_at.desc()).all()
    return render_template('classrooms.html', classrooms=classes)

@bp.route('/classrooms/delete/<int:classroom_id>', methods=['POST'])
def delete_classroom(classroom_id):
    if current_user.role == 'secretary':
        abort(403)
        
    classroom = Classroom.query.get_or_404(classroom_id)
    if classroom.teacher_id != current_user.id and current_user.role != 'admin':
        abort(403)
        
    db.session.delete(classroom)
    db.session.commit()
    flash('Classroom deleted.', 'success')
    return redirect(url_for('teacher.classrooms'))

@bp.route('/classrooms/<int:classroom_id>')
def view_classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    if classroom.teacher_id != current_user.id and current_user.role not in ['admin', 'secretary']:
        abort(403)
        
    teacher_quizzes = Quiz.query.filter_by(teacher_id=current_user.id).all()
    return render_template('view_classroom.html', classroom=classroom, teacher_quizzes=teacher_quizzes)

@bp.route('/classrooms/<int:classroom_id>/assign_quiz', methods=['POST'])
def assign_quiz_to_class(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    if classroom.teacher_id != current_user.id and current_user.role != 'admin':
        abort(403)
        
    quiz_id = request.form.get('quiz_id')
    if quiz_id:
        quiz = Quiz.query.get_or_404(quiz_id)
        if quiz not in classroom.quizzes:
            classroom.quizzes.append(quiz)
            db.session.commit()
            flash(f'Quiz "{quiz.title}" assigned to classroom.', 'success')
            
    return redirect(url_for('teacher.view_classroom', classroom_id=classroom_id))

@bp.route('/classrooms/<int:classroom_id>/unassign_quiz/<int:quiz_id>', methods=['POST'])
def unassign_quiz_from_class(classroom_id, quiz_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    if classroom.teacher_id != current_user.id and current_user.role != 'admin':
        abort(403)
        
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz in classroom.quizzes:
        classroom.quizzes.remove(quiz)
        db.session.commit()
        flash(f'Quiz unassigned from classroom.', 'success')
            
    return redirect(url_for('teacher.view_classroom', classroom_id=classroom_id))

@bp.route('/classrooms/<int:classroom_id>/remove_student/<int:user_id>', methods=['POST'])
def remove_student_from_class(classroom_id, user_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    if classroom.teacher_id != current_user.id and current_user.role != 'admin':
        abort(403)
        
    student = User.query.get_or_404(user_id)
    if student in classroom.students:
        classroom.students.remove(student)
        db.session.commit()
        flash(f'Student {student.username} removed from classroom.', 'success')
            
    return redirect(url_for('teacher.view_classroom', classroom_id=classroom_id))

@bp.route('/analytics/item_analysis/<int:quiz_id>')
def item_analysis(quiz_id):
    if current_user.role == 'secretary':
        abort(403)
        
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.teacher_id != current_user.id and current_user.role != 'admin':
        abort(403)
        
    submissions = Submission.query.filter_by(quiz_id=quiz.id).all()
    if not submissions:
        flash('No submissions yet to analyze.', 'info')
        return redirect(url_for('teacher.dashboard'))
        
    # Sort submissions by score to find top and bottom groups
    submissions_sorted = sorted(submissions, key=lambda s: s.score, reverse=True)
    n = len(submissions_sorted)
    
    # Use top 27% and bottom 27% (or min 1 if n is small)
    group_size = max(1, int(n * 0.27)) if n >= 4 else (n // 2 if n >= 2 else 1)
    
    top_group_ids = [s.id for s in submissions_sorted[:group_size]]
    bottom_group_ids = [s.id for s in submissions_sorted[-group_size:]] if n > 1 else top_group_ids
    
    analysis_data = [] # List of dicts per question
    
    for question in quiz.questions:
        if question.question_type == 'text':
            continue # Text questions generally don't have binary clear-cut metrics automatically
            
        answers = StudentAnswer.query.filter_by(question_id=question.id).all()
        
        # Difficulty Index
        correct_count = sum(1 for a in answers if a.is_correct)
        total_attempts = len(answers)
        difficulty_index = (correct_count / total_attempts) if total_attempts > 0 else 0
        
        # Discrimination Index
        top_correct = sum(1 for a in answers if a.submission_id in top_group_ids and a.is_correct)
        bottom_correct = sum(1 for a in answers if a.submission_id in bottom_group_ids and a.is_correct)
        
        if n > 1:
            discrimination_index = (top_correct - bottom_correct) / group_size
        else:
            discrimination_index = 0
            
        analysis_data.append({
            'question': question.text,
            'difficulty_index': round(difficulty_index, 2),
            'difficulty_pct': int(difficulty_index * 100),
            'discrimination_index': round(discrimination_index, 2),
            'total_attempts': total_attempts
        })
        
    return render_template('item_analysis.html', quiz=quiz, analysis_data=analysis_data)

@bp.route('/live/host/<int:quiz_id>')
@login_required
def host_live(quiz_id):
    if current_user.role not in ['admin', 'teacher']:
        abort(403)
        
    from app.models import LiveSession
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.teacher_id != current_user.id and current_user.role != 'admin':
        abort(403)
        
    import random
    import string
    # Generate 4-digit PIN
    pin = ''.join(random.choices(string.digits, k=4))
    while LiveSession.query.filter_by(pin=pin, is_active=True).first():
        pin = ''.join(random.choices(string.digits, k=4))
        
    # Create new live session
    session = LiveSession(
        quiz_id=quiz.id,
        teacher_id=current_user.id,
        pin=pin,
        is_active=True,
        current_question_index=0
    )
    db.session.add(session)
    db.session.commit()
    
    return render_template('teacher_live_host.html', live_session=session, quiz=quiz)
