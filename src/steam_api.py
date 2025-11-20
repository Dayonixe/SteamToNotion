from typing import Optional, Dict, Any
import requests
from .utils import normalize, similarity, is_sequel, convert_steam_date_to_iso
from .rawg_api import get_rawg_data, estimate_hltb_from_rawg


def search_app_id_by_name(name: str) -> Optional[int]:
    """
    Recherche optimisée du Steam AppID à partir d’un nom de jeu.

    La recherche utilise plusieurs stratégies :
    1. Match exact
    2. Match "startswith"
    3. Filtrage des faux positifs (suites non désirées)
    4. Similarité textuelle (SequenceMatcher)

    :param name: Nom du jeu

    :return: L'AppID Steam ou None si aucun match fiable
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

    # 1) Match exact -> on retourne direct, c'est parfait
    for c in candidates:
        if c["name"].lower() == name.lower():
            return c["appid"]

    # 2) Sinon -> startswith prioritaire
    startswith_matches = [
        c for c in candidates
        if normalize(c["name"]).startswith(name_norm)
    ]
    if startswith_matches:
        return startswith_matches[0]["appid"]

    # 3) Sinon -> filtrer les titres trop éloignés
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


def get_steam_game_details(app_id: int) -> Optional[Dict[str, Any]]:
    """
    Récupère toutes les informations Steam d'un jeu via son AppID.

    :param app_id: Identifiant Steam

    :return: Dictionnaire complet des infos du jeu, ou None si non trouvé
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
