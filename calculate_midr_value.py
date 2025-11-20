import sqlite3
import sys

# --- Configuração ---
DB_FILE = "hearthstone.db"
# --------------------

def get_db_connection():
    """
    Estabelece uma conexão com o banco de dados SQLite.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao SQLite: {e}", file=sys.stderr)
        sys.exit(1)

def add_midr_value_column(conn):
    """
    Adiciona a coluna 'midr_value' à tabela 'cards' se ela não existir.
    """
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(cards)")
    columns = [info[1] for info in cur.fetchall()]

    if "midr_value" not in columns:
        print("Adicionando a coluna 'midr_value' à tabela 'cards'...")
        cur.execute("ALTER TABLE cards ADD COLUMN midr_value REAL;")
        conn.commit()
        print("Coluna 'midr_value' adicionada com sucesso.")
    else:
        print("A coluna 'midr_value' já existe.")
    cur.close()

def calculate_and_update_midr_value(conn):
    """
    Calcula e preenche a coluna 'midr_value' com base na fórmula (attack + health) / cost.
    """
    print("Calculando e atualizando 'midr_value' para todas as cartas...")
    # Usamos CAST para garantir a divisão de ponto flutuante
    # E um CASE para evitar divisão por zero
    update_query = """
    UPDATE cards
    SET midr_value = CASE
        WHEN cost > 0 THEN (CAST(attack AS REAL) + health) / cost
        ELSE 0
    END;
    """
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(update_query)
            print(f"{cur.rowcount} registros foram atualizados.")
    except sqlite3.Error as e:
        print(f"Erro ao atualizar a coluna 'midr_value': {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """
    Função principal para orquestrar a adição e cálculo da coluna midr_value.
    """
    conn = None
    try:
        conn = get_db_connection()
        add_midr_value_column(conn)
        calculate_and_update_midr_value(conn)
        print("\nOperação concluída com sucesso!")
    finally:
        if conn:
            conn.close()
            print("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    main()
