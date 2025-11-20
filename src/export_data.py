from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime
import re
from difflib import SequenceMatcher
import time
import random


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

RAWG_CACHE = {}



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

    # Romans II / III / IV
    if re.search(r"\b(ii|iii|iv|v)\b", title):
        return True

    # Chiffres isolés ≠ années (1800, 2077)
    if re.search(r"\b([1-9]|10)\b(?!\d)", title):
        return True

    return False


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


def sanitize_title(title: str):
    """
    Nettoie le titre pour améliorer la recherche RAWG
    :param title: Titre à nettoyer
    :return: Titre sain
    """
    if not title:
        return ""
    t = title.lower()
    t = t.replace(":", " ")
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def safe_get_json(response):
    """
    Eviter de crash si RAWG renvoie du HTML
    :param response: Réponse de RAWG
    :return: Tri des réponses
    """
    try:
        return response.json()
    except Exception:
        return None


def extract_rawg_fields(game):
    """
    Extraction sécurisée des champs RAWG (safe parsing)
    :param game: Nom du jeu
    :return: playtime, genres, tags
    """
    playtime = game.get("playtime")  # durée médiane

    rawg_genres = game.get("genres") or []
    rawg_tags = game.get("tags") or []

    genres = [g.get("name") for g in rawg_genres if isinstance(g, dict) and "name" in g]
    tags = [t.get("name") for t in rawg_tags if isinstance(t, dict) and "name" in t]

    return playtime, genres, tags


def best_rawg_match(results, original_name):
    """
    TODO
    :param results:
    :param original_name:
    :return:
    """
    original_norm = normalize(original_name)

    best = None
    best_score = 0

    for game in results:
        name = game.get("name", "")
        score = similarity(original_norm, normalize(name))
        if score > best_score:
            best_score = score
            best = game

    return best if best_score >= 0.45 else None


def get_rawg_data(game_name: str, steam_app_id: int = None):
    """
    Recherche robuste des données d'un jeu dans RAWG
    :param game_name: Nom du jeu
    :param steam_app_id:
    :return: playtime, genres, tags
    """
    cache_key = f"{game_name}|{steam_app_id}"
    if cache_key in RAWG_CACHE:
        return RAWG_CACHE[cache_key]

    def query_rawg(search_value, retries=3):
        url = (
            f"https://api.rawg.io/api/games"
            f"?search={search_value}"
            f"&key={RAWG_API_KEY}"
        )
        for attempt in range(retries):
            try:
                headers = {"User-Agent": "SteamToNotion/1.0"}
                resp = requests.get(url, timeout=8, headers=headers)
                data = safe_get_json(resp)
                if data:
                    return data
            except Exception:
                pass

            time.sleep((2 ** attempt) + random.random())  # backoff

        print(f"⚠️ RAWG failed after {retries} attempts for search='{search_value}'")
        return None

    # Try 1: Query direct avec le nom original
    res = query_rawg(game_name)

    if not res or "results" not in res or not isinstance(res["results"], list):
        print("⚠️ RAWG: Réponse vide / HTML / structure invalide")
    else:
        if len(res["results"]) > 0:
            match = best_rawg_match(res["results"], game_name)
            if match:
                RAWG_CACHE[cache_key] = extract_rawg_fields(match)
                return RAWG_CACHE[cache_key]

    # Try 2: Query avec nom nettoyé
    cleaned_name = sanitize_title(game_name)
    if cleaned_name != game_name:
        res = query_rawg(cleaned_name)
        if res and "results" in res and len(res["results"]) > 0:
            match = best_rawg_match(res["results"], game_name)
            if match:
                RAWG_CACHE[cache_key] = extract_rawg_fields(match)
                return RAWG_CACHE[cache_key]

    # Try 3: Query “slug style”
    slug = cleaned_name.replace(" ", "-")
    res = query_rawg(slug)
    if res and "results" in res and len(res["results"]) > 0:
        match = best_rawg_match(res["results"], game_name)
        if match:
            RAWG_CACHE[cache_key] = extract_rawg_fields(match)
            return RAWG_CACHE[cache_key]

    # Try 4: Recherche via Steam App ID (RAWG comprend ça !)
    if steam_app_id:
        res = query_rawg(f"steam {steam_app_id}")
        if res and "results" in res and len(res["results"]) > 0:
            match = best_rawg_match(res["results"], game_name)
            if match:
                RAWG_CACHE[cache_key] = extract_rawg_fields(match)
                return RAWG_CACHE[cache_key]

    # Échec total RAWG → renvoyer valeurs vides
    print(f"⚠️ RAWG n’a retourné aucun résultat pour : {game_name}")
    return None, [], []


def estimate_hltb_from_rawg(rawg_playtime, genres, tags):
    """
    Calcul une estimation de la durée d'un jeu à partir de la durée extraite de RAWG
    :param rawg_playtime: Durée du jeu de RAWG
    :param genres: Liste des genres du jeu de RAWG
    :param tags: Liste des tags du jeu de RAWG
    :return: Estimation de la durée
    """
    if rawg_playtime is None or rawg_playtime <= 0:
        return None

    genres = [g.lower() for g in genres]
    tags = [t.lower() for t in tags]

    # Ratio basé sur RAWG -> HLTB
    ratio = 2.5

    # Protection sur les jeux courts
    if rawg_playtime <= 2:
        return round(rawg_playtime * 1.2, 1)
    elif rawg_playtime <= 3:
        return round(rawg_playtime * 1.5, 1)
    elif rawg_playtime <= 5:
        return round(rawg_playtime * 2.0, 1)

    # Ratios selon genre principal
    if any(g in genres for g in ["rpg", "role-playing"]):
        ratio = 5.0
    elif any(g in genres for g in ["strategy"]):
        ratio = 3.0
    elif any(g in genres for g in ["adventure"]):
        ratio = 2.5
    elif any(g in genres for g in ["action"]):
        ratio = 2.2
    elif any(g in genres for g in ["indie"]):
        ratio = 1.8
    elif any(g in genres for g in ["platformer"]):
        ratio = 1.5
    elif any(g in genres for g in ["roguelike"]):
        ratio = 2.5

    # survival sandbox long / survival horror court
    if any(t in tags for t in ["open world", "sandbox", "crafting", "exploration", "base building"]):
        ratio *= 3.5
    elif any(t in tags for t in ["survival", "horror"]):
        ratio *= 1.2

    # Simulation / factory games
    if any(g in genres for g in ["simulation"]):
        ratio = max(ratio, 3.5)

    if any(t in tags for t in ["automation", "factory", "management"]):
        ratio = max(ratio, 4.0)

    return round(rawg_playtime * ratio, 1)



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

    # Durée du jeu
    if released:
        rawg_playtime, rawg_genres, rawg_tags = get_rawg_data(name, app_id)
        hltb_time = estimate_hltb_from_rawg(rawg_playtime, rawg_genres, rawg_tags)
    else:
        hltb_time = None

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
        "hltb_time": hltb_time,
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

        # Si Platform != Steam, la page est ignorée
        if platform_value != "Steam":
            print(f"⏭️ Page ignorée ({page_id}) — Platform = {platform_value}\n")
            continue

        # Lecture de la colonne "ID"
        app_id = get_app_id_for_page(page)

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

        if game_data["released"]:
            time.sleep(0.25)  # Evite rate limiting