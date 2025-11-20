import pytest
from unittest.mock import patch, MagicMock

from src.rawg_api import (
    sanitize_title,
    safe_get_json,
    extract_rawg_fields,
    best_rawg_match,
    get_rawg_data,
)



############################################################
#  sanitize_title                                          #
############################################################

def test_sanitize_title_basic():
    assert sanitize_title("Halo: Infinite") == "halo infinite"

def test_sanitize_title_symbols():
    assert sanitize_title("Café!! World??") == "café world"

def test_sanitize_title_spaces():
    assert sanitize_title("   Game    Name   ") == "game name"



############################################################
#  safe_get_json                                           #
############################################################

def test_safe_get_json_valid():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True}
    assert safe_get_json(mock_resp) == {"ok": True}

def test_safe_get_json_invalid():
    mock_resp = MagicMock()
    mock_resp.json.side_effect = ValueError("Invalid JSON")
    assert safe_get_json(mock_resp) is None



############################################################
#  extract_rawg_fields                                     #
############################################################

def test_extract_rawg_fields_normal():
    game = {
        "playtime": 5,
        "genres": [{"name": "Action"}, {"foo": "bar"}],
        "tags": [{"name": "Coop"}, {}]
    }
    playtime, genres, tags = extract_rawg_fields(game)

    assert playtime == 5
    assert genres == ["Action"]
    assert tags == ["Coop"]

def test_extract_rawg_fields_empty():
    playtime, genres, tags = extract_rawg_fields({})
    assert playtime is None
    assert genres == []
    assert tags == []


############################################################
#  best_rawg_match                                         #
############################################################

def test_best_rawg_match_basic():
    results = [
        {"name": "Hadex"},
        {"name": "Hadez"},
        {"name": "Something Else"}
    ]
    match = best_rawg_match(results, "Hades")
    assert match["name"] == "Hadex"   # meilleure similarité

def test_best_rawg_match_below_threshold():
    results = [{"name": "TotallyDifferent"}]
    match = best_rawg_match(results, "Hades")
    assert match is None



############################################################
#  get_rawg_data — mocks                                   #
############################################################

@patch("src.rawg_api.requests.get")
def test_rawg_direct_match(mock_get):
    """Test du scénario principal : RAWG renvoie une liste correcte."""
    mock_get.return_value.json.return_value = {
        "results": [
            {"name": "Hades", "playtime": 10, "genres": [], "tags": []}
        ]
    }

    playtime, genres, tags = get_rawg_data("Hades", 1145360)
    assert playtime == 10
    assert genres == []
    assert tags == []


@patch("src.rawg_api.requests.get")
def test_rawg_no_results(mock_get):
    mock_get.return_value.json.return_value = {"results": []}
    playtime, genres, tags = get_rawg_data("UnknownGame", 123)
    assert playtime is None
    assert genres == []
    assert tags == []


@patch("src.rawg_api.requests.get")
def test_rawg_invalid_json(mock_get):
    """RAWG renvoie du HTML ou JSON cassé."""
    mock_get.return_value.json.side_effect = ValueError("Invalid JSON")
    playtime, genres, tags = get_rawg_data("Hades", 1145360)
    assert playtime is None


@patch("src.rawg_api.requests.get")
def test_rawg_fallback_cleaned_name(mock_get):
    """Le premier appel échoue mais pas celui avec sanitize_title."""
    # 1er appel → HTML invalide
    invalid = MagicMock()
    invalid.json.side_effect = ValueError("No JSON")

    # 2ème appel → bon JSON
    valid = MagicMock()
    valid.json.return_value = {
        "results": [{"name": "Hades Cleaned", "playtime": 9}]
    }

    mock_get.side_effect = [invalid, valid]

    playtime, genres, tags = get_rawg_data("Hades!!!", 1145360)
    assert playtime == 9


@patch("src.rawg_api.requests.get")
def test_rawg_fallback_slug(mock_get):
    """Nom nettoyé échoue → slug réussit"""
    bad = MagicMock()
    bad.json.return_value = {"results": []}

    good = MagicMock()
    good.json.return_value = {
        "results": [{"name": "Hades-Slug", "playtime": 8}]
    }

    mock_get.side_effect = [bad, bad, good]

    playtime, genres, tags = get_rawg_data("Hades", 1145360)
    assert playtime == 8


@patch("src.rawg_api.requests.get")
def test_rawg_fallback_steam_id(mock_get):
    """Fallback sur 'steam <id>'"""
    empty = MagicMock()
    empty.json.return_value = {"results": []}

    good = MagicMock()
    good.json.return_value = {
        "results": [{"name": "Hades Steam", "playtime": 12}]
    }

    # 3 tentatives échouent → 4e avec Steam ID réussit
    mock_get.side_effect = [empty, empty, empty, good]

    playtime, genres, tags = get_rawg_data("Hades", 1145360)
    assert playtime == 12


@patch("src.rawg_api.requests.get")
def test_rawg_cache(mock_get):
    """Deux appels identiques → 1 seul appel réseau."""
    mock_get.return_value.json.return_value = {
        "results": [{"name": "Hades", "playtime": 10}]
    }

    get_rawg_data("Hades", 1145360)
    get_rawg_data("Hades", 1145360)

    # Une seule requête réalisée
    assert mock_get.call_count == 1
