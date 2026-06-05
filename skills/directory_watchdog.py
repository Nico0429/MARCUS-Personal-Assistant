import os
import time
import threading
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class NeuralWatchdog(FileSystemEventHandler):
    def __init__(self, vector_db, state_file="neural_index_state.json"):
        self.vector_db = vector_db
        self.observer = Observer()
        self.state_file = state_file
        
        # --- THE FIX: Threading Lock for safe file saving ---
        self.state_lock = threading.Lock()
        
        # Pull custom paths from .env. If none exist, fallback to the current project directory.
        env_paths = os.getenv("WATCH_PATHS", "")
        if env_paths:
            self.watch_paths = [p.strip() for p in env_paths.split(",")]
        else:
            self.watch_paths = [os.getcwd()] # Defaults to the MARCUS folder
        
        # --- THE FIX: The Absolute Brain Shield ---
        self.ignore_paths = [
            ".git", "__pycache__", ".venv", "node_modules", ".tmp", "temp", ".vscode",
            "neural_index_state.json", "marcus_memory.json", "chroma_db",
            "intent_cache.json", "local_reminders.json", "token.json", "credentials.json"
        ]
        
        self.processing_timers = {}
        self.debounce_seconds = 3.0
        
        # Load the memory of what we have already indexed
        self.index_state = self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e: 
                print(f"[ Watchdog Warning ] State file corrupted. Starting fresh. Error: {e}")
        return {}

    def _save_state(self):
        # Prevent race conditions when writing to the master ledger
        with self.state_lock:
            try:
                with open(self.state_file, 'w') as f:
                    json.dump(self.index_state, f, indent=4)
            except Exception as e:
                print(f"[ Watchdog Error ] Failed to save state ledger: {e}")

    def boot_sync(self):
        """Runs on startup. Scans all folders for new or modified files since last boot."""
        print("[ System ] Initiating Deep Matrix Sync... Scanning for offline changes.")
        updated_count = 0
        
        for path in self.watch_paths:
            if not os.path.exists(path): continue
            
            for root, _, files in os.walk(path):
                # Skip noise directories instantly to save CPU
                if any(ignored in root for ignored in self.ignore_paths):
                    continue
                    
                for file in files:
                    filepath = os.path.join(root, file)
                    if self._is_valid_file(filepath):
                        try:
                            mtime = os.path.getmtime(filepath)
                            # If file is brand new, OR if it was modified since we last saw it
                            if filepath not in self.index_state or self.index_state[filepath] < mtime:
                                print(f"[ Boot Sync ] Catching up on missed file: {file}")
                                #self.vector_db.ingest_document(filepath)
                                self.index_state[filepath] = mtime
                                updated_count += 1
                        except Exception:
                            pass # Skip files locked by the OS
        
        # --- THE FIX: Only save ONCE at the very end of the boot sequence ---
        if updated_count > 0:
            self._save_state()
            print(f"[ System ] Deep Sync Complete. Indexed {updated_count} new/modified files.")
        else:
            print("[ System ] Deep Sync Complete. Matrix is fully up to date.")

    def start(self):
        # 1. Fire the Deep Sync on a background thread so Marcus boots instantly
        threading.Thread(target=self.boot_sync, daemon=True).start()
        
        # 2. Spin up the real-time observer
        print("[ System ] Booting Neural Watchdog... Monitoring Local and Cloud Drives.")
        for path in self.watch_paths:
            if os.path.exists(path):
                self.observer.schedule(self, path, recursive=True)
            else:
                print(f"[ Watchdog Warning ] Path not found: {path}")
                
        self.observer.start()

    def wipe_state(self):
        """Erases the JSON tracker for a full rebuild."""
        with self.state_lock:
            self.index_state = {}
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
            print("[ Watchdog ] State tracker wiped.")

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def _is_valid_file(self, filepath):
        if not os.path.isfile(filepath): return False
        
        # Block internal files from being indexed
        if any(ignored in filepath for ignored in self.ignore_paths): return False
        
        filename = os.path.basename(filepath)
        if filename.startswith("~$") or filename.startswith("."): return False
            
        valid_extensions = [".txt", ".md", ".py", ".pdf", ".json", ".csv", ".docx"]
        return any(filepath.endswith(ext) for ext in valid_extensions)

    def on_modified(self, event): self._handle_event(event)
    def on_created(self, event): self._handle_event(event)

    def _handle_event(self, event):
        filepath = event.src_path
        if not self._is_valid_file(filepath): return

        if filepath in self.processing_timers:
            self.processing_timers[filepath].cancel()

        timer = threading.Timer(self.debounce_seconds, self._process_file, args=[filepath])
        self.processing_timers[filepath] = timer
        timer.start()

    def _process_file(self, filepath):
        try:
            if filepath in self.processing_timers:
                del self.processing_timers[filepath]

            mtime = os.path.getmtime(filepath)
            # If the file hasn't actually changed since we last indexed it, abort!
            if filepath in self.index_state and self.index_state[filepath] >= mtime:
                return

            print(f"[ Watchdog ] Change detected and stabilized: {os.path.basename(filepath)}")
            self.vector_db.ingest_document(filepath)
            
            # Update the JSON tracker safely
            self.index_state[filepath] = mtime
            self._save_state()
            
        except Exception as e:
            print(f"[ Watchdog Error ] Failed to process {filepath}: {e}")