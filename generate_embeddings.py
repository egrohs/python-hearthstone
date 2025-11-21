import sqlite3
import sys
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

def generate_and_store_embeddings(conn, tokenizer, model):
    """Gera embeddings para as descrições das cartas e as armazena no banco de dados."""
    conn.row_factory = sqlite3.Row  # Acessar colunas por nome
    cur = conn.cursor()

    PROPERTIES_TO_EMBED = [
        "card_id", "dbf_id", "name", "description", "cost", "attack",
        "health", "rarity", "card_set", "card_class", "card_type", "races"
    ]
    select_query = f"SELECT {', '.join(PROPERTIES_TO_EMBED)} FROM cards WHERE row_embedding IS NULL"

    # Seleciona cartas que ainda não têm um embedding
    cur.execute(select_query)
    cards_to_process = cur.fetchmany(10)

    if not cards_to_process:
        print("Nenhuma carta nova para gerar embeddings.")
        return

    print(f"Encontradas {len(cards_to_process)} cartas para processar.")

    card_ids = [row["card_id"] for row in cards_to_process]
    
    # Constrói o texto para o embedding
    texts_to_embed = []
    for card in cards_to_process:
        text_parts = []
        for prop in PROPERTIES_TO_EMBED:
            value = card[prop]
            if value is not None and str(value).strip() != '':
                text_parts.append(f"{prop}:{value}")
        texts_to_embed.append(" ".join(text_parts))

    print("Tokenizando os textos das cartas...")
    # Processa em lotes para não sobrecarregar a memória, com max_length maior
    inputs = tokenizer(texts_to_embed, padding=True, truncation=True, return_tensors="pt", max_length=256)

    print("Gerando embeddings (isso pode levar um tempo)...")
    with torch.no_grad():
        outputs = model(**inputs)
        # Usamos o embedding do token [CLS] como a representação da sentença
        embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()

    print("Preparando dados para inserção no banco de dados...")
    update_data = []
    for i, card_id in enumerate(card_ids):
        # Converte o array numpy para bytes para armazenamento como BLOB
        embedding_blob = embeddings[i].tobytes()
        update_data.append((embedding_blob, card_id))

    print("Atualizando o banco de dados...")
    update_query = "UPDATE cards SET row_embedding = ? WHERE card_id = ?"
    try:
        with conn:
            cur.executemany(update_query, update_data)
        print(f"Sucesso! {len(update_data)} embeddings foram armazenados no banco de dados.")
    except sqlite3.Error as e:
        print(f"Erro ao atualizar o banco de dados: {e}", file=sys.stderr)
        sys.exit(1)

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
