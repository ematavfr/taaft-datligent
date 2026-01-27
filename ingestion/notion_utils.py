import requests
import json
import logging

logger = logging.getLogger(__name__)

class NotionSync:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def create_prompt_page(self, database_id, title, notion_link, description_fr, description_en, tags, publication_date):
        """Creates a new page in the Notion database for a 'Prompt of the Day'."""
        endpoint = "https://api.notion.com/v1/pages"
        
        # Prepare multi-select tags
        notion_tags = [{"name": tag} for tag in tags]
        
        data = {
            "parent": {"database_id": database_id},
            "properties": {
                "Name": {
                    "title": [
                        {"text": {"content": title}}
                    ]
                },
                "Lien Prompt": {
                    "url": notion_link
                },
                "Description (FR)": {
                    "rich_text": [
                        {"text": {"content": description_fr[:2000]}}
                    ]
                },
                "Description (EN)": {
                    "rich_text": [
                        {"text": {"content": description_en[:2000]}}
                    ]
                },
                "Tags": {
                    "multi_select": notion_tags
                },
                "Date": {
                    "date": {"start": publication_date}
                },
                "Source": {
                    "select": {"name": "TAAFT"}
                }
            }
        }
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=data)
            if response.status_code == 200:
                logger.info(f"Successfully synced prompt to Notion: {title}")
                return response.json()
            else:
                logger.error(f"Error syncing to Notion: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception during Notion sync: {e}")
            return None
