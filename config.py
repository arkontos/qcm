import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this-in-prod'
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Instance folder will be at the root, so one level up from app package? 
    # No, basedir here is root. Instance is at root/instance.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'qcm.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LANGUAGES = ['en', 'fr']
