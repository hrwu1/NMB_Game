#!/usr/bin/env python3
"""
Main entry point for the NMB Game Flask server with SocketIO support.
"""

from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
import os

# Import our modules
from api.routes import register_socket_handlers
from config import Config

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for cross-origin requests from frontend
    CORS(app, cors_allowed_origins="*")
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
    
    # Register socket event handlers
    register_socket_handlers(socketio)
    
    @app.route('/')
    def index():
        """Root endpoint with server info"""
        return {
            'status': 'ok',
            'message': 'NMB Game WebSocket server is running',
            'endpoints': {
                'health': '/health',
                'websocket': 'Connect using Socket.IO client'
            },
            'test_client': 'Open client/test.html in your browser to test the connection'
        }
    
    @app.route('/health')
    def health_check():
        """Simple health check endpoint"""
        return {'status': 'ok', 'message': 'NMB Game server is running'}
    
    return app, socketio

if __name__ == '__main__':
    app, socketio = create_app()
    
    # Get configuration
    config = app.config
    port = config.get('PORT', 5000)
    host = config.get('HOST', '0.0.0.0')
    debug = config.get('DEBUG', True)
    
    print(f"🎮 Starting NMB Game server on {host}:{port}...")
    print(f"🌐 Server will be accessible at http://localhost:{port}")
    print(f"🔧 Debug mode: {debug}")
    
    socketio.run(app, host=host, port=port, debug=debug)