import os
import requests
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

class UniversityTask:
    def __init__(self, task_id, name, due, priority, status):
        self.task_id = task_id  # Needed to perform updates
        self.name = name
        self.due = due
        self.priority = priority
        self.status = status

class NotionTool:
    def __init__(self):
        # 1. Load your API tokens and Database IDs
        self.api_token = os.getenv("NOTION_TOKEN")
        self.notion = Client(auth=self.api_token)
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        self.shopping_db_id = os.getenv("NOTION_SHOPPING_DB_ID")
        
        # 2. Define the shared security headers for all raw requests
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def fetch_tasks(self):
        try:
            response = self.notion.databases.query(database_id=self.database_id)
            results = response.get("results", [])
            tasks = []

            for row in results:
                # Capture the unique ID for this specific row/page
                task_id = row.get("id")
                props = row.get("properties", {})

                if not props: continue
                
                # 1. Get Status
                status_prop = props.get("Status", {})
                status_obj = status_prop.get("status") or status_prop.get("select") or {}
                status_name = status_obj.get("name", "To Do")
                if status_name.lower() == "done": continue

                # 2. Get Subject (Title)
                subject_prop = props.get("Subject", {})
                title_list = subject_prop.get("title", [])
                name = title_list[0].get("plain_text", "Untitled") if title_list else "Untitled"

                # 3. Get Priority
                priority_prop = props.get("Priority", {})
                priority_obj = priority_prop.get("select") or {}
                priority = priority_obj.get("name", "Low")

                # 4. Get Due Date
                date_prop = props.get("Due date", {})
                date_obj = date_prop.get("date") or {}
                due = date_obj.get("start", "")

                # Now passing the task_id and status to the object
                tasks.append(UniversityTask(task_id, name, due, priority, status_name))

            return tasks
        except Exception as e:
            print(f"Notion Fetch Error: {e}")
            return []

    def update_task_status(self, task_id, status):
        """Updates only the Status of a task in the Notion database."""
        payload = {
            "Status": {"status": {"name": status}}
        }

        try:
            self.notion.pages.update(
                page_id=task_id,
                properties=payload
            )
            print(f"Notion API: Successfully updated status to '{status}' for task {task_id}")
            return True
        except Exception as e:
            print(f"Notion API Status Update Error: {e}")
            return False

    def update_task_priority(self, task_id, priority):
        """Updates only the Priority of a task in the Notion database."""
        payload = {
            "Priority": {"select": {"name": priority}}
        }

        try:
            self.notion.pages.update(
                page_id=task_id,
                properties=payload
            )
            print(f"Notion API: Successfully updated priority to '{priority}' for task {task_id}")
            return True
        except Exception as e:
            print(f"Notion API Priority Update Error: {e}")
            return False
    
    def add_task(self, task_name, priority="Medium"):
        """Creates a new task in your Notion Database."""
        try:
            payload = {
                "parent": {"database_id": self.database_id},
                "properties": {
                    "Subject": {
                        "title": [
                            {"text": {"content": task_name}}
                        ]
                    },
                    "Priority": {
                        "select": {"name": priority}
                    },
                    "Status": {
                        "status": {"name": "Not started"} 
                    }
                }
            }
            
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=self.headers, 
                json=payload
            )
            
            if response.status_code != 200:
                print(f"[ Notion API Error ]: {response.text}")
                
            return response.status_code == 200
            
        except Exception as e:
            print(f"[ Notion API Error ]: {e}")
            return False
        
    def add_shopping_item(self, item_name):
        """Adds a new item to the shopping list database."""
        url = "https://api.notion.com/v1/pages"
        data = {
            "parent": {"database_id": self.shopping_db_id},
            "properties": {
                "Name": {"title": [{"text": {"content": item_name}}]},
                "Status": {"status": {"name": "Need to buy"}}
            }
        }
        response = requests.post(url, headers=self.headers, json=data)
        return response.status_code == 200

    def fetch_shopping_list(self):
        """Fetches all items that currently need to be bought."""
        url = f"https://api.notion.com/v1/databases/{self.shopping_db_id}/query"
        payload = {
            "filter": {
                "property": "Status",
                "status": {"equals": "Need to buy"}
            }
        }
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code != 200:
            print(f"[ Notion API Error ]: {response.text}")
            return []
            
        results = response.json().get("results", [])
        items = []
        for r in results:
            props = r.get("properties", {})
            name_list = props.get("Name", {}).get("title", [])
            name = name_list[0].get("plain_text", "Unnamed") if name_list else "Unnamed"
            # Create a quick dynamic object to hold the data
            items.append(type('obj', (object,), {'name': name, 'item_id': r['id']}))
            
        return items