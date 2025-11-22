import pytest

from src.utils import (
    convert_steam_date_to_iso,
    normalize,
    similarity,
    is_sequel,
    sanitize_title
)



##########################################################
#  convert_steam_date_to_iso                             #
##########################################################

def test_convert_steam_date_to_iso_valid():
    assert convert_steam_date_to_iso("25 Sep, 2025") == "2025-09-25"


def test_convert_steam_date_to_iso_invalid():
    assert convert_steam_date_to_iso("Invalid date") is None


def test_convert_steam_date_to_iso_empty():
    assert convert_steam_date_to_iso("") is None


def test_convert_steam_date_to_iso_wrong_format():
    assert convert_steam_date_to_iso("2025-09-25") is None



##########################################################
#  normalize                                             #
##########################################################

def test_normalize_basic():
    assert normalize("Hello World") == "hello world"


def test_normalize_special_chars():
    result = normalize("H@llø !!! Wørld ###")
    # Vérifie que lettres principales subsistent
    assert "hll" in result
    assert "wrld" in result


def test_normalize_numbers():
    assert normalize("Game 123") == "game 123"


def test_normalize_unicode():
    assert normalize("Café Été") == "caf t"


def test_normalize_empty():
    assert normalize("") == ""


def test_normalize_only_special_chars():
    assert normalize("$$$!!!###") == ""



##########################################################
#  similarity                                            #
##########################################################

def test_similarity_identical():
    assert similarity("test", "test") == 1.0


def test_similarity_completely_different():
    assert similarity("abc", "xyz") < 0.1


def test_similarity_partial():
    assert 0.5 < similarity("hades", "hade") < 1.0


def test_similarity_case_insensitive():
    assert similarity("HADES", "hades") == 1.0



##########################################################
#  is_sequel                                             #
##########################################################

def test_is_sequel_roman():
    assert is_sequel("Hades II") is True


def test_is_sequel_digit():
    assert is_sequel("Hades 2") is True


def test_is_sequel_not_sequel():
    assert is_sequel("Hades") is False


def test_is_sequel_with_roman_iii():
    assert is_sequel("Diablo III") is True


def test_is_sequel_ignore_years():
    assert is_sequel("Cyberpunk 2077") is False



##########################################################
#  sanitize_title                                        #
##########################################################

def test_sanitize_title_basic():
    assert sanitize_title("Sea of Thieves") == "sea of thieves"


def test_sanitize_title_colon():
    assert sanitize_title("Halo: Infinite") == "halo infinite"


def test_sanitize_title_special_chars():
    assert sanitize_title("Hades!!? II***") == "hades ii"


def test_sanitize_title_empty():
    assert sanitize_title("") == ""


def test_sanitize_title_unicode():
    assert sanitize_title("Café™ Edition") == "café edition"
