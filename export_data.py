from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime
import re
from difflib import SequenceMatcher


######################################################
#     Gestion du .env et configuration de Notion     #
######################################################
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
RAWG_API_KEY = os.getenv("RAWG_API_KEY")

notion_headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}



######################################################
#               Fonctions utilitaires                #
######################################################
def convert_steam_date_to_iso(date_str: str):
    """
    Convertit une date du type '25 Sep, 2025' -> '2025-09-25'
    :param date_str: Date au format '25 Sep, 2025'
    :return: La date convertie au bon format ou None
    """
    try:
        # Steam format
        dt = datetime.strptime(date_str, "%d %b, %Y")
        return dt.date().isoformat()  # '2025-09-25'
    except:
        return None


def normalize(text: str):
    """
    Normalisation d'un texte
    :param text: Texte à normaliser
    :return: Texte normalisé
    """
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()


def similarity(a, b):
    """
    Comparaison de deux séquences pour obtention d'un ratio de match entre celles-ci
    :param a: Première séquence à comparer
    :param b: Seconde séquence à comparer
    :return: Ratio de la la comparaison
    """
    return SequenceMatcher(None, a, b).ratio()


def is_sequel(title: str):
    """
    Détecte si un titre est une suite (II, 2, III, 3, etc.)
    :param title: Titre à analyser
    :return: Booléen
    """
    title = title.lower()
    return (
        " ii" in title or
        " 2" in title or
        " iii" in title or
        " 3" in title
    )


def search_app_id_by_name(name: str):
    """
    Recherche optimisée pour la récupération du bon ID du jeu :
    - Match exact prioritaire
    - Match startswith prioritaire
    - Similarité
    - Anti-suites si non présentes dans le nom recherché
    :param name: Nom du jeu
    :return: ID du jeu
    """

    url = f"https://steamcommunity.com/actions/SearchApps/{name}"
    res = requests.get(url)

    try:
        candidates = res.json()
    except:
        return None

    if not candidates:
        return None

    name_norm = normalize(name)
    name_is_sequel = is_sequel(name)

    best_score = 0
    best_app_id = None

    # 1) Match exact → on retourne direct, c'est parfait
    for c in candidates:
        if c["name"].lower() == name.lower():
            return c["appid"]

    # 2) Sinon → startswith prioritaire
    startswith_matches = [
        c for c in candidates
        if normalize(c["name"]).startswith(name_norm)
    ]
    if startswith_matches:
        return startswith_matches[0]["appid"]

    # 3) Sinon → filtrer les titres trop éloignés
    filtered = []
    for c in candidates:
        title_norm = normalize(c["name"])

        # éviter les suites si on ne les veut pas
        if is_sequel(c["name"]) and not name_is_sequel:
            continue

        # contenu textuel similaire
        if name_norm in title_norm or title_norm in name_norm:
            filtered.append(c)

    if not filtered:
        filtered = candidates

    # 4) Choisir le meilleur par similarité
    for c in filtered:
        score = similarity(name_norm, normalize(c["name"]))
        if score > best_score:
            best_score = score
            best_app_id = c["appid"]

    # seuil anti-faux-positif
    if best_score < 0.3:
        return None

    return best_app_id



######################################################
#               Fonctions Principales                #
######################################################
def get_notion_pages():
    """
    Récupérer toutes les pages de la database Notion
    :return: Liste des pages
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


def get_app_id_for_page(page):
    """
    Récupération de l'ID du jeu
    :param page: Page de Notion
    :return: ID du jeu
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


def get_steam_game_details(app_id: int):
    """
    Récupérer les infos Steam via l'app_id (ID)
    :param app_id: Numéro d'ID du jeu
    :return: Liste des informations du jeu
    """
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=fr&l=fr"
    res = requests.get(url)
    data = res.json()

    # Vérification du succès de la récupération
    if not data[str(app_id)]["success"]:
        return None

    info = data[str(app_id)]["data"]

    # Nom du jeu
    name = info.get("name")

    # Information de sortie du jeu
    released = not (info.get("release_date", {}).get("coming_soon", False))
    release_date = convert_steam_date_to_iso(info.get("release_date", {}).get("date"))

    # Prix du jeu
    price = None
    if "price_overview" in info:
        price = info["price_overview"]["final"] / 100
    elif released:
        price = 0

    # Genres du jeu
    genres = []
    if "genres" in info:
        genres = [g["description"] for g in info["genres"]]

    # Note du jeu
    metacritic_score = None
    if "metacritic" in info and "score" in info["metacritic"]:
        metacritic_score = info["metacritic"]["score"]

    # Images du jeu
    wallpaper = f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{app_id}/library_hero.jpg"
    icon = f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{app_id}/logo.png"

    return {
        "app_id": app_id,
        "name": name,
        "price": price,
        "released": released,
        "release_date": release_date,
        "genres": genres,
        "metacritic_score": metacritic_score,
        "cover_image": wallpaper,
        "icon_image": icon
    }


def update_notion_page(page_id, game):
    """
    Mise à jour des informations de la page Notion
    :param page_id: ID de la page
    :param game: Données du jeu
    :return: Réponse du JSON
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

    return response.json()



######################################################
#                        Main                        #
######################################################
if __name__ == "__main__":
    pages = get_notion_pages()

    for page in pages:
        page_id = page["id"]

        # Vérification plateforme
        platform_prop = page["properties"].get("Platform", {})
        platform_value = None

        if platform_prop.get("select"):
            platform_value = platform_prop["select"]["name"]

        # Lecture de la colonne "ID"
        app_id = get_app_id_for_page(page)

        # Si Platform != Steam, la page est ignorée
        if platform_value != "Steam":
            print(f"⏭️ Page ignorée ({page_id}) — Platform = {platform_value}")
            continue

        # S'il n'y a pas d'ID du jeu, la page est ignorée
        if not app_id:
            print(f"⚠️ ID absent pour la page {page_id}")
            continue

        print(f"🔍 Récupération Steam pour app_id = {app_id}")

        game_data = get_steam_game_details(app_id)

        # S'il n'y a pas de donnée du jeu, la page est ignorée
        if not game_data:
            print(f"❌ Impossible d'obtenir les infos Steam pour {app_id}")
            continue

        print(f"📥 Données récupérées : {game_data}")

        update_notion_page(page_id, game_data)

        print(f"✅ Page mise à jour : {page_id}\n")