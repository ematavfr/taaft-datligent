import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
# NOTE: User mentioned "integration ayant l'ID taaft-prompt et un secret enregistré dans vault."
# I assume NOTION_TOKEN is that secret.

class NotionSync:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def create_page(self, database_id, title, url, description):
        endpoint = "https://api.notion.com/v1/pages"
        data = {
            "parent": {"database_id": database_id},
            "properties": {
                "Name": {
                    "title": [
                        {"text": {"content": title}}
                    ]
                },
                "Link": {
                    "url": url
                },
                "Description": {
                    "rich_text": [
                        {"text": {"content": description[:2000]}} # Notion limit
                    ]
                },
                "Source": {
                    "select": {"name": "TAAFT"}
                }
            }
        }
        
        response = requests.post(endpoint, headers=self.headers, json=data)
        if response.status_code != 200:
            print(f"Error creating Notion page: {response.status_code} - {response.text}")
            return None
        return response.json()

if __name__ == "__main__":
    # Test block or script logic
    token = os.environ.get("NOTION_TOKEN")
    db_id = os.environ.get("NOTION_DATABASE_ID")
    if token and db_id:
        sync = NotionSync(token)
        # sync.create_page(db_id, "Test Prompt", "http://example.com", "Test desc")
        print("NotionSync ready.")
    else:
        print("NOTION_TOKEN or NOTION_DATABASE_ID missing.")
