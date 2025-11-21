import sqlite3
import sys
import json
import re
import numpy as np
from transformers import BertTokenizer, BertModel
import torch

# --- Configuração ---
DB_FILE = "hearthstone.db"
BERT_MODEL_NAME = "bert-base-uncased"
# --------------------

def get_db_connection():
    """Estabelece uma conexão com o banco de dados SQLite."""
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao SQLite: {e}", file=sys.stderr)
        sys.exit(1)

def add_embedding_column(conn):
    """Adiciona a coluna 'row_embedding' à tabela 'cards' se ela não existir."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(cards)")
    columns = [info[1] for info in cur.fetchall()]

    if "row_embedding" not in columns:
        print("Adicionando a coluna 'row_embedding' (BLOB) à tabela 'cards'...")
        cur.execute("ALTER TABLE cards ADD COLUMN row_embedding BLOB;")
        conn.commit()
        print("Coluna 'row_embedding' adicionada com sucesso.")
    else:
        print("A coluna 'row_embedding' já existe.")
    cur.close()

def load_bert_model():
    """Carrega o modelo e o tokenizador BERT pré-treinados."""
    print(f"Carregando o modelo e tokenizador '{BERT_MODEL_NAME}'...")
    try:
        tokenizer = BertTokenizer.from_pretrained(BERT_MODEL_NAME)
        model = BertModel.from_pretrained(BERT_MODEL_NAME)
        print("Modelo e tokenizador carregados com sucesso.")
        return tokenizer, model
    except Exception as e:
        print(f"Erro ao carregar o modelo da Hugging Face: {e}", file=sys.stderr)
        print("Verifique sua conexão com a internet e se as bibliotecas 'torch' e 'transformers' estão instaladas.", file=sys.stderr)
        sys.exit(1)

def augment_description(description, keyword_effects):
    """Substitui keywords no texto da descrição pelo seu efeito, tratando casos especiais."""
    if not description:
        return ""

    def replace_keyword(match):
        keyword_raw = match.group(1)
        # Normaliza a keyword para a busca (minúscula, sem ':')
        keyword_lookup = keyword_raw.replace(":", "").lower()
        
        effect = keyword_effects.get(keyword_lookup)
        
        # Retorna a keyword original (sem tags) com seu efeito
        if effect:
            return f"{keyword_raw} ({effect})"
        
        # Se não encontrar efeito, retorna a keyword original sem as tags
        return keyword_raw

    # Substitui as keywords e remove tags de formatação de valores
    processed_desc = re.sub(r'<b>(.*?)</b>', replace_keyword, description)
    processed_desc = processed_desc.replace('<i>', '').replace('</i>', '')
    return processed_desc

def generate_and_store_embeddings(conn, tokenizer, model):
    """Gera e armazena embeddings em lotes para não sobrecarregar a memória."""
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Carrega os efeitos das keywords
    try:
        cur.execute("SELECT keyword, effect FROM keywords")
        keyword_effects = {row["keyword"].lower(): row["effect"] for row in cur.fetchall()}
        print(f"Carregadas {len(keyword_effects)} keywords para aumentar a descrição.")
    except sqlite3.OperationalError:
        print("Aviso: Tabela 'keywords' não encontrada. A descrição não será aumentada.", file=sys.stderr)
        keyword_effects = {}

    PROPERTIES_TO_EMBED = [
        "card_id", "dbf_id", "name", "description", "cost", "attack",
        "health", "rarity", "card_set", "card_class", "card_type", "races"
    ]
    select_query = f"SELECT {', '.join(PROPERTIES_TO_EMBED)} FROM cards WHERE row_embedding IS NULL"
    
    total_processed_count = 0
    batch_size = 100

    while True:
        print(f"\nProcessando um novo lote de até {batch_size} cartas...")
        cur.execute(select_query)
        cards_to_process = cur.fetchmany(batch_size)

        if not cards_to_process:
            print("Nenhuma carta nova para gerar embeddings.")
            break

        print(f"Encontradas {len(cards_to_process)} cartas para processar neste lote.")

        card_ids = [row["card_id"] for row in cards_to_process]
        
        texts_to_embed = []
        for card in cards_to_process:
            card_dict = {}
            for prop in PROPERTIES_TO_EMBED:
                value = card[prop]
                if prop == 'description' and value:
                    value = augment_description(value, keyword_effects)
                if value is not None and str(value).strip() != '':
                    card_dict[prop] = value
            
            json_text = json.dumps(card_dict, ensure_ascii=False)
            # print(json_text) # Descomente para depurar o texto final
            texts_to_embed.append(json_text)

        print("Tokenizando os textos das cartas...")
        inputs = tokenizer(texts_to_embed, padding=True, truncation=True, return_tensors="pt", max_length=512)

        print("Gerando embeddings...")
        with torch.no_grad():
            outputs = model(**inputs)
            embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()

        update_data = []
        for i, card_id in enumerate(card_ids):
            embedding_blob = embeddings[i].tobytes()
            update_data.append((embedding_blob, card_id))

        print("Atualizando o banco de dados...")
        update_query = "UPDATE cards SET row_embedding = ? WHERE card_id = ?"
        try:
            with conn:
                cur.executemany(update_query, update_data)
            
            processed_in_batch = len(update_data)
            total_processed_count += processed_in_batch
            print(f"Sucesso! {processed_in_batch} embeddings armazenados neste lote.")
            print(f"Total de cartas processadas até agora: {total_processed_count}")

        except sqlite3.Error as e:
            print(f"Erro ao atualizar o banco de dados no lote: {e}", file=sys.stderr)
            sys.exit(1)

    if total_processed_count == 0:
        print("\nNenhuma carta foi processada na sessão.")
    else:
        print(f"\nOperação de embedding concluída. Total de {total_processed_count} cartas foram processadas.")

def main():
    """
    Função principal para orquestrar a geração e armazenamento de embeddings.
    """
    conn = None
    try:
        # Passo 1: Conectar ao DB e adicionar a coluna
        conn = get_db_connection()
        add_embedding_column(conn)

        # Passo 2: Carregar o modelo BERT
        tokenizer, model = load_bert_model()

        # Passo 3: Gerar e armazenar os embeddings
        generate_and_store_embeddings(conn, tokenizer, model)

        print("\nOperação de embedding concluída com sucesso!")
    finally:
        if conn:
            conn.close()
            print("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    main()
