import json
import os
import sqlite3
import sys

DB_FILE = os.path.join(os.path.dirname(__file__), 'hearthstone.db')

def process_collection():
    file_path = os.path.join(os.path.dirname(__file__), 'collection.json')
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    collection = data.get('collection', {})
    
    # Conecta ao banco de dados
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao SQLite: {e}", file=sys.stderr)
        return

    # Descobre o nome da coluna do ID e checa se 'own' existe
    cur.execute("PRAGMA table_info(cards)")
    cols = [info[1] for info in cur.fetchall()]
    
    if not cols:
        print("Tabela 'cards' não encontrada no banco de dados.")
        conn.close()
        return
        
    dbf_col = "dbfId" if "dbfId" in cols else "dbf_id"
    
    if "own" not in cols:
        print("Adicionando a coluna 'own' à tabela 'cards'...")
        cur.execute("ALTER TABLE cards ADD COLUMN own INTEGER DEFAULT 0;")
        conn.commit()

    print("Processando quantidades e atualizando o banco de dados...")
    update_data = []
    for dbf_id, counts in collection.items():
        if len(counts) >= 3:
            max_count = max(counts[0], counts[2])
            update_data.append((max_count, int(dbf_id)))

    try:
        cur.executemany(f"UPDATE cards SET own = ? WHERE {dbf_col} = ?", update_data)
        conn.commit()
        print(f"{cur.rowcount} cartas foram atualizadas com sucesso na coluna 'own'.")
    except sqlite3.Error as e:
        print(f"Erro ao atualizar o banco de dados: {e}", file=sys.stderr)
    finally:
        conn.close()

if __name__ == "__main__":
    process_collection()