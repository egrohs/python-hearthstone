import sqlite3
import re
import sys

# --- Configuração ---
DB_FILE = "hearthstone.db"
COLUMNS_TO_UPDATE = [
    "SURV",
    "FINISHER",
    "BOARD+",
    "BOARD-",
    "HAND+",
    "HAND-",
    "FETCH",
    "MANA",
    "VALUE+",
    "OPTIONS"
]

def regexp(expr, item):
    """Função REGEXP personalizada para ser usada no SQLite."""
    if item is None:
        return False
    try:
        # Remove as tags HTML da descrição antes de aplicar a regex
        cleaned_item = re.sub('<[^<]+?>', '', item)
        reg = re.compile(expr, re.IGNORECASE)
        return reg.search(cleaned_item) is not None
    except re.error as e:
        print(f"Erro de Regex com a expressão '{expr}': {e}", file=sys.stderr)
        return False

def apply_keyword_updates():
    """
    Lê a tabela 'keywords', aplica a regex de cada uma na tabela 'cards'
    e atualiza os atributos da carta se houver correspondência.
    """
    conn = None
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect(DB_FILE)
        
        # Adicionar a função regexp personalizada à conexão com o SQLite
        conn.create_function("REGEXP", 2, regexp)
        
        cursor = conn.cursor()

        # Zera todas as colunas de atributos para garantir um cálculo limpo
        print("Zerando colunas de atributos na tabela 'cards'...")
        reset_set_clause = ", ".join([f'"{col}" = 0' for col in COLUMNS_TO_UPDATE])
        cursor.execute(f"UPDATE cards SET {reset_set_clause}")
        print(f"  -> {cursor.rowcount} cartas tiveram seus atributos zerados.")

        print("\nLendo palavras-chave da tabela 'keywords'...")
        # Seleciona a regex e todas as colunas de atributos para cada palavra-chave
        quoted_columns = [f'"{col}"' for col in COLUMNS_TO_UPDATE]
        cursor.execute(f"SELECT regex, {', '.join(quoted_columns)} FROM keywords")
        keywords = cursor.fetchall()
        
        if not keywords:
            print("Nenhuma palavra-chave encontrada na tabela 'keywords'. Encerrando.")
            return

        total_updates = 0
        print(f"\nIniciando atualização de cartas com base em {len(keywords)} palavras-chave...")

        # Construir a parte SET da query dinamicamente
        set_clause = ", ".join([f'"{col}" = IFNULL("{col}", 0) + ?' for col in COLUMNS_TO_UPDATE])
        
        for i, keyword_row in enumerate(keywords):
            regex_pattern = keyword_row[0]
            values_to_add = keyword_row[1:]

            if not regex_pattern:
                print(f"  - Ignorando linha {i+1} da keyword por não ter regex.")
                continue

            print(f"\nProcessando keyword {i+1}/{len(keywords)} com regex: '{regex_pattern}'")

            try:
                # A query de UPDATE que usa a função REGEXP
                # Ela verifica a correspondência no texto da carta
                sql_update = f"""
                    UPDATE cards
                    SET {set_clause}
                    WHERE REGEXP(?, description)
                """
                # Os parâmetros para a query: valores para o SET e a regex para o WHERE
                params = list(values_to_add) + [regex_pattern]
                
                print("Executando SQL: {sql_update}")
                update_cursor = conn.cursor()
                update_cursor.execute(sql_update, params)
                
                updated_count = update_cursor.rowcount
                if updated_count > 0:
                    print(f"  -> {updated_count} carta(s) atualizada(s).")
                    total_updates += updated_count
                else:
                    print("  -> Nenhuma carta correspondeu a esta regex.")

            except sqlite3.Error as e:
                print(f"  -> Erro ao processar a regex '{regex_pattern}': {e}", file=sys.stderr)

        # Salvar (commit) as alterações no banco de dados
        conn.commit()
        print(f"\nProcesso concluído! Um total de {total_updates} atualizações foram realizadas.")

    except sqlite3.Error as e:
        print(f"Ocorreu um erro no banco de dados: {e}", file=sys.stderr)
    
    finally:
        # Fechar a conexão
        if conn:
            conn.close()
            print("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    apply_keyword_updates()
