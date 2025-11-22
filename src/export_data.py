import time
from .notion_api import get_notion_pages, get_app_id_for_page, update_notion_page
from .steam_api import get_steam_game_details


if __name__ == "__main__":
    pages = get_notion_pages()

    for page in pages:
        page_id = page["id"]

        # Platform verification
        platform_prop = page["properties"].get("Platform", {})
        platform_value = None

        if platform_prop.get("select"):
            platform_value = platform_prop["select"]["name"]

        # If Platform != Steam, the page is ignored.
        if platform_value != "Steam":
            print(f"⏭️ Page ignored ({page_id}) — Platform = {platform_value}\n")
            continue

        # Reading the 'ID' column
        app_id = get_app_id_for_page(page)

        # If there is no game ID, the page is ignored
        if not app_id:
            print(f"❌ ID missing for page {page_id}")
            continue

        print(f"🔍 Steam recovery for app_id = {app_id}")

        game_data = get_steam_game_details(app_id)

        # If there is no game data, the page is ignored.
        if not game_data:
            print(f"❌ Unable to obtain Steam information for {app_id}")
            continue

        print(f"📥 Data retrieved : {game_data}")

        update_notion_page(page_id, game_data)

        print(f"✅ Page updated : {page_id}\n")

        # Avoid rate limiting
        if game_data["released"]:
            time.sleep(0.25)
