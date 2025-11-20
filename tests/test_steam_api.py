import pytest
from unittest.mock import patch

from src.steam_api import search_app_id_by_name



##################################################
#  search_app_id_by_name — cas de base           #
##################################################

@patch("src.steam_api.requests.get")
def test_search_app_id_exact_match(mock_get):
    mock_get.return_value.json.return_value = [
        {"name": "Hades", "appid": 1145360},
        {"name": "Hades II", "appid": 1145350}
    ]

    assert search_app_id_by_name("Hades") == 1145360



@patch("src.steam_api.requests.get")
def test_search_app_id_startswith(mock_get):
    mock_get.return_value.json.return_value = [
        {"name": "Hades II", "appid": 1145350},
        {"name": "Hades Prelude", "appid": 999999}
    ]

    assert search_app_id_by_name("Hades") == 1145350



@patch("src.steam_api.requests.get")
def test_search_app_id_similarity(mock_get):
    mock_get.return_value.json.return_value = [
        {"name": "Hadez", "appid": 111111},
        {"name": "Hadex", "appid": 222222}
    ]

    assert search_app_id_by_name("Hades") == 111111



##################################################
#  search_app_id_by_name — cas d’erreurs         #
##################################################

@patch("src.steam_api.requests.get")
def test_search_app_id_invalid_json(mock_get):
    mock_get.return_value.json.side_effect = ValueError("Invalid JSON")
    assert search_app_id_by_name("Hades") is None



@patch("src.steam_api.requests.get")
def test_search_app_id_empty_list(mock_get):
    mock_get.return_value.json.return_value = []
    assert search_app_id_by_name("Hades") is None



@patch("src.steam_api.requests.get")
def test_search_app_id_similarity_too_low(mock_get):
    mock_get.return_value.json.return_value = [
        {"name": "XYZabc", "appid": 123456},
        {"name": "TotallyDifferent", "appid": 987654},
    ]

    # Aucune similarité > 0.3
    assert search_app_id_by_name("Hades") is None



##################################################
#  Cas avancés — suites & anti-suites            #
##################################################

@patch("src.steam_api.requests.get")
def test_search_app_id_avoid_wrong_sequel(mock_get):
    mock_get.return_value.json.return_value = [
        {"name": "Game II", "appid": 200},
        {"name": "Game", "appid": 100}
    ]

    # On cherche Game → pas Game II
    assert search_app_id_by_name("Game") == 100



@patch("src.steam_api.requests.get")
def test_search_app_id_accept_matching_sequel(mock_get):
    mock_get.return_value.json.return_value = [
        {"name": "Game", "appid": 100},
        {"name": "Game II", "appid": 200}
    ]

    assert search_app_id_by_name("Game II") == 200



##################################################
#  Cas avancés — nettoyage & variantes           #
##################################################

@patch("src.steam_api.requests.get")
def test_search_app_id_handles_colons(mock_get):
    mock_get.return_value.json.return_value = [
        {"name": "Halo Infinite", "appid": 123},
        {"name": "Halo: Infinite", "appid": 456}
    ]

    # Le normalize rend les deux proches
    assert search_app_id_by_name("Halo: Infinite") in {123, 456}



@patch("src.steam_api.requests.get")
def test_search_app_id_unicode(mock_get):
    mock_get.return_value.json.return_value = [
        {"name": "Café World", "appid": 10},
        {"name": "Cafe World", "appid": 20},
    ]

    # normalize enlève les accents → choix cohérent
    assert search_app_id_by_name("Café World") in {10, 20}
