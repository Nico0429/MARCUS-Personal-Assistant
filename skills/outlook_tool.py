import datetime
import win32com.client
import pythoncom

class OutlookTool:
    def __init__(self):
        pass

    def fetch_today_agenda(self):
        """Reaches into the local Outlook desktop app to read today's schedule."""
        try:
            print("[ OutlookTool ] Linking to local Outlook engine...")
            
            # 1. Initialize COM for the current thread (Prevents thread-crashing)
            pythoncom.CoInitialize()
            
            # 2. Try to hook into an already-running Outlook first
            try:
                app = win32com.client.GetActiveObject("Outlook.Application")
            except Exception:
                # If it's closed, force it to dispatch a new background process
                app = win32com.client.Dispatch("Outlook.Application")
                
            # 3. Access the data
            namespace = app.GetNamespace("MAPI")
            calendar = namespace.GetDefaultFolder(9) # 9 = Calendar
            appointments = calendar.Items
            
            # 4. Handle recurring events 
            appointments.IncludeRecurrences = True
            appointments.Sort("[Start]")
            
            # 5. Define the boundaries for "Today"
            today = datetime.datetime.now()
            begin = today.strftime("%m/%d/%Y 12:00 AM")
            end = today.strftime("%m/%d/%Y 11:59 PM")
            
            restricted_items = appointments.Restrict(f"[Start] >= '{begin}' AND [Start] <= '{end}'")
            
            parsed_events = []
            for event in restricted_items:
                if getattr(event, 'AllDayEvent', False):
                    time_str = "All Day"
                else:
                    time_str = event.Start.strftime("%H:%M")
                    
                parsed_events.append({
                    'name': event.Subject,
                    'time': time_str,
                    'raw_time': event.Start
                })
                
            # 6. Sort chronologically
            parsed_events.sort(key=lambda x: x['raw_time'])
            
            for e in parsed_events:
                del e['raw_time']
                
            return parsed_events

        except Exception as e:
            print(f"[ Local Outlook Error ]: {e}")
            return []