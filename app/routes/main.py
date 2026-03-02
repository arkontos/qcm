from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role in ['admin', 'secretary']:
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student.dashboard'))
        else:
            return redirect(url_for('teacher.dashboard'))
    return render_template('home.html')

from flask import request, session
@bp.route('/set_language', methods=['POST'])
def set_language():
    lang = request.form.get('language')
    if lang in ['en', 'fr']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('main.home'))

@bp.route('/live')
@bp.route('/student/live')
def live_redirect():
    return redirect(url_for('student.join_live'))

from app.models import Message

@bp.app_context_processor
def inject_unread_messages():
    count = 0
    if current_user.is_authenticated:
        count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    return dict(unread_messages_count=count)
