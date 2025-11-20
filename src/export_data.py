import time
from .notion_api import get_notion_pages, get_app_id_for_page, update_notion_page
from .steam_api import get_steam_game_details


if __name__ == "__main__":
    pages = get_notion_pages()

    for page in pages:
        page_id = page["id"]

        # Vérification plateforme
        platform_prop = page["properties"].get("Platform", {})
        platform_value = None

        if platform_prop.get("select"):
            platform_value = platform_prop["select"]["name"]

        # Si Platform != Steam, la page est ignorée
        if platform_value != "Steam":
            print(f"⏭️ Page ignorée ({page_id}) — Platform = {platform_value}\n")
            continue

        # Lecture de la colonne "ID"
        app_id = get_app_id_for_page(page)

        # S'il n'y a pas d'ID du jeu, la page est ignorée
        if not app_id:
            print(f"⚠️ ID absent pour la page {page_id}")
            continue

        print(f"🔍 Récupération Steam pour app_id = {app_id}")

        game_data = get_steam_game_details(app_id)

        # S'il n'y a pas de donnée du jeu, la page est ignorée
        if not game_data:
            print(f"❌ Impossible d'obtenir les infos Steam pour {app_id}")
            continue

        print(f"📥 Données récupérées : {game_data}")

        update_notion_page(page_id, game_data)

        print(f"✅ Page mise à jour : {page_id}\n")

        if game_data["released"]:
            time.sleep(0.25)  # Evite rate limiting
