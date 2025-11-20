import os
import sys
import psycopg2
from psycopg2.extras import execute_values
from hearthstone.cardxml import load
from hearthstone.enums import CardType

# --- Configuração do Banco de Dados ---
# Altere os valores abaixo para corresponder à sua configuração do PostgreSQL
DB_CONFIG = {
    "dbname": "hearthstone",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": "5432"
}
# ------------------------------------

def get_db_connection():
    """
    Estabelece uma conexão com o banco de dados PostgreSQL usando a configuração no script.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.OperationalError as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}", file=sys.stderr)
        print("Verifique se o banco de dados está em execução e se as configurações em DB_CONFIG estão corretas.", file=sys.stderr)
        sys.exit(1)

def create_cards_table(conn):
    """
    Cria a tabela 'cards' se ela não existir.
    """
    create_table_query = """
    CREATE TABLE IF NOT EXISTS cards (
        card_id VARCHAR(50) PRIMARY KEY,
        dbf_id INT UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        flavor_text TEXT,
        cost INT,
        attack INT,
        health INT,
        rarity VARCHAR(50),
        card_set VARCHAR(50),
        card_class VARCHAR(50),
        card_type VARCHAR(50),
        races TEXT[],
        artist VARCHAR(255),
        collectible BOOLEAN DEFAULT FALSE
    );
    """
    with conn.cursor() as cur:
        cur.execute(create_table_query)
        # Cria um índice para pesquisas mais rápidas por dbf_id
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_dbf_id ON cards(dbf_id);")
        conn.commit()
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
            [race.name for race in card.races], # Converte enums de raça para strings
            card.artist,
            card.collectible
        )
        collectible_cards_data.append(card_data)

    print(f"{len(collectible_cards_data)} cartas colecionáveis para inserir/atualizar.")

    if not collectible_cards_data:
        print("Nenhuma carta colecionável encontrada para processar.")
        return

    with conn.cursor() as cur:
        # Utiliza ON CONFLICT para atualizar cartas existentes (UPSERT)
        insert_query = """
        INSERT INTO cards (
            card_id, dbf_id, name, description, flavor_text, cost, attack, health,
            rarity, card_set, card_class, card_type, races, artist, collectible
        ) VALUES %s
        ON CONFLICT (card_id) DO UPDATE SET
            dbf_id = EXCLUDED.dbf_id,
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            flavor_text = EXCLUDED.flavor_text,
            cost = EXCLUDED.cost,
            attack = EXCLUDED.attack,
            health = EXCLUDED.health,
            rarity = EXCLUDED.rarity,
            card_set = EXCLUDED.card_set,
            card_class = EXCLUDED.card_class,
            card_type = EXCLUDED.card_type,
            races = EXCLUDED.races,
            artist = EXCLUDED.artist,
            collectible = EXCLUDED.collectible;
        """
        print("Inserindo dados no banco de dados...")
        execute_values(cur, insert_query, collectible_cards_data)
        conn.commit()

    print(f"Sucesso! {len(collectible_cards_data)} cartas colecionáveis foram inseridas/atualizadas no banco de dados.")

def main():
    """
    Função principal para orquestrar a conexão, criação da tabela e população do banco.
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
