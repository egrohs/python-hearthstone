# Hearthstone Deckbuilder

Um aplicativo construído em Python com Streamlit para montagem, busca, filtro e exportação de decks de Hearthstone.

## 🚀 Features (Funcionalidades)

* **Filtros Avançados:** Filtro multicoluna e multivalor para encontrar rapidamente as cartas desejadas.
* **Busca Personalizada:** CRUD de expressões de busca em texto favoritas (salve buscas complexas para reuso com tags como `@taunt`).
* **Exportação:** Geração e exportação de *Deckstrings* compatíveis com o jogo.
* **Sincronização de Dados:** Botão interativo para atualizar o banco de dados local de cartas diretamente no aplicativo.
* **Sincronização de Coleção (Own):** Controle das cartas que você possui na sua conta. 
  * *Como atualizar:* Acesse a API do HSReplay através deste link. Na aba de *preview*, copie o array JSON, salve como um arquivo `collection.json` na raiz do projeto e execute o script `parse_collection.py`.

---

## 📋 TODO (Lista de Tarefas)

### 📊 Análise e Estatísticas
- [ ] **Curva de Mana:** Criar gráficos que mostrem a distribuição de custos do deck em tempo real.
- [ ] **Simulador de Mão Inicial:** Adicionar capacidade de testar a probabilidade de compra das cartas do deck (lembrando: quem começa tem 3 cartas e o 2º player começa com 4 + a moeda; ambos com *mulligan* de até 3 cartas).
- [ ] **Aba de Probabilidades:** Adicionar área dedicada para calcular probabilidades de combos e *draws*.
- [ ] **Contadores:** Exibir relação de quantidade total de cartas vs. quantidade de cartas únicas.

### 🧠 Inteligência e Integrações
- [ ] **Indicadores de Meta:** Filtros que destaquem as cartas mais usadas em torneios recentes ou em baralhos de alto desempenho (Integração com HSReplay).
- [ ] **Ranking de Cartas:** Trazer uma coluna de `Rank` integrada com dados do HSTopDecks.
- [ ] **Sistema de Sugestão:** Sugerir cartas sinérgicas, mostrar decks similares e detectar automaticamente o arquétipo em construção.
- [ ] **Importação:** Permitir importação de listas via *Deckstrings* utilizando biblioteca externa.

### 🎨 UI e Experiência do Usuário (UX)
- [ ] **Imagem da Carta:** Exibir a arte da carta selecionada no canto superior esquerdo da interface.
- [ ] **Identidade Visual:** Mostrar o símbolo da edição/expansão correspondente ao lado de cada carta.
- [ ] **Avisos de *Nerf*:** Sinalizar cartas que foram nerfadas/modificadas recentemente como lembrete para coleta de *dust*.
- [ ] **Metadados:** Permitir adicionar título, data e expansão de foco do deck salvo.

### ⚙️ Mecânicas de Construção
- [ ] **Gerenciamento de Decks:** Implementar função para salvar (Save) e carregar (Load) diferentes listas criadas.
- [ ] **Sideboard:** Permitir edição e inclusão do "sideboard" para cartas específicas como o *E.T.C., o Empresário*.
- [ ] **Bloqueio de Classe:** Avaliar se o app deve obrigar a selecionar uma Classe antes de começar o deck ou se deixa livre para *theorycrafting* e comparações amplas.