import requests
import json
import sqlite3

DB_FILE = "hearthstone.db"
JSON_FILE = "hearthstone_cards.json"

def download_card_data():
    """
    Downloads the latest Hearthstone card data from hearthstonejson.com.
    """
    url = "https://api.hearthstonejson.com/v1/latest/enUS/cards.json"
    print(f"Downloading card data from {url}...")

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        print("Download successful. Saving data to hearthstone_cards.json...")
        with open("hearthstone_cards.json", "w", encoding="utf-8") as f:
            json.dump(response.json(), f, ensure_ascii=False, indent=4)
        print("Card data saved to hearthstone_cards.json")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during download: {e}")

def update_database():
    """
    Reads the downloaded JSON and inserts/updates the data in a SQLite database.
    """
    print(f"Updating database {DB_FILE}...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cards (
        id TEXT PRIMARY KEY,
        dbfId INTEGER UNIQUE,
        name TEXT,
        cardClass TEXT,
        cost INTEGER,
        attack INTEGER,
        health INTEGER,
        text TEXT,
        rarity TEXT,
        card_set TEXT,
        type TEXT,
        races TEXT
    )
    """)

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    cards = data
    for card in cards:
        #TODO tirar tb as castas repetidas de outras edições & PLACEHOLDER_202204, VANILLA?, REVENDRETH?, HERO_SKINS, BATTLE_OF_THE_BANDS, CORE, EXPERT1, LEGACY, EVENT
        # Talvez jogar num set temporário e depois inserir só os únicos por name e/ou text.
        if card.get("collectible"):
            races = card.get("races")
            races_str = ",".join(races) if races else None
            cursor.execute("""
            INSERT OR REPLACE INTO cards (id, dbfId, name, cardClass, cost, attack, health, text, rarity, card_set, type, races)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card.get("id"),
                card.get("dbfId"),
                card.get("name"),
                card.get("cardClass"),
                card.get("cost"),
                card.get("attack"),
                card.get("health"),
                card.get("text"),
                card.get("rarity"),
                card.get("set"),
                card.get("type"),
                races_str
            ))

    conn.commit()
    conn.close()
    print("Database update complete.")

if __name__ == "__main__":
    try:
#        access_token = get_access_token()
        download_card_data()
        update_database()
    except requests.exceptions.RequestException as e:
        print(f"A critical error occurred: {e}")
