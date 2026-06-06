"""
================================================================================
FILE: main.py
ROLE: The Master Bootloader
================================================================================
This is the entry point for M.A.R.C.U.S. It operates strictly as a bootloader, 
responsible only for instantiating core cognitive components, launching the Qt 
UI, and starting the background hardware daemons. 

To maintain a buttery-smooth UI, absolutely no heavy processing, API calls, or 
audio stream management should occur in this file. It simply builds the engine 
and turns the key.
================================================================================
"""


import os
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--log-level=3" # Suppresses harmless Chromium GPU warnings
import sys
import asyncio
import time
import signal
import traceback

from qasync import QEventLoop
from PySide6.QtWidgets import QApplication

from ui.theme import get_master_stylesheet
from voice import global_face
from brain import MarcusBrain
from briefing import Briefing
from system_events import SystemEventBridge

from ui.media_ui import MediaWindow
from ui.library_window import LibraryWindow
from ui.graph_window import GraphWindow
from ui.timer_window import TimerWindow
from ui.edgepulse import EdgePulseOverlay
from ui.holo_grid import HoloGridOverlay

from ui.ui_manager import UIManager
import keyboard

from skills.daemon import ProactiveDaemon
from audio.audio_daemon import AudioDaemon

# --- DYNAMIC PATHING ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging"
os.environ["PATH"] = ASSETS_DIR + os.pathsep + os.environ.get("PATH", "")

import logging
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# 1. APP INIT
app = QApplication.instance() or QApplication(sys.argv)
is_running_main = True

# --- APPLY GLOBAL UI THEME ---
app.setStyleSheet(get_master_stylesheet())

async def main_async():
    global is_running_main
    
    # 1. INITIALIZE CORE COMPONENTS
    shared_brain = MarcusBrain()
    await shared_brain.router.initialize()
    face = global_face
    briefing = Briefing()
    edge_pulse = EdgePulseOverlay()

   # 2. INITIALIZE UI COMPONENTS (Fully Decoupled)
    terminal_window = LibraryWindow()  
    brain_window = GraphWindow()       
    brain_window.refresh_graph() 
    timer_window = TimerWindow()
    media_window = MediaWindow()
    grid_overlay = HoloGridOverlay(grid_size=40)

    # --- INITIALIZE THE CENTRAL MANAGER ---
    ui_manager = UIManager(
        face=face,
        library=terminal_window,
        graph=brain_window,
        media=media_window,
        timer=timer_window,
        grid=grid_overlay
    )
    # --------------------------------------

    # 3. INITIALIZE DAEMONS
    marcus_daemon = ProactiveDaemon()
    audio_daemon = AudioDaemon(shared_brain, face, briefing, ASSETS_DIR)

    from skills.directory_watchdog import NeuralWatchdog
    directory_watchdog = NeuralWatchdog(shared_brain.vector_db)

    # 4. INITIALIZE EVENT BRIDGE (Controller)
    def trigger_shutdown():
        global is_running_main
        is_running_main = False
        
        print("[ System ] Initiating cinematic UI teardown...")
        keyboard.unhook_all()
        
        # Trigger Ghost Mode instantly to perfectly sync the fade-out of ALL windows!
        if not ui_manager._is_ghost_mode:
            from event_engine import bus
            bus.emit_sync("toggle_ui_visibility", {})
        
        # Tell the face to shrink into nothingness
        face.trigger_shutdown()

    event_bridge = SystemEventBridge(
        brain=shared_brain,
        face=face,
        briefing=briefing,
        terminal_window=terminal_window,
        brain_window=brain_window,
        marcus_daemon=marcus_daemon,
        shutdown_callback=trigger_shutdown
    )

    # ==========================================================
    # SYSTEM BOOT PROTOCOL
    # ==========================================================
    await audio_daemon.initialize_hardware()

    print("[ System ] Neural link established. Initializing UI...")
    audio_daemon.play_blip() 
    face.show()
    terminal_window.fade_in()
    edge_pulse.start()

    await asyncio.sleep(3.0)


    # ==========================================================
    # GHOST MODE HOTKEY
    # ==========================================================
    def trigger_ghost_mode():
        from event_engine import bus
        bus.emit_sync("toggle_ui_visibility", {})

    # Binds to Alt + Space. You can change this to 'ctrl+shift+m' etc.
    keyboard.add_hotkey('alt+space', trigger_ghost_mode, suppress=True)
    # ==========================================================



    # 5. START ACTIVE WORKERS
    asyncio.create_task(audio_daemon.run_wake_word_worker())
    asyncio.create_task(audio_daemon.run_ai_worker())
    asyncio.create_task(marcus_daemon.run_worker())
    directory_watchdog.start()
    
    # 6. RUN INITIAL BRIEFING
    await briefing.execute_hardcoded_briefing()

    # 7. MAIN EVENT LOOP
    while is_running_main:
        await asyncio.sleep(0.5)


    # The UI already faded away while Marcus was talking, so we can exit instantly!
    print("[ System ] main_async completed. Cleaning up Qt loop...")
    QApplication.instance().quit()


if __name__ == "__main__":
    def force_quit(signum, frame):
        print("\n[ System ] Manual override (Ctrl+C) detected. Hard shutting down...")
        os._exit(0)
    
    signal.signal(signal.SIGINT, force_quit)

    # =================================================================
    # --- THE CRISP FONT FIX: Force Windows High-DPI Awareness ---
    # =================================================================
    import ctypes
    try:
        # Tells Windows 10/11 to render fonts natively instead of bitmap-stretching them
        ctypes.windll.shcore.SetProcessDpiAwareness(2) 
    except Exception:
        pass
    
    # Enable high-resolution pixmaps in Qt
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    # =================================================================

    app = QApplication.instance() or QApplication(sys.argv)
    
    # --- ENFORCE GLOBAL ANTI-ALIASING FOR CONSOLAS ---
    from PySide6.QtGui import QFont
    global_font = QFont("Consolas")
    global_font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
    app.setFont(global_font)
    # -------------------------------------------------

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    from event_engine import bus
    bus.set_main_loop(loop)

    try:
        with loop: loop.run_until_complete(main_async())
    except Exception as e:
        print("\n[ CRITICAL SYSTEM FAILURE ]")
        import traceback
        traceback.print_exc()
    
    print("[ Process Terminated. Have a good evening, Sir. ]")
    time.sleep(0.2)
    os._exit(0)