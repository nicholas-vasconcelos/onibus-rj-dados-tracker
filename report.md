# Relatório de Projeto: Rastreador de Linhas de Ônibus SPPO do Rio
**Nome:** Nicholas Borges de Vasconcelos

**Matricula:** 202407138829

**Disciplina:** Extração e Preparação de Dados

**Instituição:** Ibmec 

## 1. Visão Geral

Este aplicativo rastreia ônibus municipais no Rio de Janeiro, demonstrando um pipeline de dados completo, desde a extração bruta da API até a visualização interativa em um painel Streamlit (publicado em https://onibus-rj-dados-tracker.streamlit.app/). A arquitetura se alinha às etapas fundamentais do processo de mineração de dados e foi desenvolvida para a disciplina de Extração e Preparação de Dados (5º período de CDIA no Ibmec).

## 2. Etapa 1: Coleta e Limpeza 

Esta fase reúne e prepara os dados brutos para garantir a qualidade dos resultados nas etapas posteriores.

* A função `fetch_bus_positions()` extrai dados em tempo real no formato JSON da API de mobilidade aberta do Rio, com cache de 60 segundos (`@st.cache_data`) e `requests` com timeout para estabilidade.

* Para limpar e validar os registros, o código verifica a presença de campos obrigatórios como `linha`, `ordem`, coordenadas e `datahora` antes de processar.

* A função `normalize_coordinate` padroniza os dados, substituindo vírgulas decimais por pontos e convertendo-os para float, uniformizando formatos e estruturas.



## 3. Etapa 2: Transformação 

Aqui, os dados limpos são convertidos e normalizados em formatos adequados para análise.

* A função `parse_timestamp` converte milissegundos em objetos `datetime` com fuso horário, preparando valores para ordenação e exibição.

* A função `prepare_bus_dataframe` remove linhas incompletas, filtra pela linha escolhida via sidebar e normaliza colunas críticas (coordenadas, velocidade e timestamp formatado para o usuário).

* O código aplica uma janela de recência de 5 minutos para descartar pontos de GPS desatualizados, mantendo o painel leve e focado.



## 4. Etapa 3: Mineração 

Esta etapa envolve a aplicação de algoritmos e técnicas específicas para descobrir padrões nos dados preparados.

* O aplicativo destaca padrões ao permitir filtrar um ônibus específico e exibir suas últimas localizações (até 10 pontos) com cores progressivamente mais claras para evidenciar trajetória.

* O pipeline estrutura o DataFrame para suportar futuras aplicações preditivas, como estimativa de chegada e análises de frequência de passagem.

* Esses dados estruturados também podem ser aplicados à logística para otimização de rotas e balanceamento de frota por linha.



## 5. Etapa 4: Avaliação 

A fase final valida os resultados obtidos para garantir sua utilidade prática.

* O aplicativo combina um mapa Folium (com ajuste automático de bounds e marcadores coloridos por ônibus) com um DataFrame estilizado, facilitando a leitura de padrões espaço-temporais.

* O `@st.cache_data` do Streamlit e o fluxo de recarga manual reduzem a carga da API, permitindo experimentação rápida sem perder estabilidade.
