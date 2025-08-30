#!/usr/bin/env python3
"""
Simple HTTP server for the NMB Game frontend.
Serves the client files on http://localhost:8000
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

# Set the port for the frontend server
PORT = 8000

# Change to the client directory
client_dir = Path(__file__).parent
os.chdir(client_dir)

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"[WEB] Frontend server running on http://localhost:{PORT}")
        print(f"[DIR] Serving files from: {client_dir}")
        print(f"[GAME] Game available at http://localhost:{PORT}/game.html")
        print("[INFO] Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[STOP] Frontend server stopped")