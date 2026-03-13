# Relatório de Projeto: Rastreador de Linhas de Ônibus SPPO do Rio
**Nome:** Nicholas Borges de Vasconcelos

**Matricula:** 202407138829

**Disciplina:** Extração e Preparação de Dados

**Instituição:** Ibmec 

## Intro

Aplicativo Streamlit que visualiza as posições em tempo real de qualquer linha SPPO do Rio de Janeiro. Os dados vêm da API oficial de mobilidade em https://dados.mobilidade.rio/gps/sppo. O app busca automaticamente um novo snapshot (em cache por 60 segundos), permite escolher uma linha a partir do conjunto retornado e exibe os resultados em um mapa colorido sincronizado com uma tabela. Projeto para a disciplina Extração e Preparação de Dados (5º período de CDIA no Ibmec).

## Acesso rápido
- Use direto no Streamlit Cloud: https://onibus-rj-dados-tracker.streamlit.app/ (recomendado).

## Funcionalidades
- Busca automática a cada execução com cache do Streamlit (`@st.cache_data`), reutilizando o mesmo snapshot da API em reexecuções dentro de 60 segundos.
- Normalização automática das coordenadas (decimais com vírgula → floats) e formatação de timestamp ciente de fuso horário.
- Filtro de frescor de cinco minutos para manter a interface leve e focada na telemetria recente.
- Seletor de linha preenchido a partir do dataset obtido e seletor opcional de ônibus para isolar uma `ordem`.
- Quando apenas um ônibus é selecionado, as últimas 10 localizações aparecem com marcadores progressivamente mais claros para visualizar o trajeto.
- O mapa centraliza e dá zoom nos ônibus ativos e usa cores por ônibus que correspondem a uma coluna estilizada na grade de dados.
- Grade de dados do Streamlit para inspeção rápida, incluindo legenda de cores e metadados de última atualização.

## Estrutura do Projeto
```
app.py              # Ponto de entrada da aplicação Streamlit
requirements.txt    # Dependências Python
README.md           # Este documento
```

## Pré-requisitos
- Python 3.11+ (ZoneInfo exige Python 3.9+, mas o Streamlit se beneficia de versões mais novas)
- Ferramenta de ambiente virtual de sua preferência (opcional, porém recomendada)

## Instalação para desenvolvimento
- Clone o repositório e crie um ambiente virtual se quiser isolar dependências.
- `pip install -r requirements.txt`
- `streamlit run app.py`
- Abra a URL local (tipicamente http://localhost:8501), escolha uma linha e filtre ônibus se necessário.

## Como Funciona
1. `fetch_bus_positions()` busca dados da API sempre que o app é reexecutado e os coloca em cache por 60 segundos para reduzir carga.
2. `prepare_bus_dataframe()` filtra o DataFrame pela linha solicitada, restringe os dados aos últimos cinco minutos, normaliza coordenadas, interpreta velocidades e formata timestamps.
3. `assign_bus_colors()` + auxiliares de estilo garantem cores consistentes entre os marcadores do Folium e a legenda da tabela.
4. `build_map()` centraliza/dá zoom nos ônibus ativos, adiciona trilhas históricas quando um único ônibus é selecionado e renderiza a camada Folium.
5. O Streamlit renderiza tanto a tabela estilizada quanto o mapa Folium (via `st_folium`).

## Observações
- Se nenhum ônibus corresponder à linha solicitada ou o ônibus selecionado não tiver dados recentes, a interface explica o motivo em vez de falhar silenciosamente.
- Respostas com erro da API são exibidas como mensagem de erro ao usuário.
- As funções de limpeza de dados são escritas para serem reutilizáveis em outras stacks (por exemplo, migrando acesso a dados/lógica de negócio para outro backend).
- Snapshots em cache permanecem estáveis durante o TTL de 60 segundos, permitindo aplicar vários filtros sobre o mesmo conjunto de dados para análises consistentes.
