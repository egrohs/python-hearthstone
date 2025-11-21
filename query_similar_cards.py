import sqlite3
import numpy as np
import argparse
import sys
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans

DB_FILE = "hearthstone.db"

def get_db_connection():
    """Estabelece uma conexão com o banco de dados SQLite."""
    try:
        return sqlite3.connect(DB_FILE)
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao SQLite: {e}", file=sys.stderr)
        return None

def load_data_and_embeddings(conn):
    """Carrega nomes de cartas, IDs e seus embeddings do banco de dados."""
    print("Carregando dados e embeddings do banco de dados...")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        cur.execute("SELECT card_id, name, row_embedding FROM cards WHERE row_embedding IS NOT NULL")
        rows = cur.fetchall()
    except sqlite3.OperationalError as e:
        print(f"Erro ao ler a tabela 'cards': {e}", file=sys.stderr)
        print("Verifique se o banco de dados existe e se o script 'generate_embeddings.py' foi executado.", file=sys.stderr)
        return None, None, None

    if not rows:
        print("Nenhum embedding encontrado no banco de dados.", file=sys.stderr)
        return None, None, None

    card_ids = []
    card_names = []
    embeddings = []

    for row in rows:
        card_ids.append(row["card_id"])
        card_names.append(row["name"])
        embedding = np.frombuffer(row["row_embedding"], dtype=np.float32)
        if embedding.shape[0] == 768:
            embeddings.append(embedding)
        else:
            print(f"Aviso: Embedding para '{row['name']}' tem formato inesperado {embedding.shape} e será ignorado.", file=sys.stderr)

    if not embeddings:
        print("Nenhum embedding com formato válido foi carregado.", file=sys.stderr)
        return None, None, None

    print(f"{len(embeddings)} embeddings carregados com sucesso.")
    return card_names, np.array(embeddings), card_ids

def find_similar_cards(target_card_name, card_names, embeddings, top_k=10):
    """Encontra as cartas mais similares a uma carta alvo usando similaridade de cosseno."""
    try:
        target_index = card_names.index(target_card_name)
    except ValueError:
        print(f"Erro: A carta '{target_card_name}' não foi encontrada no banco de dados.", file=sys.stderr)
        matches = [name for name in card_names if target_card_name.lower() in name.lower()]
        if matches:
            print(f"Você quis dizer uma destas? {', '.join(matches[:5])}", file=sys.stderr)
        return None, None

    target_embedding = embeddings[target_index].reshape(1, -1)
    similarities = cosine_similarity(embeddings, target_embedding)
    similar_indices = similarities.flatten().argsort()[-top_k-1:-1][::-1]
    similar_scores = similarities[similar_indices].flatten()
    return similar_indices, similar_scores

def cluster_cards_by_mechanics(embeddings, n_clusters=20):
    """Agrupa cartas por mecânicas similares usando K-Means."""
    print(f"\nExecutando K-Means para agrupar cartas em {n_clusters} clusters...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(embeddings)
    print("Clusterização concluída.")
    return clusters

def main():
    """Função principal para executar ações baseadas em embeddings de cartas."""
    parser = argparse.ArgumentParser(
        description="Execute ações em embeddings de cartas de Hearthstone.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcomando para encontrar cartas similares
    parser_find = subparsers.add_parser("find", help="Encontra cartas semanticamente similares a uma carta alvo.")
    parser_find.add_argument(
        "card_name",
        type=str,
        help="O nome exato da carta para a qual encontrar similares. Ex: 'Fireball'"
    )
    parser_find.add_argument(
        "-k", "--top_k",
        type=int,
        default=10,
        help="O número de cartas similares a serem retornadas (padrão: 10)."
    )

    # Subcomando para clusterizar cartas
    parser_cluster = subparsers.add_parser("cluster", help="Agrupa cartas por mecânicas similares usando K-Means.")
    parser_cluster.add_argument(
        "-n", "--n_clusters",
        type=int,
        default=20,
        help="O número de clusters a serem formados (padrão: 20)."
    )

    args = parser.parse_args()

    conn = get_db_connection()
    if not conn:
        sys.exit(1)

    try:
        all_card_names, all_embeddings, _ = load_data_and_embeddings(conn)
        if all_card_names is None:
            sys.exit(1)

        if args.command == "find":
            similar_indices, similar_scores = find_similar_cards(
                args.card_name,
                all_card_names,
                all_embeddings,
                args.top_k
            )
            if similar_indices is not None:
                print(f"\n--- Cartas mais similares a '{args.card_name}' ---")
                for i, idx in enumerate(similar_indices):
                    score = similar_scores[i]
                    print(f"{i+1:2d}. {all_card_names[idx]} (Similaridade: {score:.4f})")
                print("----------------------------------------------------")

        elif args.command == "cluster":
            clusters = cluster_cards_by_mechanics(all_embeddings, args.n_clusters)
            
            grouped_cards = defaultdict(list)
            for card_name, cluster_id in zip(all_card_names, clusters):
                grouped_cards[cluster_id].append(card_name)

            print("\n--- Grupos de Cartas por Similaridade de Mecânica ---")
            for cluster_id, cards_in_cluster in sorted(grouped_cards.items()):
                print(f"\n--- Cluster {cluster_id} ---")
                # Imprime até 15 cartas por cluster para não poluir a saída
                print(", ".join(cards_in_cluster[:15]))
                if len(cards_in_cluster) > 15:
                    print(f"... e mais {len(cards_in_cluster) - 15} cartas.")
            print("\n---------------------------------------------------")

    finally:
        if conn:
            conn.close()
            print("\nConexão com o banco de dados fechada.")


if __name__ == "__main__":
    main()