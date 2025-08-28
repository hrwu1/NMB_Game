"""
Configuration settings for the NMB Game server.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'nmb-game-dev-secret-key-change-in-production'
    
    # SocketIO settings
    SOCKETIO_ASYNC_MODE = 'threading'
    
    # Game settings
    MAX_PLAYERS_PER_GAME = int(os.environ.get('MAX_PLAYERS_PER_GAME', 4))
    GAME_SESSION_TIMEOUT = timedelta(hours=2)
    
    # Server settings
    PORT = int(os.environ.get('PORT', 5000))
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    # CORS settings
    cors_origins_env = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173')
    CORS_ORIGINS = [origin.strip() for origin in cors_origins_env.split(',')]
    
    # Development settings
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set for production environment")

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}