"""
================================================================================
FILE: brain.py
ROLE: The Cognitive Controller 
================================================================================
The high-level logic coordinator for M.A.R.C.U.S. 

This class delegates heavy lifting to specialized sub-engines: it passes user 
queries to the SemanticRouter for intent classification, hands RAG execution to 
the AgenticEngine, and manages global state components like the conversation 
history and vector memory. It contains zero file-system logic and zero UI code.
================================================================================
"""


import os, requests, json, time, re
from google import genai
from google.genai import types
import watchdog
from skills.notion_tool import NotionTool
from dotenv import load_dotenv
from datetime import datetime, timedelta
from skills.tools import *
from config.config import MODEL_NAME, TEMPERATURE
from skills.tools import fetch_tasks_tool, update_task_tool, open_application, close_application
import ollama
import asyncio
import threading
import random
from config.dialogue import thinking_phrases, affirmation_phrases
from config.personas import AGENT_PERSONAS
from config.triggers import NEWS_OPT_IN
from event_engine import bus
from cognitive.llm_service import LLMService
from cognitive.memory_controller import MemoryController
from cognitive.skill_controller import SkillController
from skills.timer_tool import TimerSkill
from memory_graph import MemoryGraph
from vector_memory import VectorMemory
from skills.media_skill import MediaSkill
from skills.directory_watchdog import NeuralWatchdog  
from config.prompts import get_general_chat_prompt, get_fallback_chat_prompt  
from cognitive.agentic_engine import AgenticEngine             
from cognitive.semantic_router import SemanticRouter

class MarcusBrain:
    def __init__(self):
        self.local_model = MODEL_NAME
        self.agents = AGENT_PERSONAS
        self.interrupt_event = asyncio.Event()

        self.awaiting_news_opt_in = False
        self.last_cited_filepath = None
        
        self.memory = MemoryGraph()
        self.vector_db = VectorMemory()


        self.llm = LLMService(self.local_model, self.agents)
        self.memory_controller = MemoryController(self.memory, self.vector_db, self.llm, self.interrupt_event)
        self.skill_controller = SkillController(self)
        self.timer_skill = TimerSkill(self)
        self.media_skill = MediaSkill(self)
        
        
        self.router = SemanticRouter(self.llm)
        self.agentic_engine = AgenticEngine(self.llm, self.vector_db, self.memory, self.timer_skill)
    
        self.conversation_history = []
        self.max_history_turns = 6
        
        async def _on_opt_in_set(state):
            self.awaiting_news_opt_in = state
            
            if state:
                async def run_timeout():
                    await asyncio.sleep(8.0)
                    if getattr(self, 'awaiting_news_opt_in', False):
                        print("[ News Opt-In Timeout: Defaulting to No ]")
                        self.awaiting_news_opt_in = False
                        
                        from event_engine import bus
                        await bus.emit("user_spoken_text", "[ System: Response Timeout ]")
                        
                        import random
                        from config.dialogue import intro_phrases
                        from voice import say
                        
                        farewell = "Understood. " + random.choice(intro_phrases)
                        await say(farewell, ui_text=farewell)
                
                asyncio.create_task(run_timeout())
                
        bus.subscribe("set_news_opt_in_state", _on_opt_in_set)

    # ==========================================
    # 1. THE CHAIN MANAGER (Command Splitter)
    # ==========================================
    async def chat_async(self, query):
        self.interrupt_event.clear()
        query_l = query.lower().strip()
        loop = asyncio.get_running_loop()

        # --- THE OPT-IN TRAP (Global Priority) ---
        if getattr(self, 'awaiting_news_opt_in', False):
            self.awaiting_news_opt_in = False 
            if any(w in query_l for w in NEWS_OPT_IN):
                return await self.skill_controller.handle_news_fetch("AI and politics")
            else:
                import random
                from config.dialogue import intro_phrases
                from voice import say
                farewell = "Understood. " + random.choice(intro_phrases)
                await say(farewell, ui_text=farewell)
                return False 

        if query_l == "/help":
            return await self.skill_controller.handle_help()
        
        if query_l == "/rebuild":
            from voice import say
            print("[ System ] INITIATING FULL NEURAL MATRIX REBUILD...")
            await say("Right away, Sir. Purging document matrix and initiating deep resync.")
            
            # Threaded DB Purge to protect the UI loop
            await loop.run_in_executor(None, self.vector_db.wipe_documents)
            
            # Tell the system to restart the watchdog
            from event_engine import bus
            await bus.emit("trigger_watchdog_rebuild")
            
            return False

        # --- DELEGATED TO ROUTER ---
        queries_to_process = await self.router.split_commands(query)
        
        keep_listening_overall = False
        
        for idx, q in enumerate(queries_to_process):
            if self.interrupt_event.is_set():
                print("[ System ] Chain execution aborted by user.")
                break 
                
            result = await self._process_single_query(q)
            if result: 
                keep_listening_overall = True
            
            if idx < len(queries_to_process) - 1:
                await asyncio.sleep(0.5)
            
        return keep_listening_overall

    # ==========================================
    # 2. THE TRAFFIC COP (Routing Hub)
    # ==========================================
    async def _process_single_query(self, query):
        query_l = query.lower().strip()
        self.conversation_history.append({"role": "User", "content": query})
        
        # --- DELEGATED TO ROUTER ---
        intent = await self.router.route_query(query_l)
        print(f"[ LLM Router ] Dynamically classified as '{intent}'.")

        if intent == "timer_control": return await self.skill_controller.handle_timer(query_l)
        elif intent == "media_control": return await self.skill_controller.handle_media(query_l)
        elif intent == "app_control": return await self.skill_controller.handle_app_control(query_l)
        elif intent == "task_add": return await self.skill_controller.handle_task_add(query_l)
        elif intent == "task_update": return await self.skill_controller.handle_task_update(query_l)
        elif intent == "task_fetch": return await self.skill_controller.handle_task_fetch(query_l)
        elif intent == "news_fetch": return await self.skill_controller.handle_news_fetch(query_l)
        elif intent == "calendar_fetch": return await self.skill_controller.handle_calendar_fetch(query_l)
        elif intent == "reminder_add": return await self.skill_controller.handle_custom_reminder(query_l)
        elif intent == "reminder_cancel": return await self.skill_controller.handle_cancel_reminder(query_l)
        elif intent == "event_search": return await self.skill_controller.handle_event_search(query_l)
        elif intent == "shopping_add": return await self.skill_controller.handle_shopping_add(query_l)
        elif intent == "shopping_fetch": return await self.skill_controller.handle_shopping_fetch(query_l)
        elif intent == "telemetry": return await self.skill_controller.handle_telemetry(query_l)
        elif intent == "deep_work": return await self.skill_controller.handle_deep_work(query_l)
        elif intent == "web_search": return await self.skill_controller.handle_web_search(query, query_l) 
        elif intent == "memory_add": return await self.memory_controller.handle_memory_add(query_l)
        elif intent == "memory_prune": return await self.memory_controller.handle_memory_prune(query_l)
        elif intent == "ui_control": return await self.skill_controller.handle_ui_control(query_l)
        elif intent == "document_search": return await self.skill_controller.handle_document_search(query_l)
        elif intent == "document_open": return await self.skill_controller.handle_document_open(query_l)
        else: return await self.handle_llm_chat(query)

    # ==========================================
    # 3. THE GENERAL CONVERSATIONAL ENGINE
    # ==========================================
    async def handle_llm_chat(self, raw_query):
        from voice import say, global_face
        print("[ Waking Conversational Agent... ]")
        loop = asyncio.get_running_loop()
        
        # 1. Ask the engine to do all the heavy lifting
        msg = await self.agentic_engine.process_chat(raw_query, self.conversation_history)

        # Catch if a Timer protocol returned True/False directly instead of a string
        if isinstance(msg, bool):
            return msg

        # 2. Handle System Memory
        await loop.run_in_executor(None, lambda: self.vector_db.remember_interaction(raw_query, msg))
        self.conversation_history.append({"role": "User", "content": raw_query})
        self.conversation_history.append({"role": "Marcus", "content": msg})
        
        if len(self.conversation_history) >= self.max_history_turns:
            transcript = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.conversation_history])
            self.conversation_history = [] 
            asyncio.create_task(self.memory_controller.consolidate_memory(transcript))
        
        # 3. Handle Telemetry (Fire-and-forget)
        import random
        if random.random() < 0.05:
            print("[ System ] Spontaneous Telemetry Triggered")
            snarky_comments = [
                " Oh, and by the way Sir, here are the system diagnostics you didn't ask for.",
                " I've also dropped my core telemetry into your terminal. Consider it proof of life.",
                " And before I forget, I am running a spontaneous diagnostic on the console."
            ]
            msg += random.choice(snarky_comments)
            
            async def run_detached_telemetry():
                from skills.visual_tool import generate_telemetry
                telemetry_block = await generate_telemetry()
                from event_engine import bus
                await bus.emit("user_spoken_text", f"\n{telemetry_block}")
            
            asyncio.create_task(run_detached_telemetry())

        # 4. Interface with User
        global_face.set_thinking(False)
        print(f"Marcus: {msg}")
        await say(msg)
        return True