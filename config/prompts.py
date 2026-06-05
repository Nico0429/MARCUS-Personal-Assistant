"""
================================================================================
FILE: config/prompts.py
ROLE: The Cognitive Prompt Registry
================================================================================
Centralized repository for all LLM system prompts, tool schemas, and HUD data.
By keeping prompts here, we separate the "Personality and Rules" from the 
hardcoded Python logic in the engines.
================================================================================
"""

from datetime import datetime
import json

# ==========================================
# 1. GLOBAL SYSTEM STATE (HUD)
# ==========================================
import json
import os
from datetime import datetime

# ==========================================
# 1. GLOBAL SYSTEM STATE (HUD)
# ==========================================
def build_system_hud(brain):
    """Generates the real-time environmental context for Marcus."""
    current_time = datetime.now().strftime("%I:%M %p")
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    
    # Pull location from .env, fallback to New York for public repos
    city = os.getenv("HOME_CITY", "New York")
    country = os.getenv("HOME_COUNTRY", "United States")
    
    # Check for active environmental states
    timer_state = f"Active ({brain.active_timer_task.get_name()})" if getattr(brain, 'active_timer_task', None) and not brain.active_timer_task.done() else "None"
    last_file = getattr(brain, 'last_cited_filepath', 'None')
    
    return (
        f"[ SYSTEM HUD ]\n"
        f"TIME: {current_time} | DATE: {current_date} | LOCATION: {city}, {country}\n"
        f"ACTIVE TIMER: {timer_state}\n"
        f"LAST REFERENCED FILE: {last_file}\n"
        f"----------------------------------------\n"
    )

# ==========================================
# 2. THE COMMAND SPLITTER (New!)
# ==========================================
def get_splitter_prompt(query):
    """Determines if a sentence contains multiple unrelated commands."""
    return (
        f"You are an NLP command parsing engine. Determine if the user's input contains MULTIPLE, UNRELATED commands that must be executed separately.\n\n"
        f"USER INPUT: '{query}'\n\n"
        f"CRITICAL RULES:\n"
        f"1. ONLY split if the commands require completely different actions or tools (e.g., opening an app vs setting a timer).\n"
        f"2. DO NOT split conversational phrasing like 'search the web and tell me...' or 'look up x and see if...'. These are a single action.\n"
        f"3. DO NOT split modifiers. 'Add a task to wash the car and make it high priority' is a single action.\n"
        f"4. If a verb applies to multiple targets, distribute the verb: 'open spotify and discord' -> [\"open spotify\", \"open discord\"].\n"
        f"5. Return ONLY a valid JSON array of strings. No markdown, no explanations.\n\n"
        f"EXAMPLES:\n"
        f"- 'open spotify and close terminal' -> [\"open spotify\", \"close terminal\"]\n"
        f"- 'search the web and tell me who won the super bowl' -> [\"search the web and tell me who won the super bowl\"]\n"
        f"- 'start a timer for 10 minutes and call it laundry' -> [\"start a timer for 10 minutes and call it laundry\"]\n"
        f"- 'turn on deep work and open my stat480 notes' -> [\"turn on deep work\", \"open my stat480 notes\"]\n"
    )

# ==========================================
# 3. AGENTIC TOOL REGISTRY
# ==========================================
AGENT_TOOLS = [
    {
        "name": "task_add",
        "description": "Use this to create a new task. CRITICAL: Also use this if the user states an intent to do something in the future, even casually (e.g., 'I need to...', 'I have to...', 'Remind me to...')."
    },
    {
        "name": "task_update",
        "description": "Updates the status or priority of an existing task (e.g., 'mark that task as done', 'change priority to high', 'finish that task')."
    },
    {
        "name": "task_fetch",
        "description": "Retrieves the user's active tasks and to-do queue (e.g., 'what are my tasks', 'show me my to do list', 'what is on my plate')."
    },
    {
        "name": "news_fetch",
        "description": "Use this ONLY when the user asks for a general daily briefing or headlines (e.g., 'what is on the news', 'give me a briefing'). DO NOT use this to answer specific factual questions."
    },
    {
        "name": "calendar_fetch",
        "description": "Fetches a broad agenda or timeline for a day, week, or month (e.g., 'what is on my agenda today', 'what do i have to do this week', 'read my schedule')."
    },
    {
        "name": "shopping_add",
        "description": "Adds specific items to the grocery or supply requisitions list (e.g., 'add milk to the shopping list', 'we are out of coffee')."
    },
    {
        "name": "shopping_fetch",
        "description": "Reads the current shopping/grocery list (e.g., 'what is on the shopping list', 'what do we need to buy')."
    },
    {
        "name": "web_search",
        "description": "Use this to search the internet for specific facts, recent events, or sports results (e.g., 'Who won the F1 race?', 'What is the capital of X?')."
    },
    {
        "name": "memory_add",
        "description": "ONLY use this if the user is explicitly telling you to learn a NEW fact (e.g., 'remember that...', 'log this...'). CRITICAL: NEVER use this if the user is ASKING a question (e.g., 'what is', 'who is'). All questions must be routed to general_chat."
    },
    {
        "name": "memory_prune",
        "description": "Deletes or erases a specific fact from permanent memory (e.g., 'forget about the pizza', 'delete the node for my favorite color')."
    },
    {
        "name": "ui_control",
        "description": "Opens, closes, or toggles system UI panels like the terminal, matrix, HUD, brain, or console (e.g., 'open the neural matrix', 'show me your brain', 'close the HUD')."
    },
    {
        "name": "timer_control",
        "description": "Starts, stops, or checks a countdown timer or alarm (e.g., 'set a timer for 45 minutes', 'cancel the timer', 'how much time is left')."
    },
    {
        "name": "media_control",
        "description": "Controls audio playback and media player UI (e.g., 'play music', 'pause the music', 'skip this song', 'show the media controller'). Note: Use app_control to launch an app."
    },
    {
        "name": "telemetry",
        "description": "Pulls core system status, diagnostics, CPU/RAM/GPU usage, and hardware reports (e.g., 'run diagnostics', 'how is the cpu', 'system status update')."
    },
    {
        "name": "deep_work",
        "description": "Initiates a strict focus session or deep work protocol (e.g., 'execute deep work mode', 'start a focus session for stats')."
    },
    {
        "name": "reminder_add",
        "description": "Sets a time-specific reminder for a future event (e.g., 'remind me to submit my project at 4pm', 'set a reminder to check the oven')."
    },
    {
        "name": "reminder_cancel",
        "description": "Cancels, deletes, or removes an active reminder from the queue (e.g., 'cancel the temp reminder', 'delete my reminder for 5pm', 'remove the reminder')."
    },
    {
        "name": "event_search",
        "description": "Searches the calendar for the specific date/time of a single event, exam, or meeting (e.g., 'when is my multivariate exam', 'what time is the meeting')."
    },
    {
        "name": "document_search",
        "description": "CRITICAL: Use this for ALL academic, statistical, mathematical, or thesis-related questions (e.g., 'tell me about mean vectors', 'what is in module 1', 'explain fault detection'). It searches the user's local university PDFs and notes."
    },
    {
        "name": "document_open",
        "description": "Physically opens or launches local files, PDFs, projects, or code files (e.g., 'open my honors project', 'open STAT480 module 1', 'no i meant open the python file')."
    },
    {
        "name": "app_control",
        "description": "Physically launches or closes desktop applications like Spotify, Chrome, or Apple Music (e.g., 'open spotify', 'launch chrome', 'open apple music', 'close word')."
    },
    {
        "name": "general_chat",
        "description": "Fallback tool for casual conversation, identity questions, greetings, or jokes (e.g., 'hello marcus', 'how are you doing', 'who am i')."
    }

]

def get_router_prompt(query, custom_tools=None):
    tools = custom_tools if custom_tools else AGENT_TOOLS
    tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in tools])
    
    return (
        f"You are the central routing intelligence for an AI system.\n"
        f"Analyze the user's input and select the correct tool.\n\n"
        f"USER INPUT: '{query}'\n\n"
        f"AVAILABLE TOOLS:\n{tool_descriptions}\n\n"
        f"CRITICAL RULE: You MUST return a valid JSON object. You must explain your reasoning FIRST, paying close attention to whether the user is asking a question or giving a command. Then, output the exact tool name.\n\n"
        f"EXAMPLE 1:\n"
        f"Input: 'remember that my ID is 12345'\n"
        f"{{\n"
        f"  \"reasoning\": \"The user is commanding me to learn a new fact. This is an explicit memory addition.\",\n"
        f"  \"intent\": \"memory_add\"\n"
        f"}}\n\n"
        f"EXAMPLE 2:\n"
        f"Input: 'what is my ID number?'\n"
        f"{{\n"
        f"  \"reasoning\": \"The user is asking a question about a known fact. Questions should never add memory.\",\n"
        f"  \"intent\": \"general_chat\"\n"
        f"}}\n\n"
        f"Output ONLY the JSON object for the user's input."
    )

# ==========================================
# 4. DOCUMENT ENGINE PROMPTS
# ==========================================
def get_document_open_scrubber_prompt(brain, query_l, transcript, kg_context):
    return (
        f"You are a file search keyword extractor.\n"
        f"Extract search keywords for this file request: '{query_l}'.\n"
        f"Combine the topic, file names, and extensions (pdf, docx).\n\n"
        f"RULES:\n"
        f"1. Output NOTHING but the space-separated keywords.\n"
        f"2. Do not write sentences. Do not use punctuation.\n\n"
        f"EXAMPLE 1:\n"
        f"Request: 'open my stat480 notes'\n"
        f"Output: stat480 notes pdf docx\n\n"
        f"EXAMPLE 2:\n"
        f"Request: 'no i meant the python file'\n"
        f"Output: python py\n\n"
        f"CURRENT REQUEST:\n"
        f"Request: '{query_l}'\n"
        f"Output: "
    )

def get_document_open_selector_prompt(brain, query_l, transcript, kg_context, paths_str):
    hud = build_system_hud(brain)
    return (
        f"{hud}"
        f"The user wants to open a file based on this request: '{query_l}'.\n"
        f"Recent conversation transcript for context:\n{transcript}\n"
        f"Here are the candidate file paths mapped from their system:\n"
        f"--------------------\n{paths_str}\n--------------------\n"
        f"Identify the SINGLE file path that logically matches the user's request.\n"
        f"CRITICAL RULES:\n"
        f"1. Prioritize personal work/drafts unless the user explicitly asks for a generic pdf, notes, or assignment instructions.\n"
        f"2. Return ONLY the exact absolute file path. Nothing else. If none match, return 'NONE'."
    )

# ==========================================
# 5. CONVERSATIONAL PROMPTS
# ==========================================
def get_general_chat_prompt(brain, raw_query, context_block, transcript):
    hud = build_system_hud(brain)
    return (
        f"You are Marcus, a highly professional AI butler.\n\n"
        f"{hud}"
        f"--- BACKGROUND KNOWLEDGE ---\n"
        f"{context_block}"
        f"----------------------------\n\n"
        f"SESSION TRANSCRIPT:\n{transcript}\n\n"
        f"CURRENT USER QUERY: {raw_query}\n\n"
        f"INSTRUCTIONS:\n"
        f"If the query requires taking an action or fetching external data, output ONLY one of these exact tags:\n"
        f" <WEB: search_term> (To look up weather, facts, or real-time info)\n"
        f" <AGENDA> (To check schedule, tasks, or calendar)\n"
        f" <TIMER: minutes | task_name> (To start a countdown)\n"
        f" <STOP_TIMER> (To cancel an active timer)\n\n"
        f"Otherwise, answer the CURRENT USER QUERY directly and concisely. Use the Background Knowledge and Session Transcript if they are relevant, but do not explicitly announce that you are reading from a document or memory."
    )

def get_fallback_chat_prompt(brain, raw_query, context_block2):
    hud = build_system_hud(brain)
    return (
        f"You are Marcus, a highly professional AI butler.\n\n"
        f"{hud}"
        f"{context_block2}"
        f"USER QUERY: {raw_query}\n\n"
        f"INSTRUCTIONS: Answer clearly and concisely using the provided context. Do not announce your data sources."
    )