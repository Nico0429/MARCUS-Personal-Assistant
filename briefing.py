"""
================================================================================
FILE: briefing.py
ROLE: The Startup Briefing Module
================================================================================
Compiles the initial boot monologue for M.A.R.C.U.S. 

It runs parallel API fetches to gather weather data, upcoming calendar events, 
high-priority directives, and any reminders missed while offline. It formats 
this data into a cohesive UI layout and a single, interruptible voice payload, 
concluding with a seamless handoff to the News Opt-In sequence.
================================================================================
"""



import asyncio
from datetime import datetime, time, timedelta
from random import random
from skills.notion_tool import NotionTool
import time, os
from config.dialogue import intro_phrases, off_phrases
from event_engine import bus
from voice import say, global_face

class Briefing:

    async def execute_hardcoded_briefing(self):
        from voice import say
        from skills.notion_tool import NotionTool
        from skills.gcalendar_tool import GCalTool
        from config.dialogue import intro_phrases
        import random, asyncio, datetime

        # =========================================================
        # 1. DYNAMIC GREETING & WEATHER CHECK
        # =========================================================
        base_greeting = await self._generate_dynamic_greeting()

        print("[ System ] Initiating Dark Boot Sequence...")
        print("[ System ] Synchronizing databases...")
        
        try:
            notion = NotionTool()
            gcal = GCalTool()
            loop = asyncio.get_running_loop()
    
            # 2. Parallel Fetch (Tasks, Calendar, AND Reminders)
            tasks_future = loop.run_in_executor(None, notion.fetch_tasks)
            gcal_future = loop.run_in_executor(None, gcal.fetch_today_agenda)
            reminder_future = loop.run_in_executor(None, self._check_missed_reminders)
            
            all_tasks, raw_agenda, (missed_spoken, missed_list) = await asyncio.gather(tasks_future, gcal_future, reminder_future)
            
            print("[ System ] Synchronization Complete. Building UI...")
            
            bullet_points = []
            spoken_lines = [base_greeting]

            # =========================================================
            # THE UI DISPLAY: Inject Missed Alerts right at the top
            # =========================================================
            if missed_list:
                spoken_lines.append(missed_spoken)
                bullet_points.append("\n:: MISSED ALERTS ::")
                bullet_points.append("========================================")
                for m in missed_list:
                    bullet_points.append(f" [!] MISSED : {m.upper()}")
                bullet_points.append("========================================")

            # =========================================================
            # 3. FILTER AGENDA (Drop Past Events)
            # =========================================================
            merged_agenda = []
            for event in raw_agenda:
                time_str = event.get('time', '')
                if "All Day" in time_str or not time_str:
                    merged_agenda.append(event)
                    continue
                try:
                    current_dt = datetime.datetime.now()
                    end_time_str = time_str.split("-")[-1].strip()
                    event_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()
                    event_dt = datetime.datetime.combine(current_dt.date(), event_time)
                    if event_dt >= current_dt:
                        merged_agenda.append(event)
                except ValueError:
                    merged_agenda.append(event)

            # 4. Filter for High Priority Tasks
            target_tasks = [t for t in all_tasks if t.priority == "High"]


            # --- AGENDA SECTION ---
            if merged_agenda:
                bullet_points.append("\n:: DAILY AGENDA ::")
                bullet_points.append("========================================")
                spoken_lines.append("Your remaining schedule for today includes:")
                for event in merged_agenda:
                    bullet_points.append(f" [◈] {event['time']} : {event['name'].upper()}")
                    spoken_lines.append(f"{event['name']} at {event['time']}.")
                bullet_points.append("========================================")
            else:
                spoken_lines.append("Your calendar is currently clear for the rest of the day.")
            
            # --- TASKS SECTION ---
            if not target_tasks:
                spoken_lines.append("Sir, all high priority systems are clear. No immediate tasks on the horizon.")
                bullet_points.append("\nSir, all high priority systems are clear.")
            else:
                spoken_lines.append("Your high priority tasks are as follows:")
                bullet_points.append("\n:: HIGH PRIORITY DIRECTIVES ::")
                bullet_points.append("========================================")
                
                task_speech_items = []
                for idx, t in enumerate(target_tasks, 1):
                    friendly_date = self._get_friendly_date(t.due)
                    if friendly_date:
                        task_speech_items.append(f"{t.name} due {friendly_date}")
                        bullet_points.append(f" [◈] DIRECTIVE {idx:02d} : {t.name.upper()}")
                        bullet_points.append(f"    └─ DEADLINE : {friendly_date.upper()}")
                        bullet_points.append(f"    └─ STATUS   : UNRESOLVED\n")
                    else:
                        task_speech_items.append(t.name)
                        bullet_points.append(f" [◈] DIRECTIVE {idx:02d} : {t.name.upper()}")
                        bullet_points.append(f"    └─ STATUS   : UNRESOLVED\n")
                
                bullet_points.append("========================================")
                task_list_spoken = ", ".join(task_speech_items)
                spoken_lines.append(f"{task_list_spoken}.")
                
            # =========================================================
            # 5. THE NEWS HANDOFF (Appended to prevent UI thread killing)
            # =========================================================
            prompt = "I have pulled today's top stories in Artificial Intelligence and politics. Shall I read them to you?"
            
            # Stitch the prompt directly into the final text payload
            spoken_lines.append(prompt)
            bullet_points.append(f"\n[?] {prompt}")
            
            # Build the ONE final string
            spoken_text = " ".join(spoken_lines)
            ui_text = base_greeting + "\n" + "\n".join(bullet_points)
            
            print(f"Marcus:\n{ui_text}")
            await say(spoken_text, ui_text=ui_text) 
            
            # --- THE FIX: Abort if the user interrupted the briefing! ---
            from voice import engine
            if getattr(engine, '_interrupt_flag', False):
                print("[ Briefing Skipped: Aborting News Opt-In ]")
                return
            # ------------------------------------------------------------
            
            # 1. Tell the brain to expect a yes/no answer
            await bus.emit("set_news_opt_in_state", True)
            
            # 2. Pop the microphone open instantly!
            global_face.trigger_toggle = True
            
        except Exception as e:
            print(f"Briefing Error: {e}")
            await say("Sir, I was unable to access the databases for the initial briefing.")




    def _check_missed_reminders(self):
        import os, json
        from datetime import datetime
        
        print("\n[ Reminder Check ] Booting offline reminder scan...")
        reminder_file = "local_reminders.json"
        
        if not os.path.exists(reminder_file): 
            print("[ Reminder Check ] No local_reminders.json file found.")
            return "", []

        try:
            with open(reminder_file, 'r') as f:
                reminders = json.load(f)
                print(f"[ Reminder Check ] Successfully loaded {len(reminders)} reminders from file.")
        except Exception as e:
            print(f"[ Reminder Check Error ] Failed to read JSON: {e}")
            return "", []

        now = datetime.now()
        missed = []
        updated_file = False

        for r in reminders:
            is_notified = r.get("notified", True)
            title = r.get("title", "Unknown")
            print(f"[ Reminder Check ] Analyzing '{title}'. Notified status: {is_notified}")
            
            if not is_notified:
                date_str = r.get("date_target", now.strftime("%Y-%m-%d"))
                time_str = r.get("time_target", "00:00")
                
                try:
                    target_dt = datetime.strptime(f"{date_str} {time_str.strip()}", "%Y-%m-%d %H:%M")
                    print(f"[ Reminder Check ] Target Time: {target_dt} | Current Time: {now}")
                    
                    if target_dt < now:
                        print(f"[ Reminder Check ] FLAG TRIGGERED: Missed '{title}'!")
                        missed.append(title)
                        r["notified"] = True
                        updated_file = True
                    else:
                        print(f"[ Reminder Check ] Reminder is in the future. Ignoring.")
                except Exception as e:
                    print(f"[ Reminder Parse Error ]: Failed on '{title}': {e}")

        if updated_file:
            try:
                with open(reminder_file, 'w') as f:
                    json.dump(reminders, f, indent=4)
                print("[ Reminder Check ] Successfully updated JSON file.")
            except Exception as e: 
                print(f"[ Reminder Check Error ] Failed to save JSON: {e}")

        if missed:
            if len(missed) == 1:
                spoken = f"Oh, and Sir, while I was offline, you missed a reminder to '{missed[0]}'."
            else:
                missed_str = ', and '.join([f"'{m}'" for m in missed])
                spoken = f"Oh, and Sir, while I was offline, you missed {len(missed)} reminders. They were: {missed_str}."
            return spoken, missed
            
        print("[ Reminder Check ] Scan complete. No missed reminders found.")
        return "", []
    


    def _get_friendly_date(self, date_str):
        if not date_str: return ""
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        diff = (target_date - today).days

        if diff == 0: return "today"
        if diff == 1: return "tomorrow"
        if 1 < diff < 7: return f"this {target_date.strftime('%A')}"
        if 7 <= diff < 14: return f"next {target_date.strftime('%A')}"
        return f"on {target_date.strftime('%B %d')}"
    
    # THE FIX: Added 'prefix' so we can dynamically attach "Understood. " to the front
    async def _enter_sleep_mode(self, prefix=""):
        from voice import global_face, say, bus
        import random
        import asyncio
        from config.dialogue import off_phrases

        global_face.stop_toggle = False 
        
        farewell = prefix + random.choice(off_phrases)
        print(f"Marcus: {farewell}")
        await say(farewell, ui_text=farewell)

        # Reduced from 10.0 to 4.0 so the system closes smoothly after he finishes speaking
        await asyncio.sleep(4.0)

        print("[ Briefing ] Broadcasting visual shutdown signal...")
        await bus.emit("system_shutdown_requested")

    async def _generate_dynamic_greeting(self):
        import datetime
        import requests
        import os
        import asyncio

        # 1. Determine Time of Day
        now = datetime.datetime.now()
        hour = now.hour
        if hour < 12:
            time_str = "morning"
        elif hour < 17:
            time_str = "afternoon"
        else:
            time_str = "evening"

        today_date = now.strftime("%Y-%m-%d")
        greeting = f"Good {time_str} Sir. It is {today_date}."

        # 2. Fetch Environmental Data (Background Thread)
        def fetch_weather_data():
            try:
                # Default fallback is New York if .env is missing
                lat = os.getenv("HOME_LAT", "40.7128")
                lon = os.getenv("HOME_LON", "-74.0060")
                url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                res = requests.get(url, timeout=3).json()
                return res['current_weather']
            except:
                return None

        loop = asyncio.get_running_loop()
        weather = await loop.run_in_executor(None, fetch_weather_data)

        # 3. Build the Context-Aware Phrase
        if weather:
            temp = round(weather['temperature'])
            code = weather['weathercode']
            is_day = weather['is_day'] # 1 for day, 0 for night

            if code == 0:
                condition = "It is clear and sunny outside" if is_day else "We have clear skies tonight"
            elif code in [1, 2, 3]:
                condition = "It is looking a bit cloudy" if is_day else "It is a cloudy night"
            elif code in [45, 48]:
                condition = "Visibility is low due to fog"
            elif code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
                condition = "It is gloomy and raining outside" if is_day else "It is a wet and rainy night"
            elif code in [71, 73, 75, 77]:
                condition = "It is currently snowing"
            elif code in [95, 96, 99]:
                condition = "There is an active thunderstorm"
            else:
                condition = "Conditions are standard"
            
            weather_phrase = f"{condition} at {temp} degrees."
            return f"{greeting} {weather_phrase}"
        
        # Fallback if the internet or API is down
        return greeting