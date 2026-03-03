from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import func
from app.models import User, Quiz, Submission
from app import db

bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You do not have permission to access that page.', 'error')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
def dashboard():
    if current_user.role not in ['admin', 'secretary']:
        flash('You do not have permission to access that page.', 'error')
        return redirect(url_for('main.home'))

    search = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)

    query = User.query.filter(User.id != current_user.id)
    if search:
        query = query.filter(User.email.ilike(f'%{search}%') | User.role.ilike(f'%{search}%'))
        
    pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=12, error_out=False)
    users = pagination.items
    
    # Global Stats
    total_users = User.query.count()
    total_teachers = User.query.filter_by(role='teacher').count()
    total_quizzes = Quiz.query.count()
    total_submissions = Submission.query.count()
    
    global_stats = {
        'total_users': total_users,
        'total_teachers': total_teachers,
        'total_quizzes': total_quizzes,
        'total_submissions': total_submissions
    }
    
    # Teacher Stats
    teachers = User.query.filter_by(role='teacher').all()
    teacher_stats = []
    for teacher in teachers:
        quiz_count = Quiz.query.filter_by(teacher_id=teacher.id).count()
        
        # Using a join or subquery is more efficient, but since we have the models:
        submission_count = db.session.query(func.count(Submission.id))\
            .join(Quiz)\
            .filter(Quiz.teacher_id == teacher.id).scalar() or 0
            
        teacher_stats.append({
            'id': teacher.id,
            'email': teacher.email,
            'is_active': teacher.is_active,
            'quiz_count': quiz_count,
            'submission_count': submission_count
        })

    return render_template('admin_dashboard.html', 
                         users=users, 
                         pagination=pagination,
                         search=search,
                         global_stats=global_stats, 
                         teacher_stats=teacher_stats)

@bp.route('/user/new', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        is_active = request.form.get('is_active') == 'true'
        role = request.form.get('role', 'teacher')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return redirect(url_for('admin.add_user'))
            
        new_user = User(email=email, role=role, is_active=is_active, email_confirmed=True)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('admin.dashboard'))
        
    return render_template('admin_teacher_form.html', action="Add", user=None)

@bp.route('/user/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    if user.role != 'teacher' and user.role != 'secretary' and user.role != 'admin':
        flash('Invalid user.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        is_active = request.form.get('is_active') == 'true'
        role = request.form.get('role', user.role)
        
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != user.id:
            flash('Email already taken.', 'error')
            return redirect(url_for('admin.edit_user', id=id))
            
        user.email = email
        user.is_active = is_active
        user.role = role
        if password: # only update if provided
            user.set_password(password)
            
        db.session.commit()
        return redirect(url_for('admin.dashboard'))
        
    return render_template('admin_teacher_form.html', action="Edit", user=user)

@bp.route('/user/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin.dashboard'))
