import re
from typing import Optional, Any
from datetime import datetime
from difflib import SequenceMatcher
import requests


def normalize(text: Optional[str]) -> str:
    """
    Normalise un texte pour comparaison.

    :param text: Texte d’entrée

    :return: Texte normalisé (minuscules, alphanumériques, espaces)
    """
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()


def similarity(a: str, b: str) -> float:
    """
    Calcule un score de similarité entre deux chaînes.

    :param a: Première chaîne
    :param b: Deuxième chaîne

    :return: Ratio de similarité entre 0 et 1
    """
    a_norm = a.lower() if isinstance(a, str) else ""
    b_norm = b.lower() if isinstance(b, str) else ""
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def convert_steam_date_to_iso(date_str: Optional[str]) -> Optional[str]:
    """
    Convertit une date Steam en format ISO AAAA-MM-JJ.
    Exemple : "25 Sep, 2025" -> "2025-09-25"

    :param date_str: Date Steam

    :return: Date formatée en ISO ou None si invalide
    """
    try:
        # Steam format
        dt = datetime.strptime(date_str, "%d %b, %Y")
        return dt.date().isoformat()  # '2025-09-25'
    except:
        return None


def sanitize_title(title: Optional[str]) -> str:
    """
    Nettoie un titre pour une recherche RAWG plus fiable.

    :param title: Titre original

    :return: Titre nettoyé
    """
    if not title:
        return ""
    t = title.lower()
    t = t.replace(":", " ")
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def safe_get_json(response: requests.Response) -> Optional[Any]:
    """
    Retourne response.json() en sécurisant les erreurs HTML/texte.

    :param response: Réponse HTTP

    :return: JSON parsé, ou None si impossible
    """
    try:
        return response.json()
    except Exception:
        return None


def is_sequel(title: Optional[str]) -> bool:
    """
    Détecte si un titre semble être une suite (II, III, IV, 2, 3…).
    La fonction ignore les années (ex: 2077, 1998).

    :param title: Titre du jeu

    :return: True si c’est une suite, False sinon
    """
    title = title.lower()

    # Romains II / III / IV
    if re.search(r"\b(ii|iii|iv|v)\b", title):
        return True

    # Chiffres isolés ≠ années (1800, 2077)
    if re.search(r"\b([1-9]|10)\b(?!\d)", title):
        return True

    return False
