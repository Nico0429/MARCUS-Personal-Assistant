from skills.notion_tool import NotionTool
import threading
import os
import time
import pyautogui
import threading

APP_REGISTRY = {
    "apple music": "AppleMusic.exe",
    "spotify": "Spotify.exe",
    "chrome": "chrome.exe",
    "discord": "Update.exe --processStart Discord.exe", 
    "calculator": "CalculatorApp.exe" 
}

def fetch_tasks_tool() -> list:
    """
    Fetches all active high-priority tasks from Notion.
    """
    print("[ Fetching Tasks from Notion... ]")
    tool = NotionTool()
    tasks = tool.fetch_tasks()
    
    # We only send 'd' (due) if it's not an empty string
    return [
        {
            "t": t.name, 
            "p": t.priority, 
            **({"d": t.due} if t.due else {}) 
        } 
        for t in tasks if t.priority == "High"
    ]

def update_task_tool(task_id=None, status=None, priority=None):
    """Updates a task. If task_id is unknown, the system will search by name."""
    from notion_tool import NotionTool
    tool = NotionTool()
    
    # If the model is dumb and doesn't provide an ID, 
    # we use the query/context to find it.
    if not task_id or task_id.lower() == "sir":
        return "Sir, I need to know which task to update."

    print(f"Marcus: Searching for task related to '{task_id}'...")
    all_tasks = tool.fetch_tasks()
    
    target_id = None
    # Look for a name match
    for t in all_tasks:
        if task_id.lower() in t.name.lower():
            target_id = t.task_id
            break
            
    if not target_id:
        return f"I couldn't find a task named {task_id}, Sir."

    success = tool.update_task(target_id, status=status, priority=priority)
    return "Success" if success else "Update failed."

def search_internet(search_query: str) -> str:
    """Searches the web using DuckDuckGo and returns the top snippets."""
    # Updated import for the new ddgs library
    from ddgs import DDGS 
    
    try:
        # DDGS syntax remains largely the same
        results = DDGS().text(search_query, max_results=3)
        
        if not results:
            return "No results found on the internet."
            
        snippets = []
        for r in results:
            # Safely grab the title and body
            title = r.get('title', 'Unknown Source')
            body = r.get('body', '')
            snippets.append(f"Source - {title}: {body}")
            
        return "\n".join(snippets)
    except Exception as e:
        print(f"Web Search Error: {e}")
        return "The search engine blocked the request or is currently offline."
    


def open_application(app_name):
    """
    Dynamically attempts to open any app.
    Combines AppOpener logic with Bulletproof OS Macros.
    """
    def _run():
        target_exe = APP_REGISTRY.get(app_name.lower())
        
        # Strategy 1: Explicit Registry Map (Always check this FIRST)
        if target_exe:
            result = os.system(f"start {target_exe}")
            if result == 0: 
                print(f"[ Tool Execution: Opened {app_name} via OS Registry ]")
                return

        # Strategy 2: AppOpener (For standard apps not in our registry)
        try:
            from AppOpener import open as open_app
            open_app(app_name, match_closest=True)
            print(f"[ Tool Execution: Opened {app_name} via AppOpener ]")
            return
        except Exception:
            pass 

        # Strategy 3: The Bulletproof OS Macro Fallback
        print(f"[ SmartLauncher ] CLI failed for '{app_name}'. Using Start Menu fallback...")
        pyautogui.press('win')
        time.sleep(0.5)
        pyautogui.write(app_name)
        time.sleep(0.5)
        pyautogui.press('enter')

    threading.Thread(target=_run, daemon=True).start()
    return True

def close_application(app_name):
    """
    Dynamically attempts to force-kill any app.
    """
    # --- SURVIVAL INSTINCT GUARDRAIL ---
    safe_name = app_name.lower()
    if "code" in safe_name or "visual studio" in safe_name or "vs code" in safe_name:
        print("[ Tool Execution Blocked: Cannot close host environment. ]")
        return False
        
    def _run():
        target_exe = APP_REGISTRY.get(safe_name)
        
        # If it's in our registry, hard-kill it immediately
        if target_exe:
            os.system(f"taskkill /f /im {target_exe}")
            print(f"[ Tool Execution: TaskKilled {app_name} ]")
            return

        # Otherwise, let AppOpener handle standard apps
        try:
            from AppOpener import close as close_app
            close_app(app_name, match_closest=False)
            print(f"[ Tool Execution: Closed {app_name} ]")
        except Exception as e:
            print(f"[ Tool Execution Error - {app_name} ]: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return True