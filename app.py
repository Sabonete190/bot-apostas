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

PESO_XG = pesos_1x2["peso_xg"]
PESO_CHUTES = pesos_1x2["peso_chutes"]
PESO_EFICIENCIA = pesos_1x2["peso_eficiencia"]
PESO_TABELA = pesos_1x2["peso_tabela"]
PESO_FORMA = pesos_1x2["peso_forma"]
PESO_FORCA = pesos_1x2["peso_forca"]

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
# CONFIGURAÇÃO DA PAGINA
st.set_page_config(
    page_title="Bot de Apostas",
    layout="centered"
)

# =========================
# SESSION STATE
# =========================

if "melhor_mercado" not in st.session_state:

    st.session_state["melhor_mercado"] = "N/A"

# TITULO
st.title("Bot de Apostas Profissional")

st.write("Preencha os dados da partida.")
# =========================
# HISTORICO CSV
# =========================

ARQUIVO_HISTORICO = "historico_apostas.csv"
ARQUIVO_RESULTADOS = "resultados_apostas.csv"

# =========================
# ESQUEMA DE COLUNAS (CONTEXTO COMPLETO DA APOSTA)
# =========================
# Conjunto Ãºnico de campos de contexto, usado tanto no histÃ³rico
# quanto no registro de resultados, na ordem definida pelo usuÃ¡rio.

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
    "EficiÃªncia Casa",
    "EficiÃªncia Fora",
    "Chutes Casa",
    "Chutes Fora",
    "Gols Esperados Casa",
    "Gols Esperados Fora",
    "Placar Final",
]

# historico_apostas.csv precisa de um identificador estÃ¡vel para o
# selectbox de "Selecione a aposta", entÃ£o "ID" Ã© mantido como a
# Ãºnica coluna extra alÃ©m do contexto pedido.
COLUNAS_HISTORICO = ["ID"] + COLUNAS_CONTEXTO

# resultados_apostas.csv precisa de Stake/Lucro para o painel de
# performance (winrate, ROI) e para o cÃ¡lculo de banca, entÃ£o essas
# duas colunas sÃ£o mantidas alÃ©m do contexto pedido.
COLUNAS_RESULTADOS = COLUNAS_CONTEXTO + ["Stake R$", "Lucro"]

# =========================
# CARREGAMENTO TOLERANTE A ESQUEMA ANTIGO
# =========================
# CSVs salvos antes da migraÃ§Ã£o de colunas (ex.: com "Resultado" em
# vez de "Resultado Mercado", ou sem "Placar Final") nÃ£o tÃªm as
# colunas novas. Esta funÃ§Ã£o sempre devolve um DataFrame com todas
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
        df = pd.read_csv(caminho)
    except Exception:
        return pd.DataFrame(columns=colunas_esperadas)

    if mapa_legado:
        for coluna_antiga, coluna_nova in mapa_legado.items():
            if coluna_antiga in df.columns and coluna_nova not in df.columns:
                df = df.rename(columns={coluna_antiga: coluna_nova})

    # Garante que toda coluna esperada existe. NaN (em vez de "")
    # para nÃ£o quebrar .mean()/agregaÃ§Ãµes nas colunas numÃ©ricas;
    # comparaÃ§Ãµes como df["Resultado Mercado"] == "GREEN" continuam
    # funcionando normalmente (dÃ£o False, nÃ£o erro).
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
                ARQUIVO_HISTORICO
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
        index=False
    )


def salvar_resultado(dados):

    df_novo = pd.DataFrame([dados])

    if os.path.exists(ARQUIVO_RESULTADOS):

        try:

            df_antigo = pd.read_csv(
                ARQUIVO_RESULTADOS
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
        index=False
    )
def salvar_pesos():

    # MantÃ©m a estrutura aninhada original do pesos.json
    # (1x2 / over25 / under25 / btts). SÃ³ o bloco "1x2" Ã©
    # atualizado, pois Ã© o Ãºnico ajustado por atualizar_pesos().
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
        "btts": pesos_btts
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

    # resultados_apostas.csv agora jÃ¡ traz o contexto completo (xG,
    # chutes, forma etc.), entÃ£o nÃ£o Ã© mais necessÃ¡rio fazer merge
    # com o historico_apostas.csv para obter essas estatÃ­sticas.
    # carregar_csv_com_esquema jÃ¡ garante que todas as colunas do
    # esquema existem (mesmo que vazias), entÃ£o nÃ£o Ã© preciso
    # verificar coluna a coluna aqui.

    ultimos = df.tail(10)

    # Separa por mercado
    mercados = {
        "1x2": ["VitÃ³ria Casa", "Empate", "VitÃ³ria Fora"],
        "over25": ["Over 2.5"],
        "under25": ["Under 2.5"],
        "btts": ["BTTS SIM", "BTTS NÃƒO"]
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

        # Ajuste pequeno para evitar mudanÃ§as bruscas
        ajuste = saldo * 0.01

        media_xg = resultados_mercado[["xG Casa", "xG Fora"]].mean().mean()
        media_chutes = resultados_mercado[["Chutes Casa", "Chutes Fora"]].mean().mean()
        media_eficiencia = resultados_mercado[["EficiÃªncia Casa", "EficiÃªncia Fora"]].mean().mean()
        media_forma = resultados_mercado[["Forma Casa", "Forma Fora"]].mean().mean() / 30

        # Cada termo sÃ³ Ã© aplicado se houver dado vÃ¡lido para ele,
        # em vez de pular o mercado inteiro quando falta uma Ãºnica
        # estatÃ­stica. PosiÃ§Ã£o na tabela nÃ£o faz mais parte do
        # esquema de colunas pedido, entÃ£o PESO_TABELA nÃ£o Ã© mais
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
    "Odd BTTS NÃƒO",
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

odd_time_marca_primeiro = st.number_input(
    "Odd Time marca primeiro",
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
# POSIÃ‡ÃƒO NA TABELA
# =========================

st.subheader("Tabela BrasileirÃ£o")

posicao_casa = st.number_input(
    "PosiÃ§Ã£o Time Casa",
    min_value=1,
    max_value=20,
    value=10
)

posicao_fora = st.number_input(
    "PosiÃ§Ã£o Time Fora",
    min_value=1,
    max_value=20,
    value=10
)
# =========================
# DADOS DOS TIMES
# =========================

st.subheader("Dados dos Times")

xg_casa = st.number_input(
    "xG Casa",
    min_value=0.0,
    step=0.1
)

xg_fora = st.number_input(
    "xG Fora",
    min_value=0.0,
    step=0.1
)

xga_casa = st.number_input(
    "xGA Casa",
    min_value=0.0,
    step=0.1
)

xga_fora = st.number_input(
    "xGA Fora",
    min_value=0.0,
    step=0.1
)

sofridos_casa = st.number_input(
    "Gols Sofridos Casa",
    min_value=0.0,
    step=0.1
)

sofridos_fora = st.number_input(
    "Gols Sofridos Fora",
    min_value=0.0,
    step=0.1
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
    "EficiÃªncia Casa",
    min_value=0.0,
    step=0.1
)

eficiencia_fora = st.number_input(
    "EficiÃªncia Fora",
    min_value=0.0,
    step=0.1
)
# =========================
# FORMA RECENTE
# =========================

st.subheader("Forma Recente")

forma_casa = st.number_input(
    "Forma Casa (Ãºltimos 5 jogos)",
    min_value=0,
    max_value=15,
    step=1
)

forma_fora = st.number_input(
    "Forma Fora (Ãºltimos 5 jogos)",
    min_value=0,
    max_value=15,
    step=1
)

# =========================
# FORÃ‡A AUTOMÃTICA
# =========================

def calcular_forca(odd):

    if odd <= 1.70:
        return 1.35, "Muito Forte"

    elif odd <= 2.10:
        return 1.20, "Forte"

    elif odd <= 2.80:
        return 1.00, "MÃ©dio"

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

st.subheader("ForÃ§a AutomÃ¡tica")

st.write(
    f"ForÃ§a Casa: {nivel_casa}"
)

st.write(
    f"ForÃ§a Fora: {nivel_fora}"
)
# =========================
# IDENTIFICAÃ‡ÃƒO DO JOGO
# =========================

time_casa = st.text_input(
    "Time Casa"
)

time_fora = st.text_input(
    "Time Fora"
)

campeonato = st.text_input(
    "Campeonato"
)

# =========================
# DADOS DO BRASILEIRÃƒO
# =========================

media_gols_liga = 2.63

media_btts_liga = 0.57

media_over35_liga = 0.49

media_mandante_liga = 0.47

media_visitante_liga = 0.24

media_empate_liga = 0.29

# =========================
# BOTÃƒO
# =========================

if st.button("Analisar Jogo"):

    # =========================
    # FORÃ‡A DA TABELA
    # =========================

    forca_tabela_casa = (
        (21 - posicao_casa) / 20
    )

    forca_tabela_fora = (
        (21 - posicao_fora) / 20
    )
    # =========================
    # FORÃ‡A OFENSIVA
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
    # FORÃ‡A DEFENSIVA
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
    # FORÃ‡A DE GOL
    # =========================

    forca_gol = (
        (ataque_casa / (defesa_fora + 0.5)) +
        (ataque_fora / (defesa_casa + 0.5))
    ) / 2

    st.subheader("AnÃ¡lise EstatÃ­stica")

    st.write(f"Ataque Casa: {round(ataque_casa, 2)}")
    st.write(f"Ataque Fora: {round(ataque_fora, 2)}")

    st.write(f"Defesa Casa: {round(defesa_casa, 2)}")
    st.write(f"Defesa Fora: {round(defesa_fora, 2)}")

    st.write(f"ForÃ§a de Gol: {round(forca_gol, 2)}")
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

    # Guardados aqui porque o botÃ£o "Salvar Aposta" roda num rerun
    # separado do Streamlit, onde as variÃ¡veis locais deste bloco
    # ("Analisar Jogo") nÃ£o existem mais.
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

    st.subheader("Placares Mais ProvÃ¡veis")

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
    # FUNÃ‡ÃƒO PARA SOMAR
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
    # TIME MARCA PRIMEIRO
    # =========================

    prob_time_marca_primeiro = (
        probabilidade_mercado(
            lambda casa, fora:
            casa > 0 and casa > fora
        )
        +
        probabilidade_mercado(
            lambda casa, fora:
            fora > 0 and fora > casa
        )
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

        "BTTS NÃƒO": {
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

        "Time marca primeiro": {
            "probabilidade": prob_time_marca_primeiro,
            "odd": odd_time_marca_primeiro
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

    st.subheader("ðŸ† Melhor Mercado")

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
            f"ðŸ”¥ Melhor Mercado: {melhor_mercado}"
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
            "âŒ Nenhum mercado possui valor positivo."
            )


        # =========================
        # EXIBIR RESULTADOS
        # =========================

        st.subheader(
            "AnÃ¡lise Completa dos Mercados"
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
            f"BTTS NÃƒO: "
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
            f"Odd Justa BTTS NÃƒO: "
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
            f"EV BTTS NÃƒO: "
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
            f"Edge BTTS NÃƒO: "
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
            f"Kelly BTTS NÃƒO: "
            f"{round(kelly_btts_nao * 100, 2)}%"
        )
     # =========================
        # PROBABILIDADES PRÃ“PRIAS
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
        # PROBABILIDADES IMPLÃCITAS
        # =========================

        prob_casa = 1 / odd_casa
        prob_empate = 1 / odd_empate
        prob_fora = 1 / odd_fora

        # =========================
        # NORMALIZAÃ‡ÃƒO
        # =========================

        soma = prob_casa + prob_empate + prob_fora

        prob_casa /= soma
        prob_empate /= soma
        prob_fora /= soma

        # =========================
        # RESULTADO
        # =========================

        st.success("AnÃ¡lise concluÃ­da")

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
        # CONFIANÃ‡A DO MODELO
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

        st.subheader("ConfianÃ§a do Modelo")

        st.write(
            f"ConfianÃ§a: {round(confianca, 1)}/10"
        )
        # =========================
        # DECISÃƒO INTELIGENTE
        # =========================

        st.subheader("DecisÃ£o do Modelo")

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
                "ðŸ”¥ Entrada Forte Detectada"
            )

        elif (
            melhor_edge >= 0.05
            and melhor_ev >= 0.05
            and confianca >= 5
        ):

            st.warning(
                "âš ï¸ Entrada Moderada"
            )

        else:

            st.error(
                "âŒ Jogo Sem Valor"
            )

        # =========================
        # GESTÃƒO DE STAKE
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

        perfil_jogo = "âš–ï¸ Equilibrado"

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

            perfil_jogo = "ðŸ”¥ Jogo Explosivo"

        # Jogo defensivo

        elif (
            total_xg <= 2
            and prob_under25 >= 0.55
        ):

            perfil_jogo = "ðŸ§± Jogo Defensivo"

        # Favorito forte

        elif (
            diferenca_forca >= 1
            and confianca >= 7
        ):

            perfil_jogo = "ðŸŽ¯ Favorito Forte"

        # BTTS forte

        elif (
            prob_btts_sim >= 0.65
        ):

            perfil_jogo = "âš”ï¸ Jogo Aberto"

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
                ARQUIVO_HISTORICO
            )

            novo_id = len(df_ids) + 1

        except:

            novo_id = 1

    else:

        novo_id = 1

    # =========================
    # RECUPERAR DADOS DA ANÃLISE
    # =========================

    mercado_salvo = st.session_state.get(
        "melhor_mercado",
        "N/A"
    )

    # =========================
    # DEFINIR ODD DO MERCADO
    # =========================

    odds_mercados = {

        "ðŸ”¥ VitÃ³ria Casa": odd_casa,
        "ðŸ¤ Empate": odd_empate,
        "ðŸ”¥ VitÃ³ria Fora": odd_fora,

        "âš½ Over 2.5": odd_over25,
        "ðŸ›¡ï¸ Under 2.5": odd_under25,

        "ðŸ”¥ BTTS SIM": odd_btts_sim,
        "âŒ BTTS NÃƒO": odd_btts_nao,

        "VitÃ³ria Casa": odd_casa,
        "Empate": odd_empate,
        "VitÃ³ria Fora": odd_fora,

        "Over 2.5": odd_over25,
        "Under 2.5": odd_under25,

        "BTTS SIM": odd_btts_sim,
        "BTTS NÃƒO": odd_btts_nao
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

        # Ainda nÃ£o hÃ¡ resultado nem placar no momento da anÃ¡lise;
        # esses campos sÃ£o preenchidos depois, em "Salvar Resultado".
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

        "EficiÃªncia Casa": eficiencia_casa,

        "EficiÃªncia Fora": eficiencia_fora,

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
        "âœ… Aposta salva no histÃ³rico"
    )

# =========================
# RESULTADO DAS APOSTAS
# =========================

st.subheader("Resultado da Aposta")
# =========================
# CARREGAR HISTÃ“RICO
# =========================

historico_resultados = carregar_csv_com_esquema(
    ARQUIVO_HISTORICO,
    COLUNAS_HISTORICO,
    mapa_legado=MAPA_COLUNAS_LEGADAS
)

# =========================
# SELECIONAR APOSTA
# =========================

# Garante que a variÃ¡vel sempre exista, mesmo sem histÃ³rico ainda
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
        # (contexto completo herdado da aposta salva no histÃ³rico,
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
            ARQUIVO_HISTORICO
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
            index=False
          )

          salvar_no_github(
             ARQUIVO_HISTORICO
          )

        except Exception as e:

          st.error(
             f"Erro ao atualizar histÃ³rico: {e}"
          )
    
        verificar_rodada()

        st.success(
            "âœ… Resultado salvo"
        )

# =========================
# ESTATÃSTICAS DO BOT
# =========================

df_stats = carregar_csv_com_esquema(
    ARQUIVO_RESULTADOS,
    COLUNAS_RESULTADOS,
    mapa_legado=MAPA_COLUNAS_LEGADAS
)

# =========================
# PAINEL
# =========================

st.subheader("Performance do Bot")

st.write("PAINEL CARREGADO")

if not df_stats.empty:

    total_apostas = len(df_stats)

    greens = len(
        df_stats[
            df_stats["Resultado Mercado"] == "GREEN"
        ]
    )

    reds = len(
        df_stats[
            df_stats["Resultado Mercado"] == "RED"
        ]
    )

    voids = len(
        df_stats[
            df_stats["Resultado Mercado"] == "VOID"
        ]
    )

    winrate = (
        (greens / total_apostas) * 100
    )

    lucro_total = (
        df_stats["Lucro"].sum()
    )

    total_stakes = (
        df_stats["Stake R$"].sum()
    )

    if total_stakes > 0:

        roi = (
            lucro_total / total_stakes
        ) * 100

    else:

        roi = 0

    st.write(
        f"Total de Apostas: {total_apostas}"
    )

    st.write(
        f"ðŸŸ¢ Greens: {greens}"
    )

    st.write(
        f"ðŸ”´ Reds: {reds}"
    )

    st.write(
        f"âšª Voids: {voids}"
    )

    st.write(
        f"ðŸŽ¯ Winrate: {round(winrate, 2)}%"
    )

    st.write(
        f"ðŸ’° Lucro Total: R$ {round(lucro_total, 2)}"
    )

    st.write(
        f"ðŸ“ˆ ROI: {round(roi, 2)}%"
    )

else:

    st.warning(
        "Nenhum resultado salvo ainda."
    )
