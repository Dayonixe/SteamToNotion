import re
from typing import Optional, Any
from datetime import datetime
from difflib import SequenceMatcher
import requests


def normalize(text: Optional[str]) -> str:
    """
    Normalises text for comparison.

    :param text: Input text

    :return: Standard text (lowercase letters, alphanumeric characters, spaces)
    """
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()


def similarity(a: str, b: str) -> float:
    """
    Calculates a similarity score between two strings.

    :param a: First string
    :param b: Second string

    :return: Similarity ratio between 0 and 1
    """
    a_norm = a.lower() if isinstance(a, str) else ""
    b_norm = b.lower() if isinstance(b, str) else ""
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def convert_steam_date_to_iso(date_str: Optional[str]) -> Optional[str]:
    """
    Converts a Steam date to ISO format YYYY-MM-DD.
    Example: "25 Sep, 2025" -> "2025-09-25"

    :param date_str: Steam date

    :return: Date formatted in ISO or None if invalid
    """
    try:
        # Steam format
        dt = datetime.strptime(date_str, "%d %b, %Y")
        return dt.date().isoformat()  # '2025-09-25'
    except:
        return None


def sanitize_title(title: Optional[str]) -> str:
    """
    Cleans up a title for more reliable RAWG searching.

    :param title: Original title

    :return: Cleaned title
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
    Returns response.json() with HTML/text error handling.

    :param response: HTTP response

    :return: Parsed JSON or None if impossible
    """
    try:
        return response.json()
    except Exception:
        return None


def is_sequel(title: Optional[str]) -> bool:
    """
    Detects whether a title appears to be a sequel (II, III, IV, 2, 3, etc.).
    The function ignores years (e.g. 2077, 1998).

    :param title: Game title

    :return: True if it is a suite, False otherwise
    """
    title = title.lower()

    # Romans II / III / IV
    if re.search(r"\b(ii|iii|iv|v)\b", title):
        return True

    # Isolated figures != years (1800, 2077)
    if re.search(r"\b([1-9]|10)\b(?!\d)", title):
        return True

    return False
