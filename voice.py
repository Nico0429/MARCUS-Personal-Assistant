"""
================================================================================
FILE: voice.py
ROLE: The Edge TTS & Interruption Engine
================================================================================
The core audio playback and lip-sync manager. 

It accepts massive strings of text, chunks them intelligently, downloads the 
speech audio concurrently via Edge TTS, and maps root-mean-square (RMS) 
amplitudes to the UI for accurate hologram lip-syncing. It features a hard 
kill-switch that instantly trashes processing queues upon user interruption.
================================================================================
"""



import os
import sys

# --- FORCE SYSTEM PATHING FIRST ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

os.makedirs(TEMP_DIR, exist_ok=True)

# Inject the assets folder directly into the Windows Environment Path 
# so subprocesses like ffprobe can be globally discovered by Python!
os.environ["PATH"] = ASSETS_DIR + os.pathsep + os.environ.get("PATH", "")


import asyncio
import edge_tts
import pygame
import threading
import queue
import time
import re
from pydub import AudioSegment
from PySide6.QtWidgets import QApplication

# Explicitly link pydub (just to be safe)
AudioSegment.converter = os.path.join(ASSETS_DIR, "ffmpeg.exe")
AudioSegment.ffprobe = os.path.join(ASSETS_DIR, "ffprobe.exe")

class MarcusVoice:
    def __init__(self, face_handle):
        self.voice = "en-GB-RyanNeural"
        self.text_queue = queue.Queue()
        self.audio_ready_queue = queue.Queue()
        self.face = face_handle
        self._interrupt_flag = False
        
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        threading.Thread(target=self._run_download_loop, daemon=True).start()
        threading.Thread(target=self._playback_worker, daemon=True).start()

    def wait_until_done(self):
        """Actively monitors for a RIGHT-CLICK while safely waiting for queues to empty."""
        # Restored to music.get_busy() so it ignores background sound effects!
        while self.text_queue.unfinished_tasks > 0 or self.audio_ready_queue.unfinished_tasks > 0 or pygame.mixer.music.get_busy():
            if self.face.stop_toggle:
                self.stop()
            time.sleep(0.05)

    def stop(self):
        """Flags the workers to skip remaining tasks, stops audio, and TRASHES the queues."""
        self._interrupt_flag = True
        self.face.stop_toggle = False 
        
        # 1. Kill active audio
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

        # 2. Dump the Text Queue
        while not self.text_queue.empty():
            try:
                self.text_queue.get_nowait()
                self.text_queue.task_done()
            except queue.Empty:
                break
                
        # 3. Dump the Audio Queue and delete downloaded files
        while not self.audio_ready_queue.empty():
            try:
                filename = self.audio_ready_queue.get_nowait()
                if os.path.exists(filename):
                    try: os.remove(filename)
                    except: pass
                self.audio_ready_queue.task_done()
            except queue.Empty:
                break

    def _run_download_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try: 
            loop.run_until_complete(self._download_worker())
        except Exception as e:
            print(f"Download Loop Error: {e}")

    async def _download_worker(self):
        chunk_id = 0
        print("[ System ] Voice download worker is active.")
        while True:
            # Wait for text to arrive
            text = await asyncio.to_thread(self.text_queue.get)
            print(f"[ System ] TTS Engine received text: '{text[:40]}...'")
            
            file_name = f"temp_Marcus_{chunk_id}.mp3"
            temp_file = os.path.join(TEMP_DIR, file_name)
            
            await self._process_text(text, temp_file)
            
            chunk_id += 1
            self.text_queue.task_done() 

    async def _process_text(self, text, filename):
        try:
            if self._interrupt_flag: 
                return 
                
            print(f"[ System ] Contacting Edge TTS servers...")
            communicate = edge_tts.Communicate(text, self.voice, rate="+20%")
            await communicate.save(filename)
            
            print(f"[ System ] Audio downloaded successfully!")
            self.audio_ready_queue.put(filename)
            
        except Exception as e:
            print(f"[ CRITICAL ] TTS Synthesis Error: {e}")

    def _playback_worker(self):
        last_file = None 
        
        while True:
            filename = self.audio_ready_queue.get()
            
            if self._interrupt_flag:
                if os.path.exists(filename):
                    try: os.remove(filename)
                    except: pass
                self.audio_ready_queue.task_done()
                continue

            try:
                # 1. Pydub now successfully calculates the mouth amplitudes!
                audio = AudioSegment.from_file(filename)
                chunk_ms = 30 
                amplitudes = []
                for i in range(0, len(audio), chunk_ms):
                    chunk = audio[i:i+chunk_ms]
                    amp = min(chunk.rms / 4000.0, 1.0)
                    amplitudes.append(amp)

                self.face.set_speaking(True)
                
                # 2. Restored to streaming the exact MP3
                pygame.mixer.music.load(filename)
                
                if last_file and os.path.exists(last_file) and last_file != filename:
                    try: os.remove(last_file)
                    except: pass
                last_file = filename 
                
                pygame.mixer.music.set_volume(1.0)
                pygame.mixer.music.play()
                
                start_time = time.time()
                
                # 3. Restored the original, perfectly timed animation loop
                while pygame.mixer.music.get_busy():
                    if self.face.stop_toggle:
                        print("\n[ Marcus Muted: User Interruption ]")
                        self.stop()
                        break

                    elapsed = int((time.time() - start_time) * 1000)
                    idx = elapsed // chunk_ms
                    
                    if idx < len(amplitudes):
                        self.face.set_audio_level(amplitudes[idx])
                    
                    time.sleep(0.01) 
                
            except Exception as e:
                print(f"Playback Sync Error: {e}")
            finally:
                self.face.set_speaking(False)
                self.face.set_audio_level(0)
                self.audio_ready_queue.task_done()

    def speak(self, text):
        self._interrupt_flag = False # Reset the flag for the new sentence
        
        # Consume click if they right-clicked right before he processed text
        if self.face.stop_toggle: 
            self.face.stop_toggle = False
            return
            
        if not text: return
        chunks = re.split(r'(?<=[.!?;:])\s+', text)
        for chunk in chunks:
            clean = chunk.strip()
            if len(clean) > 1:
                self.text_queue.put(clean)

# --- GLOBAL INITIALIZATION ---
from ui.face import MarcusFace

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

global_face = MarcusFace()
engine = MarcusVoice(global_face)

# 1. Add the global variable so main.py can attach the window to it
global_library_window = None

import asyncio
from event_engine import bus

# 1. ADD THE GLOBAL MUTE STATE AND LISTENER HERE
_is_muted = False

def _update_voice_mute(data):
    """Listens to the bus and updates the voice engine's internal mute state."""
    global _is_muted
    _is_muted = data.get("muted", False)
    print(f"[ Voice Engine ] Mute state synced to: {'MUTED' if _is_muted else 'ACTIVE'}")

# Subscribe to the event
bus.subscribe("sync_mute_state", _update_voice_mute)


async def say(text, ui_text=None):
    global _is_muted
    
    # --- THE DECOUPLED MUTE CHECK ---
    if _is_muted:
        # We are muted. Just type the text to the UI and exit instantly.
        display_text = ui_text if ui_text else text
        print(f"[ Muted Output ]: {text}") # Print to terminal so you know he 'said' it
        await bus.emit("marcus_speaking", {"text": display_text, "audio": ""})
        await asyncio.sleep(0.5) # Tiny buffer so the UI catches up
        await bus.emit("marcus_finished_speaking")
        return
    # --------------------------------

    # 1. PRE-FLIGHT CHECK
    # Only return early if we are NOT in the middle of a shutdown
    if getattr(global_face, 'stop_toggle', False):
        await bus.emit("marcus_finished_speaking")
        # We don't reset the toggle here yet, let the handler do it
        return

    display_text = ui_text if ui_text else text
    await bus.emit("marcus_speaking", {"text": display_text, "audio": text})
    
    loop = asyncio.get_running_loop()
    
    # Ensure the toggle is clear before we start
    global_face.stop_toggle = False 

    # 2. DEFINE THE WRAPPER
    def speak_worker():
        engine.speak(text) 
        # Force the thread to physically block until the audio finishes playing
        engine.wait_until_done() 
        
    # 3. EXECUTE & MONITOR
    speech_task = loop.run_in_executor(None, speak_worker)
    
    # Wait for speech to finish OR for an interruption
    while not speech_task.done():
        if getattr(global_face, 'stop_toggle', False):
            print("[ Voice Interrupted: Silencing Marcus ]")
            try:
                engine.stop() 
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.stop()
            except Exception as e:
                print(f"Error stopping audio: {e}")
            break
        
        # Yield control to the event loop so the UI stays smooth
        await asyncio.sleep(0.05)

    # 4. CLEANUP
    await bus.emit("marcus_finished_speaking")
    
    # Only reset the toggle if we actually hit an interruption
    if getattr(global_face, 'stop_toggle', False):
        global_face.stop_toggle = False