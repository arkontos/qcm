from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_babel import Babel
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from config import Config
from flask_mail import Mail

from sqlalchemy import MetaData

naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

load_dotenv()

db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'error'

def get_locale():
    # If a user is logged in and has a language preference (to be added)
    # if current_user.is_authenticated and current_user.lang:
    #     return current_user.lang
    # Check if a specific language is active in session
    if 'lang' in session:
        return session['lang']
    from flask import current_app
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])

babel = Babel()
socketio = SocketIO()
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    socketio.init_app(app, cors_allowed_origins="*")
    mail.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Register Blueprints
    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.routes.teacher import bp as teacher_bp
    app.register_blueprint(teacher_bp, url_prefix='/teacher')

    from app.routes.student import bp as student_bp
    app.register_blueprint(student_bp, url_prefix='/student')

    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.routes.messages import bp as messages_bp
    app.register_blueprint(messages_bp, url_prefix='/messages')

    # Register error handlers
    from flask import render_template
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    # Create tables if not exist (useful for dev)
    with app.app_context():
        import os
        if not os.path.exists(app.instance_path):
            os.makedirs(app.instance_path, exist_ok=True)
            
        # Import models so SQLAlchemy knows about them
        from app import models

        # Create default admin user if none exists
        try:
            if not models.User.query.filter_by(email='admin@qcm.com').first():
                admin_user = models.User(
                    email='admin@qcm.com',
                    role='admin',
                    email_confirmed=True
                )
                admin_user.set_password('password')
                db.session.add(admin_user)
                db.session.commit()
                print("Default admin user created: admin@qcm.com / password")
        except Exception:
            db.session.rollback()

        # Seed initial achievements if none exist
        try:
            if models.Achievement.query.count() == 0:
                achievements = [
                    models.Achievement(name='First Steps', description='Completed your first quiz.', icon_url='🏅', condition_type='first_quiz'),
                    models.Achievement(name='Perfectionist', description='Achieved a score of 100% on a quiz.', icon_url='⭐', condition_type='perfect_score'),
                    models.Achievement(name='Speed Demon', description='Completed a quiz quickly.', icon_url='⚡', condition_type='quick_finisher'),
                    models.Achievement(name='Consistent Learner', description='Completed 5 quizzes.', icon_url='📚', condition_type='five_quizzes'),
                ]
                db.session.bulk_save_objects(achievements)
                db.session.commit()
                print("Seeded initial achievements.")
        except Exception:
            db.session.rollback()
            
    # Register SocketIO events
    from app import events

    return app
