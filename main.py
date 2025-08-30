#!/usr/bin/env python3
"""
Main launcher for NMB Game development environment.
Automatically starts both backend and frontend servers.
"""

import subprocess
import threading
import time
import webbrowser
import signal
import sys
import os
from pathlib import Path

# Configuration
BACKEND_PORT = 5000
FRONTEND_PORT = 8000
GAME_URL = f"http://localhost:{FRONTEND_PORT}/game.html"

class GameServerLauncher:
    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.running = False
        
    def start_backend(self):
        """Start the Flask/SocketIO backend server"""
        print(f"[BACKEND] Starting backend server on port {BACKEND_PORT}...")
        
        # Change to server directory and start
        backend_dir = Path(__file__).parent / "server"
        self.backend_process = subprocess.Popen(
            [sys.executable, "run.py"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor backend output in a separate thread
        def monitor_backend():
            for line in iter(self.backend_process.stdout.readline, ''):
                if line.strip():
                    print(f"[BACKEND] {line.strip()}")
        
        threading.Thread(target=monitor_backend, daemon=True).start()
        
    def start_frontend(self):
        """Start the frontend HTTP server"""
        print(f"[FRONTEND] Starting frontend server on port {FRONTEND_PORT}...")
        
        # Change to client directory and start
        client_dir = Path(__file__).parent / "client"
        self.frontend_process = subprocess.Popen(
            [sys.executable, "serve.py"],
            cwd=client_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor frontend output in a separate thread
        def monitor_frontend():
            for line in iter(self.frontend_process.stdout.readline, ''):
                if line.strip():
                    print(f"[FRONTEND] {line.strip()}")
        
        threading.Thread(target=monitor_frontend, daemon=True).start()
        
    def wait_for_servers(self):
        """Wait for both servers to be ready"""
        print("[WAIT] Waiting for servers to start...")
        
        # Wait for backend
        backend_ready = False
        frontend_ready = False
        
        for attempt in range(30):  # 30 seconds timeout
            time.sleep(1)
            
            # Check backend
            if not backend_ready:
                try:
                    import urllib.request
                    urllib.request.urlopen(f"http://localhost:{BACKEND_PORT}/health", timeout=1)
                    backend_ready = True
                    print("[OK] Backend server is ready!")
                except:
                    pass
            
            # Check frontend  
            if not frontend_ready:
                try:
                    urllib.request.urlopen(f"http://localhost:{FRONTEND_PORT}", timeout=1)
                    frontend_ready = True
                    print("[OK] Frontend server is ready!")
                except:
                    pass
            
            if backend_ready and frontend_ready:
                break
                
        return backend_ready and frontend_ready
        
    def open_game(self):
        """Open the game in the default browser"""
        print(f"[GAME] Opening game at {GAME_URL}")
        webbrowser.open(GAME_URL)
        
    def cleanup(self):
        """Clean up processes on exit"""
        print("\n[STOP] Shutting down servers...")
        
        if self.backend_process:
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
            print("[STOP] Backend server stopped")
            
        if self.frontend_process:
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
            print("[STOP] Frontend server stopped")
            
        self.running = False
        
    def run(self):
        """Main run method"""
        try:
            self.running = True
            
            # Setup signal handler for clean shutdown
            def signal_handler(signum, frame):
                self.cleanup()
                sys.exit(0)
                
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            print("NMB Game Development Server")
            print("=" * 50)
            
            # Start both servers
            self.start_backend()
            time.sleep(2)  # Give backend a head start
            self.start_frontend()
            
            # Wait for servers to be ready
            if self.wait_for_servers():
                print("\n[SUCCESS] All servers ready!")
                print(f"[GAME] Game URL: {GAME_URL}")
                print(f"[API] Backend API: http://localhost:{BACKEND_PORT}")
                print(f"[WEB] Frontend: http://localhost:{FRONTEND_PORT}")
                print("\n[INFO] Instructions:")
                print("   1. The game will open automatically in your browser")
                print("   2. Create or join a game to start playing")
                print("   3. Press Ctrl+C to stop all servers")
                print("\n" + "=" * 50)
                
                # Auto-open browser after a short delay
                threading.Timer(3.0, self.open_game).start()
                
                # Keep main thread alive
                while self.running:
                    time.sleep(1)
                    
                    # Check if processes are still alive
                    if self.backend_process and self.backend_process.poll() is not None:
                        print("[ERROR] Backend server crashed!")
                        break
                    if self.frontend_process and self.frontend_process.poll() is not None:
                        print("[ERROR] Frontend server crashed!")
                        break
                        
            else:
                print("[ERROR] Failed to start servers within timeout")
                self.cleanup()
                return False
                
        except KeyboardInterrupt:
            print("\n[STOP] Received shutdown signal")
        except Exception as e:
            print(f"[ERROR] Error: {e}")
        finally:
            self.cleanup()
            
        return True

def main():
    """Entry point"""
    # Check if we're in the right directory
    if not (Path("server").exists() and Path("client").exists()):
        print("[ERROR] Please run this script from the NMB_Game root directory")
        print("   Expected directory structure:")
        print("   NMB_Game/")
        print("   ├── main.py (this file)")
        print("   ├── server/")
        print("   └── client/")
        return False
        
    # Check dependencies
    try:
        import flask
        import flask_socketio
        print("[OK] Dependencies available")
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("[INFO] Install dependencies with: pip install -r server/requirements.txt")
        return False
    
    # Start the game servers
    launcher = GameServerLauncher()
    return launcher.run()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)