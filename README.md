# User Manual

Team : Théo Pirouelle

<a href="https://www.python.org/">
  <img src="https://img.shields.io/badge/language-python-blue?style=flat-square" alt="laguage-python" />
</a>

---

## Preamble

To use the script, you'll need a Notion API key and a Notion database ID.
You'll need to create a `.env` file containing the variables `NOTION_TOKEN` and `NOTION_DATABASE_ID` with your API key and database ID for the script to work correctly.

> [!IMPORTANT]
> To use the application, you need to be connected to the internet so that it can call the Steam and Notion APIs.

## Installation

> [!IMPORTANT]
> For the application to work properly, the `.env` file must be in the same place as the executable.

> [!NOTE]
> For information, the code has been developed and works with the following library versions:
> | Library | Version |
> | --- | --- |
> | requests | 2.32.5 |

Please also remember to install Python. The code was developed and works with Python 3.11.

---

## Usage

In the Notion database configured in the `.env`, the following properties are required for the script to work:
- Platform (select): For the page to be processed, the selected platform must be ‘Steam’.
- ID (number): Similarly, for the page to be processed, there must be a game ID (or at least the game title as the page title).
- Price (number)
- Released (checkbox)
- Genres (multi_select)
- Metacritic (number)
- Release date (date)

To easily find the game ID, simply go to the game's page in the Steam store and retrieve the ID from the page's URL.
For example, in the URL `https://store.steampowered.com/app/3097560/Liars_Bar/`, the game ID is `3097560`.

To run the script in a Linux or PowerShell terminal:
```bash
python[3] [path/to/]export_data.py
```

The script will run and you should see the following lines displayed, for example:
```
🔍 Récupération Steam pour app_id = 1172620
📥 Données récupérées : {'app_id': 1172620, 'name': 'Sea of Thieves: 2025 Edition', 'price': 39.99, 'released': True, 'release_date': '2020-06-03', 'genres': ['Action', 'Adventure'], 'metacritic_score': None, 'cover_image': 'https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1172620/library_hero.jpg', 'icon_image': 'https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1172620/logo.png'}
✅ Page mise à jour : xxxxxxxxxxxxxxxx

🔍 Récupération Steam pour app_id = 1203180
📥 Données récupérées : {'app_id': 1203180, 'name': 'Breakwaters: Crystal Tides', 'price': 16.79, 'released': True, 'release_date': '2021-12-09', 'genres': ['Action', 'Adventure', 'Indie', 'Simulation', 'Early Access'], 'metacritic_score': None, 'cover_image': 'https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1203180/library_hero.jpg', 'icon_image': 'https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1203180/logo.png'}
✅ Page mise à jour : xxxxxxxxxxxxxxxx

⏭️ Page ignorée (xxxxxxxxxxxxxxxx) — Platform = Epic Games

🔍 Récupération Steam pour app_id = 113200
📥 Données récupérées : {'app_id': 113200, 'name': 'The Binding of Isaac', 'price': 4.99, 'released': True, 'release_date': '2011-09-28', 'genres': ['Action', 'Adventure', 'Indie', 'RPG'], 'metacritic_score': 84, 'cover_image': 'https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/113200/library_hero.jpg', 'icon_image': 'https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/113200/logo.png'}
✅ Page mise à jour : xxxxxxxxxxxxxxxx

[...]
```

---

## Result

Before:
<img src="docs/Result_before" alt="before" />

After:
<img src="docs/Result_after" alt="after" />
