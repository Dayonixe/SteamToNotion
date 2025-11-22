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
    Selects the best RAWG match based on similarity.

    The comparison uses a similarity ratio (SequenceMatcher)
    between the original name and the names returned by RAWG.

    :param results: Raw list of games returned by RAWG
    :param original_name: Exact name of the game you are looking for

    :return: The RAWG game dictionary with the best match or None if the match quality is too low
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
    Extracts and secures useful fields from RAWG.

    :param game: RAWG object representing a game

    :return: Tuple:
            - playtime (Optional[int])
            - genres (List[str])
            - tags   (List[str])
    """
    playtime = game.get("playtime")  # Median duration

    rawg_genres = game.get("genres") or []
    rawg_tags = game.get("tags") or []

    genres = [g.get("name") for g in rawg_genres if isinstance(g, dict) and "name" in g]
    tags = [t.get("name") for t in rawg_tags if isinstance(t, dict) and "name" in t]

    return playtime, genres, tags


def query_rawg(search_value, retries=3):
    """
    Queries the RAWG API with exponential backoff and error handling.

    :param search_value: Search value (name, slug, 'steam <id>'...)
    :param retries: Number of attempts before giving up

    :return: RAWG or None response in case of failure
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

        time.sleep((2 ** attempt) + random.random())  # Backoff

    print(f"⚠️ RAWG failed after {retries} attempts for search='{search_value}'")
    return None


def get_rawg_data(game_name: str, steam_app_id: Optional[int] = None) -> Tuple[Optional[int], List[str], List[str]]:
    """
    Robust search for game data in RAWG.

    Several strategies are attempted:
    1. Original name
    2. Cleaned name (without punctuation)
    3. Slug version
    4. Search by Steam AppID

    The results are cached to avoid reloading RAWG multiple times.

    :param game_name: Name of the game
    :param steam_app_id: Optional, improves accuracy

    :return: Tuple:
            - playtime (Optional[int])
            - genres (List[str])
            - tags (List[str])
    """
    cache_key = f"{game_name}|{steam_app_id}"
    if cache_key in RAWG_CACHE:
        return RAWG_CACHE[cache_key]

    # 1. Direct query with the original name
    res = query_rawg(game_name)

    if not res or "results" not in res or not isinstance(res["results"], list):
        print("⚠️ RAWG: Réponse vide / HTML / structure invalide")
    else:
        if len(res["results"]) > 0:
            match = best_rawg_match(res["results"], game_name)
            if match:
                RAWG_CACHE[cache_key] = extract_rawg_fields(match)
                return RAWG_CACHE[cache_key]

    # 2. Query with cleaned name
    cleaned_name = sanitize_title(game_name)
    if cleaned_name != game_name:
        res = query_rawg(cleaned_name)
        if res and "results" in res and len(res["results"]) > 0:
            match = best_rawg_match(res["results"], game_name)
            if match:
                RAWG_CACHE[cache_key] = extract_rawg_fields(match)
                return RAWG_CACHE[cache_key]

    # 3. Query 'slug style'
    slug = cleaned_name.replace(" ", "-")
    res = query_rawg(slug)
    if res and "results" in res and len(res["results"]) > 0:
        match = best_rawg_match(res["results"], game_name)
        if match:
            RAWG_CACHE[cache_key] = extract_rawg_fields(match)
            return RAWG_CACHE[cache_key]

    # 4. Search via Steam App ID
    if steam_app_id:
        res = query_rawg(f"steam {steam_app_id}")
        if res and "results" in res and len(res["results"]) > 0:
            match = best_rawg_match(res["results"], game_name)
            if match:
                RAWG_CACHE[cache_key] = extract_rawg_fields(match)
                return RAWG_CACHE[cache_key]

    # Total failure RAWG -> return empty values
    print(f"⚠️ RAWG did not return any results for: {game_name}")
    return None, [], []


def estimate_hltb_from_rawg(rawg_playtime: Optional[int], genres: List[str], tags: List[str]) -> Optional[float]:
    """
    Estimates a duration 'HowLongToBeat' based on RAWG durations.

    The estimate applies an intelligent ratio based on:
    - gross duration
    - genres
    - tags (open-world, sandbox, horror, etc.)
    - special rules (short games)

    :param rawg_playtime: RAWG duration (playtime)
    :param genres: RAWG genres
    :param tags: RAWG tags

    :return: Estimated duration or None
    """
    if rawg_playtime is None or rawg_playtime <= 0:
        return None

    genres = [g.lower() for g in genres]
    tags = [t.lower() for t in tags]

    # Ratio based on RAWG -> HLTB
    ratio = 2.5

    # Protection on short games
    if rawg_playtime <= 2:
        return round(rawg_playtime * 1.2, 1)
    elif rawg_playtime <= 3:
        return round(rawg_playtime * 1.5, 1)
    elif rawg_playtime <= 5:
        return round(rawg_playtime * 2.0, 1)

    # Ratios by main genre
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

    # Long survival sandbox / short survival horror
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
