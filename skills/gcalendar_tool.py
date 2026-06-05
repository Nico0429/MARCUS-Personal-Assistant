import os.path
import datetime
from typing import List, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError

# If modifying these scopes, delete the file token.json.
# We are starting with 'readonly' so Marcus can't accidentally delete your exams.
SCOPES: List[str] = ['https://www.googleapis.com/auth/calendar.readonly']

class GCalTool:
    def __init__(self) -> None:
        creds = None
        
        # The file token.json stores the user's access and refresh tokens.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
        # If there are no (valid) credentials available, prompt the user to log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError:
                    print("[ System Warning ] Google Calendar Token Expired! Requesting new login...")
                    if os.path.exists('token.json'):
                        os.remove('token.json')
                    creds = None # Force the flow to trigger a new login
            
            # If creds is None (either missing initially, or deleted due to expiry)
            if not creds or not creds.valid:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        self.service = build('calendar', 'v3', credentials=creds, cache_discovery=False)

    def fetch_today_agenda(self) -> List[Dict[str, Any]]:
        """Legacy wrapper to keep existing code safe."""
        return self.fetch_agenda(days_ahead=0)

    def fetch_agenda(self, days_ahead: int = 0, span_days: int = 1) -> List[Dict[str, Any]]:
        """Fetches events using localized day boundaries based on span parameters."""
        try:
            now = datetime.datetime.now()
            target_day = now + datetime.timedelta(days=days_ahead)
            
            start_dt = datetime.datetime(target_day.year, target_day.month, target_day.day, 0, 0, 0)
            if days_ahead == 0:
                start_dt = now
                
            end_target = target_day + datetime.timedelta(days=span_days - 1)
            end_dt = datetime.datetime(end_target.year, end_target.month, end_target.day, 23, 59, 59)

            # Construct explicit local RFC3339 strings
            start_iso = start_dt.astimezone().isoformat()
            end_iso = end_dt.astimezone().isoformat()

            events_result = self.service.events().list(
                calendarId='primary', 
                timeMin=start_iso, 
                timeMax=end_iso,
                maxResults=50, 
                singleEvents=True, 
                orderBy='startTime'
            ).execute()
            
            parsed_events: List[Dict[str, Any]] = []
            for event in events_result.get('items', []):
                start_raw = event['start'].get('dateTime', event['start'].get('date'))
                name = event.get('summary', 'Untitled Event')
                
                if 'T' in start_raw:
                    dt_part, ts_part = start_raw.split('T')
                    date_display = dt_part[5:] # MM-DD
                    time_str = ts_part[:5]
                    time_display = f"{time_str} ({date_display})" if span_days > 1 else time_str
                    
                    # --- Safe ISO parsing without breaking the date string ---
                    try:
                        raw_datetime = datetime.datetime.fromisoformat(start_raw.replace('Z', '+00:00'))
                    except ValueError:
                        raw_datetime = datetime.datetime.now()
                else:
                    time_display = f"All Day ({start_raw[5:]})" if span_days > 1 else "All Day"
                    try:
                        raw_datetime = datetime.datetime.strptime(start_raw, "%Y-%m-%d")
                    except ValueError:
                        raw_datetime = datetime.datetime.now()
                    
                parsed_events.append({
                    'name': name, 
                    'time': time_display,
                    'datetime': raw_datetime
                })
                
            return parsed_events
        except Exception as e:
            print(f"[ Google Calendar API Error ]: {e}")
            return []
        

    def search_event(self, query_text: str, months_ahead: int = 3) -> List[Dict[str, str]]:
        """Searches the calendar for a specific text string (e.g., 'Multivariate')."""
        try:
            now = datetime.datetime.now()
            end_target = now + datetime.timedelta(days=30 * months_ahead)
            
            start_iso = now.astimezone().isoformat()
            end_iso = end_target.astimezone().isoformat()

            events_result = self.service.events().list(
                calendarId='primary', 
                timeMin=start_iso, 
                timeMax=end_iso,
                q=query_text, 
                maxResults=5, 
                singleEvents=True, 
                orderBy='startTime'
            ).execute()
            
            parsed_events: List[Dict[str, str]] = []
            for event in events_result.get('items', []):
                start_raw = event['start'].get('dateTime', event['start'].get('date'))
                name = event.get('summary', 'Untitled Event')
                
                if 'T' in start_raw:
                    dt_part, ts_part = start_raw.split('T')
                    time_display = f"{ts_part[:5]} on {dt_part}"
                else:
                    time_display = f"All Day on {start_raw}"
                    
                parsed_events.append({'name': name, 'time': time_display})
                
            return parsed_events
        except Exception as e:
            print(f"[ Google Calendar Search Error ]: {e}")
            return []

# --- ONE-TIME SETUP SCRIPT ---
if __name__ == '__main__':
    print("Initiating First-Time Google Authentication...")
    tool = GCalTool()
    agenda = tool.fetch_today_agenda()
    
    print("\n--- TEST FETCH: TODAY'S AGENDA ---")
    if not agenda:
        print("Your calendar is completely clear for the rest of the day.")
    else:
        for item in agenda:
            print(f"[{item['time']}] {item['name']}")
    print("----------------------------------")
    print("Setup Complete! A token.json file has been generated.")