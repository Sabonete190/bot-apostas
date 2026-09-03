import streamlit as st
import math
import pandas as pd
import os
import requests
import base64
import json
from datetime import datetime

with open("pesos.json", "r") as f:
    pesos = json.load(f)

pesos_1x2 = pesos["1x2"]
pesos_over25 = pesos["over25"]
pesos_under25 = pesos["under25"]
pesos_btts = pesos["btts"]

# Valores padrão usados apenas se o pesos.json ainda não tiver esses
# dois blocos (compatibilidade com arquivos salvos antes desta
# atualização).
_DEFAULT_PESOS_MARCA_PRIMEIRO = {
    "peso_xg": 0.30,
    "peso_chutes": 0.20,
    "peso_eficiencia": 0.20,
    "peso_tabela": 0.10,
    "peso_forma": 0.15,
    "peso_forca": 0.05
}

pesos_casa_marca_primeiro = pesos.get(
    "casa_marca_primeiro",
    _DEFAULT_PESOS_MARCA_PRIMEIRO
)

pesos_fora_marca_primeiro = pesos.get(
    "fora_marca_primeiro",
    _DEFAULT_PESOS_MARCA_PRIMEIRO
)

PESO_XG = pesos_1x2["peso_xg"]
PESO_CHUTES = pesos_1x2["peso_chutes"]
PESO_EFICIENCIA = pesos_1x2["peso_eficiencia"]
PESO_TABELA = pesos_1x2["peso_tabela"]
PESO_FORMA = pesos_1x2["peso_forma"]
PESO_FORCA = pesos_1x2["peso_forca"]

# =========================
# BANCO DE DADOS LOCAL DOS TIMES
# =========================
# Estatísticas reais dos times (partidas jogadas, médias de gols
# marcados/sofridos, % de Over) lidas de um arquivo JSON local, em
# vez de vir de uma API. Veja times_serie_a.json para o formato.

ARQUIVO_TIMES = "times_serie_a.json"


def carregar_times():

    if not os.path.exists(ARQUIVO_TIMES):
        return {}

    try:
        with open(ARQUIVO_TIMES, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        return {}

    # Ignora chaves de metadado/comentário (começam com "_") e
    # mantém só os times de verdade.
    return {
        nome: stats
        for nome, stats in dados.items()
        if not nome.startswith("_")
    }


TIMES_DB = carregar_times()

OPCAO_TIME_MANUAL = "➕ Outro time (preencher manualmente)"

# Lista de times para os dropdowns, em ordem alfabética, com uma
# opção extra para times que ainda não estão no banco de dados.
NOMES_TIMES = sorted(TIMES_DB.keys()) + [OPCAO_TIME_MANUAL]


def obter_stats_time(nome_time):
    """Devolve as estatísticas do time no banco local, ou um
    dicionário zerado se o time não existir (ex.: opção manual)."""

    return TIMES_DB.get(
        nome_time,
        {
            "jogos": 0,
            "gols_marcados_media": 0.0,
            "gols_sofridos_media": 0.0,
            "over05": 0.0,
            "over15": 0.0,
            "over25": 0.0,
            "over35": 0.0,
        }
    )

# =========================
# FUNÇÃO KELLY
# =========================

def calcular_kelly(probabilidade, odd):

    if odd <= 1:
        return 0

    b = odd - 1

    kelly = (
        (probabilidade * b)
        - (1 - probabilidade)
    ) / b

    return max(kelly, 0)
# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Bot de Apostas",
    layout="centered"
)

# =========================
# SESSION STATE
# =========================

if "melhor_mercado" not in st.session_state:

    st.session_state["melhor_mercado"] = "N/A"

# TÍTULO
st.title("📊 Bot de Apostas Profissional")


# =========================
# ABAS PRINCIPAIS
# =========================
aba_bot, aba_base = st.tabs([
    "🎯 Bot de Apostas",
    "📊 Análise por Base de Dados"
])

with aba_bot:

    st.write("Preencha os dados da partida.")
    # =========================
    # HISTÓRICO CSV
    # =========================

    ARQUIVO_HISTORICO = "historico_apostas.csv"
    ARQUIVO_RESULTADOS = "resultados_apostas.csv"

    # =========================
    # ESQUEMA DE COLUNAS (CONTEXTO COMPLETO DA APOSTA)
    # =========================
    # Conjunto único de campos de contexto, usado tanto no histórico
    # quanto no registro de resultados, na ordem definida pelo usuário.

    COLUNAS_CONTEXTO = [
        "Data",
        "Campeonato",
        "Time Casa",
        "Time Fora",
        "Mercado",
        "Resultado Mercado",
        "Probabilidade Modelo",
        "Odd Mercado",
        "Odd Justa",
        "EV",
        "Edge",
        "Kelly",
        "xG Casa",
        "xG Fora",
        "xGA Casa",
        "xGA Fora",
        "Forma Casa",
        "Forma Fora",
        "Eficiência Casa",
        "Eficiência Fora",
        "Chutes Casa",
        "Chutes Fora",
        "Gols Esperados Casa",
        "Gols Esperados Fora",
        "Placar Final",
    ]

    # historico_apostas.csv precisa de um identificador estável para o
    # selectbox de "Selecione a aposta", então "ID" é mantido como a
    # única coluna extra além do contexto pedido.
    COLUNAS_HISTORICO = ["ID"] + COLUNAS_CONTEXTO

    # resultados_apostas.csv precisa de Stake/Lucro para o painel de
    # performance (winrate, ROI) e para o cálculo de banca, então essas
    # duas colunas são mantidas além do contexto pedido.
    COLUNAS_RESULTADOS = COLUNAS_CONTEXTO + ["Stake R$", "Lucro"]

    # =========================
    # CARREGAMENTO TOLERANTE A ESQUEMA ANTIGO
    # =========================
    # CSVs salvos antes da migração de colunas (ex.: com "Resultado" em
    # vez de "Resultado Mercado", ou sem "Placar Final") não têm as
    # colunas novas. Esta função sempre devolve um DataFrame com todas
    # as colunas esperadas presentes, para nenhuma leitura/filtro do
    # tipo df["Resultado Mercado"] quebrar com KeyError.

    MAPA_COLUNAS_LEGADAS = {
        "Resultado": "Resultado Mercado",
        "Odd": "Odd Mercado",
    }


    def carregar_csv_com_esquema(caminho, colunas_esperadas, mapa_legado=None):

        if not os.path.exists(caminho):
            return pd.DataFrame(columns=colunas_esperadas)

        try:
            df = pd.read_csv(caminho, encoding="utf-8")
        except Exception:
            return pd.DataFrame(columns=colunas_esperadas)

        if mapa_legado:
            for coluna_antiga, coluna_nova in mapa_legado.items():
                if coluna_antiga in df.columns and coluna_nova not in df.columns:
                    df = df.rename(columns={coluna_antiga: coluna_nova})

        # Garante que toda coluna esperada existe. NaN (em vez de "")
        # para não quebrar .mean()/agregações nas colunas numéricas;
        # comparações como df["Resultado Mercado"] == "GREEN" continuam
        # funcionando normalmente (dão False, não erro).
        for coluna in colunas_esperadas:
            if coluna not in df.columns:
                df[coluna] = pd.NA

        return df

    # =========================
    # GITHUB
    # =========================

    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_USER = st.secrets["GITHUB_USER"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]

    def salvar_no_github(nome_arquivo):

        url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{nome_arquivo}"

        headers = {
            "Authorization": f"token {GITHUB_TOKEN}"
        }

        with open(nome_arquivo, "rb") as file:
            content = base64.b64encode(file.read()).decode()

        response = requests.get(url, headers=headers)

        sha = None

        if response.status_code == 200:
            sha = response.json()["sha"]

        data = {
            "message": f"Atualizando {nome_arquivo}",
            "content": content,
            "branch": "main"
        }

        if sha:
            data["sha"] = sha

        requests.put(
            url,
            headers=headers,
            json=data
        )

    def salvar_aposta(dados):

        df_novo = pd.DataFrame([dados])

        if os.path.exists(ARQUIVO_HISTORICO):

            try:

                df_antigo = pd.read_csv(
                    ARQUIVO_HISTORICO,
                    encoding="utf-8"
                )

            except:

                df_antigo = pd.DataFrame()

            df_final = pd.concat(
                [df_antigo, df_novo],
                ignore_index=True
            )

        else:

            df_final = df_novo

        # Garante a ordem e o conjunto exato de colunas do esquema,
        # mesmo que o CSV antigo tenha colunas diferentes.
        df_final = df_final.reindex(
            columns=COLUNAS_HISTORICO
        )

        df_final.to_csv(
            ARQUIVO_HISTORICO,
            index=False,
            encoding="utf-8"
        )


    def salvar_resultado(dados):

        df_novo = pd.DataFrame([dados])

        if os.path.exists(ARQUIVO_RESULTADOS):

            try:

                df_antigo = pd.read_csv(
                    ARQUIVO_RESULTADOS,
                    encoding="utf-8"
                )

            except:

                df_antigo = pd.DataFrame()

            df_final = pd.concat(
                [df_antigo, df_novo],
                ignore_index=True
            )

        else:

            df_final = df_novo

        df_final = df_final.reindex(
            columns=COLUNAS_RESULTADOS
        )

        df_final.to_csv(
            ARQUIVO_RESULTADOS,
            index=False,
            encoding="utf-8"
        )
    def salvar_pesos():

        # Mantém a estrutura aninhada original do pesos.json
        # (1x2 / over25 / under25 / btts / casa_marca_primeiro /
        # fora_marca_primeiro). Só o bloco "1x2" é atualizado, pois é
        # o único cujos pesos alimentam diretamente o cálculo de força
        # (ataque/defesa) — os demais blocos, incluindo os dois novos,
        # são mantidos e realimentados pelo saldo de acertos/erros de
        # cada mercado em atualizar_pesos(), no mesmo padrão que
        # over25/under25/btts já seguiam.
        pesos_atualizados = {
            "1x2": {
                "peso_xg": PESO_XG,
                "peso_chutes": PESO_CHUTES,
                "peso_eficiencia": PESO_EFICIENCIA,
                "peso_tabela": PESO_TABELA,
                "peso_forma": PESO_FORMA,
                "peso_forca": PESO_FORCA
            },
            "over25": pesos_over25,
            "under25": pesos_under25,
            "btts": pesos_btts,
            "casa_marca_primeiro": pesos_casa_marca_primeiro,
            "fora_marca_primeiro": pesos_fora_marca_primeiro
        }

        with open("pesos.json", "w") as f:
            json.dump(pesos_atualizados, f, indent=4)

        salvar_no_github("pesos.json")

    def atualizar_pesos():

        global PESO_XG, PESO_CHUTES, PESO_EFICIENCIA, PESO_TABELA, PESO_FORMA

        df = carregar_csv_com_esquema(
            ARQUIVO_RESULTADOS,
            COLUNAS_RESULTADOS,
            mapa_legado=MAPA_COLUNAS_LEGADAS
        )

        if df.empty:
            return

        if not os.path.exists(ARQUIVO_HISTORICO):
            return

        # resultados_apostas.csv agora já traz o contexto completo (xG,
        # chutes, forma etc.), então não é mais necessário fazer merge
        # com o historico_apostas.csv para obter essas estatísticas.
        # carregar_csv_com_esquema já garante que todas as colunas do
        # esquema existem (mesmo que vazias), então não é preciso
        # verificar coluna a coluna aqui.

        ultimos = df.tail(10)

        # Separa por mercado
        mercados = {
            "1x2": ["Vitória Casa", "Empate", "Vitória Fora"],
            "over25": ["Over 2.5"],
            "under25": ["Under 2.5"],
            "btts": ["BTTS SIM", "BTTS NÃO"],
            "casa_marca_primeiro": ["Casa marca primeiro"],
            "fora_marca_primeiro": ["Fora marca primeiro"]
        }

        for nome_mercado, nomes in mercados.items():

            resultados_mercado = ultimos[
                ultimos["Mercado"].isin(nomes)
            ]

            if resultados_mercado.empty:
                continue

            greens = len(
                resultados_mercado[
                    resultados_mercado["Resultado Mercado"] == "GREEN"
                ]
            )

            reds = len(
                resultados_mercado[
                    resultados_mercado["Resultado Mercado"] == "RED"
                ]
            )

            saldo = greens - reds

            # Ajuste pequeno para evitar mudanças bruscas
            ajuste = saldo * 0.01

            media_xg = resultados_mercado[["xG Casa", "xG Fora"]].mean().mean()
            media_chutes = resultados_mercado[["Chutes Casa", "Chutes Fora"]].mean().mean()
            media_eficiencia = resultados_mercado[["Eficiência Casa", "Eficiência Fora"]].mean().mean()
            media_forma = resultados_mercado[["Forma Casa", "Forma Fora"]].mean().mean() / 30

            # Cada termo só é aplicado se houver dado válido para ele,
            # em vez de pular o mercado inteiro quando falta uma única
            # estatística. Posição na tabela não faz mais parte do
            # esquema de colunas pedido, então PESO_TABELA não é mais
            # reajustado automaticamente aqui (permanece com o valor
            # carregado de pesos.json).
            if not pd.isna(media_xg):
                PESO_XG += ajuste * media_xg * 0.10
                PESO_XG = max(0.10, min(PESO_XG, 3))

            if not pd.isna(media_chutes):
                PESO_CHUTES += ajuste * media_chutes * 0.05
                PESO_CHUTES = max(0.10, min(PESO_CHUTES, 3))

            if not pd.isna(media_eficiencia):
                PESO_EFICIENCIA += ajuste * media_eficiencia * 0.10
                PESO_EFICIENCIA = max(0.10, min(PESO_EFICIENCIA, 3))

            if not pd.isna(media_forma):
                PESO_FORMA += ajuste * media_forma * 0.20
                PESO_FORMA = max(0.10, min(PESO_FORMA, 3))

        salvar_pesos()
    def verificar_rodada():

        df = carregar_csv_com_esquema(
            ARQUIVO_RESULTADOS,
            COLUNAS_RESULTADOS,
            mapa_legado=MAPA_COLUNAS_LEGADAS
        )

        if df.empty:
            return

        jogos = len(
            df[
                df["Resultado Mercado"].isin(
                  ["GREEN", "RED"]
                )
            ]
        )

        if jogos % 10 == 0:
            atualizar_pesos()

    # =========================
    # ODDS 1X2
    # =========================

    st.subheader("Mercado 1X2")

    odd_casa = st.number_input(
        "Odd Casa",
        min_value=1.0,
        step=0.01
    )

    odd_empate = st.number_input(
        "Odd Empate",
        min_value=1.0,
        step=0.01
    )

    odd_fora = st.number_input(
        "Odd Fora",
        min_value=1.0,
        step=0.01
    )

    # =========================
    # OVER / UNDER
    # =========================

    st.subheader("Over / Under")

    odd_over15 = st.number_input(
        "Odd Over 1.5",
        min_value=1.0,
        step=0.01
    )

    odd_over25 = st.number_input(
        "Odd Over 2.5",
        min_value=1.0,
        step=0.01
    )

    odd_over35 = st.number_input(
        "Odd Over 3.5",
        min_value=1.0,
        step=0.01
    )

    odd_under25 = st.number_input(
        "Odd Under 2.5",
        min_value=1.0,
        step=0.01
    )

    odd_under35 = st.number_input(
        "Odd Under 3.5",
        min_value=1.0,
        step=0.01
    )


    # =========================
    # BTTS
    # =========================

    st.subheader("BTTS")

    odd_btts_sim = st.number_input(
        "Odd BTTS SIM",
        min_value=1.0,
        step=0.01
    )

    odd_btts_nao = st.number_input(
        "Odd BTTS NÃO",
        min_value=1.0,
        step=0.01
    )


    # =========================
    # GOLS POR EQUIPE
    # =========================

    st.subheader("Gols por Equipe")

    odd_casa_marca_1 = st.number_input(
        "Odd Casa marca 1+ gol",
        min_value=1.0,
        step=0.01
    )

    odd_fora_marca_1 = st.number_input(
        "Odd Fora marca 1+ gol",
        min_value=1.0,
        step=0.01
    )

    odd_casa_marca_2 = st.number_input(
        "Odd Casa marca 2+ gols",
        min_value=1.0,
        step=0.01
    )

    odd_fora_marca_2 = st.number_input(
        "Odd Fora marca 2+ gols",
        min_value=1.0,
        step=0.01
    )

    odd_casa_over05 = st.number_input(
        "Odd Casa Over 0.5",
        min_value=1.0,
        step=0.01
    )

    odd_casa_over15 = st.number_input(
        "Odd Casa Over 1.5",
        min_value=1.0,
        step=0.01
    )

    odd_casa_over25 = st.number_input(
        "Odd Casa Over 2.5",
        min_value=1.0,
        step=0.01
    )

    odd_fora_over05 = st.number_input(
        "Odd Fora Over 0.5",
        min_value=1.0,
        step=0.01
    )

    odd_fora_over15 = st.number_input(
        "Odd Fora Over 1.5",
        min_value=1.0,
        step=0.01
    )

    odd_fora_over25 = st.number_input(
        "Odd Fora Over 2.5",
        min_value=1.0,
        step=0.01
    )


    # =========================
    # DUPLA CHANCE
    # =========================

    st.subheader("Dupla Chance")

    odd_dupla_1x = st.number_input(
        "Odd Dupla Chance 1X",
        min_value=1.0,
        step=0.01
    )

    odd_dupla_x2 = st.number_input(
        "Odd Dupla Chance X2",
        min_value=1.0,
        step=0.01
    )

    odd_dupla_12 = st.number_input(
        "Odd Dupla Chance 12",
        min_value=1.0,
        step=0.01
    )


    # =========================
    # EMPATE ANULA APOSTA - DNB
    # =========================

    st.subheader("Empate Anula a Aposta - DNB")

    odd_dnb_casa = st.number_input(
        "Odd DNB Casa",
        min_value=1.0,
        step=0.01
    )

    odd_dnb_fora = st.number_input(
        "Odd DNB Fora",
        min_value=1.0,
        step=0.01
    )


    # =========================
    # MERCADOS COMBINADOS
    # =========================

    st.subheader("Mercados Combinados")

    odd_casa_marca_primeiro = st.number_input(
        "Odd Casa marca primeiro",
        min_value=1.0,
        step=0.01
    )

    odd_fora_marca_primeiro = st.number_input(
        "Odd Fora marca primeiro",
        min_value=1.0,
        step=0.01
    )

    odd_casa_vence_over15 = st.number_input(
        "Odd Casa vence + Over 1.5",
        min_value=1.0,
        step=0.01
    )

    odd_fora_vence_over15 = st.number_input(
        "Odd Fora vence + Over 1.5",
        min_value=1.0,
        step=0.01
    )

    odd_btts_over25 = st.number_input(
        "Odd BTTS + Over 2.5",
        min_value=1.0,
        step=0.01
    )

    odd_btts_over35 = st.number_input(
        "Odd BTTS + Over 3.5",
        min_value=1.0,
        step=0.01
    )


    # =========================
    # POSIÇÃO NA TABELA
    # =========================

    st.subheader("Tabela Brasileirão")

    posicao_casa = st.number_input(
        "Posição Time Casa",
        min_value=1,
        max_value=20,
        value=10
    )

    posicao_fora = st.number_input(
        "Posição Time Fora",
        min_value=1,
        max_value=20,
        value=10
    )
    # =========================
    # IDENTIFICAÇÃO DO JOGO
    # (times vêm do banco de dados local, não mais de texto livre)
    # =========================

    st.subheader("Times")

    campeonato = st.text_input(
        "Campeonato",
        value="Brasileirão"
    )

    time_casa_selecionado = st.selectbox(
        "Time Casa",
        NOMES_TIMES
    )

    if time_casa_selecionado == OPCAO_TIME_MANUAL:

        time_casa = st.text_input(
            "Nome do Time Casa (manual)"
        )

    else:

        time_casa = time_casa_selecionado

    time_fora_selecionado = st.selectbox(
        "Time Fora",
        NOMES_TIMES
    )

    if time_fora_selecionado == OPCAO_TIME_MANUAL:

        time_fora = st.text_input(
            "Nome do Time Fora (manual)"
        )

    else:

        time_fora = time_fora_selecionado

    # Estatísticas reais do banco de dados local para os times
    # selecionados (vazio/zerado se for a opção manual).
    stats_casa = obter_stats_time(time_casa_selecionado)
    stats_fora = obter_stats_time(time_fora_selecionado)

    st.caption(
        f"📊 {time_casa or '—'}: {stats_casa['jogos']} jogos no banco • "
        f"Gols marcados: {stats_casa['gols_marcados_media']} • "
        f"Gols sofridos: {stats_casa['gols_sofridos_media']} • "
        f"Over 1.5: {round(stats_casa['over15'] * 100, 1)}% • "
        f"Over 2.5: {round(stats_casa['over25'] * 100, 1)}%"
    )

    st.caption(
        f"📊 {time_fora or '—'}: {stats_fora['jogos']} jogos no banco • "
        f"Gols marcados: {stats_fora['gols_marcados_media']} • "
        f"Gols sofridos: {stats_fora['gols_sofridos_media']} • "
        f"Over 1.5: {round(stats_fora['over15'] * 100, 1)}% • "
        f"Over 2.5: {round(stats_fora['over25'] * 100, 1)}%"
    )

    # =========================
    # DADOS DOS TIMES
    # (pré-preenchidos com o banco de dados local; o campo continua
    # editável manualmente, caso queira ajustar)
    # =========================

    st.subheader("Dados dos Times")

    xg_casa = st.number_input(
        "xG Casa (auto: gols marcados/jogo do banco)",
        min_value=0.0,
        step=0.1,
        value=float(stats_casa["gols_marcados_media"]),
        key=f"xg_casa_{time_casa_selecionado}"
    )

    xg_fora = st.number_input(
        "xG Fora (auto: gols marcados/jogo do banco)",
        min_value=0.0,
        step=0.1,
        value=float(stats_fora["gols_marcados_media"]),
        key=f"xg_fora_{time_fora_selecionado}"
    )

    xga_casa = st.number_input(
        "xGA Casa (auto: gols sofridos/jogo do banco)",
        min_value=0.0,
        step=0.1,
        value=float(stats_casa["gols_sofridos_media"]),
        key=f"xga_casa_{time_casa_selecionado}"
    )

    xga_fora = st.number_input(
        "xGA Fora (auto: gols sofridos/jogo do banco)",
        min_value=0.0,
        step=0.1,
        value=float(stats_fora["gols_sofridos_media"]),
        key=f"xga_fora_{time_fora_selecionado}"
    )

    sofridos_casa = st.number_input(
        "Gols Sofridos Casa (auto: banco de dados)",
        min_value=0.0,
        step=0.1,
        value=float(stats_casa["gols_sofridos_media"]),
        key=f"sofridos_casa_{time_casa_selecionado}"
    )

    sofridos_fora = st.number_input(
        "Gols Sofridos Fora (auto: banco de dados)",
        min_value=0.0,
        step=0.1,
        value=float(stats_fora["gols_sofridos_media"]),
        key=f"sofridos_fora_{time_fora_selecionado}"
    )

    chutes_casa = st.number_input(
        "Chutes no Gol Casa",
        min_value=0.0,
        step=0.1
    )

    chutes_fora = st.number_input(
        "Chutes no Gol Fora",
        min_value=0.0,
        step=0.1
    )

    eficiencia_casa = st.number_input(
        "Eficiência Casa",
        min_value=0.0,
        step=0.1
    )

    eficiencia_fora = st.number_input(
        "Eficiência Fora",
        min_value=0.0,
        step=0.1
    )
    # =========================
    # FORMA RECENTE
    # =========================

    st.subheader("Forma Recente")

    forma_casa = st.number_input(
        "Forma Casa (últimos 5 jogos)",
        min_value=0,
        max_value=15,
        step=1
    )

    forma_fora = st.number_input(
        "Forma Fora (últimos 5 jogos)",
        min_value=0,
        max_value=15,
        step=1
    )

    # =========================
    # FORÇA AUTOMÁTICA
    # =========================

    def calcular_forca(odd):

        if odd <= 1.70:
            return 1.35, "Muito Forte"

        elif odd <= 2.10:
            return 1.20, "Forte"

        elif odd <= 2.80:
            return 1.00, "Médio"

        elif odd <= 4.00:
            return 0.80, "Fraco"

        else:
            return 0.65, "Muito Fraco"

    forca_casa_valor, nivel_casa = calcular_forca(
        odd_casa
    )

    forca_fora_valor, nivel_fora = calcular_forca(
        odd_fora
    )

    st.subheader("Força Automática")

    st.write(
        f"Força Casa: {nivel_casa}"
    )

    st.write(
        f"Força Fora: {nivel_fora}"
    )
    # =========================
    # DADOS DO BRASILEIRÃO
    # =========================

    media_gols_liga = 2.63

    media_btts_liga = 0.57

    media_over35_liga = 0.49

    media_mandante_liga = 0.47

    media_visitante_liga = 0.24

    media_empate_liga = 0.29

    # =========================
    # BOTÃO
    # =========================

    if st.button("Analisar Jogo"):

        # =========================
        # FORÇA DA TABELA
        # =========================

        forca_tabela_casa = (
            (21 - posicao_casa) / 20
        )

        forca_tabela_fora = (
            (21 - posicao_fora) / 20
        )
        # =========================
        # FORÇA OFENSIVA
        # =========================

        ataque_casa = (

        xg_casa * PESO_XG +

        chutes_casa * PESO_CHUTES +

        eficiencia_casa * PESO_EFICIENCIA +

        forca_tabela_casa * PESO_TABELA +

        (forma_casa / 15) * PESO_FORMA +

        forca_casa_valor * PESO_FORCA

        )

        ataque_fora = (

        xg_fora * PESO_XG +

        chutes_fora * PESO_CHUTES +

        eficiencia_fora * PESO_EFICIENCIA +

        forca_tabela_fora * PESO_TABELA +

        (forma_fora / 15) * PESO_FORMA +

        forca_fora_valor * PESO_FORCA

        )

        # =========================
        # FORÇA DEFENSIVA
        # =========================

        defesa_casa = (
            xga_casa * 0.6 +
            sofridos_casa * 0.4
        )

        defesa_fora = (
            xga_fora * 0.6 +
            sofridos_fora * 0.4
        )

        # =========================
        # FORÇA DE GOL
        # =========================

        forca_gol = (
            (ataque_casa / (defesa_fora + 0.5)) +
            (ataque_fora / (defesa_casa + 0.5))
        ) / 2

        st.subheader("Análise Estatística")

        st.write(f"Ataque Casa: {round(ataque_casa, 2)}")
        st.write(f"Ataque Fora: {round(ataque_fora, 2)}")

        st.write(f"Defesa Casa: {round(defesa_casa, 2)}")
        st.write(f"Defesa Fora: {round(defesa_fora, 2)}")

        st.write(f"Força de Gol: {round(forca_gol, 2)}")
        # =========================
        # GOLS ESPERADOS
        # =========================

        gols_esperados_casa = (
            ataque_casa / (defesa_fora + 0.5)
        )

        gols_esperados_fora = (
            ataque_fora / (defesa_casa + 0.5)
        )

        st.subheader("Gols Esperados")

        st.write(
            f"Gols Esperados Casa: {round(gols_esperados_casa, 2)}"
        )

        st.write(
            f"Gols Esperados Fora: {round(gols_esperados_fora, 2)}"
        )

        # Guardados aqui porque o botão "Salvar Aposta" roda num rerun
        # separado do Streamlit, onde as variáveis locais deste bloco
        # ("Analisar Jogo") não existem mais.
        st.session_state["gols_esperados_casa"] = gols_esperados_casa
        st.session_state["gols_esperados_fora"] = gols_esperados_fora

        # =========================
        # POISSON
        # =========================

        def poisson(gols_esperados, gols):
            return (
                (math.exp(-gols_esperados) *
                gols_esperados ** gols)
                / math.factorial(gols)
            )

        st.subheader("Poisson")

        for i in range(4):

            prob_casa_gols = poisson(
                gols_esperados_casa,
                i
            )

            prob_fora_gols = poisson(
                gols_esperados_fora,
                i
            )

            st.write(
                f"Casa marcar {i} gols: "
                f"{round(prob_casa_gols * 100, 2)}%"
            )

            st.write(
                f"Fora marcar {i} gols: "
                f"{round(prob_fora_gols * 100, 2)}%"
            )

            st.write("---")

        # =========================
        # MATRIZ COMPLETA DE POISSON
        # =========================

        # Limite de gols utilizado na matriz
        MAX_GOLS = 10

        matriz_placares = []

        for gols_casa in range(MAX_GOLS + 1):

            for gols_fora in range(MAX_GOLS + 1):

                prob_casa = poisson(
                    gols_esperados_casa,
                    gols_casa
                )

                prob_fora = poisson(
                    gols_esperados_fora,
                    gols_fora
                )

                prob_placar = (
                    prob_casa *
                    prob_fora
                )

                matriz_placares.append({
                    "gols_casa": gols_casa,
                    "gols_fora": gols_fora,
                    "probabilidade": prob_placar
                })


        # =========================
        # TOP PLACARES
        # =========================

        st.subheader("Placares Mais Prováveis")

        placares_ordenados = sorted(
            matriz_placares,
            key=lambda x: x["probabilidade"],
            reverse=True
        )

        top_placares = placares_ordenados[:5]

        for placar in top_placares:

            st.write(
                f'{placar["gols_casa"]} x '
                f'{placar["gols_fora"]} = '
                f'{round(placar["probabilidade"] * 100, 2)}%'
            )


        # =========================
        # FUNÇÃO PARA SOMAR
        # PROBABILIDADES DOS PLACARES
        # =========================

        def probabilidade_mercado(
            condicao
        ):

            probabilidade = 0

            for placar in matriz_placares:

                if condicao(
                    placar["gols_casa"],
                    placar["gols_fora"]
                ):

                    probabilidade += (
                        placar["probabilidade"]
                    )

            return probabilidade


        # =========================
        # OVER / UNDER
        # =========================

        prob_over15 = probabilidade_mercado(
            lambda casa, fora:
            casa + fora >= 2
        )

        prob_over25 = probabilidade_mercado(
            lambda casa, fora:
            casa + fora >= 3
        )

        prob_over35 = probabilidade_mercado(
            lambda casa, fora:
            casa + fora >= 4
        )

        prob_under25 = probabilidade_mercado(
            lambda casa, fora:
            casa + fora <= 2
        )

        prob_under35 = probabilidade_mercado(
            lambda casa, fora:
            casa + fora <= 3
        )


        # =========================
        # GOLS POR EQUIPE
        # =========================

        prob_casa_marca_1 = probabilidade_mercado(
            lambda casa, fora:
            casa >= 1
        )

        prob_fora_marca_1 = probabilidade_mercado(
            lambda casa, fora:
            fora >= 1
        )

        prob_casa_marca_2 = probabilidade_mercado(
            lambda casa, fora:
            casa >= 2
        )

        prob_fora_marca_2 = probabilidade_mercado(
            lambda casa, fora:
            fora >= 2
        )

        prob_casa_over05 = probabilidade_mercado(
            lambda casa, fora:
            casa >= 1
        )

        prob_casa_over15 = probabilidade_mercado(
            lambda casa, fora:
            casa >= 2
        )

        prob_casa_over25 = probabilidade_mercado(
            lambda casa, fora:
            casa >= 3
        )

        prob_fora_over05 = probabilidade_mercado(
            lambda casa, fora:
            fora >= 1
        )

        prob_fora_over15 = probabilidade_mercado(
            lambda casa, fora:
            fora >= 2
        )

        prob_fora_over25 = probabilidade_mercado(
            lambda casa, fora:
            fora >= 3
        )


        # =========================
        # BTTS
        # =========================

        prob_btts_sim = probabilidade_mercado(
            lambda casa, fora:
            casa >= 1 and fora >= 1
        )

        prob_btts_nao = (
            1 - prob_btts_sim
        )


        # =========================
        # RESULTADO 1X2
        # =========================

        prob_casa_modelo = probabilidade_mercado(
            lambda casa, fora:
            casa > fora
        )

        prob_empate_modelo = probabilidade_mercado(
            lambda casa, fora:
            casa == fora
        )

        prob_fora_modelo = probabilidade_mercado(
            lambda casa, fora:
            casa < fora
        )


        # =========================
        # DUPLA CHANCE
        # =========================

        prob_dupla_1x = (
            prob_casa_modelo +
            prob_empate_modelo
        )

        prob_dupla_x2 = (
            prob_empate_modelo +
            prob_fora_modelo
        )

        prob_dupla_12 = (
            prob_casa_modelo +
            prob_fora_modelo
        )


        # =========================
        # DNB
        # =========================

        prob_dnb_casa = prob_casa_modelo

        prob_dnb_fora = prob_fora_modelo


        # =========================
        # CASA/FORA MARCA PRIMEIRO
        # =========================

        prob_casa_marca_primeiro = probabilidade_mercado(
            lambda casa, fora:
            casa > 0 and casa > fora
        )

        prob_fora_marca_primeiro = probabilidade_mercado(
            lambda casa, fora:
            fora > 0 and fora > casa
        )


        # =========================
        # CASA VENCE + OVER 1.5
        # =========================

        prob_casa_vence_over15 = (
            probabilidade_mercado(
                lambda casa, fora:
                casa > fora
                and casa + fora >= 2
            )
        )


        # =========================
        # FORA VENCE + OVER 1.5
        # =========================

        prob_fora_vence_over15 = (
            probabilidade_mercado(
                lambda casa, fora:
                fora > casa
                and casa + fora >= 2
            )
        )


        # =========================
        # BTTS + OVER 2.5
        # =========================

        prob_btts_over25 = (
            probabilidade_mercado(
                lambda casa, fora:
                casa >= 1
                and fora >= 1
                and casa + fora >= 3
            )
        )


        # =========================
        # BTTS + OVER 3.5
        # =========================

        prob_btts_over35 = (
            probabilidade_mercado(
                lambda casa, fora:
                casa >= 1
                and fora >= 1
                and casa + fora >= 4
            )
        )
            # =========================
        # ODDS JUSTAS, EV, EDGE E KELLY
        # NOVOS MERCADOS
        # =========================

        def calcular_odd_justa(probabilidade):

            if probabilidade <= 0:
                return 0

            return 1 / probabilidade


        def calcular_ev(probabilidade, odd):

            if odd <= 1:
                return 0

            return (
                probabilidade * odd
            ) - 1


        def calcular_edge(probabilidade, odd):

            if odd <= 1:
                return 0

            return (
                probabilidade -
                (1 / odd)
            )


        def calcular_kelly_mercado(
            probabilidade,
            odd
        ):

            if odd <= 1:
                return 0

            b = odd - 1

            kelly = (
                (
                    probabilidade * b
                )
                -
                (
                    1 - probabilidade
                )
            ) / b

            return max(
                kelly,
                0
            )
                # =========================
        # RESULTADOS DOS NOVOS MERCADOS
        # ODDS JUSTAS, EV, EDGE E KELLY
        # =========================

        resultados_mercados = {

            # =========================
            # OVER / UNDER
            # =========================

            "Over 1.5": {
                "probabilidade": prob_over15,
                "odd": odd_over15
            },

            "Over 2.5": {
                "probabilidade": prob_over25,
                "odd": odd_over25
            },

            "Over 3.5": {
                "probabilidade": prob_over35,
                "odd": odd_over35
            },

            "Under 2.5": {
                "probabilidade": prob_under25,
                "odd": odd_under25
            },

            "Under 3.5": {
                "probabilidade": prob_under35,
                "odd": odd_under35
            },


            # =========================
            # BTTS
            # =========================

            "BTTS SIM": {
                "probabilidade": prob_btts_sim,
                "odd": odd_btts_sim
            },

            "BTTS NÃO": {
                "probabilidade": prob_btts_nao,
                "odd": odd_btts_nao
            },


            # =========================
            # GOLS POR EQUIPE
            # =========================

            "Casa marca 1+ gol": {
                "probabilidade": prob_casa_marca_1,
                "odd": odd_casa_marca_1
            },

            "Fora marca 1+ gol": {
                "probabilidade": prob_fora_marca_1,
                "odd": odd_fora_marca_1
            },

            "Casa marca 2+ gols": {
                "probabilidade": prob_casa_marca_2,
                "odd": odd_casa_marca_2
            },

            "Fora marca 2+ gols": {
                "probabilidade": prob_fora_marca_2,
                "odd": odd_fora_marca_2
            },

            "Casa Over 0.5": {
                "probabilidade": prob_casa_over05,
                "odd": odd_casa_over05
            },

            "Casa Over 1.5": {
                "probabilidade": prob_casa_over15,
                "odd": odd_casa_over15
            },

            "Casa Over 2.5": {
                "probabilidade": prob_casa_over25,
                "odd": odd_casa_over25
            },

            "Fora Over 0.5": {
                "probabilidade": prob_fora_over05,
                "odd": odd_fora_over05
            },

            "Fora Over 1.5": {
                "probabilidade": prob_fora_over15,
                "odd": odd_fora_over15
            },

            "Fora Over 2.5": {
                "probabilidade": prob_fora_over25,
                "odd": odd_fora_over25
            },


            # =========================
            # DUPLA CHANCE
            # =========================

            "Dupla Chance 1X": {
                "probabilidade": prob_dupla_1x,
                "odd": odd_dupla_1x
            },

            "Dupla Chance X2": {
                "probabilidade": prob_dupla_x2,
                "odd": odd_dupla_x2
            },

            "Dupla Chance 12": {
                "probabilidade": prob_dupla_12,
                "odd": odd_dupla_12
            },


            # =========================
            # DNB
            # =========================

            "DNB Casa": {
                "probabilidade": prob_dnb_casa,
                "odd": odd_dnb_casa
            },

            "DNB Fora": {
                "probabilidade": prob_dnb_fora,
                "odd": odd_dnb_fora
            },


            # =========================
            # MERCADOS COMBINADOS
            # =========================

            "Casa marca primeiro": {
                "probabilidade": prob_casa_marca_primeiro,
                "odd": odd_casa_marca_primeiro
            },

            "Fora marca primeiro": {
                "probabilidade": prob_fora_marca_primeiro,
                "odd": odd_fora_marca_primeiro
            },

            "Casa vence + Over 1.5": {
                "probabilidade": prob_casa_vence_over15,
                "odd": odd_casa_vence_over15
            },

            "Fora vence + Over 1.5": {
                "probabilidade": prob_fora_vence_over15,
                "odd": odd_fora_vence_over15
            },

            "BTTS + Over 2.5": {
                "probabilidade": prob_btts_over25,
                "odd": odd_btts_over25
            },

            "BTTS + Over 3.5": {
                "probabilidade": prob_btts_over35,
                "odd": odd_btts_over35
            }
        }
        # =========================
        # RESULTADOS DOS MERCADOS
        # =========================

        resultados_completos = {}

        for mercado, dados in resultados_mercados.items():

            probabilidade = dados["probabilidade"]
            odd = dados["odd"]

            odd_justa = calcular_odd_justa(probabilidade)
            ev = calcular_ev(probabilidade, odd)
            edge = calcular_edge(probabilidade, odd)
            kelly = calcular_kelly_mercado(
                probabilidade,
                odd
            )

            resultados_completos[mercado] = {

                "probabilidade": probabilidade,
                "odd": odd,
                "odd_justa": odd_justa,
                "ev": ev,
                "edge": edge,
                "kelly": kelly
            }
                # =========================
        # MELHOR MERCADO
        # =========================

        st.subheader("🏆 Melhor Mercado")

        melhor_mercado = None
        melhor_dados = None

        for nome, dados in resultados_completos.items():

            if (
                melhor_dados is None
                or dados["ev"] > melhor_dados["ev"]
            ):

                melhor_mercado = nome
                melhor_dados = dados


        if (
            melhor_dados is not None
            and melhor_dados["ev"] > 0
        ):

            st.success(
                f"🔥 Melhor Mercado: {melhor_mercado}"
            )

            st.write(
                f"Probabilidade: "
                f"{round(melhor_dados['probabilidade'] * 100, 2)}%"
            )

            st.write(
                f"Odd Mercado: "
                f"{round(melhor_dados['odd'], 2)}"
            )

            st.write(
                f"Odd Justa: "
                f"{round(melhor_dados['odd_justa'], 2)}"
            )

            st.write(
                f"EV: "
                f"{round(melhor_dados['ev'] * 100, 2)}%"
            )

            st.write(
                f"Edge: "
                f"{round(melhor_dados['edge'] * 100, 2)}%"
            )

            st.write(
                f"Kelly: "
                f"{round(melhor_dados['kelly'] * 100, 2)}%"
            )

            st.session_state["melhor_mercado"] = melhor_mercado

            st.session_state["melhor_probabilidade"] = (
                melhor_dados["probabilidade"]
            )

            st.session_state["melhor_odd_justa"] = (
                melhor_dados["odd_justa"]
            )

            st.session_state["melhor_ev"] = (
                melhor_dados["ev"]
            )

            st.session_state["melhor_edge"] = (
                melhor_dados["edge"]
            )

            st.session_state["melhor_kelly"] = (
                melhor_dados["kelly"]
            )

        else:

            st.error(
                "❌ Nenhum mercado possui valor positivo."
                )


            # =========================
            # EXIBIR RESULTADOS
            # =========================

            st.subheader(
                "Análise Completa dos Mercados"
            )


            for mercado, dados in resultados_completos.items():

                st.write(
                    f"### {mercado}"
                )

                st.write(
                    f"Probabilidade Modelo: "
                    f"{round(dados['probabilidade'] * 100, 2)}%"
                )

                st.write(
                    f"Odd Justa: "
                    f"{round(dados['odd_justa'], 2)}"
                )

                st.write(
                    f"Odd Mercado: "
                    f"{round(dados['odd'], 2)}"
                )

                st.write(
                    f"EV: "
                    f"{round(dados['ev'] * 100, 2)}%"
                )

                st.write(
                    f"Edge: "
                    f"{round(dados['edge'] * 100, 2)}%"
                )

                st.write(
                    f"Kelly: "
                    f"{round(dados['kelly'] * 100, 2)}%"
                )

                st.write("---")

            # =========================
            # ODDS JUSTAS OVER/UNDER
            # =========================

            odd_justa_over25 = (
                1 / prob_over25
            )

            odd_justa_under25 = (
                1 / prob_under25
            )

            st.subheader("Odds Justas Over/Under")

            st.write(
                f"Odd Justa Over 2.5: "
                f"{round(odd_justa_over25, 2)}"
            )

            st.write(
                f"Odd Justa Under 2.5: "
                f"{round(odd_justa_under25, 2)}"
            )
                 # =========================
            # BTTS
            # =========================

            prob_btts_sim = 0

            for gols_casa in range(8):

                for gols_fora in range(8):

                    if gols_casa >= 1 and gols_fora >= 1:

                        prob_btts_sim += (
                            poisson(
                                gols_esperados_casa,
                                gols_casa
                            )
                            *
                            poisson(
                                gols_esperados_fora,
                                gols_fora
                            )
                        )

            prob_btts_nao = 1 - prob_btts_sim

            st.subheader("BTTS")

            st.write(
                f"BTTS SIM: "
                f"{round(prob_btts_sim * 100, 2)}%"
            )

            st.write(
                f"BTTS NÃO: "
                f"{round(prob_btts_nao * 100, 2)}%"
            )
            # =========================
            # ODDS JUSTAS BTTS
            # =========================

            odd_justa_btts_sim = (
                1 / prob_btts_sim
            )

            odd_justa_btts_nao = (
                1 / prob_btts_nao
            )

            st.subheader("Odds Justas BTTS")

            st.write(
                f"Odd Justa BTTS SIM: "
                f"{round(odd_justa_btts_sim, 2)}"
            )

            st.write(
                f"Odd Justa BTTS NÃO: "
                f"{round(odd_justa_btts_nao, 2)}"
            )
            # =========================
            # EV OVER/UNDER
            # =========================

            ev_over25 = (
                prob_over25 * odd_over25
            ) - 1

            ev_under25 = (
                prob_under25 * odd_under25
            ) - 1

            st.subheader("EV Over/Under")

            st.write(
                f"EV Over 2.5: "
                f"{round(ev_over25, 2)}"
            )

            st.write(
                f"EV Under 2.5: "
                f"{round(ev_under25, 2)}"
            )

            # =========================
            # EV BTTS
            # =========================

            ev_btts_sim = (
                prob_btts_sim * odd_btts_sim
            ) - 1

            ev_btts_nao = (
                prob_btts_nao * odd_btts_nao
            ) - 1

            st.subheader("EV BTTS")

            st.write(
                f"EV BTTS SIM: "
                f"{round(ev_btts_sim, 2)}"
            )

            st.write(
                f"EV BTTS NÃO: "
                f"{round(ev_btts_nao, 2)}"
            )
            # =========================
            # EDGE OVER/BTTS
            # =========================

            edge_over25 = (
                prob_over25 -
                (1 / odd_over25)
            )

            edge_under25 = (
                prob_under25 -
                (1 / odd_under25)
            )

            edge_btts_sim = (
                prob_btts_sim -
                (1 / odd_btts_sim)
            )

            edge_btts_nao = (
                prob_btts_nao -
                (1 / odd_btts_nao)
            )

            st.subheader("Edge Over/BTTS")

            st.write(
                f"Edge Over 2.5: "
                f"{round(edge_over25 * 100, 2)}%"
            )

            st.write(
                f"Edge Under 2.5: "
                f"{round(edge_under25 * 100, 2)}%"
            )

            st.write(
                f"Edge BTTS SIM: "
                f"{round(edge_btts_sim * 100, 2)}%"
            )

            st.write(
                f"Edge BTTS NÃO: "
                f"{round(edge_btts_nao * 100, 2)}%"
            )
            # =========================
            # KELLY OVER/BTTS
            # =========================

            kelly_over25 = calcular_kelly(
                prob_over25,
                odd_over25
            )

            kelly_under25 = calcular_kelly(
                prob_under25,
                odd_under25
            )

            kelly_btts_sim = calcular_kelly(
                prob_btts_sim,
                odd_btts_sim
            )

            kelly_btts_nao = calcular_kelly(
                prob_btts_nao,
                odd_btts_nao
            )

            st.subheader("Kelly Over/BTTS")

            st.write(
                f"Kelly Over 2.5: "
                f"{round(kelly_over25 * 100, 2)}%"
            )

            st.write(
                f"Kelly Under 2.5: "
                f"{round(kelly_under25 * 100, 2)}%"
            )

            st.write(
                f"Kelly BTTS SIM: "
                f"{round(kelly_btts_sim * 100, 2)}%"
            )

            st.write(
                f"Kelly BTTS NÃO: "
                f"{round(kelly_btts_nao * 100, 2)}%"
            )
         # =========================
            # PROBABILIDADES PRÓPRIAS
            # =========================

            forca_total = ataque_casa + ataque_fora + defesa_casa + defesa_fora

            prob_casa_modelo = (
                ataque_casa + defesa_fora
            ) / forca_total

            prob_fora_modelo = (
                ataque_fora + defesa_casa
            ) / forca_total

            equilibrio = abs(prob_casa_modelo - prob_fora_modelo)

            prob_empate_modelo = 0.30 - (equilibrio * 0.2)

            prob_empate_modelo = max(0.10, prob_empate_modelo)

            soma_modelo = (
                prob_casa_modelo +
                prob_fora_modelo +
                prob_empate_modelo
            )

            prob_casa_modelo /= soma_modelo
            prob_fora_modelo /= soma_modelo
            prob_empate_modelo /= soma_modelo

            st.subheader("Probabilidades do Modelo")

            st.write(f"Casa Modelo: {round(prob_casa_modelo * 100, 2)}%")
            st.write(f"Empate Modelo: {round(prob_empate_modelo * 100, 2)}%")
            st.write(f"Fora Modelo: {round(prob_fora_modelo * 100, 2)}%")
            # =========================
            # ODDS JUSTAS
            # =========================

            odd_justa_casa = (
                1 / prob_casa_modelo
            )

            odd_justa_empate = (
                1 / prob_empate_modelo
            )

            odd_justa_fora = (
                1 / prob_fora_modelo
            )

            st.subheader("Odds Justas")

            st.write(
                f"Odd Justa Casa: "
                f"{round(odd_justa_casa, 2)}"
            )

            st.write(
                f"Odd Justa Empate: "
                f"{round(odd_justa_empate, 2)}"
            )

            st.write(
                f"Odd Justa Fora: "
                f"{round(odd_justa_fora, 2)}"
            )
            # =========================
            # PROBABILIDADES IMPLÍCITAS
            # =========================

            prob_casa = 1 / odd_casa
            prob_empate = 1 / odd_empate
            prob_fora = 1 / odd_fora

            # =========================
            # NORMALIZAÇÃO
            # =========================

            soma = prob_casa + prob_empate + prob_fora

            prob_casa /= soma
            prob_empate /= soma
            prob_fora /= soma

            # =========================
            # RESULTADO
            # =========================

            st.success("Análise concluída")

            st.subheader("Probabilidades")

            st.write(f"Casa: {round(prob_casa * 100, 2)}%")
            st.write(f"Empate: {round(prob_empate * 100, 2)}%")
            st.write(f"Fora: {round(prob_fora * 100, 2)}%")

            # =========================
            # EV
            # =========================

            # =========================
            # EV DO MODELO
            # =========================

            ev_casa = (
                prob_casa_modelo * odd_casa
            ) - 1

            ev_empate = (
                prob_empate_modelo * odd_empate
            ) - 1

            ev_fora = (
                prob_fora_modelo * odd_fora
            ) - 1

            st.subheader("EV do Modelo")

            st.write(
                f"EV Casa: {round(ev_casa, 2)}"
            )

            st.write(
                f"EV Empate: {round(ev_empate, 2)}"
            )

            st.write(
                f"EV Fora: {round(ev_fora, 2)}"
            )
            # =========================
            # EDGE 1X2
            # =========================

            edge_casa = (
                prob_casa_modelo -
                (1 / odd_casa)
            )

            edge_empate = (
                prob_empate_modelo -
                (1 / odd_empate)
            )

            edge_fora = (
                prob_fora_modelo -
                (1 / odd_fora)
            )

            st.subheader("Edge 1X2")

            st.write(
                f"Edge Casa: "
                f"{round(edge_casa * 100, 2)}%"
            )

            st.write(
                f"Edge Empate: "
                f"{round(edge_empate * 100, 2)}%"
            )

            st.write(
                f"Edge Fora: "
                f"{round(edge_fora * 100, 2)}%"
            )
            # =========================
            # EDGE
            # =========================

            edge_casa = (
                prob_casa_modelo - prob_casa
            )

            edge_empate = (
                prob_empate_modelo - prob_empate
            )

            edge_fora = (
                prob_fora_modelo - prob_fora
            )

            st.subheader("Edge do Modelo")

            st.write(
                f"Edge Casa: {round(edge_casa * 100, 2)}%"
            )

            st.write(
                f"Edge Empate: {round(edge_empate * 100, 2)}%"
            )

            st.write(
                f"Edge Fora: {round(edge_fora * 100, 2)}%"
            )
            # =========================
            # KELLY CRITERION
            # =========================

            def calcular_kelly(probabilidade, odd):

                if odd <= 1:
                    return 0

                kelly = (
                    (
                        odd * probabilidade
                    ) - 1
                ) / (odd - 1)

                return max(kelly, 0)

            kelly_casa = calcular_kelly(
                prob_casa_modelo,
                odd_casa
            )

            kelly_empate = calcular_kelly(
                prob_empate_modelo,
                odd_empate
            )

            kelly_fora = calcular_kelly(
                prob_fora_modelo,
                odd_fora
            )

            st.subheader("Kelly Criterion")

            st.write(
                f"Kelly Casa: "
                f"{round(kelly_casa * 100, 2)}%"
            )

            st.write(
                f"Kelly Empate: "
                f"{round(kelly_empate * 100, 2)}%"
            )

            st.write(
                f"Kelly Fora: "
                f"{round(kelly_fora * 100, 2)}%"
            )
            # =========================
            # CONFIANÇA DO MODELO
            # =========================

            maior_edge = max(
                abs(edge_casa),
                abs(edge_empate),
                abs(edge_fora)
            )

            maior_ev = max(
                ev_casa,
                ev_empate,
                ev_fora
            )

            confianca = (
                (forca_gol * 4)
                +
                (maior_edge * 20)
                +
                (maior_ev * 10)
            )

            confianca = max(
                0,
                min(confianca, 10)
            )

            st.subheader("Confiança do Modelo")

            st.write(
                f"Confiança: {round(confianca, 1)}/10"
            )
            # =========================
            # DECISÃO INTELIGENTE
            # =========================

            st.subheader("Decisão do Modelo")

            melhor_edge = max(
                edge_casa,
                edge_empate,
                edge_fora
            )

            melhor_ev = max(
                ev_casa,
                ev_empate,
                ev_fora
            )

            if (
                melhor_edge >= 0.10
                and melhor_ev >= 0.10
                and confianca >= 7
            ):

                st.success(
                    "🔥 Entrada Forte Detectada"
                )

            elif (
                melhor_edge >= 0.05
                and melhor_ev >= 0.05
                and confianca >= 5
            ):

                st.warning(
                    "⚠️ Entrada Moderada"
                )

            else:

                st.error(
                    "❌ Jogo Sem Valor"
                )

            # =========================
            # GESTÃO DE STAKE
            # =========================

            st.subheader("Stake Sugerida")

            stake = 0

            if (
                melhor_edge >= 0.10
                and melhor_ev >= 0.10
                and confianca >= 7
            ):

                stake = 5

            elif (
                melhor_edge >= 0.05
                and melhor_ev >= 0.05
                and confianca >= 5
            ):

                stake = 2

            else:

                stake = 0

            st.write(
                f"Stake Recomendada: {stake}% da banca"
            )
        # =========================
            # PERFIL DO JOGO
            # =========================

            st.subheader("Perfil da Partida")

            perfil_jogo = "⚖️ Equilibrado"

            total_xg = (
                gols_esperados_casa +
                gols_esperados_fora
            )

            diferenca_forca = abs(
                ataque_casa - ataque_fora
            )

            # Jogo explosivo

            if (
                total_xg >= 3
                and prob_over25 >= 0.65
            ):

                perfil_jogo = "🔥 Jogo Explosivo"

            # Jogo defensivo

            elif (
                total_xg <= 2
                and prob_under25 >= 0.55
            ):

                perfil_jogo = "🧱 Jogo Defensivo"

            # Favorito forte

            elif (
                diferenca_forca >= 1
                and confianca >= 7
            ):

                perfil_jogo = "🎯 Favorito Forte"

            # BTTS forte

            elif (
                prob_btts_sim >= 0.65
            ):

                perfil_jogo = "⚔️ Jogo Aberto"

            st.success(
                f"{perfil_jogo}"
            )
            # =========================
            # SALVAR RESULTADOS
            # =========================

            st.session_state["melhor_mercado"] = melhor_mercado

            st.session_state["ev_casa"] = ev_casa
            st.session_state["ev_empate"] = ev_empate
            st.session_state["ev_fora"] = ev_fora

            st.session_state["edge_casa"] = edge_casa
            st.session_state["edge_empate"] = edge_empate
            st.session_state["edge_fora"] = edge_fora

            st.session_state["stake"] = stake
            st.session_state["confianca"] = confianca
            st.session_state["perfil_jogo"] = perfil_jogo    

    # =========================
    # SALVAR APOSTA
    # =========================

    if st.button("Salvar Aposta"):

        if os.path.exists(ARQUIVO_HISTORICO):

            try:

                df_ids = pd.read_csv(
                    ARQUIVO_HISTORICO,
                    encoding="utf-8"
                )

                novo_id = len(df_ids) + 1

            except:

                novo_id = 1

        else:

            novo_id = 1

        # =========================
        # RECUPERAR DADOS DA ANÁLISE
        # =========================

        mercado_salvo = st.session_state.get(
            "melhor_mercado",
            "N/A"
        )

        # =========================
        # DEFINIR ODD DO MERCADO
        # =========================

        odds_mercados = {

            "🔥 Vitória Casa": odd_casa,
            "🤝 Empate": odd_empate,
            "🔥 Vitória Fora": odd_fora,

            "⚽ Over 2.5": odd_over25,
            "🛡️ Under 2.5": odd_under25,

            "🔥 BTTS SIM": odd_btts_sim,
            "❌ BTTS NÃO": odd_btts_nao,

            "Vitória Casa": odd_casa,
            "Empate": odd_empate,
            "Vitória Fora": odd_fora,

            "Over 2.5": odd_over25,
            "Under 2.5": odd_under25,

            "BTTS SIM": odd_btts_sim,
            "BTTS NÃO": odd_btts_nao,

            "Casa marca primeiro": odd_casa_marca_primeiro,
            "Fora marca primeiro": odd_fora_marca_primeiro
        }

        odd_escolhida = odds_mercados.get(
            mercado_salvo,
            0
        )

        # =========================
        # DADOS DA APOSTA
        # (esquema de contexto completo, na ordem definida em
        # COLUNAS_HISTORICO / COLUNAS_CONTEXTO)
        # =========================

        dados_aposta = {

            "ID": novo_id,

            "Data": datetime.now().strftime("%d/%m/%Y"),

            "Campeonato": campeonato,

            "Time Casa": time_casa,

            "Time Fora": time_fora,

            "Mercado": mercado_salvo,

            # Ainda não há resultado nem placar no momento da análise;
            # esses campos são preenchidos depois, em "Salvar Resultado".
            "Resultado Mercado": "",

            "Probabilidade Modelo": st.session_state.get(
                "melhor_probabilidade",
                0
            ),

            "Odd Mercado": odd_escolhida,

            "Odd Justa": st.session_state.get(
                "melhor_odd_justa",
                0
            ),

            "EV": st.session_state.get(
                "melhor_ev",
                0
            ),

            "Edge": st.session_state.get(
                "melhor_edge",
                0
            ),

            "Kelly": st.session_state.get(
                "melhor_kelly",
                0
            ),

            "xG Casa": xg_casa,

            "xG Fora": xg_fora,

            "xGA Casa": xga_casa,

            "xGA Fora": xga_fora,

            "Forma Casa": forma_casa,

            "Forma Fora": forma_fora,

            "Eficiência Casa": eficiencia_casa,

            "Eficiência Fora": eficiencia_fora,

            "Chutes Casa": chutes_casa,

            "Chutes Fora": chutes_fora,

            "Gols Esperados Casa": st.session_state.get(
                "gols_esperados_casa",
                0
            ),

            "Gols Esperados Fora": st.session_state.get(
                "gols_esperados_fora",
                0
            ),

            "Placar Final": "",
        }

        salvar_aposta(
            dados_aposta
        )


        salvar_no_github(
            ARQUIVO_HISTORICO
        )

        st.success(
            "✅ Aposta salva no histórico"
        )

    # =========================
    # RESULTADO DAS APOSTAS
    # =========================

    st.subheader("Resultado da Aposta")
    # =========================
    # CARREGAR HISTÓRICO
    # =========================

    historico_resultados = carregar_csv_com_esquema(
        ARQUIVO_HISTORICO,
        COLUNAS_HISTORICO,
        mapa_legado=MAPA_COLUNAS_LEGADAS
    )

    # =========================
    # SELECIONAR APOSTA
    # =========================

    # Garante que a variável sempre exista, mesmo sem histórico ainda
    aposta_selecionada = None

    if (
        not historico_resultados.empty
        and "ID" in historico_resultados.columns
    ):

        id_aposta = st.selectbox(
            "Selecione a aposta",
            historico_resultados["ID"]
        )

    else:

        st.warning(
            "Nenhuma aposta com ID encontrada."
        )

    if "ID" in historico_resultados.columns:

        aposta_selecionada = historico_resultados[
            historico_resultados["ID"] == id_aposta
        ]

        mercado_atual = aposta_selecionada.iloc[0]["Mercado"]
        st.info(
        f"Mercado Atual: {mercado_atual}"
    )
        st.write("Aposta selecionada:")

        st.write(
            aposta_selecionada[
                [
                    "Time Casa",
                    "Time Fora",
                    "Mercado"
                ]
            ]
        )

    else:

        st.warning(
            "Salve uma nova aposta para gerar IDs."
        )
    resultado_aposta = st.selectbox(
        "Resultado",
        [
            "GREEN",
            "RED",
            "VOID"
        ]
    )

    valor_stake = st.number_input(
        "Valor da Stake (R$)",
        min_value=0.0,
        value=100.0,
        step=10.0
    )

    # =========================
    # ODD DA APOSTA FEITA
    # =========================

    odd_aposta = st.number_input(
        "Odd da aposta realizada",
        min_value=1.01,
        value=2.00,
        step=0.01
    )

    # =========================
    # PLACAR FINAL
    # =========================

    gols_casa_final = st.number_input(
        "Gols Casa (Placar Final)",
        min_value=0,
        step=1
    )

    gols_fora_final = st.number_input(
        "Gols Fora (Placar Final)",
        min_value=0,
        step=1
    )

    # =========================
    # SALVAR RESULTADO
    # =========================

    if st.button("Salvar Resultado"):

        if aposta_selecionada is None or aposta_selecionada.empty:

            st.warning(
                "Selecione uma aposta salva antes de registrar o resultado."
            )

        else:

            lucro = 0

            if resultado_aposta == "GREEN":

                lucro = (
                    valor_stake * odd_aposta
                ) - valor_stake

            elif resultado_aposta == "RED":

                lucro = -valor_stake

            else:

                lucro = 0

            placar_final = f"{gols_casa_final} x {gols_fora_final}"

            # =========================
            # DADOS RESULTADO
            # (contexto completo herdado da aposta salva no histórico,
            # sobrescrevendo apenas o que muda no momento do resultado:
            # Resultado Mercado, Odd Mercado real, Placar Final)
            # =========================

            aposta_linha = aposta_selecionada.iloc[0]

            dados_resultado = {}

            for coluna in COLUNAS_CONTEXTO:
                dados_resultado[coluna] = aposta_linha.get(coluna, "")

            dados_resultado["Resultado Mercado"] = resultado_aposta

            dados_resultado["Odd Mercado"] = odd_aposta

            dados_resultado["Placar Final"] = placar_final

            dados_resultado["Stake R$"] = valor_stake

            dados_resultado["Lucro"] = round(lucro, 2)

            salvar_resultado(
                dados_resultado
            )

            salvar_no_github(
                ARQUIVO_RESULTADOS
            )

            try:

              df_hist = pd.read_csv(
                ARQUIVO_HISTORICO,
                encoding="utf-8"
              )

              filtro = (
                  df_hist["ID"] == id_aposta
              )

              df_hist.loc[
                filtro,
                "Resultado Mercado"
              ] = resultado_aposta

              df_hist.loc[
                filtro,
                "Placar Final"
              ] = placar_final

              df_hist.to_csv(
                ARQUIVO_HISTORICO,
                index=False,
                encoding="utf-8"
              )

              salvar_no_github(
                 ARQUIVO_HISTORICO
              )

            except Exception as e:

              st.error(
                 f"Erro ao atualizar histórico: {e}"
              )

            verificar_rodada()

            st.success(
                "✅ Resultado salvo"
            )

    # =========================
    # ESTATÍSTICAS DO BOT
    # =========================

    df_stats_raw = carregar_csv_com_esquema(
        ARQUIVO_RESULTADOS,
        COLUNAS_RESULTADOS,
        mapa_legado=MAPA_COLUNAS_LEGADAS
    )

    # =========================
    # PAINEL
    # =========================

    st.subheader("Performance do Bot")

    if not df_stats_raw.empty:

        df_stats = df_stats_raw.copy()

        # Normaliza o texto: remove espaços e padroniza maiúsculas
        # para que "green", " GREEN " etc. sejam todos reconhecidos.
        df_stats["Resultado Mercado"] = (
            df_stats["Resultado Mercado"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # Força Lucro e Stake para numérico.
        # Se o CSV tiver células vazias ("") o pandas as carrega como
        # string, fazendo .sum() concatenar texto em vez de somar.
        df_stats["Lucro"] = pd.to_numeric(
            df_stats["Lucro"], errors="coerce"
        ).fillna(0)

        df_stats["Stake R$"] = pd.to_numeric(
            df_stats["Stake R$"], errors="coerce"
        ).fillna(0)

        # Só contabiliza apostas que já têm resultado (exclui as
        # salvas mas ainda não resolvidas, onde Resultado Mercado="").
        df_resolvidas = df_stats[
            df_stats["Resultado Mercado"].isin(["GREEN", "RED", "VOID"])
        ]

        total_apostas = len(df_resolvidas)

        if total_apostas == 0:

            st.warning("Nenhum resultado registrado ainda.")

        else:

            greens = len(df_resolvidas[df_resolvidas["Resultado Mercado"] == "GREEN"])
            reds   = len(df_resolvidas[df_resolvidas["Resultado Mercado"] == "RED"])
            voids  = len(df_resolvidas[df_resolvidas["Resultado Mercado"] == "VOID"])

            # Winrate: só sobre apostas com resultado definitivo
            # (GREEN ou RED) — VOIDs são devoluções e não entram.
            apostas_validas = greens + reds
            winrate = (
                (greens / apostas_validas * 100)
                if apostas_validas > 0 else 0
            )

            lucro_total  = df_resolvidas["Lucro"].sum()
            total_stakes = df_resolvidas["Stake R$"].sum()
            roi = (
                (lucro_total / total_stakes * 100)
                if total_stakes > 0 else 0
            )

            st.write(f"Total de Apostas Resolvidas: {total_apostas}")
            st.write(f"🟢 Greens: {greens}")
            st.write(f"🔴 Reds: {reds}")
            st.write(f"⚪ Voids: {voids}")
            st.write(f"🎯 Winrate: {round(winrate, 2)}%")
            st.write(f"💰 Lucro Total: R$ {round(lucro_total, 2)}")
            st.write(f"📈 ROI: {round(roi, 2)}%")

    else:

        st.warning(
            "Nenhum resultado salvo ainda."
        )


# =========================
# ABA 2: ANÁLISE POR BASE DE DADOS
# =========================

with aba_base:

    import math as _math

    st.header("📊 Análise por Base de Dados — Série A")
    st.caption(
        "Preencha o arquivo times_serie_a_completo.csv com os dados reais dos times. "
        "Selecione o confronto e clique em Analisar."
    )

    # ------------------------------------------------------------------
    # CONSTANTES DO MÓDULO EMBUTIDO
    # ------------------------------------------------------------------

    ARQUIVO_BASE = "times_serie_a_completo.csv"
    ARQUIVO_PREVISOES = "previsoes_serie_a.csv"
    ARQUIVO_CALIBRACAO = "calibracao.json"
    MEDIA_LIGA_GOLS = 2.60
    MEDIA_LIGA_CANTOS = 9.80
    MEDIA_LIGA_CARTOES = 3.90
    MEDIA_LIGA_CHUTES = 12.5

    COLUNAS_BASE = [
        "Equipe", "Partidas",
        "BP_Geral", "BP_Casa", "BP_Fora",
        "Jogos_Casa", "Jogos_Fora",
        "Gols_Marcados", "Gols_Sofridos",
        # Resultado histórico do time (0.0–1.0 = 0%–100%)
        "Vitoria_%", "Empate_%", "Derrota_%",
        "Over_05_Gols", "Under_05_Gols",
        "Over_15_Gols", "Under_15_Gols",
        "Over_25_Gols", "Under_25_Gols",
        "Over_35_Gols", "Under_35_Gols",
        "Cantos_Tomados", "Cantos_Concedidos",
        "Over_75_Cantos", "Under_75_Cantos",
        "Over_85_Cantos", "Under_85_Cantos",
        "Over_95_Cantos", "Under_95_Cantos",
        "Over_105_Cantos", "Under_105_Cantos",
        "Cartoes_Recebidos", "Cartoes_Opostos",
        "Over_25_Cartoes", "Under_25_Cartoes",
        "Over_35_Cartoes", "Under_35_Cartoes",
        "Over_45_Cartoes", "Under_45_Cartoes",
        "Over_55_Cartoes", "Under_55_Cartoes",
        "BTTS_Sim", "BTTS_Nao",
        "xG_Para", "xG_Contra", "Diff_xG",
        "Metas_Para", "Metas_Contra",  # chutes a favor / sofridos por partida
        "Finalizando_Delta", "Delta_Concedido",
    ]

    # Colunas que o usuário preenche em % (0–100) mas que o sistema
    # armazena e usa internamente como fração (0.0–1.0). A conversão
    # acontece no data_editor via column_config (sem tocar nos dados
    # internos dos cálculos).
    COLUNAS_PERCENTUAL = [
        "Vitoria_%", "Empate_%", "Derrota_%",
        "Over_05_Gols", "Under_05_Gols",
        "Over_15_Gols", "Under_15_Gols",
        "Over_25_Gols", "Under_25_Gols",
        "Over_35_Gols", "Under_35_Gols",
        "Over_75_Cantos", "Under_75_Cantos",
        "Over_85_Cantos", "Under_85_Cantos",
        "Over_95_Cantos", "Under_95_Cantos",
        "Over_105_Cantos", "Under_105_Cantos",
        "Over_25_Cartoes", "Under_25_Cartoes",
        "Over_35_Cartoes", "Under_35_Cartoes",
        "Over_45_Cartoes", "Under_45_Cartoes",
        "Over_55_Cartoes", "Under_55_Cartoes",
        "BTTS_Sim", "BTTS_Nao",
    ]

    PARES_OVER_UNDER = [
        ("Over_05_Gols", "Under_05_Gols"),
        ("Over_15_Gols", "Under_15_Gols"),
        ("Over_25_Gols", "Under_25_Gols"),
        ("Over_35_Gols", "Under_35_Gols"),
        ("Over_75_Cantos", "Under_75_Cantos"),
        ("Over_85_Cantos", "Under_85_Cantos"),
        ("Over_95_Cantos", "Under_95_Cantos"),
        ("Over_105_Cantos", "Under_105_Cantos"),
        ("Over_25_Cartoes", "Under_25_Cartoes"),
        ("Over_35_Cartoes", "Under_35_Cartoes"),
        ("Over_45_Cartoes", "Under_45_Cartoes"),
        ("Over_55_Cartoes", "Under_55_Cartoes"),
        ("BTTS_Sim", "BTTS_Nao"),
    ]

    TIMES_SERIE_A = [
        "Atlético-MG", "Athletico-PR", "Bahia", "Botafogo", "Bragantino",
        "Chapecoense", "Corinthians", "Coritiba", "Cruzeiro", "Flamengo",
        "Fluminense", "Grêmio", "Internacional", "Mirassol", "Palmeiras",
        "Remo", "Santos", "São Paulo", "Vasco", "Vitória",
    ]

    LINHAS_DISPLAY = {
        "05": "0.5", "15": "1.5", "25": "2.5", "35": "3.5",
        "45": "4.5", "55": "5.5", "75": "7.5", "85": "8.5",
        "95": "9.5", "105": "10.5",
    }

    CALIBRACAO_PADRAO = {
        "peso_xg_ataque": 0.5,
        "peso_xg_defesa": 0.5,
        "peso_finalizacao": 0.15,
        "peso_concedido": 0.15,
        "peso_chutes_ataque": 0.15,
        "peso_chutes_defesa": 0.15,
        "fator_mando": 1.10,
        "fator_calibracao_gols": 1.00,
        "fator_calibracao_cantos": 1.00,
        "fator_calibracao_cartoes": 1.00,
        "peso_historico_cantos": 0.40,
        "peso_historico_cartoes": 0.40,
        "peso_historico_btts": 0.40,
        "peso_bp": 0.15,
    }

    LIMITES_CALIBRACAO = {
        "fator_calibracao_gols": (0.70, 1.30),
        "fator_calibracao_cantos": (0.70, 1.30),
        "fator_calibracao_cartoes": (0.70, 1.30),
    }

    # ------------------------------------------------------------------
    # FUNÇÕES DA BASE DE DADOS
    # ------------------------------------------------------------------

    def _linha_zerada_base(nome):
        linha = {c: 0.0 for c in COLUNAS_BASE}
        linha["Equipe"] = nome
        return linha

    def _recalcular_derivadas(df):
        df = df.copy()
        for col_over, col_under in PARES_OVER_UNDER:
            df[col_under] = (1 - df[col_over]).round(4)
        df["Diff_xG"] = (df["xG_Para"] - df["xG_Contra"]).round(4)
        return df

    def _criar_base_inicial():
        linhas = []
        for t in TIMES_SERIE_A:
            l = _linha_zerada_base(t)
            if t == "Atlético-MG":
                l["Partidas"] = 23
                l["Gols_Marcados"] = 1.30
                l["Gols_Sofridos"] = 1.17
                l["BTTS_Sim"] = 0.60
                l["xG_Para"] = 1.30
                l["xG_Contra"] = 1.21
            linhas.append(l)
        df = pd.DataFrame(linhas, columns=COLUNAS_BASE)
        return _recalcular_derivadas(df)

    def _carregar_base():
        if not os.path.exists(ARQUIVO_BASE):
            df = _criar_base_inicial()
            _salvar_base(df)
            return df
        try:
            df = pd.read_csv(ARQUIVO_BASE, encoding="utf-8")
        except Exception:
            return _criar_base_inicial()
        for c in COLUNAS_BASE:
            if c not in df.columns:
                df[c] = 0.0
        return _recalcular_derivadas(df[COLUNAS_BASE])

    def _salvar_base(df):
        df[COLUNAS_BASE].to_csv(ARQUIVO_BASE, index=False, encoding="utf-8")
        salvar_no_github(ARQUIVO_BASE)

    def _obter_time(df, nome):
        linha = df[df["Equipe"] == nome]
        if linha.empty:
            raise ValueError(f"Time '{nome}' não encontrado.")
        return linha.iloc[0]

    # ------------------------------------------------------------------
    # FUNÇÕES DE CALIBRAÇÃO
    # ------------------------------------------------------------------

    def _obter_calibracao():
        if not os.path.exists(ARQUIVO_CALIBRACAO):
            _salvar_calibracao(CALIBRACAO_PADRAO.copy())
            return CALIBRACAO_PADRAO.copy()
        try:
            with open(ARQUIVO_CALIBRACAO, "r", encoding="utf-8") as f:
                c = json.load(f)
        except Exception:
            return CALIBRACAO_PADRAO.copy()
        for k, v in CALIBRACAO_PADRAO.items():
            if k not in c:
                c[k] = v
        return c

    def _salvar_calibracao(calib):
        with open(ARQUIVO_CALIBRACAO, "w", encoding="utf-8") as f:
            json.dump(calib, f, indent=4, ensure_ascii=False)
        salvar_no_github(ARQUIVO_CALIBRACAO)

    def _ajustar_fator(calib, chave, delta):
        v = calib[chave] + delta
        if chave in LIMITES_CALIBRACAO:
            vmin, vmax = LIMITES_CALIBRACAO[chave]
            v = max(vmin, min(vmax, v))
        calib[chave] = round(v, 4)
        return calib

    # ------------------------------------------------------------------
    # MOTOR DE CÁLCULO (POISSON + CRUZAMENTO DE VARIÁVEIS)
    # ------------------------------------------------------------------

    def _poisson(k, lam):
        lam = max(lam, 0.01)
        return (lam ** k) * _math.exp(-lam) / _math.factorial(k)

    def _prob_over_linha(lam, linha):
        limite = int(_math.floor(linha)) + 1
        return max(0.0, min(1.0, 1 - sum(_poisson(k, lam) for k in range(limite))))

    def _matriz_poisson(lam_c, lam_f, mx=10):
        return {
            (gc, gf): _poisson(gc, lam_c) * _poisson(gf, lam_f)
            for gc in range(mx + 1) for gf in range(mx + 1)
        }

    def _prob_cond(matriz, cond):
        return sum(p for (gc, gf), p in matriz.items() if cond(gc, gf))

    def _conf_amostra(jogos, minimo=10):
        return min(1.0, jogos / minimo) if jogos > 0 else 0.0

    def _fator_chutes(chutes):
        return chutes / MEDIA_LIGA_CHUTES if chutes > 0 else 1.0

    def _forca_ataque(time, calib):
        pxg = calib["peso_xg_ataque"]
        base = time["Gols_Marcados"] * (1 - pxg) + time["xG_Para"] * pxg
        base += time["Finalizando_Delta"] * calib["peso_finalizacao"]
        mult = 1 + (_fator_chutes(time["Metas_Para"]) - 1) * calib["peso_chutes_ataque"]
        return max(0.05, base * mult)

    def _forca_defesa(time, calib):
        pxg = calib["peso_xg_defesa"]
        base = time["Gols_Sofridos"] * (1 - pxg) + time["xG_Contra"] * pxg
        base += time["Delta_Concedido"] * calib["peso_concedido"]
        mult = 1 + (_fator_chutes(time["Metas_Contra"]) - 1) * calib["peso_chutes_defesa"]
        return max(0.05, base * mult)

    def _gols_esperados(tc, tf, calib):
        ac = _forca_ataque(tc, calib)
        df_ = _forca_defesa(tf, calib)
        af = _forca_ataque(tf, calib)
        dc = _forca_defesa(tc, calib)
        lc = (ac / MEDIA_LIGA_GOLS) * (df_ / MEDIA_LIGA_GOLS) * MEDIA_LIGA_GOLS * calib["fator_mando"] * calib["fator_calibracao_gols"]
        lf = (af / MEDIA_LIGA_GOLS) * (dc / MEDIA_LIGA_GOLS) * MEDIA_LIGA_GOLS * calib["fator_calibracao_gols"]
        cc = _conf_amostra(tc["Jogos_Casa"])
        cf = _conf_amostra(tf["Jogos_Fora"])
        lc = lc * cc + (MEDIA_LIGA_GOLS / 2) * (1 - cc)
        lf = lf * cf + (MEDIA_LIGA_GOLS / 2) * (1 - cf)
        return max(0.05, lc), max(0.05, lf)

    def _prever(df_times, nome_casa, nome_fora):
        calib = _obter_calibracao()
        tc = _obter_time(df_times, nome_casa)
        tf = _obter_time(df_times, nome_fora)

        lc, lf = _gols_esperados(tc, tf, calib)
        matriz = _matriz_poisson(lc, lf)

        # 1X2 base (Poisson)
        pc = _prob_cond(matriz, lambda gc, gf: gc > gf)
        pe = _prob_cond(matriz, lambda gc, gf: gc == gf)
        pf = _prob_cond(matriz, lambda gc, gf: gc < gf)

        # Ajuste por BP
        conf_c = _conf_amostra(tc["Jogos_Casa"], 8)
        conf_f = _conf_amostra(tf["Jogos_Fora"], 8)
        bp_c = tc["BP_Casa"] * conf_c + tc["BP_Geral"] * (1 - conf_c)
        bp_f = tf["BP_Fora"] * conf_f + tf["BP_Geral"] * (1 - conf_f)
        ajuste_bp = ((bp_c - bp_f) / 3.0) * calib["peso_bp"]
        pc = max(0.01, min(0.98, pc + ajuste_bp))
        pf = max(0.01, min(0.98, pf - ajuste_bp))
        pe = max(0.01, 1 - pc - pf)

        # Ajuste por histórico de Vitória/Empate/Derrota_%
        # Só aplica se os dados foram preenchidos (soma > 0).
        # Usa a taxa histórica de vitória da casa e derrota do
        # visitante (= vitória da casa no ponto de vista do fora)
        # como um sinal adicional, com peso pequeno (20%) para não
        # sobrepor o modelo de gols.
        hist_peso = 0.20
        v_casa = tc["Vitoria_%"]   # taxa histórica de vitória da casa
        v_fora = tf["Vitoria_%"]   # taxa histórica de vitória do fora
        e_casa = tc["Empate_%"]
        e_fora = tf["Empate_%"]
        d_casa = tc["Derrota_%"]   # = taxa de derrota da casa (visitante vence)

        soma_hist_c = v_casa + e_casa + d_casa
        soma_hist_f = v_fora + e_fora + tf["Derrota_%"]

        if soma_hist_c > 0 and soma_hist_f > 0:
            # Taxa histórica ponderada de cada resultado
            hist_pc = (v_casa / soma_hist_c + (1 - tf["Derrota_%"] / soma_hist_f) * 0.5) / 1.5
            hist_pe = (e_casa / soma_hist_c + e_fora / soma_hist_f) / 2
            hist_pf = (d_casa / soma_hist_c + v_fora / soma_hist_f) / 2
            # Mistura modelo Poisson+BP (80%) com histórico (20%)
            pc = pc * (1 - hist_peso) + hist_pc * hist_peso
            pe = pe * (1 - hist_peso) + hist_pe * hist_peso
            pf = pf * (1 - hist_peso) + hist_pf * hist_peso

        soma = pc + pe + pf
        pc, pe, pf = pc / soma, pe / soma, pf / soma

        # Over/Under gols
        gols_over = {}
        for lin, val in [("05", 0.5), ("15", 1.5), ("25", 2.5), ("35", 3.5)]:
            p_ov = _prob_cond(matriz, lambda gc, gf, v=val: (gc + gf) > v)
            gols_over[lin] = round(p_ov, 4)

        # BTTS
        btts_mod = _prob_cond(matriz, lambda gc, gf: gc >= 1 and gf >= 1)
        med_btts = (tc["BTTS_Sim"] + tf["BTTS_Sim"]) / 2
        ph = calib["peso_historico_btts"]
        btts = btts_mod * (1 - ph) + med_btts * ph

        # Cantos
        lc_cant = (tc["Cantos_Concedidos"] + tf["Cantos_Tomados"]) / 2 * calib["fator_calibracao_cantos"]
        lf_cant = (tf["Cantos_Concedidos"] + tc["Cantos_Tomados"]) / 2 * calib["fator_calibracao_cantos"]
        tot_cant = max(0.5, lc_cant) + max(0.5, lf_cant)
        cant_over = {}
        ph_cant = calib["peso_historico_cantos"]
        for lin, val in [("75", 7.5), ("85", 8.5), ("95", 9.5), ("105", 10.5)]:
            pm = _prob_over_linha(tot_cant, val)
            mh = (tc[f"Over_{lin}_Cantos"] + tf[f"Over_{lin}_Cantos"]) / 2
            cant_over[lin] = round(pm * (1 - ph_cant) + mh * ph_cant, 4)

        # Cartões
        lc_cart = (tc["Cartoes_Recebidos"] + tf["Cartoes_Opostos"]) / 2 * calib["fator_calibracao_cartoes"]
        lf_cart = (tf["Cartoes_Recebidos"] + tc["Cartoes_Opostos"]) / 2 * calib["fator_calibracao_cartoes"]
        tot_cart = max(0.2, lc_cart) + max(0.2, lf_cart)
        cart_over = {}
        ph_cart = calib["peso_historico_cartoes"]
        for lin, val in [("25", 2.5), ("35", 3.5), ("45", 4.5), ("55", 5.5)]:
            pm = _prob_over_linha(tot_cart, val)
            mh = (tc[f"Over_{lin}_Cartoes"] + tf[f"Over_{lin}_Cartoes"]) / 2
            cart_over[lin] = round(pm * (1 - ph_cart) + mh * ph_cart, 4)

        return {
            "casa": nome_casa, "fora": nome_fora,
            "lc": round(lc, 2), "lf": round(lf, 2),
            "pc": round(pc, 4), "pe": round(pe, 4), "pf": round(pf, 4),
            "btts_sim": round(btts, 4), "btts_nao": round(1 - btts, 4),
            "gols_over": gols_over,
            "cant_total": round(tot_cant, 2),
            "cant_over": cant_over,
            "cart_total": round(tot_cart, 2),
            "cart_over": cart_over,
        }

    # ------------------------------------------------------------------
    # AUTO-APRENDIZADO
    # ------------------------------------------------------------------

    def _registrar_previsao(prev):
        df = pd.read_csv(ARQUIVO_PREVISOES, encoding="utf-8") if os.path.exists(ARQUIVO_PREVISOES) else pd.DataFrame()
        novo_id = int(df["ID"].max()) + 1 if not df.empty and "ID" in df.columns else 1
        linha = {
            "ID": novo_id, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Time_Casa": prev["casa"], "Time_Fora": prev["fora"],
            "Gols_Esp_Casa": prev["lc"], "Gols_Esp_Fora": prev["lf"],
            "Cantos_Esp": prev["cant_total"], "Cartoes_Esp": prev["cart_total"],
            "Gols_Casa_Real": "", "Gols_Fora_Real": "",
            "Cantos_Real": "", "Cartoes_Real": "",
            "Erro_Gols": "", "Erro_Cantos": "", "Erro_Cartoes": "",
            "Resolvida": False,
        }
        df = pd.concat([df, pd.DataFrame([linha])], ignore_index=True)
        df.to_csv(ARQUIVO_PREVISOES, index=False, encoding="utf-8")
        salvar_no_github(ARQUIVO_PREVISOES)
        return novo_id

    def _registrar_resultado(id_prev, gc_real, gf_real, cant_real, cart_real):
        if not os.path.exists(ARQUIVO_PREVISOES):
            return None
        df = pd.read_csv(ARQUIVO_PREVISOES, encoding="utf-8")
        filtro = df["ID"] == id_prev
        if not filtro.any():
            return None
        linha = df[filtro].iloc[0]
        gols_prev = float(linha["Gols_Esp_Casa"]) + float(linha["Gols_Esp_Fora"])
        erro_g = round(gols_prev - (gc_real + gf_real), 2)
        erro_c = round(float(linha["Cantos_Esp"]) - cant_real, 2)
        erro_ct = round(float(linha["Cartoes_Esp"]) - cart_real, 2)
        df.loc[filtro, ["Gols_Casa_Real", "Gols_Fora_Real", "Cantos_Real", "Cartoes_Real",
                        "Erro_Gols", "Erro_Cantos", "Erro_Cartoes", "Resolvida"]] = [
            gc_real, gf_real, cant_real, cart_real, erro_g, erro_c, erro_ct, True
        ]
        df.to_csv(ARQUIVO_PREVISOES, index=False, encoding="utf-8")
        salvar_no_github(ARQUIVO_PREVISOES)
        # Ajusta calibração
        calib = _obter_calibracao()
        calib = _ajustar_fator(calib, "fator_calibracao_gols", -erro_g * 0.02)
        calib = _ajustar_fator(calib, "fator_calibracao_cantos", -erro_c * 0.01)
        calib = _ajustar_fator(calib, "fator_calibracao_cartoes", -erro_ct * 0.01)
        _salvar_calibracao(calib)
        return {"erro_gols": erro_g, "erro_cantos": erro_c, "erro_cartoes": erro_ct}

    # ------------------------------------------------------------------
    # INTERFACE STREAMLIT DA ABA 2
    # ------------------------------------------------------------------

    df_base = _carregar_base()
    nomes_times = sorted(df_base["Equipe"].tolist())

    col1, col2 = st.columns(2)
    with col1:
        sel_casa = st.selectbox("🏠 Time Casa", nomes_times, key="base_casa")
    with col2:
        sel_fora = st.selectbox("✈️ Time Fora", nomes_times, key="base_fora")

    if sel_casa == sel_fora:
        st.warning("Selecione times diferentes.")
    else:
        tc_info = _obter_time(df_base, sel_casa)
        tf_info = _obter_time(df_base, sel_fora)

        col1, col2 = st.columns(2)
        with col1:
            st.caption(
                f"**{sel_casa}** — {int(tc_info['Partidas'])} jogos | "
                f"Gols: {tc_info['Gols_Marcados']} marcados / {tc_info['Gols_Sofridos']} sofridos | "
                f"xG: {tc_info['xG_Para']} / {tc_info['xG_Contra']}"
            )
        with col2:
            st.caption(
                f"**{sel_fora}** — {int(tf_info['Partidas'])} jogos | "
                f"Gols: {tf_info['Gols_Marcados']} marcados / {tf_info['Gols_Sofridos']} sofridos | "
                f"xG: {tf_info['xG_Para']} / {tf_info['xG_Contra']}"
            )

        if st.button("🔍 Analisar Partida", key="base_analisar"):

            with st.spinner("Calculando..."):
                prev = _prever(df_base, sel_casa, sel_fora)

            st.session_state["ultima_previsao_base"] = prev

            st.subheader(f"📋 {sel_casa} x {sel_fora}")

            # 1X2
            col1, col2, col3 = st.columns(3)
            col1.metric("🏠 Casa", f"{prev['pc']*100:.1f}%")
            col2.metric("🤝 Empate", f"{prev['pe']*100:.1f}%")
            col3.metric("✈️ Fora", f"{prev['pf']*100:.1f}%")

            st.write(
                f"⚽ Gols esperados: **{prev['lc']}** x **{prev['lf']}** "
                f"(total: {prev['lc'] + prev['lf']:.2f})"
            )

            # BTTS
            col1, col2 = st.columns(2)
            col1.metric("BTTS Sim", f"{prev['btts_sim']*100:.1f}%")
            col2.metric("BTTS Não", f"{prev['btts_nao']*100:.1f}%")

            # Gols Over/Under
            st.subheader("⚽ Gols — Over/Under")
            cols = st.columns(4)
            for i, lin in enumerate(["05", "15", "25", "35"]):
                ov = prev["gols_over"][lin]
                cols[i].metric(f"Over {LINHAS_DISPLAY[lin]}", f"{ov*100:.1f}%", f"Under {(1-ov)*100:.1f}%")

            # Cantos
            st.subheader(f"🚩 Cantos (esperado: {prev['cant_total']})")
            cols = st.columns(4)
            for i, lin in enumerate(["75", "85", "95", "105"]):
                ov = prev["cant_over"][lin]
                cols[i].metric(f"Over {LINHAS_DISPLAY[lin]}", f"{ov*100:.1f}%", f"Under {(1-ov)*100:.1f}%")

            # Cartões
            st.subheader(f"🟨 Cartões (esperado: {prev['cart_total']})")
            cols = st.columns(4)
            for i, lin in enumerate(["25", "35", "45", "55"]):
                ov = prev["cart_over"][lin]
                cols[i].metric(f"Over {LINHAS_DISPLAY[lin]}", f"{ov*100:.1f}%", f"Under {(1-ov)*100:.1f}%")

            # Salvar previsão
            if st.button("💾 Salvar Previsão", key="base_salvar_prev"):
                id_prev = _registrar_previsao(prev)
                st.success(f"Previsão salva com ID {id_prev} em {ARQUIVO_PREVISOES}")

    # ------------------------------------------------------------------
    # AUTO-APRENDIZADO: REGISTRAR RESULTADO REAL
    # ------------------------------------------------------------------

    st.divider()
    st.subheader("🎓 Auto-Aprendizado — Registrar Resultado Real")
    st.caption(
        "Informe o resultado real de uma partida já prevista. "
        "O sistema ajusta automaticamente os pesos internos (calibracao.json)."
    )

    if os.path.exists(ARQUIVO_PREVISOES):
        df_prev = pd.read_csv(ARQUIVO_PREVISOES, encoding="utf-8")
        pendentes = df_prev[df_prev["Resolvida"] == False] if "Resolvida" in df_prev.columns else pd.DataFrame()

        if not pendentes.empty:
            opcoes = pendentes.apply(
                lambda r: f"ID {int(r['ID'])} — {r['Time_Casa']} x {r['Time_Fora']} ({r['Data']})",
                axis=1
            ).tolist()
            sel_prev = st.selectbox("Selecione a previsão", opcoes, key="base_sel_prev")
            id_sel = int(sel_prev.split(" ")[1])

            col1, col2 = st.columns(2)
            with col1:
                gc_real = st.number_input("Gols Casa (real)", min_value=0, step=1, key="base_gc")
                cant_real = st.number_input("Cantos (real)", min_value=0, step=1, key="base_cant")
            with col2:
                gf_real = st.number_input("Gols Fora (real)", min_value=0, step=1, key="base_gf")
                cart_real = st.number_input("Cartões (real)", min_value=0, step=1, key="base_cart")

            if st.button("✅ Registrar e Aprender", key="base_aprender"):
                resultado = _registrar_resultado(id_sel, gc_real, gf_real, cant_real, cart_real)
                if resultado:
                    st.success(
                        f"Resultado registrado! "
                        f"Erro gols: {resultado['erro_gols']} | "
                        f"Erro cantos: {resultado['erro_cantos']} | "
                        f"Erro cartões: {resultado['erro_cartoes']}"
                    )
                    calib_atual = _obter_calibracao()
                    st.write("🔧 Calibração atualizada:")
                    st.json({
                        k: v for k, v in calib_atual.items()
                        if k.startswith("fator_calibracao")
                    })
        else:
            st.info("Nenhuma previsão pendente de resultado.")
    else:
        st.info("Nenhuma previsão salva ainda. Analise uma partida e clique em 'Salvar Previsão'.")

    # ------------------------------------------------------------------
    # EDITAR BASE DE DADOS
    # ------------------------------------------------------------------

    st.divider()
    with st.expander("📝 Editar Base de Dados dos Times"):
        st.caption(
            "Edite os valores direto aqui e clique em Salvar. "
            "Ou edite o arquivo times_serie_a_completo.csv no GitHub e recarregue o app. "
            "Os campos de % aceitam valores de 0 a 100 (ex: 60 = 60%). "
            "O sistema converte automaticamente para fração interna."
        )

        # Cria uma cópia de exibição com percentuais em escala 0-100
        # para facilitar a edição. Os valores internos continuam em
        # 0.0-1.0 para os cálculos.
        df_exibicao = df_base.copy()
        for col in COLUNAS_PERCENTUAL:
            if col in df_exibicao.columns:
                df_exibicao[col] = (df_exibicao[col] * 100).round(1)

        # Configuração visual das colunas no data_editor
        col_cfg = {}
        for col in COLUNAS_PERCENTUAL:
            col_cfg[col] = st.column_config.NumberColumn(
                col,
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.1f%%",
                help="Digite o valor em % (ex: 60 para 60%)"
            )

        df_editado = st.data_editor(
            df_exibicao,
            column_config=col_cfg,
            use_container_width=True,
            num_rows="fixed",
            key="base_editor"
        )

        if st.button("💾 Salvar Base de Dados", key="base_salvar"):
            # Converte de volta para fração (0.0-1.0) antes de salvar
            df_salvar = df_editado.copy()
            for col in COLUNAS_PERCENTUAL:
                if col in df_salvar.columns:
                    df_salvar[col] = (df_salvar[col] / 100).round(4)
            df_salvar_calc = _recalcular_derivadas(df_salvar)
            _salvar_base(df_salvar_calc)
            st.success("Base salva e enviada ao GitHub!")
