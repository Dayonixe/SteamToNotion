import pytest
from unittest.mock import patch, MagicMock
import json

from src.notion_api import (
    get_notion_pages,
    update_notion_page,
    get_app_id_for_page
)


##########################################################
#  get_notion_pages                                      #
##########################################################
@patch("src.notion_api.requests.post")
def test_get_notion_pages_single_page(mock_post):
    """The DB returns a single page without pagination."""
    mock_post.return_value.json.return_value = {
        "results": [{"id": "page1"}],
        "has_more": False
    }

    pages = get_notion_pages()
    assert len(pages) == 1
    assert pages[0]["id"] == "page1"
    assert mock_post.call_count == 1


@patch("src.notion_api.requests.post")
def test_get_notion_pages_multiple_pages(mock_post):
    """Correct pagination test (has_more = True)."""

    # First reply (page 1)
    first = MagicMock()
    first.json.return_value = {
        "results": [{"id": "page1"}],
        "has_more": True,
        "next_cursor": "cursor123"
    }

    # Second answer (page 2)
    second = MagicMock()
    second.json.return_value = {
        "results": [{"id": "page2"}],
        "has_more": False
    }

    mock_post.side_effect = [first, second]

    pages = get_notion_pages()
    assert len(pages) == 2
    assert pages[0]["id"] == "page1"
    assert pages[1]["id"] == "page2"
    assert mock_post.call_count == 2


##########################################################
#  get_app_id_for_page                                   #
##########################################################
def test_get_app_id_for_page_existing_id():
    """If the ID is already present in Notion, it is returned directly."""
    page = {
        "properties": {
            "ID": {"number": 1234}
        }
    }
    assert get_app_id_for_page(page) == 1234


@patch("src.notion_api.search_app_id_by_name")
def test_get_app_id_for_page_from_name(mock_search):
    """If the ID is not present, we search by the name of the game."""
    mock_search.return_value = 5678

    page = {
        "properties": {
            "ID": {"number": None},
            "Name": {"title": [{"plain_text": "Hades"}]}
        }
    }

    assert get_app_id_for_page(page) == 5678
    mock_search.assert_called_once_with("Hades")


@patch("src.notion_api.search_app_id_by_name")
def test_get_app_id_for_page_no_search_result(mock_search):
    """No Steam match -> returns None."""
    mock_search.return_value = None

    page = {
        "properties": {
            "ID": {"number": None},
            "Name": {"title": [{"plain_text": "Unknown Game"}]}
        }
    }

    assert get_app_id_for_page(page) is None


def test_get_app_id_for_page_no_name():
    """There is no ID or Name -> None."""
    page = {"properties": {}}
    assert get_app_id_for_page(page) is None


##########################################################
#  update_notion_page                                    #
##########################################################
@patch("src.notion_api.requests.patch")
def test_update_notion_page_success(mock_patch):
    """Successful testing of a Notion update."""

    # Notion renvoie un JSON valide
    mock_patch.return_value.status_code = 200
    mock_patch.return_value.json.return_value = {"object": "page", "id": "test123"}

    game = {
        "app_id": 1145360,
        "name": "Hades",
        "price": 24.5,
        "released": True,
        "release_date": "2020-09-17",
        "genres": ["Action", "Indie"],
        "hltb_time": 15.2,
        "metacritic_score": 93,
        "icon_image": "https://example.com/icon.png",
        "cover_image": "https://example.com/cover.jpg",
    }

    res = update_notion_page("page123", game)

    assert res["id"] == "test123"
    assert mock_patch.call_count == 1

    sent = mock_patch.call_args[1]["data"]
    sent_json = json.loads(sent)

    assert sent_json["icon"]["external"]["url"] == "https://example.com/icon.png"
    assert sent_json["cover"]["external"]["url"] == "https://example.com/cover.jpg"
    assert sent_json["properties"]["ID"]["number"] == 1145360
    assert sent_json["properties"]["Price"]["number"] == 24.5
    assert sent_json["properties"]["Estimated duration"]["number"] == 15.2


@patch("src.notion_api.requests.patch")
def test_update_notion_page_invalid_json(mock_patch):
    """Notion returns invalid HTML or JSON -> must handle properly."""

    mock_patch.return_value.status_code = 400
    mock_patch.return_value.json.side_effect = ValueError("not JSON")
    mock_patch.return_value.text = "<html>Error</html>"

    game = {
        "app_id": 999,
        "name": "Test",
        "price": None,
        "released": False,
        "release_date": None,
        "genres": [],
        "hltb_time": None,
        "metacritic_score": None,
        "icon_image": "https://example.com/i.png",
        "cover_image": "https://example.com/c.png",
    }

    res = update_notion_page("page123", game)
    assert res is None
