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
    Récupère l'AppID Steam d'une page Notion.

    Priorité :
    1. Si la propriété "ID" contient déjà un numéro valide -> utiliser.
    2. Sinon, récupérer le nom ("Name") et effectuer une recherche Steam.

    :param page: Objet de page Notion issu de l’API

    :return: AppID Steam, ou None si introuvable
    """
    id_prop = page["properties"].get("ID")

    # Si ID présent et valide
    if id_prop and id_prop["number"]:
        return id_prop["number"]

    # Sinon rechercher via "Name"
    name_prop = page["properties"].get("Name", {})
    if "title" in name_prop and len(name_prop["title"]) > 0:
        game_name = name_prop["title"][0]["plain_text"]
        app_id = search_app_id_by_name(game_name)
        if app_id:
            print(f"🔎 Trouvé app_id = {app_id} via le nom '{game_name}'")
            return app_id
        else:
            print(f"⚠️ Aucun app_id trouvé pour '{game_name}'")

    return None


def get_notion_pages() -> List[Dict[str, Any]]:
    """
    Récupère toutes les pages d'une database Notion (pagination incluse).

    :return: Liste complète des pages de la DB
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
    Met à jour une page Notion avec les informations d'un jeu.

    :param page_id: ID Notion de la page
    :param game: Données complètes du jeu (Steam + HLTB estimé)

    :return: Réponse JSON de Notion, ou None si non JSON
    """
    url = f"https://api.notion.com/v1/pages/{page_id}"

    # Évite les valeurs non valides
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

    # Cas spécial Notion : release_date doit être None OU une date ISO
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

    # Debug utile :
    if response.status_code >= 400:
        print("⚠️ Erreur Notion :", response.text)

    try:
        return response.json()
    except Exception:
        print("❌ Notion a renvoyé une réponse non JSON. Réponse brute :")
        print(response.text)
        return None
