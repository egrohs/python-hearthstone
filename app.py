import streamlit as st
import sqlite3
import pandas as pd
import re
import subprocess
import sys
import os
from hearthstone.deckstrings import Deck
from hearthstone.enums import FormatType

# Configuração inicial da página
st.set_page_config(page_title="Hearthstone Deckbuilder", layout="wide")

# Inicializa o deck no session_state se não existir
if 'deck' not in st.session_state:
    st.session_state.deck = []

# Função para carregar e fazer o cache dos dados do banco SQLite
@st.cache_data
def load_data():
    try:
        # Conecta ao banco e carrega a tabela de cartas 
        # (Ajuste "cards" caso sua tabela tenha outro nome)
        conn = sqlite3.connect('hearthstone.db')
        
        # Verifica qual o nome correto da coluna de ID dependendo do script de geração usado
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(cards)")
        cols = [info[1] for info in cur.fetchall()]
        dbf_col = "dbfId" if "dbfId" in cols else "dbf_id"
        own_col = "own, " if "own" in cols else "0 as own, "
        
        query = f"SELECT {dbf_col} as dbfId, {own_col}name, cardClass, cost, attack, health, races, rarity, type, card_set, text FROM cards"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("O banco de dados está vazio ou a tabela não foi encontrada.")
    st.stop()

# ==========================================
# BARRA LATERAL - FILTROS BÁSICOS
# ==========================================
st.sidebar.title("Filtros do Deck")

# Função auxiliar para extrair as opções únicas e ordená-las
def get_options(column_name):
    options = df[column_name].dropna().unique().tolist()
    return sorted(options)

selected_class = st.sidebar.multiselect("Classe", get_options('cardClass'))

# Sliders para Custo, Ataque e Vida
min_cost = int(df['cost'].dropna().min()) if not df['cost'].dropna().empty else 0
max_cost = int(df['cost'].dropna().max()) if not df['cost'].dropna().empty else 10
selected_cost = st.sidebar.slider("Custo", min_value=min_cost, max_value=max_cost, value=(min_cost, max_cost))

min_attack = int(df['attack'].dropna().min()) if not df['attack'].dropna().empty else 0
max_attack = int(df['attack'].dropna().max()) if not df['attack'].dropna().empty else 10
selected_attack = st.sidebar.slider("Ataque", min_value=min_attack, max_value=max_attack, value=(min_attack, max_attack))

min_health = int(df['health'].dropna().min()) if not df['health'].dropna().empty else 0
max_health = int(df['health'].dropna().max()) if not df['health'].dropna().empty else 10
selected_health = st.sidebar.slider("Vida", min_value=min_health, max_value=max_health, value=(min_health, max_health))

selected_rarity = st.sidebar.multiselect("Raridade", get_options('rarity'))
selected_type = st.sidebar.multiselect("Tipo", get_options('type'))
selected_races = st.sidebar.multiselect("Raça", get_options('races'))
selected_set = st.sidebar.multiselect("Conjunto (Set)", get_options('card_set'))

# Aplica os filtros da barra lateral no DataFrame
filtered_df = df.copy()

if selected_class:
    filtered_df = filtered_df[filtered_df['cardClass'].isin(selected_class)]
if selected_cost != (min_cost, max_cost):
    filtered_df = filtered_df[filtered_df['cost'].between(selected_cost[0], selected_cost[1])]
if selected_rarity:
    filtered_df = filtered_df[filtered_df['rarity'].isin(selected_rarity)]
if selected_type:
    filtered_df = filtered_df[filtered_df['type'].isin(selected_type)]
if selected_attack != (min_attack, max_attack):
    filtered_df = filtered_df[filtered_df['attack'].between(selected_attack[0], selected_attack[1])]
if selected_health != (min_health, max_health):
    filtered_df = filtered_df[filtered_df['health'].between(selected_health[0], selected_health[1])]
if selected_races:
    filtered_df = filtered_df[filtered_df['races'].isin(selected_races)]
if selected_set:
    filtered_df = filtered_df[filtered_df['card_set'].isin(selected_set)]

# ==========================================
# GERENCIAMENTO DE FAVORITOS
# ==========================================
FAVORITES_FILE = "search_favorites.txt"

def load_favorites():
    favs = {}
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    tag, expr = line.split(":", 1)
                    favs[tag.strip()] = expr.strip()
    return favs

def save_favorites(favs):
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        for tag, expr in favs.items():
            f.write(f"{tag}:{expr}\n")

favorites = load_favorites()

st.sidebar.markdown("---")
st.sidebar.subheader("Favoritos de Busca")
with st.sidebar.expander("Gerenciar Favoritos"):
    new_tag = st.text_input("Tag/Palavra-chave (ex: @taunt)")
    new_expr = st.text_input("Expressão (ex: Taunt AND Divine)")
    if st.button("Salvar Favorito"):
        if new_tag and new_expr:
            favorites[new_tag] = new_expr
            save_favorites(favorites)
            st.success(f"Favorito '{new_tag}' salvo!")
            st.rerun()
    
    if favorites:
        st.write("Salvos:")
        for tag, expr in list(favorites.items()):
            col1, col2 = st.columns([4, 1])
            col1.write(f"**{tag}**: `{expr}`")
            if col2.button("❌", key=f"del_{tag}"):
                del favorites[tag]
                save_favorites(favorites)
                st.rerun()

# ==========================================
# CORPO PRINCIPAL - BUSCA E EXIBIÇÃO
# ==========================================
st.title("Hearthstone Deckbuilder")

if st.button("🔄 Atualizar Banco de Dados das Cartas"):
    with st.spinner("Baixando e executando atualização... (Isso pode levar alguns minutos)"):
        try:
            subprocess.run([sys.executable, "update_card_database.py"], check=True)
            st.cache_data.clear()
            st.success("Banco de dados atualizado com sucesso!")
            st.rerun()
        except subprocess.CalledProcessError as e:
            st.error(f"Erro ao atualizar: o script falhou com código {e.returncode}")
        except Exception as e:
            st.error(f"Erro inesperado ao atualizar: {e}")

# Definição das cores para as linhas das tabelas
def get_class_color(row):
    colors = {
        'DEATHKNIGHT': 'rgba(168, 209, 223, 0.2)',
        'DEMONHUNTER': 'rgba(166, 207, 161, 0.2)',
        'DRUID': 'rgba(197, 168, 126, 0.2)',
        'HUNTER': 'rgba(166, 212, 140, 0.2)',
        'MAGE': 'rgba(156, 214, 228, 0.2)',
        'PALADIN': 'rgba(235, 215, 138, 0.2)',
        'PRIEST': 'rgba(229, 229, 229, 0.2)',
        'ROGUE': 'rgba(150, 150, 150, 0.2)',
        'SHAMAN': 'rgba(139, 182, 219, 0.2)',
        'WARLOCK': 'rgba(179, 156, 208, 0.2)',
        'WARRIOR': 'rgba(224, 148, 148, 0.2)',
        'NEUTRAL': 'rgba(200, 200, 200, 0.1)'
    }
    card_class = str(row.get('cardClass', '')).upper()
    bg_color = colors.get(card_class, '')
    return [f'background-color: {bg_color}' if bg_color else ''] * len(row)

def get_rarity_color(row):
    colors = {
        'FREE': 'rgba(200, 200, 200, 0.2)',
        'COMMON': 'rgba(255, 255, 255, 0.1)',
        'RARE': 'rgba(0, 112, 221, 0.2)',
        'EPIC': 'rgba(163, 53, 238, 0.2)',
        'LEGENDARY': 'rgba(255, 128, 0, 0.2)'
    }
    rarity = str(row.get('rarity', '')).upper()
    bg_color = colors.get(rarity, '')
    return [f'background-color: {bg_color}' if bg_color else ''] * len(row)

# Campo de busca avançada
search_query = st.text_input(
    "Filtrar pelo texto da carta (Suporta 'AND', 'OR', parênteses e suas tags de favoritos)",
    placeholder="Ex: @minhatag OR Deathrattle"
)

# Lógica para processar operadores booleanos e parênteses
if search_query:
    # Substitui as tags salvas pela expressão correspondente
    for tag, expr in favorites.items():
        if tag in search_query:
            search_query = search_query.replace(tag, f"({expr})")

    # Divide a string mantendo os operadores e parênteses como tokens
    tokens = re.split(r'(\(|\)|\bAND\b|\bOR\b)', search_query, flags=re.IGNORECASE)
    tokens = [t.strip() for t in tokens if t.strip()]
    
    masks = {}
    expr = []
    
    for i, token in enumerate(tokens):
        upper_token = token.upper()
        if upper_token in ('(', ')'):
            expr.append(token)
        elif upper_token == 'AND':
            expr.append('&')
        elif upper_token == 'OR':
            expr.append('|')
        else:
            mask_name = f"m_{i}"
            masks[mask_name] = filtered_df['text'].str.contains(token, case=False, na=False)
            expr.append(mask_name)
            
    eval_str = " ".join(expr)
    try:
        # Avalia a expressão booleana usando as máscaras (Series do Pandas)
        final_mask = eval(eval_str, {"__builtins__": None}, masks)
        filtered_df = filtered_df[final_mask]
    except Exception:
        # Fallback caso a expressão seja inválida (ex: parênteses sem fechar)
        st.warning("Expressão de busca inválida. Ignorando operadores e buscando o texto exato.")
        filtered_df = filtered_df[filtered_df['text'].str.contains(search_query, case=False, na=False)]

# Exibe a quantidade de resultados
st.markdown(f"**Cartas encontradas:** `{len(filtered_df)}`")

# Placeholder para colocar o botão acima da tabela
add_btn_container = st.empty()

# Renderiza a tabela interativa do Streamlit
# O st.dataframe suporta nativamente ordenação clicando no cabeçalho da coluna
event_add = st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True,
    height=400,
    on_select="rerun",
    selection_mode="multi-row",
    column_config={
        "dbfId": None,
            "own": st.column_config.NumberColumn("Possui", format="%d"),
        "text": st.column_config.TextColumn(width="large"),
        "cost": st.column_config.NumberColumn("Custo", format="%d"),
        "attack": st.column_config.NumberColumn("Ataque", format="%d"),
        "health": st.column_config.NumberColumn("Vida", format="%d")
    }
)

with add_btn_container:
    if st.button("Adicionar Cartas Selecionadas", disabled=not event_add.selection.rows):
        selected_cards = filtered_df.iloc[event_add.selection.rows].to_dict('records')
        
        for card in selected_cards:
            # Verifica limites do deck e quantidade de cópias
            if len(st.session_state.deck) >= 40:
                st.toast("O deck já atingiu o limite de 40 cartas!")
                break
                
            current_count = sum(1 for c in st.session_state.deck if c['name'] == card['name'])
            is_legendary = str(card.get('rarity')).upper() == 'LEGENDARY'
            limit = 1 if is_legendary else 2
            
            if current_count < limit:
                st.session_state.deck.append(card)
            else:
                st.toast(f"Limite alcançado para a carta: {card['name']}")
                
        st.rerun()

# ==========================================
# SEÇÃO DO DECK
# ==========================================
st.markdown("---")
st.subheader(f"Seu Deck ({len(st.session_state.deck)}/40 cartas)")

if st.session_state.deck:
    deck_df = pd.DataFrame(st.session_state.deck)
    
    # Agrupar e contar as cópias de cada carta
    cols_to_group = deck_df.columns.tolist()
    deck_grouped = deck_df.groupby(cols_to_group, dropna=False).size().reset_index(name='QNT')
    
    # Reordenar para que QNT seja a primeira coluna da esquerda
    cols = ['QNT'] + [c for c in deck_grouped.columns if c != 'QNT']
    deck_grouped = deck_grouped[cols]
    
    # Ordenar o deck por Custo de Mana e então por Nome
    deck_grouped = deck_grouped.sort_values(by=['cost', 'name'], ascending=[True, True]).reset_index(drop=True)

    remove_btn_container = st.empty()
    
    try:
        event_remove = st.dataframe(
            deck_grouped.style.apply(get_rarity_color, axis=1),
            use_container_width=True,
            hide_index=True,
            height=300,
            on_select="rerun",
            selection_mode="multi-row",
            column_config={
                "dbfId": None,
                "text": st.column_config.TextColumn(width="large"),
                "QNT": st.column_config.NumberColumn("QNT", width="small"),
                "cost": st.column_config.NumberColumn("Custo", format="%d"),
                "attack": st.column_config.NumberColumn("Ataque", format="%d"),
                "health": st.column_config.NumberColumn("Vida", format="%d")
            }
        )
    except Exception:
        event_remove = st.dataframe(
            deck_grouped,
            use_container_width=True,
            hide_index=True,
            height=300,
            on_select="rerun",
            selection_mode="multi-row",
            column_config={
                "dbfId": None,
                "text": st.column_config.TextColumn(width="large"),
                "QNT": st.column_config.NumberColumn("QNT", width="small"),
                "cost": st.column_config.NumberColumn("Custo", format="%d"),
                "attack": st.column_config.NumberColumn("Ataque", format="%d"),
                "health": st.column_config.NumberColumn("Vida", format="%d")
            }
        )
    
    with remove_btn_container:
        col_rm, col_clr = st.columns([3, 7])
        with col_rm:
            if st.button("Remover Cartas Selecionadas", disabled=not event_remove.selection.rows):
                indices_to_remove = sorted(event_remove.selection.rows, reverse=True)
                for i in indices_to_remove:
                    card_name_to_remove = deck_grouped.iloc[i]['name']
                    # Encontra e remove apenas 1 cópia da carta selecionada por vez
                    for j, card in enumerate(st.session_state.deck):
                        if card['name'] == card_name_to_remove:
                            st.session_state.deck.pop(j)
                            break
                st.rerun()
        with col_clr:
            if st.button("Limpar Deck"):
                st.session_state.deck = []
                st.rerun()
                
    st.markdown("---")
    st.subheader("Exportar Deck")
    if st.button("Gerar Deckstring"):
        HERO_DBF_IDS = {
            'DEATHKNIGHT': 78065,
            'DEMONHUNTER': 56550,
            'DRUID': 274,
            'HUNTER': 31,
            'MAGE': 637,
            'PALADIN': 671,
            'PRIEST': 813,
            'ROGUE': 930,
            'SHAMAN': 1066,
            'WARLOCK': 893,
            'WARRIOR': 7,
            'NEUTRAL': 637 # Mage como fallback
        }
        
        # Identificar classe primária do deck para escolher o herói correspondente
        classes_in_deck = deck_grouped[deck_grouped['cardClass'].astype(str).str.upper() != 'NEUTRAL']['cardClass']
        main_class = str(classes_in_deck.mode()[0]).upper() if not classes_in_deck.empty else 'NEUTRAL'
        
        # Criar instância do deck
        deck = Deck()
        deck.format = FormatType.FT_WILD # FT_WILD permite todas as cartas do formato Livre
        deck.heroes = [HERO_DBF_IDS.get(main_class, 637)]
        
        # Adicionar cartas e suas quantidades
        cards_to_add = []
        for _, row in deck_grouped.iterrows():
            cards_to_add.append((int(row['dbfId']), int(row['QNT'])))
        deck.cards = cards_to_add
        
        try:
            deckstring = deck.as_deckstring
            st.success("Deckstring gerada com sucesso! Copie o código abaixo:")
            st.code(deckstring, language="text")
        except Exception as e:
            st.error(f"Erro ao gerar deckstring: {e}")
else:
    st.info("Seu deck está vazio. Selecione cartas na lista acima e clique em 'Adicionar Cartas Selecionadas'.")
