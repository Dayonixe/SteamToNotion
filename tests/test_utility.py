import pytest
from unittest.mock import patch

from src.export_data import (
    convert_steam_date_to_iso,
    normalize,
    similarity,
    is_sequel,
    search_app_id_by_name
)



###############################
#  convert_steam_date_to_iso  #
###############################
def test_convert_steam_date_to_iso_valid():
    assert convert_steam_date_to_iso("25 Sep, 2025") == "2025-09-25"

def test_convert_steam_date_to_iso_invalid():
    assert convert_steam_date_to_iso("Invalid date") is None

def test_convert_steam_date_to_iso_empty():
    assert convert_steam_date_to_iso("") is None



###############################
#         normalize           #
###############################
def test_normalize_basic():
    assert normalize("Hello World") == "hello world"

def test_normalize_special_chars():
    result = normalize("H@llø !!! Wørld ###")
    assert "hll" in result
    assert "wrld" in result

def test_normalize_numbers():
    assert normalize("Game 123") == "game 123"

def test_normalize_empty():
    assert normalize("") == ""



###############################
#         similarity          #
###############################
def test_similarity_identical():
    assert similarity("test", "test") == 1.0

def test_similarity_completely_different():
    assert similarity("abc", "xyz") < 0.1

def test_similarity_partial():
    assert 0.5 < similarity("hades", "hade") < 1.0



###############################
#         is_sequel           #
###############################
def test_is_sequel_roman():
    assert is_sequel("Hades II") is True

def test_is_sequel_digit():
    assert is_sequel("Hades 2") is True

def test_is_sequel_not_sequel():
    assert is_sequel("Hades") is False

def test_is_sequel_with_iii():
    assert is_sequel("Diablo III") is True



#########################################
#     search_app_id_by_name (mocked)    #
#########################################
@patch("src.export_data.requests.get")
def test_search_app_id_by_name_exact_match(mock_get):
    mock_get.return_value.json.return_value = [
        {"name": "Hades", "appid": 1145360},
        {"name": "Hades II", "appid": 1145350}
    ]

    assert search_app_id_by_name("Hades") == 1145360


@patch("src.export_data.requests.get")
def test_search_app_id_by_name_startswith(mock_get):
    mock_get.return_value.json.return_value = [
        {"name": "Hades II", "appid": 1145350},
        {"name": "Hades: Prelude", "appid": 999999}
    ]

    # "Hades" n'est pas un match exact donc on prend celui qui commence par hades
    assert search_app_id_by_name("Hades") == 1145350


@patch("src.export_data.requests.get")
def test_search_app_id_by_name_similarity(mock_get):
    mock_get.return_value.json.return_value = [
        {"name": "Hadez", "appid": 111111},
        {"name": "Hadex", "appid": 222222}
    ]

    # Similarité la plus forte ("hadez")
    assert search_app_id_by_name("Hades") == 111111


@patch("src.export_data.requests.get")
def test_search_app_id_by_name_no_results(mock_get):
    mock_get.return_value.json.return_value = []
    assert search_app_id_by_name("Hades") is None


@patch("src.export_data.requests.get")
def test_search_app_id_by_name_invalid_json(mock_get):
    mock_get.return_value.json.side_effect = ValueError("Invalid JSON")
    assert search_app_id_by_name("Hades") is None