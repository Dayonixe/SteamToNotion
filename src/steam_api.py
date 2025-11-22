from typing import Optional, Dict, Any
import requests
from .utils import normalize, similarity, is_sequel, convert_steam_date_to_iso
from .rawg_api import get_rawg_data, estimate_hltb_from_rawg


def search_app_id_by_name(name: str) -> Optional[int]:
    """
    Optimised search for Steam AppID based on game name.

    The research uses several strategies:
    1. Exact match
    2. Match 'startswith'
    3. Filtering false positives (unwanted sequences)
    4. Textual similarity (SequenceMatcher)

    :param name: Name of the game

    :return: The Steam AppID or None if no reliable match
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

    # 1. Exact match -> we go straight back, that's perfect
    for c in candidates:
        if c["name"].lower() == name.lower():
            return c["appid"]

    # 2. Otherwise -> startswith takes precedence
    startswith_matches = [
        c for c in candidates
        if normalize(c["name"]).startswith(name_norm)
    ]
    if startswith_matches:
        return startswith_matches[0]["appid"]

    # 3. Otherwise -> filter out titles that are too far apart
    filtered = []
    for c in candidates:
        title_norm = normalize(c["name"])

        # Avoid consequences if you don't want them
        if is_sequel(c["name"]) and not name_is_sequel:
            continue

        # Similar textual content
        if name_norm in title_norm or title_norm in name_norm:
            filtered.append(c)

    if not filtered:
        filtered = candidates

    # 4. Selecting the best by similarity
    for c in filtered:
        score = similarity(name_norm, normalize(c["name"]))
        if score > best_score:
            best_score = score
            best_app_id = c["appid"]

    # False positive threshold
    if best_score < 0.3:
        return None

    return best_app_id


def get_steam_game_details(app_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves all Steam information for a game via its AppID.

    :param app_id: Steam ID

    :return: Complete dictionary of game information or None if not found
    """
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=fr&l=fr"
    res = requests.get(url)
    data = res.json()

    # Verifying the success of the recovery
    if not data[str(app_id)]["success"]:
        return None

    info = data[str(app_id)]["data"]

    # Name of the game
    name = info.get("name")

    # Game release information
    released = not (info.get("release_date", {}).get("coming_soon", False))
    release_date = convert_steam_date_to_iso(info.get("release_date", {}).get("date"))

    # Game price
    price = None
    if "price_overview" in info:
        price = info["price_overview"]["final"] / 100
    elif released:
        price = 0

    # Game genres
    genres = []
    if "genres" in info:
        genres = [g["description"] for g in info["genres"]]

    # Game duration
    if released:
        rawg_playtime, rawg_genres, rawg_tags = get_rawg_data(name, app_id)
        hltb_time = estimate_hltb_from_rawg(rawg_playtime, rawg_genres, rawg_tags)
    else:
        hltb_time = None

    # Game rating
    metacritic_score = None
    if "metacritic" in info and "score" in info["metacritic"]:
        metacritic_score = info["metacritic"]["score"]

    # Game images
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
