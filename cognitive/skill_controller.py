"""
================================================================================
FILE: skills/skill_controller.py
ROLE: The Skill Execution Hub
================================================================================
The execution center for all concrete, routed actions. 

When the Semantic Router identifies an intent (e.g., "task_fetch", "news_fetch", 
"app_control"), this controller handles the execution. For tasks that generate 
massive text lists, it utilizes tripwire-safe iterative loops, allowing the 
user to gracefully interrupt the voice engine mid-readout.
================================================================================
"""



import os, re, json, asyncio, requests, random
from ddgs import DDGS
from event_engine import bus
from voice import say, global_face
import config.dialogue as dialogue
import config.triggers as triggers
from skills.notion_tool import NotionTool
from skills.gcalendar_tool import GCalTool
from skills.news_tool import NewsTool
from skills.tools import open_application, close_application
from config.prompts import get_document_open_scrubber_prompt, get_document_open_selector_prompt
from datetime import datetime, timedelta

class SystemExecutor:
    """Centralized handler for all system actions, UI outputs, and global memory logging."""
    def __init__(self, brain):
        self.brain = brain

    async def respond(self, msg):
        global_face.set_thinking(False)
        print(f"Marcus: {msg}")
        if hasattr(self.brain, 'conversation_history'):
            self.brain.conversation_history.append({"role": "Marcus", "content": msg})
        await say(msg)

    async def launch_file_safe(self, file_path):
        try:
            display_name = os.path.basename(file_path)
            msg = f"Right away, Sir. Launching '{display_name}'."
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, os.startfile, file_path)
            await self.respond(msg)
            return True
        except Exception as e:
            print(f"[ System Executor Error ]: {e}")
            await self.respond("Sir, the operating system blocked my attempt to open the file.")
            return False

class SkillController:
    def __init__(self, brain):
        self.brain = brain
        self.executor = SystemExecutor(brain)

    async def handle_app_control(self, query_l):
        clauses = re.split(r'\s+and\s+|\s+then\s+', query_l)
        apps_opened, apps_closed = [], []
        current_action = None 
        loop = asyncio.get_running_loop()
        tasks = []
        
        for clause in clauses:
            clause = clause.strip()
            app_name = ""
            if "open " in clause:
                current_action = "open"
                app_name = clause.split("open ")[-1].strip()
            elif "close " in clause:
                current_action = "close"
                app_name = clause.split("close ")[-1].strip()
            else:
                if current_action: app_name = clause.strip()
            
            app_name = app_name.replace(".", "").replace("?", "").strip()
            if app_name.endswith(" and"): app_name = app_name[:-4].strip()
            if app_name.endswith(" then"): app_name = app_name[:-5].strip()
            
            # --- THE FIX: Parallel execution to prevent sequential micro-blocking ---
            if app_name and current_action:
                if current_action == "open":
                    tasks.append(loop.run_in_executor(None, open_application, app_name))
                    apps_opened.append(app_name)
                elif current_action == "close":
                    tasks.append(loop.run_in_executor(None, close_application, app_name))
                    apps_closed.append(app_name)
        
        if tasks:
            await asyncio.gather(*tasks)
            
        if apps_opened or apps_closed:
            responses = []
            if apps_opened: responses.append(f"opening {', '.join(apps_opened)}")
            if apps_closed: responses.append(f"closing {', '.join(apps_closed)}")
            response_text = "Right away sir, " + " and ".join(responses) + "."
            await self.executor.respond(response_text) 
        return False

    async def handle_task_add(self, query_l):
        print("[ Creating New Task... ]")
        task_content = query_l
        detected_priority = "Medium"
        if "high priority" in task_content or "make it high" in task_content: detected_priority = "High"
        elif "medium priority" in task_content or "make it medium" in task_content: detected_priority = "Medium"
        elif "low priority" in task_content or "make it low" in task_content: detected_priority = "Low"
            
        for p_phrase in triggers.PRIORITY_SCRUBBER_PHRASES: task_content = task_content.replace(p_phrase, "")
        for phrase in triggers.CONVERSATIONAL_FILLER: task_content = task_content.replace(phrase, "")
        
        task_content = task_content.strip()
        if task_content.startswith("to "): task_content = task_content.replace("to ", "", 1)
        if task_content.startswith("and "): task_content = task_content.replace("and ", "", 1)
        if task_content.endswith(" and"): task_content = task_content[:-4]
        if task_content.endswith(" priority"): task_content = task_content[:-9]
        if task_content.endswith(" medium") or task_content.endswith(" high") or task_content.endswith(" low"):
            task_content = task_content.rsplit(' ', 1)[0]
        
        task_name = task_content.strip().capitalize()
        if task_name:
            tool = NotionTool()
            loop = asyncio.get_running_loop()
            success = await loop.run_in_executor(None, lambda: tool.add_task(task_name, priority=detected_priority))
            msg = f"Right away, Sir. I have added '{task_name}' to your assignments with {detected_priority} priority." if success else "Sir, the Notion API rejected the insertion."
        else:
            msg = "Sir, I heard the command to add a task, but I couldn't capture the description."
            
        await self.executor.respond(msg)
        return False

    async def handle_task_update(self, query_l):
        print("[ Updating Task Data... ]")
        tool = NotionTool()
        loop = asyncio.get_running_loop()
        all_tasks = await loop.run_in_executor(None, tool.fetch_tasks)
        
        target_task = None
        for t in all_tasks:
            task_name_clean = t.name.lower()
            if "capital" in query_l and "capita" in task_name_clean: target_task = t; break
            elif any(word in query_l for word in task_name_clean.split() if len(word) > 3): target_task = t; break

        if target_task:
            is_priority = any(w in query_l for w in triggers.PRIORITY_KEYWORDS)
            if is_priority:
                new_priority = "High" if "high" in query_l else "Medium" if "medium" in query_l else "Low"
                success = await loop.run_in_executor(None, lambda: tool.update_task_priority(target_task.task_id, new_priority))
                msg = f"Right away, Sir. I have shifted '{target_task.name}' to {new_priority} priority." if success else "API error."
            else:
                success = await loop.run_in_executor(None, lambda: tool.update_task_status(target_task.task_id, "Done"))
                msg = f"Consider it done, Sir. '{target_task.name}' has been marked as complete." if success else "API error."
        else: msg = "Sir, I couldn't determine which task you wanted to modify."
        
        await self.executor.respond(msg)
        return False

    async def handle_task_fetch(self, query_l):
        print("[ Fetching Task Data... ]")
        tool = NotionTool()
        loop = asyncio.get_running_loop()
        all_tasks = await loop.run_in_executor(None, tool.fetch_tasks)
        
        # Check tripwire after network delay
        if self.brain.interrupt_event.is_set(): return False 

        if "high" in query_l: filtered_tasks, context = [t for t in all_tasks if t.priority == "High"], "HIGH PRIORITY "
        elif "medium" in query_l: filtered_tasks, context = [t for t in all_tasks if t.priority == "Medium"], "MEDIUM PRIORITY "
        elif "low" in query_l: filtered_tasks, context = [t for t in all_tasks if t.priority == "Low"], "LOW PRIORITY "
        else: filtered_tasks, context = all_tasks, "ACTIVE "

        priority_weights = {"High": 1, "Medium": 2, "Low": 3}
        filtered_tasks.sort(key=lambda t: priority_weights.get(getattr(t, 'priority', 'UNASSIGNED') or 'UNASSIGNED', 4))

        if not filtered_tasks:
            await self.executor.respond(f"Sir, your {context.lower().strip()} queue is currently clear.")
            return True

        speak_lines = []
        bullet_points = [f"\n:: {context.strip()} DIRECTIVES ::", "========================================"]
        for idx, t in enumerate(filtered_tasks, 1):
            priority_val = getattr(t, 'priority', 'UNASSIGNED') or 'UNASSIGNED'
            bullet_points.append(f" [◈] DIRECTIVE {idx:02d} : {t.name.upper()}\n    └─ PRIORITY : {priority_val.upper()}\n")
            speak_lines.append(f"{t.name}, priority {priority_val}" if priority_val != 'UNASSIGNED' else t.name)
        bullet_points.append("========================================")
        
        task_list_speak = speak_lines[0] if len(speak_lines) == 1 else (f"{speak_lines[0]}, and {speak_lines[1]}" if len(speak_lines) == 2 else ", ".join(speak_lines[:-1]) + f", and {speak_lines[-1]}")
        msg_intro = f"Sir, your {context.lower().strip()} tasks are:"

        global_face.set_thinking(False)
        
        # Last check before he locks up the audio driver with a 30-second list of tasks
        if not self.brain.interrupt_event.is_set():
            await say(f"{msg_intro} {task_list_speak}.", ui_text=f"{msg_intro}\n{chr(10).join(bullet_points)}")
            
        return True

    async def handle_shopping_add(self, query_l):
        print("[ Adding to Shopping List... ]")
        item_content = query_l
        for trigger in triggers.SHOPPING_ADD_TRIGGERS: item_content = item_content.replace(trigger, "")
        for phrase in triggers.CONVERSATIONAL_FILLER: item_content = item_content.replace(phrase, "")
        item_content = item_content.replace("to the", "").replace("some ", "").strip().capitalize()
        
        if item_content:
            tool = NotionTool()
            success = await asyncio.get_running_loop().run_in_executor(None, lambda: tool.add_shopping_item(item_content))
            msg = f"Right away, Sir. I have added '{item_content}' to your supply requisitions." if success else "Notion API rejected the insertion."
        else: msg = "Sir, I couldn't capture the item."
        await self.executor.respond(msg)
        return False

    async def handle_shopping_fetch(self, query_l):
        print("[ Fetching Shopping Data... ]")
        tool = NotionTool()
        items = await asyncio.get_running_loop().run_in_executor(None, tool.fetch_shopping_list)

        # Check tripwire after network delay
        if self.brain.interrupt_event.is_set(): return False 

        if not items:
            await self.executor.respond("Sir, your supply requisition list is currently empty.")
            return True

        speak_lines = []
        bullet_points = ["\n:: SUPPLY REQUISITIONS ::", "========================================"]
        for idx, item in enumerate(items, 1):
            bullet_points.append(f" [◈] ITEM {idx:02d} : {item.name.upper()}")
            speak_lines.append(item.name)
        bullet_points.append("========================================")
        
        items_speak = speak_lines[0] if len(speak_lines) == 1 else (f"{speak_lines[0]}, and {speak_lines[1]}" if len(speak_lines) == 2 else ", ".join(speak_lines[:-1]) + f", and {speak_lines[-1]}")
        
        # --- ADD IT RIGHT HERE ---
        # Unlock the mic so the Wake Word can hear you while he reads the list!
        from voice import global_face
        global_face.set_thinking(False)
        # -------------------------

        # Last check before he speaks
        if not self.brain.interrupt_event.is_set():
            await say(f"Sir, you currently need to purchase: {items_speak}.", ui_text="\n".join(bullet_points))
            
        return True

    async def handle_calendar_fetch(self, query_l=""):
        span_days, days_ahead, timeframe_label = 1, 0, "today"
        if "next week" in query_l: days_ahead, span_days, timeframe_label = 7, 7, "next week"
        elif "tomorrow" in query_l: days_ahead, span_days, timeframe_label = 1, 1, "tomorrow"
        elif "week" in query_l: span_days, timeframe_label = 7, "this week"
        elif "month" in query_l: span_days, timeframe_label = 30, "this month"

        loop = asyncio.get_running_loop()
        cal_tool, notion_tool = GCalTool(), NotionTool()

        cal_task = loop.run_in_executor(None, lambda: cal_tool.fetch_agenda(days_ahead=days_ahead, span_days=span_days))
        tasks_task = loop.run_in_executor(None, notion_tool.fetch_tasks)
        cal_events, active_tasks = await asyncio.gather(cal_task, tasks_task)

        bullet_points = [f"\n:: EXECUTIVE DASHBOARD ({timeframe_label.upper()}) ::", "========================================"]
        if cal_events:
            bullet_points.append(" [◈] CALENDAR TIMELINE:")
            for e in cal_events: bullet_points.append(f"     └─ {e['time']} : {e['name']}")
        else: bullet_points.append(" [◈] CALENDAR: No scheduled events.")

        now = datetime.now()
        start_boundary = now + timedelta(days=days_ahead)
        end_boundary = start_boundary + timedelta(days=span_days)
        dated_tasks, undated_high_priority = [], []

        for t in active_tasks:
            task_date = getattr(t, 'date', getattr(t, 'due_date', getattr(t, 'deadline', getattr(t, 'due', None))))
            if task_date:
                if isinstance(task_date, str):
                    try: task_date = datetime.fromisoformat(task_date.split('T')[0])
                    except: continue
                if isinstance(task_date, datetime): task_date = task_date.date()
                if start_boundary.date() <= task_date <= end_boundary.date(): dated_tasks.append((task_date, t))
            elif getattr(t, 'priority', 'Medium') == 'High': undated_high_priority.append(t)

        dated_tasks.sort(key=lambda item: item[0])
        if dated_tasks:
            bullet_points.append("\n [◈] ACTIONABLE DEADLINES:")
            for task_date, t in dated_tasks:
                bullet_points.append(f"     └─ [{task_date.strftime('%m-%d')}] {t.name.upper()} ({getattr(t, 'priority', 'Medium')})")
        if undated_high_priority and span_days > 1:
            bullet_points.append("\n [◈] ONGOING HIGH PRIORITY DIRECTIVES:")
            for t in undated_high_priority: bullet_points.append(f"     └─ [O] {t.name.upper()}")

        bullet_points.append("========================================")
        ui_string = "\n".join(bullet_points)
        
        if not cal_events and not dated_tasks and not undated_high_priority:
            await say(f"Sir, your agenda and task directives are completely clear for {timeframe_label}.", ui_text=ui_string)
        else:
            await say(f"Sir, I have updated your terminal with your executive summary for {timeframe_label}.", ui_text=ui_string)
        return False

    async def handle_custom_reminder(self, query_l):
        import re
        from datetime import datetime, timedelta
        print("[ Extracting Ad-Hoc Voice Reminder... ]")
        
        # 1. Smarter Regex: Matches "10:30", "10.30", "10 am", or just plain "10"
        time_match = re.search(r'(at|for)\s+(\d{1,2}[:.]\d{2}|\d{1,2}\s*(am|pm)?)', query_l)
        if not time_match:
            await self.executor.respond("Sir, I caught the directive to add a reminder, but I couldn't discern a target time format.")
            return False
            
        raw_time_string = time_match.group(2).replace('.', ':').strip().lower()
        has_am_pm = "am" in raw_time_string or "pm" in raw_time_string
        
        # --- TIME NORMALIZER ---
        if ":" not in raw_time_string:
            if has_am_pm:
                raw_time_string = raw_time_string.replace(" am", ":00 am").replace(" pm", ":00 pm").replace("am", ":00 am").replace("pm", ":00 pm")
            else:
                raw_time_string = f"{int(raw_time_string):02d}:00"

        try:
            if has_am_pm:
                parsed_time = datetime.strptime(raw_time_string, "%I:%M %p")
            else:
                parsed_time = datetime.strptime(raw_time_string, "%H:%M")
                
            # --- THE TEMPORAL AWARENESS FIX ---
            now = datetime.now()
            # Combine today's date with the parsed time
            target_dt = datetime.combine(now.date(), parsed_time.time())
            
            if target_dt < now:
                # If you didn't say AM/PM and it's a morning hour (e.g., "5"), try making it PM
                if not has_am_pm and target_dt.hour < 12:
                    potential_pm = target_dt + timedelta(hours=12)
                    if potential_pm > now:
                        target_dt = potential_pm
                
                # If the time is STILL in the past (e.g., you said "2" but it's 4 PM, so 14:00 is also passed)
                # OR you explicitly said an AM/PM time that has passed today, bump to tomorrow.
                if target_dt < now:
                    target_dt = target_dt + timedelta(days=1)
            
            final_time_string = target_dt.strftime("%H:%M")
            final_date_string = target_dt.strftime("%Y-%m-%d")
            
        except Exception as e:
            print(f"[ Time Parse Error ]: {e}")
            final_time_string = raw_time_string # Fallback just in case
            final_date_string = datetime.now().strftime("%Y-%m-%d")

        # 2. Extract Body & Fix Double Spaces
        reminder_body = query_l.replace(time_match.group(0), "").strip()
        reminder_body = re.sub(r'\s+', ' ', reminder_body)
        
        # 3. Aggressive Conversational Prefix Scrubber
        prefixes = [
            "can you set a reminder to", "can you set a reminder for", "can you remind me to", 
            "can you remind me about", "please remind me to", "remind me to", 
            "remind me about", "set a reminder to", "set a reminder for", 
            "can you set a", "please set a", "set a", "can you", "please", "i need to",
            "a reminder to", "reminder to"
        ]
        
        for prefix in prefixes:
            if reminder_body.startswith(prefix):
                reminder_body = reminder_body[len(prefix):].strip()
                
        # 4. Final cleanup for dangling words
        if reminder_body.startswith("to "): reminder_body = reminder_body[3:].strip()
        if reminder_body.startswith("about "): reminder_body = reminder_body[6:].strip()
        if reminder_body.endswith(" reminder"): reminder_body = reminder_body[:-9].strip()
        if reminder_body.endswith(" at"): reminder_body = reminder_body[:-3].strip()
        
        reminder_title = reminder_body.capitalize()
        if not reminder_title:
            reminder_title = "General Alert"
            
        def save_reminder_sync():
            import os, json
            reminder_file = "local_reminders.json"
            reminders_list = []
            if os.path.exists(reminder_file):
                try:
                    with open(reminder_file, 'r') as f: reminders_list = json.load(f)
                except: pass
            
            # Save using the smartly calculated time AND date
            reminders_list.append({
                "title": reminder_title, 
                "time_target": final_time_string,
                "date_target": final_date_string,  # <-- Using the calculated date
                "notified": False,
                "notified_30m": False,
                "notified_now": False
            })
            with open(reminder_file, 'w') as f: json.dump(reminders_list, f, indent=4)

        await asyncio.get_running_loop().run_in_executor(None, save_reminder_sync)
        
        # Let's make his response confirm if it's tomorrow so you know he caught it
        day_str = "tomorrow" if final_date_string != datetime.now().strftime("%Y-%m-%d") else "today"
        await self.executor.respond(f"Understood Sir. Mental coordinate locked: I will remind you to '{reminder_title}' at precisely {final_time_string} {day_str}.")
        return False
    
    async def handle_cancel_reminder(self, query_l):
        import json, os, re
        
        print("[ Canceling Ad-Hoc Voice Reminder... ]")
        reminder_file = "local_reminders.json"
        
        if not os.path.exists(reminder_file):
            await self.executor.respond("Sir, you currently have no active reminders to cancel.")
            return False

        try:
            with open(reminder_file, 'r') as f:
                reminders_list = json.load(f)
        except Exception as e:
            print(f"[ Reminder Parse Error ]: {e}")
            await self.executor.respond("Sir, I encountered an error reading the neural database.")
            return False

        if not reminders_list:
            await self.executor.respond("Sir, your reminder queue is already empty.")
            return False

        # 1. Clean the query to isolate the target subject
        clean_query = query_l.lower()
        for word in ["cancel", "delete", "remove", "that", "the", "reminder", "about", "to"]:
            clean_query = re.sub(rf'\b{word}\b', '', clean_query)
        clean_query = clean_query.strip()

        # 2. Score matches based on overlapping words
        best_match_index = -1
        highest_overlap = 0
        query_words = set(clean_query.split())

        for i, rem in enumerate(reminders_list):
            title_lower = rem.get("title", "").lower()
            title_words = set(title_lower.split())
            
            # Direct subset match (e.g., "send a temp" is in "send a temp")
            if clean_query and (clean_query in title_lower or title_lower in clean_query):
                best_match_index = i
                break
                
            # Fallback: Count word overlap
            overlap = len(query_words.intersection(title_words))
            if overlap > highest_overlap:
                highest_overlap = overlap
                best_match_index = i

        # 3. Execute Deletion
        if best_match_index != -1:
            removed = reminders_list.pop(best_match_index)
            with open(reminder_file, 'w') as f:
                json.dump(reminders_list, f, indent=4)
            await self.executor.respond(f"Done, Sir. I have stricken the reminder for '{removed['title']}' from my active memory.")
        else:
            await self.executor.respond("Sir, I couldn't find a matching reminder in your queue. Please check the exact phrasing.")
            
        return False

        
    async def handle_event_search(self, query_l):
        prompt = (f"Extract the specific event, class, or task the user is looking for: '{query_l}'. "
                  f"Return ONLY the core search term. No filler.")
        search_term = await self.brain.llm.generate(prompt, agent_role="researcher", routing="groq")
        search_term = search_term.strip(' "\'\n').lower()
        print(f"[ Agenda Search ] Scanning databases for '{search_term}'...")
        
        loop = asyncio.get_running_loop()
        cal_events = await loop.run_in_executor(None, lambda: GCalTool().search_event(search_term))
        active_tasks = await loop.run_in_executor(None, NotionTool().fetch_tasks)
        
        matched_tasks = []
        for t in active_tasks:
            if search_term in t.name.lower() or any(word in t.name.lower() for word in search_term.split() if len(word) > 4):
                task_date = getattr(t, 'date', getattr(t, 'due_date', getattr(t, 'deadline', getattr(t, 'due', None))))
                matched_tasks.append(f"Task directive '{t.name}' due on {task_date if task_date else 'Ongoing'}.")

        if not cal_events and not matched_tasks:
            await self.executor.respond(f"Sir, I scanned your records, but I couldn't find any upcoming entries matching '{search_term}'.")
            return False
            
        results = [f"Calendar: '{e['name']}' at {e['time']}." for e in cal_events] + matched_tasks
        speech_prompt = f"Answer concisely and professionally based on this data: {' '.join(results)}. Just state the date and time."
        
        global_face.set_thinking(True)
        final_msg = await self.brain.llm.generate(speech_prompt, agent_role="butler", routing="groq")
        global_face.set_thinking(False)
        await self.executor.respond(final_msg)
        return False

    async def handle_news_fetch(self, query_l):
        print("[ Accessing News Networks & Financial Markets... ]")
        try:
            tool = NewsTool()
            loop = asyncio.get_running_loop()
            topic = "Artificial Intelligence OR Politics" if query_l == "ai and politics" else "general"
            if any(t in query_l for t in triggers.NEWS_TECH): topic = "technology"
            elif any(t in query_l for t in triggers.NEWS_SPORT): topic = "sports"

            market_task = loop.run_in_executor(None, tool.fetch_markets)
            news_task = loop.run_in_executor(None, lambda: tool.fetch_daily_news(topic))
            markets, articles = await asyncio.gather(market_task, news_task)
            
            if not articles:
                await self.executor.respond(random.choice(dialogue.NEWS_ERROR))
                return True

            global_face.set_thinking(False)
            intro_msg = random.choice(dialogue.NEWS_GATHERING) + (markets or "")
            await say(intro_msg, ui_text=intro_msg)
            
            # Use the tripwire as the sleep mechanism. If pulled early, it aborts immediately.
            try: await asyncio.wait_for(self.brain.interrupt_event.wait(), timeout=2.0)
            except asyncio.TimeoutError: pass
            if self.brain.interrupt_event.is_set(): return False # <--- TRIPWIRE CHECK

            previous_type = None
            for article in articles:
                # <--- TRIPWIRE CHECK AT START OF EVERY LOOP
                if self.brain.interrupt_event.is_set():
                    print("[ System ] News readout aborted by user.")
                    break 

                image_path = "temp_news_img.jpg"
                if os.path.exists(image_path):
                    try: os.remove(image_path)
                    except: pass

                if article.get('image_url'):
                    try:
                        def _fetch_and_save(url, path):
                            data = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).content
                            with open(path, 'wb') as f: f.write(data)
                        await loop.run_in_executor(None, _fetch_and_save, article['image_url'], image_path)
                    except: pass

                intro = random.choice(dialogue.NEWS_MINOR_TRANSITIONS) if article['type'] == previous_type else (
                    random.choice(dialogue.NEWS_LOCAL_INTROS) if article['type'] == 'Local' else 
                    random.choice(dialogue.NEWS_TOPIC_INTROS).format(topic=topic) if topic != "general" else 
                    random.choice(dialogue.NEWS_GLOBAL_INTROS)
                )
                
                previous_type = article['type']
                spoken_text = f"{intro} {article['title']}. {article['description']}".strip()
                await bus.emit("show_news_ui", {"title": article['title'], "image": image_path if os.path.exists(image_path) else ""})
                
                ui_text = f"\n:: {article['type'].upper()} NEWS ::\n===================\n[{article['title']}]\n\n{article['description']}\n==================="
                await say(spoken_text, ui_text=ui_text)
                
                try: await asyncio.wait_for(self.brain.interrupt_event.wait(), timeout=(len(spoken_text.split()) / 2.5) + 1.5)
                except asyncio.TimeoutError: pass

            if os.path.exists("temp_news_img.jpg"):
                try: os.remove("temp_news_img.jpg")
                except: pass
            await bus.emit("close_news_ui")
            
            # Only say closing line if he wasn't interrupted
            if not self.brain.interrupt_event.is_set():
                await self.executor.respond(random.choice(dialogue.NEWS_CLOSING))
            return False # Let the chain manager end cleanly
            
        except Exception as e:
            await self.executor.respond("I encountered a critical error while processing the news feed.")
            return True

    async def handle_web_search(self, raw_query, query_l):
        print("[ Waking Web Researcher Agent... ]")
        clean_query = query_l
        for word in triggers.WEB_SEARCH_SCRUBBERS: clean_query = clean_query.replace(word, "").strip()
        scraped_data = await asyncio.get_running_loop().run_in_executor(None, lambda: list(DDGS().text(clean_query or query_l, max_results=4)))
        
        snippets = "\n".join([f"[{r.get('title')}] {r.get('body')}" for r in scraped_data]) if isinstance(scraped_data, list) else "Search failed."
        prompt = f"The user asked: '{raw_query}'. Answer directly based ONLY on this web data: {snippets}."
        
        msg = await self.brain.llm.generate(prompt, agent_role="researcher", routing="groq")
        global_face.set_thinking(False)
        await self.executor.respond(msg)
        return True

    async def handle_ui_control(self, query_l):
        action = "open" if any(w in query_l for w in ["open", "show", "view", "bring up"]) else "close"
        target, spoken_name = ("matrix", "Neural Matrix") if any(w in query_l for w in ["matrix", "brain", "graph", "memory"]) else (
            ("terminal", "Main Terminal") if any(w in query_l for w in ["terminal", "console", "hud"]) else ("unknown", "interface")
        )
        if target != "unknown":
            await bus.emit("ui_window_control", {"target": target, "action": action})
            await self.executor.respond(f"{'Rendering' if action == 'open' else 'Hiding'} the {spoken_name}, Sir.")
        else:
            await self.executor.respond("Sir, I am unsure which interface panel you are referring to.")
        return False

    async def handle_help(self):
        print("[ System ] Generating Protocol List...")
        bullet_points = ["\n:: SYSTEM PROTOCOLS ::", "========================"]
        try:
            from config.prompts import AGENT_TOOLS
            for tool in AGENT_TOOLS:
                bullet_points.append(f" [◈] {tool['name'].replace('_', ' ').upper()}\n    └─ Action : {tool['description']}\n")
        except Exception as e: bullet_points.append(f" [!] Error reading matrix: {e}")
        bullet_points.extend([" [◈] MANUAL OVERRIDES\n    └─ Commands : \"/help\", \"/rebuild\"\n", "========================"])
        
        await say("Sir, I have dynamically mapped the current system protocols to your terminal.", ui_text="\n".join(bullet_points))
        return False
    
    async def handle_timer(self, query):
        import re
        q = query.lower().strip()
        timer = self.brain.timer_skill
        
        # 1. Action Intercepts
        if any(w in q for w in ["stop", "cancel", "end", "kill"]):
            return await timer.stop_timer_protocol(ui_triggered=False)
            
        if any(w in q for w in ["pause", "hold"]):
            return await timer.toggle_pause(is_voice=True)
            
        if any(w in q for w in ["resume", "continue", "unpause"]):
            # If paused, toggle it back on
            if timer.timer_paused:
                await timer.toggle_pause(is_voice=True)
            return True
            
        if any(w in q for w in ["skip", "fast forward"]):
            return await timer.skip_timer()
            
        if "go back" in q or "subtract" in q or "remove" in q:
            match = re.search(r'(\d+)', q)
            mins = float(match.group(1)) if match else 5
            return await timer.modify_time(-mins)
            
        if "add" in q or "extend" in q:
            match = re.search(r'(\d+)', q)
            mins = float(match.group(1)) if match else 5
            return await timer.modify_time(mins)

        # 2. Initialization Fallback (Extract numbers and task name)
        mins_match = re.search(r'(\d+)', q)
        minutes = float(mins_match.group(1)) if mins_match else 25
        task_name = "Focus Session"
        
        if "for " in q:
            parts = q.split("for ")
            if len(parts) > 1:
                clean_task = re.sub(r'\b(minutes?|mins?|timer|start|set)\b', '', parts[-1]).strip()
                if clean_task: task_name = clean_task.title()
                
        return await timer.execute_timer_protocol(minutes, task_name)
    
    async def handle_media(self, query):
        q = query.lower()
        command = "hide" if any(w in q for w in ["close", "hide", "dismiss"]) else (
            "show" if any(w in q for w in ["show", "bring up"]) else 
            "next" if any(w in q for w in ["next", "skip"]) else 
            "prev" if any(w in q for w in ["previous", "prev"]) else "play"
        )
        return await self.brain.media_skill.execute_media_command(command)
    
    async def handle_telemetry(self, query_l):
        from skills.visual_tool import generate_telemetry
        await self.executor.respond("Pulling core system telemetry, Sir.")
        telemetry_block = await generate_telemetry()
        await bus.emit("user_spoken_text", f"\n{telemetry_block}")
        await self.executor.respond("Diagnostic complete.")
        return False

    async def handle_deep_work(self, query_l):
        import pyautogui
        await self.executor.respond("Initiating Deep Work Protocol. Clearing workspace and entering silent mode.")
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, pyautogui.hotkey, 'win', 'd')
        await asyncio.sleep(0.5)

        prompt = f"Extract the target study focus task topic from: '{query_l}'. Return ONLY the task name or 'None'."
        focus_task = await self.brain.llm.generate(prompt, agent_role="researcher", routing="groq")
        task_name = focus_task.strip(' "\'\n').title() if focus_task.strip().lower() != "none" else "Deep Work Session"

        ui_display = f"\n:: DEEP WORK ACTIVE ::\n====================\n [◈] TARGET : {task_name.upper()}\n [◈] DURATION : 45 MINS\n====================\n"
        await bus.emit("user_spoken_text", ui_display)
        
        await loop.run_in_executor(None, open_application, "apple music")
        
        await bus.emit("ui_window_control", {"target": "terminal", "action": "close"})
        await bus.emit("sync_mute_state", {"muted": True}) 
        
        # --- NEW: Sever the microphone feed and update the UI ---
        await bus.emit("mic_mute_control", {"muted": True})
        await bus.emit("sync_mic_state", {"muted": True})

        await self.brain.timer_skill.execute_timer_protocol(45, task_name)



        async def delayed_media_boot():
            await asyncio.sleep(3.5)
            await self.brain.media_skill.execute_media_command("show")
        asyncio.create_task(delayed_media_boot())
        return False
    
    async def handle_document_search(self, query_l):
        print(f"[ Document Engine ] Searching archives for: '{query_l}'...")
        global_face.set_thinking(True)
        context = await asyncio.get_running_loop().run_in_executor(None, lambda: self.brain.vector_db.search_documents(query_l, top_k=3))
        
        if not context:
            global_face.set_thinking(False)
            await self.executor.respond("Sir, I scanned your local archives, but I couldn't find any relevant data.")
            return False
            
        match = re.search(r"Source File \((.*?)\):", context)
        self.brain.last_cited_filepath = match.group(1).strip() if match else None
        display_name = os.path.basename(self.brain.last_cited_filepath) if self.brain.last_cited_filepath else "Unknown Document"

        prompt = (f"The user asked: '{query_l}'. Answer concisely using ONLY these document excerpts:\n{context}\n"
                  f"End naturally by mentioning you sourced this from '{display_name}'.")
        response_text = await self.brain.llm.generate(prompt, agent_role="researcher", routing="cloud")
        global_face.set_thinking(False)
        await self.executor.respond(response_text)
        return False
    
    async def handle_document_open(self, query_l):
        print("[ Document Engine ] Attempting Hybrid Semantic-Lexical mapping...")
        target_path = None
        loop = asyncio.get_running_loop()
        
        if any(t in query_l for t in ["open that", "open it", "open the file"]) and getattr(self.brain, 'last_cited_filepath', None):
            target_path = self.brain.last_cited_filepath
        else:
            global_face.set_thinking(True)
            
            kg_context = await loop.run_in_executor(None, self.brain.memory.retrieve_context, query_l)
            transcript = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.brain.conversation_history[-4:]]) if self.brain.conversation_history else "No context."
            
            clean_prompt = get_document_open_scrubber_prompt(self.brain, query_l, transcript, kg_context)
            
            # --- THE FIX: Using Gemini (Cloud) for complex keyword extraction ---
            search_target = await self.brain.llm.generate(clean_prompt, agent_role="researcher", routing="cloud")
            search_words = [w.lower().strip() for w in search_target.split() if len(w) > 2]
            search_string = " ".join(search_words)
            print(f"[ Debug ] Hybrid Search Keywords: '{search_string}'")
            
            def fetch_hybrid_paths():
                paths = set()
                try:
                    context = self.brain.vector_db.search_documents(search_string, top_k=15)
                    if context: paths.update(re.findall(r"Source File \((.*?)\):\n", context))
                except Exception as e: print(f"[ Semantic Fetch Error ]: {e}")
                try:
                    if os.path.exists("neural_index_state.json"):
                        with open("neural_index_state.json", "r") as f: ledger_paths = list(json.load(f).keys())
                        scored_paths = [(sum(1 for w in search_words if w in p.lower()), p) for p in ledger_paths]
                        scored_paths.sort(key=lambda x: x[0], reverse=True)
                        paths.update([p[1] for p in scored_paths[:15] if p[0] > 0])
                except Exception as e: print(f"[ Lexical Fetch Error ]: {e}")
                return list(paths)[:30]

            unique_paths = await loop.run_in_executor(None, fetch_hybrid_paths)
            if unique_paths:
                paths_str = "\n".join(unique_paths)
                prompt = get_document_open_selector_prompt(self.brain, query_l, transcript, kg_context, paths_str)
                
                # --- THE FIX: Using Gemini (Cloud) for complex path deduction ---
                final_target = await self.brain.llm.generate(prompt, agent_role="researcher", routing="cloud")
                final_target = final_target.strip(' "\'\n')
                if final_target != "NONE" and os.path.exists(final_target): target_path = final_target
            global_face.set_thinking(False)

        if not target_path or not os.path.exists(target_path):
            await self.executor.respond("Sir, I couldn't logically map that request to a specific document on your drive.")
            return False
            
        await self.executor.launch_file_safe(target_path)
        return False