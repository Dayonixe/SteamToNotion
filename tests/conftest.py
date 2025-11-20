import pytest
from src import rawg_api

@pytest.fixture(autouse=True)
def reset_rawg_cache():
    rawg_api.RAWG_CACHE.clear()
