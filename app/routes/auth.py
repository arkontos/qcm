from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student.dashboard'))
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been disabled. Contact an administrator.', 'error')
                return redirect(url_for('auth.login'))
                
            from datetime import date, timedelta
            from app import db
            today = date.today()
            if user.last_login_date != today:
                if user.last_login_date == today - timedelta(days=1):
                    user.current_streak += 1
                else:
                    user.current_streak = 1
                user.last_login_date = today
                db.session.commit()
                
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student.dashboard'))
            # Let's redirect to the next if it exists, otherwise to teacher dashboard
            next_page = request.args.get('next')
            return redirect(next_page or url_for('teacher.dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student.dashboard'))
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.register'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('auth.register'))

        new_user = User(username=username, role='student', is_active=True)
        new_user.set_password(password)
        
        from app import db
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not current_user.check_password(current_password):
            flash('Incorrect current password.', 'error')
            return redirect(url_for('auth.change_password'))

        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('auth.change_password'))

        if len(new_password) < 6: # Optional simple validation
            flash('New password must be at least 6 characters long.', 'error')
            return redirect(url_for('auth.change_password'))

        current_user.set_password(new_password)
        from app import db
        db.session.commit()
        
        flash('Password updated successfully.', 'success')
        
        # Redirect to the appropriate dashboard
        if current_user.role == 'admin' or current_user.role == 'secretary':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student.dashboard'))
        return redirect(url_for('teacher.dashboard'))

    return render_template('change_password.html')
