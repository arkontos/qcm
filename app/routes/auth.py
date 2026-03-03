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
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been disabled. Contact an administrator.', 'error')
                return redirect(url_for('auth.login'))
                
            if not user.email_confirmed:
                flash('Please confirm your email address before logging in.', 'error')
                # redirect to confirm_email page with email pre-filled if we had it, but simple redirect works too
                return redirect(url_for('auth.confirm_email', email=user.email))
                
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
            flash('Invalid email or password', 'error')

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
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Please choose a different one or log in.', 'error')
            return redirect(url_for('auth.register'))

        import random, string
        confirmation_code = ''.join(random.choices(string.digits, k=6))

        new_user = User(
            email=email, 
            role='student', 
            is_active=True, 
            email_confirmed=False, 
            confirmation_code=confirmation_code
        )
        new_user.set_password(password)
        
        from app import db, mail
        from flask_mail import Message
        db.session.add(new_user)
        db.session.commit()
        
        # Send Confirmation Email 
        try:
            msg = Message("Confirm your QCM Platform Account", recipients=[email])
            msg.body = f"Welcome to QCM Platform!\n\nYour confirmation code is: {confirmation_code}\n\nPlease enter this code to activate your account."
            mail.send(msg)
            flash('Registration successful! Please check your email for the confirmation code.', 'success')
        except Exception as e:
            # If mail fails (especially in development without real SMTP), print it but still allow the flow.
            print(f"Failed to send email to {email}: {str(e)}")
            print(f"CONFIRMATION CODE FOR {email}: {confirmation_code}")
            flash('Registration successful! (Note: Email sending failed. Check server console for confirmation code).', 'warning')
            
        return redirect(url_for('auth.confirm_email', email=email))

    return render_template('register.html')
    
@bp.route('/confirm_email', methods=['GET', 'POST'])
def confirm_email():
    email = request.args.get('email', '')
    
    if request.method == 'POST':
        submitted_email = request.form.get('email')
        code = request.form.get('code')
        
        user = User.query.filter_by(email=submitted_email).first()
        if not user:
            flash('Invalid email address.', 'error')
            return redirect(url_for('auth.confirm_email', email=submitted_email))
            
        if user.email_confirmed:
            flash('Email is already confirmed. Please log in.', 'info')
            return redirect(url_for('auth.login'))
            
        if user.confirmation_code == code:
            user.email_confirmed = True
            user.confirmation_code = None
            from app import db
            db.session.commit()
            flash('Email confirmed successfully! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid confirmation code. Please try again.', 'error')
            return redirect(url_for('auth.confirm_email', email=submitted_email))
            
    return render_template('confirm_email.html', email=email)

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
