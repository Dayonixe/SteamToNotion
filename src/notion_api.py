from typing import List, Dict, Optional, Any
import requests
import json
from dotenv import load_dotenv
import os
from .steam_api import search_app_id_by_name

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

notion_headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def get_app_id_for_page(page: Dict[str, Any]) -> Optional[int]:
    """
    Retrieves the Steam AppID from a Notion page.

    Priority:
    1. If the 'ID' property already contains a valid number -> use it.
    2. Otherwise, retrieve the name ('Name') and perform a Steam search.

    :param page: Page object Notion from the API

    :return: Steam AppID or None if not found
    """
    id_prop = page["properties"].get("ID")

    # 1. If 'ID' present and valid
    if id_prop and id_prop["number"]:
        return id_prop["number"]

    # 2. Otherwise, search via 'Name'
    name_prop = page["properties"].get("Name", {})
    if "title" in name_prop and len(name_prop["title"]) > 0:
        game_name = name_prop["title"][0]["plain_text"]
        app_id = search_app_id_by_name(game_name)
        if app_id:
            print(f"📥 Found app_id = {app_id} via name '{game_name}'")
            return app_id
        else:
            print(f"❌ No app_id found for '{game_name}'")

    return None


def get_notion_pages() -> List[Dict[str, Any]]:
    """
    Retrieves all pages from a Notion database (including pagination).

    :return: Complete list of pages in the database
    """
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    all_results = []
    payload = {}

    while True:
        response = requests.post(url, headers=notion_headers, json=payload).json()

        all_results.extend(response["results"])

        if not response.get("has_more"):
            break

        payload["start_cursor"] = response["next_cursor"]

    return all_results


def update_notion_page(page_id: str, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Updates a Notion page with information about a game.

    :param page_id: Notion page ID
    :param game: Complete game data (Steam + estimated HLTB)

    :return: JSON response from Notion or None if not JSON
    """
    url = f"https://api.notion.com/v1/pages/{page_id}"

    # Avoid invalid values
    properties = {
        "Name": {
            "title": [{"text": {"content": game["name"]}}]
        },
        "ID": {
            "number": int(game["app_id"])
        },
        "Price": {
            "number": float(game["price"]) if game["price"] is not None else None
        },
        "Released": {
            "checkbox": bool(game["released"])
        },
        "Genres": {
            "multi_select": [{"name": genre} for genre in game["genres"]]
        },
        "Estimated duration": {
            "number": float(game["hltb_time"]) if game["hltb_time"] is not None else None
        },
        "Metacritic": {
            "number": int(game["metacritic_score"]) if game["metacritic_score"] is not None else None
        }
    }

    # Notion special case: release_date must be None OR an ISO date
    if game["release_date"] is None:
        properties["Release date"] = {"date": None}
    else:
        properties["Release date"] = {"date": {"start": game["release_date"]}}

    data = {
        "icon": {
            "type": "external",
            "external": {"url": game["icon_image"]}
        },
        "cover": {
            "type": "external",
            "external": {"url": game["cover_image"]}
        },
        "properties": properties
    }
    response = requests.patch(url, headers=notion_headers, data=json.dumps(data))

    # Useful debugging
    if response.status_code >= 400:
        print("⚠️ Notion error:", response.text)

    try:
        return response.json()
    except Exception:
        print("❌ Notion returned a non-JSON response. Raw response:")
        print(response.text)
        return None
