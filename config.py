import os
from datetime import timedelta


class Config:
    
    SECRET_KEY = os.environ.get('SECRET_KEY', 'shinxity-dev-key-change-in-production')
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///shinxity.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=5)