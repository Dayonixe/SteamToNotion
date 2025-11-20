from typing import Tuple, List, Dict, Optional, Any
import requests
import time
import random
from dotenv import load_dotenv
import os
from .utils import sanitize_title, safe_get_json, normalize, similarity

load_dotenv()
RAWG_API_KEY = os.getenv("RAWG_API_KEY")

RAWG_CACHE = {}


def best_rawg_match(results: List[Dict], original_name: str) -> Optional[Dict]:
    """
    Sélectionne la meilleure correspondance RAWG basée sur la similarité.

    La comparaison utilise un ratio de ressemblance (SequenceMatcher)
    entre le nom original et les noms renvoyés par RAWG.

    :param results: Liste brute des jeux renvoyés par RAWG
    :param original_name: Nom exact du jeu recherché

    :return: Le dictionnaire du jeu RAWG ayant le meilleur match, ou None si la qualité du match est trop faible
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


def extract_rawg_fields(game: Dict[str, Any]) -> Tuple[Optional[int], List[str], List[str]]:
    """
    Extrait et sécurise les champs utiles de RAWG.

    :param game: Objet RAWG représentant un jeu

    :return: Tuple:
            - playtime (Optional[int])
            - genres (List[str])
            - tags   (List[str])
    """
    playtime = game.get("playtime")  # durée médiane

    rawg_genres = game.get("genres") or []
    rawg_tags = game.get("tags") or []

    genres = [g.get("name") for g in rawg_genres if isinstance(g, dict) and "name" in g]
    tags = [t.get("name") for t in rawg_tags if isinstance(t, dict) and "name" in t]

    return playtime, genres, tags


def query_rawg(search_value, retries=3):
    """
    Interroge l’API RAWG avec backoff exponentiel et gestion des erreurs.

    :param search_value: Valeur de recherche (nom, slug, "steam <id>"...)
    :param retries: Nombre de tentatives avant abandon

    :return: Réponse RAWG ou None en cas d’échec
    """
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


def get_rawg_data(game_name: str, steam_app_id: Optional[int] = None) -> Tuple[Optional[int], List[str], List[str]]:
    """
    Recherche robuste des données d’un jeu dans RAWG.

    Plusieurs stratégies sont tentées :
    1. Nom original
    2. Nom nettoyé (sans ponctuation)
    3. Version slug
    4. Recherche par Steam AppID (RAWG supporte ça !)

    Les résultats sont mis en cache pour éviter de recharger RAWG plusieurs fois.

    :param game_name: Nom du jeu
    :param steam_app_id: Optionnel, améliore la précision

    :return: Tuple:
            - playtime (Optional[int])
            - genres (List[str])
            - tags (List[str])
    """
    cache_key = f"{game_name}|{steam_app_id}"
    if cache_key in RAWG_CACHE:
        return RAWG_CACHE[cache_key]

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

    # Échec total RAWG -> renvoyer valeurs vides
    print(f"⚠️ RAWG n’a retourné aucun résultat pour : {game_name}")
    return None, [], []


def estimate_hltb_from_rawg(rawg_playtime: Optional[int], genres: List[str], tags: List[str]) -> Optional[float]:
    """
    Estime une durée “HowLongToBeat” à partir des durées RAWG.

    L’estimation applique un ratio intelligent selon :
    - la durée brute
    - les genres
    - les tags (open-world, sandbox, horror...)
    - des règles spéciales (jeux courts)

    :param rawg_playtime: Durée RAWG (playtime)
    :param genres: Genres RAWG
    :param tags: Tags RAWG

    :return: Durée estimée ou None
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
