import os
import sys
import sqlite3
import json # Usaremos json para armazenar a lista de raças
from hearthstone.cardxml import load
from hearthstone.enums import CardType

# --- Configuração ---
DB_FILE = "hearthstone.db"
# --------------------

def get_db_connection():
    """
    Estabelece uma conexão com o banco de dados SQLite. O arquivo será criado se não existir.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao SQLite: {e}", file=sys.stderr)
        sys.exit(1)

def create_cards_table(conn):
    """
    Cria a tabela 'cards' se ela não existir.
    """
    create_table_query = """
    CREATE TABLE IF NOT EXISTS cards (
        card_id TEXT PRIMARY KEY,
        dbf_id INTEGER UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        flavor_text TEXT,
        cost INTEGER,
        attack INTEGER,
        health INTEGER,
        rarity TEXT,
        card_set TEXT,
        card_class TEXT,
        card_type TEXT,
        races TEXT, -- SQLite não tem array, usaremos JSON
        artist TEXT,
        collectible INTEGER DEFAULT 0 -- SQLite usa 0 para False e 1 para True
    );
    """
    with conn:
        cur = conn.cursor()
        cur.execute(create_table_query)
        # Cria um índice para pesquisas mais rápidas por dbf_id
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_dbf_id ON cards(dbf_id);")
    print("Tabela 'cards' verificada/criada com sucesso.")

def populate_database(conn):
    """
    Carrega os dados do CardDefs.xml, filtra as cartas colecionáveis e as insere no banco de dados.
    """
    print("Carregando CardDefs.xml...")
    # A biblioteca hearthstone_data baixa e armazena em cache o XML
    try:
        cards, _ = load(locale="enUS")
    except Exception as e:
        print(f"Erro ao carregar CardDefs.xml: {e}", file=sys.stderr)
        print("Certifique-se de que a biblioteca 'hearthstone_data' está instalada e que você tem conexão com a internet na primeira execução.", file=sys.stderr)
        sys.exit(1)

    print(f"{len(cards)} cartas encontradas no total. Filtrando por colecionáveis...")

    collectible_cards_data = []
    for card in cards.values():
        if not card.collectible:
            continue

        # Ignora encantamentos e poderes de herói que podem ser marcados como colecionáveis
        if card.type in (CardType.ENCHANTMENT, CardType.HERO_POWER):
            continue

        card_data = (
            card.id,
            card.dbf_id,
            card.name,
            card.description,
            card.flavortext,
            card.cost,
            card.atk,
            card.health,
            card.rarity.name if card.rarity else None,
            card.card_set.name if card.card_set else None,
            card.card_class.name if card.card_class else None,
            card.type.name if card.type else None,
            json.dumps([race.name for race in card.races]), # Converte lista para string JSON
            card.artist,
            1 if card.collectible else 0
        )
        collectible_cards_data.append(card_data)

    print(f"{len(collectible_cards_data)} cartas colecionáveis para inserir/atualizar.")

    if not collectible_cards_data:
        print("Nenhuma carta colecionável encontrada para processar.")
        return

    with conn:
        cur = conn.cursor()
        # Utiliza INSERT OR REPLACE para atualizar cartas existentes (UPSERT no SQLite)
        insert_query = """
        INSERT OR REPLACE INTO cards (
            card_id, dbf_id, name, description, flavor_text, cost, attack, health,
            rarity, card_set, card_class, card_type, races, artist, collectible
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        print("Inserindo dados no banco de dados...")
        cur.executemany(insert_query, collectible_cards_data)

    print(f"Sucesso! {len(collectible_cards_data)} cartas colecionáveis foram inseridas/atualizadas no banco de dados.")

def main():
    """
    Função principal para orquestrar a conexão, criação da tabela e população do banco de dados SQLite.
    """
    conn = None
    try:
        conn = get_db_connection()
        create_cards_table(conn)
        populate_database(conn)
    finally:
        if conn:
            conn.close()
            print("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    main()
