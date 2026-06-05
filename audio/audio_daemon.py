"""
================================================================================
FILE: audio/audio_daemon.py
ROLE: The Hardware Audio Daemon
================================================================================
A dedicated background worker completely isolated from the Main UI thread. 

This daemon manages all PyAudio microphone streams, OpenWakeWord ONNX inference, 
and Google Speech-to-Text transcription. It employs a self-healing protocol to 
reboot the audio driver if the OS chokes the microphone, ensuring M.A.R.C.U.S. 
is always actively listening.
================================================================================
"""


import asyncio
import os
import pygame
import pyaudio
import numpy as np
import speech_recognition as sr
from event_engine import bus
from config.triggers import EXIT_PHRASES

class AudioDaemon:
    def __init__(self, brain, face, briefing, assets_dir):
        self.brain = brain
        self.face = face
        self.briefing = briefing
        self.assets_dir = assets_dir
        
        self.running = True
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        self.blip_sound = None
        self.riff_sound = None
        self.ww_model = None
        self.ww_stream = None
        self.p_audio = pyaudio.PyAudio()
        
        self.is_mic_muted = False
        bus.subscribe("mic_mute_control", self._on_mute_control)

        # Listen for shutdown to kill internal loops safely
        bus.subscribe("system_shutdown_requested", self._on_shutdown)

        self.global_speech_lock = False
        bus.subscribe("marcus_speaking", lambda _: setattr(self, 'global_speech_lock', True))
        bus.subscribe("marcus_finished_speaking", lambda _: setattr(self, 'global_speech_lock', False))

    def _on_mute_control(self, data):
        self.is_mic_muted = data.get("muted", False)
        print(f"[ Audio Daemon ] Hardware mic state synced to: {'MUTED' if self.is_mic_muted else 'ACTIVE'}")

    async def _on_shutdown(self, _):
        self.running = False

    def play_intro_riff(self):
        try:
            if self.riff_sound: self.riff_sound.play()
        except: pass

    def play_blip(self):
        try:
            if self.blip_sound: self.blip_sound.play()
        except: pass

    async def initialize_hardware(self):
        print("[ System ] Unpacking Neural Models... (This may take a moment)")
        loop = asyncio.get_running_loop()

        # 1. Load Wake Word Model
        def load_ww_model():
            from openwakeword.model import Model
            model_path = os.path.join(self.assets_dir, "ma_kis.onnx")
            return Model(wakeword_models=[model_path], inference_framework="onnx")
        
        self.ww_model = await loop.run_in_executor(None, load_ww_model)

        # 2. Open Mic Stream
        self.ww_stream = self.p_audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1280)

        # 3. Calibrate Mic
        print("[ System ] Calibrating spatial audio...")
        def calibrate_mic():
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
        await loop.run_in_executor(None, calibrate_mic)

        # 4. Load Audio Drivers & Sounds
        print("[ System ] Warming up audio drivers...")
        if not pygame.mixer.get_init(): 
            pygame.mixer.init()
            
        blip_path = os.path.join(self.assets_dir, "hologram_blip.mp3")
        riff_path = os.path.join(self.assets_dir, "intro_riff.mp3")
        
        if os.path.exists(blip_path):
            self.blip_sound = pygame.mixer.Sound(blip_path)
            self.blip_sound.set_volume(0.8)
        if os.path.exists(riff_path):
            self.riff_sound = pygame.mixer.Sound(riff_path)
            self.riff_sound.set_volume(0.4)

    async def run_ai_worker(self):
        self.play_intro_riff() 
        print("\n[ Marcus READY ]")

        while self.running:
            if self.face.trigger_toggle:
                self.face.trigger_toggle = False

                if getattr(self.face, 'stop_toggle', False):
                    await asyncio.sleep(0.2)
                    self.face.stop_toggle = False
                
                session_active = True
                print("\n[ Session Started ]")
                
                while session_active and self.running:
                   # --- MOUTH LOCK ---
                    # THE FIX: Added self.global_speech_lock to the condition
                    while self.global_speech_lock or getattr(self.face, 'is_speaking', False) or (pygame.mixer.get_init() and pygame.mixer.music.get_busy()):
                        await asyncio.sleep(0.1)
                        
                    await asyncio.sleep(0.3) 
                    
                    audio = None
                    text_lower = None

                    # --- RECORDING BLOCK ---
                    try:

                        if self.is_mic_muted:
                            print("[ Neural Link Closed: Microphone is hard-muted ]")
                            session_active = False
                            continue

                        self.face.is_recording = True 
                        with self.microphone as source:
                            self.face.set_listening(True)
                            print("\n[ Neural Link Open: Recording... ]")
                            
                            self.recognizer.pause_threshold = 1.5 
                            loop = asyncio.get_event_loop()
                            
                            audio = await loop.run_in_executor(None, lambda: self.recognizer.listen(
                                source, timeout=5, phrase_time_limit=20
                            ))
                    except sr.WaitTimeoutError:
                        print("[ Link Closed: Timeout ]")
                        session_active = False; continue
                    except Exception as e:
                        print(f"[ Link Closed: {e} ]")
                        session_active = False; continue
                    finally:
                        self.face.is_recording = False
                        self.face.set_listening(False)

                    # --- TRANSCRIPTION BLOCK ---
                    if audio:
                        self.face.set_thinking(True)
                        try:
                            raw_text = await loop.run_in_executor(None, self.recognizer.recognize_google, audio)
                            text_lower = raw_text.lower().strip()
                            await bus.emit("user_spoken_text", raw_text)
                            print(f"You: {raw_text}")
                        except sr.UnknownValueError:
                            print("[ Link Closed: Unintelligible ]")
                            session_active = False
                        except Exception as e:
                            print(f"[ STT Error ]: {e}")
                            session_active = False
                        finally:
                            self.face.set_thinking(False)

                    # --- BRAIN PROCESSING ---
                    if text_lower:
                        if any(phrase in text_lower for phrase in EXIT_PHRASES):
                            print("[ Initiating Shutdown Sequence... ]")
                            await self.briefing._enter_sleep_mode()
                            return 

                        self.face.set_thinking(True)
                        keep_listening = await self.brain.chat_async(text_lower)
                        self.face.set_thinking(False)
                        
                        if not keep_listening:
                            session_active = False
                            
            await asyncio.sleep(0.1)

    async def run_wake_word_worker(self):
        CHUNK = 1280
        print("[ Wake Word Engine Active: Listening for 'MARCUS' ]")
        loop = asyncio.get_event_loop() 

        while self.running:
            if self.face.is_listening or getattr(self.face, 'is_thinking', False) or self.is_mic_muted:
                # Read and discard the audio chunk so the buffer doesn't overflow while muted
                try:
                    if self.ww_stream and not self.ww_stream.is_stopped():
                        self.ww_stream.read(CHUNK, exception_on_overflow=False)
                except: pass
                
                await asyncio.sleep(0.1)
                continue

            def _listen_and_predict(active_stream):
                try:
                    data = active_stream.read(CHUNK, exception_on_overflow=False)
                    audio_frame = np.frombuffer(data, dtype=np.int16)
                    return self.ww_model.predict(audio_frame)
                except OSError: return None

            prediction = await loop.run_in_executor(None, _listen_and_predict, self.ww_stream)

            # --- SELF HEALING PROTOCOL ---
            if prediction is None:
                print("[ Audio Driver Choked ]: OS interrupted the microphone. Rebooting stream...")
                try:
                    self.ww_stream.stop_stream()
                    self.ww_stream.close()
                except: pass
                
                await asyncio.sleep(0.3) 
                try:
                    self.ww_stream = self.p_audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=CHUNK)
                    print("[ Audio Driver Healed ]: Marcus is listening again.")
                except Exception: pass
                continue

            for wakeword, score in prediction.items():
                required_score = 0.30 if self.face.is_speaking else 0.55
                if score > required_score:
                    print(f"Wake Word: {score}")
                    await bus.emit("wake_word_detected", {"score": score, "interruption": self.face.is_speaking})
                    self.ww_model.reset()
            
            await asyncio.sleep(0.01)