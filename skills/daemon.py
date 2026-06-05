"""
================================================================================
FILE: skills/daemon.py
ROLE: The Proactive Reminder Daemon
================================================================================
A background time-tracker that constantly monitors calendars, task deadlines, 
and user-set ad-hoc reminders. 

It utilizes a dual-stage trigger mechanism (e.g., 30-minute warning + exact time 
alert) and pushes all network API calls (Notion, Google Calendar) into 
background asyncio threads, ensuring proactive alerts never freeze the user 
interface.
================================================================================
"""

import asyncio
import datetime
import json
import os
from skills.gcalendar_tool import GCalTool
from skills.notion_tool import NotionTool
from voice import say, global_face

class ProactiveDaemon:
    def __init__(self):
        self.running = True
        self.notified_events = set()
        self.notified_task_deadlines = set()

    async def run_worker(self):
        print("[ System ] Intelligent Proactive Reminder Daemon Online.")
        
        # Instantiate tools once to avoid overhead
        gcal = GCalTool()
        notion = NotionTool()
        
        while self.running:
            try:
                now = datetime.datetime.now()
                
                # --- 1. PROACTIVE CALENDAR CHECKS (Background Thread) ---
                # THE FIX: Eject the synchronous API call to a background OS thread
                agenda = await asyncio.to_thread(gcal.fetch_agenda, days_ahead=0)
                
                for event in agenda:
                    if "All Day" in event['time']: 
                        continue
                    event_time_str = event['time'].split(" ")[0]
                    event_time = datetime.datetime.strptime(event_time_str, "%H:%M").replace(
                        year=now.year, month=now.month, day=now.day
                    )
                    time_diff = (event_time - now).total_seconds() / 60.0
                    if 29.0 <= time_diff <= 30.5 and event['name'] not in self.notified_events:
                        self.notified_events.add(event['name'])
                        msg = f"Sir, pardon the interruption. You have your '{event['name']}' scheduled in exactly 30 minutes."
                        global_face.set_thinking(True)
                        await say(msg)
                        global_face.set_thinking(False)

                # --- 2. MULTI-DAY NOTION TASKS (Background Thread) ---
                # THE FIX: Eject the Notion API call so it doesn't freeze the UI
                notion_tasks = await asyncio.to_thread(notion.fetch_tasks)
                
                for task in notion_tasks:
                    task_date = getattr(task, 'date', None)
                    if task_date and task.name not in self.notified_task_deadlines:
                        if isinstance(task_date, str):
                            try: task_date = datetime.datetime.fromisoformat(task_date.split('T')[0])
                            except: continue
                        
                        days_remaining = (task_date.date() - now.date()).days
                        if 1 <= days_remaining <= 2:
                            self.notified_task_deadlines.add(task.name)
                            msg = f"Sir, an executive status update: Your directive assignment, '{task.name}', is due in less than 48 hours. I advise adjusting focus blocks."
                            global_face.set_thinking(True)
                            await say(msg)
                            global_face.set_thinking(False)

                # --- 3. DUAL-STAGE VOICE REMINDERS (Background Thread) ---
                reminder_file = "local_reminders.json"
                if os.path.exists(reminder_file):
                    
                    # THE FIX: Eject Disk I/O to a background thread
                    def _read_reminders():
                        try:
                            with open(reminder_file, 'r') as f: return json.load(f)
                        except: return []
                    
                    reminders = await asyncio.to_thread(_read_reminders)
                    modified = False
                    
                    for r in reminders:
                        if not r.get("notified_now", False) or not r.get("notified", False):
                            date_str = r.get("date_target", now.strftime("%Y-%m-%d"))
                            time_str = r.get("time_target", "00:00")
                            
                            try:
                                target_dt = datetime.datetime.strptime(f"{date_str} {time_str.strip()}", "%Y-%m-%d %H:%M")
                                time_diff = (target_dt - now).total_seconds() / 60.0
                                
                                if 0 < time_diff <= 30.5 and not r.get("notified_30m", False):
                                    r["notified_30m"] = True
                                    modified = True
                                    msg = f"Sir, as a heads up, your reminder to '{r['title']}' is coming up in {int(time_diff)} minutes."
                                    global_face.set_thinking(True)
                                    await say(msg)
                                    global_face.set_thinking(False)
                                    
                                elif time_diff <= 0 and not r.get("notified_now", False):
                                    r["notified_now"] = True
                                    r["notified"] = True  
                                    modified = True
                                    msg = f"Sir, it is time to '{r['title']}'."
                                    global_face.set_thinking(True)
                                    await say(msg)
                                    global_face.set_thinking(False)
                                    
                            except Exception as e:
                                print(f"[ Daemon Parse Error ]: {e}")
                                
                    if modified:
                        # THE FIX: Eject File Writing to background thread
                        def _write_reminders():
                            try:
                                with open(reminder_file, 'w') as f: json.dump(reminders, f, indent=4)
                            except: pass
                        await asyncio.to_thread(_write_reminders)

            except Exception as e:
                print(f"[ Proactive Reminder Daemon Error ]: {e}")
                
            await asyncio.sleep(20)