import streamlit as st
import math
import pandas as pd
import os
import requests
import base64
import json

with open("pesos.json","r") as f:
    pesos = json.load(f)
    PESO_XG = pesos["peso_xg"]
PESO_CHUTES = pesos["peso_chutes"]
PESO_EFICIENCIA = pesos["peso_eficiencia"]
PESO_TABELA = pesos["peso_tabela"]
PESO_FORMA = pesos["peso_forma"]
PESO_FORCA = pesos["peso_forca"]

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

st.write("Preencha os dados da partida.")
# =========================
# HISTÓRICO CSV
# =========================

ARQUIVO_HISTORICO = "historico_apostas.csv"

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

    df_final.to_csv(
        ARQUIVO_HISTORICO,
        index=False
    )
def salvar_pesos():

    import json

    pesos = {
        "peso_xg": PESO_XG,
        "peso_chutes": PESO_CHUTES,
        "peso_eficiencia": PESO_EFICIENCIA,
        "peso_tabela": PESO_TABELA,
        "peso_forma": PESO_FORMA,
        "peso_forca": PESO_FORCA
    }

    with open("pesos.json", "w") as f:
        json.dump(pesos, f, indent=4)

    salvar_no_github("pesos.json")

def atualizar_pesos():

    global PESO_XG
    global PESO_CHUTES
    global PESO_EFICIENCIA
    global PESO_TABELA
    global PESO_FORMA
    global PESO_FORCA

    df = pd.read_csv(
        "resultados_apostas.csv"
    )

    ultimos = df.tail(10)

    greens = len(
        ultimos[
            ultimos["Resultado"] == "GREEN"
        ]
    )

    reds = len(
        ultimos[
            ultimos["Resultado"] == "RED"
        ]
    )

    saldo = greens - reds

    ajuste = saldo * 0.01

    PESO_XG += ajuste
    PESO_CHUTES += ajuste
    PESO_EFICIENCIA += ajuste

    PESO_TABELA -= ajuste / 2
    PESO_FORMA += ajuste / 2
    PESO_FORCA += ajuste / 2

    salvar_pesos()

def verificar_rodada():

    df = pd.read_csv(
    "resultados_apostas.csv"
    )

    jogos = len(
        df[
            df["Resultado"].isin(
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

odd_under25 = st.number_input(
    "Odd Under 2.5",
    min_value=1.0,
    step=0.01
)

odd_over35 = st.number_input(
    "Odd Over 3.5",
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
# IDENTIFICAÇÃO DO JOGO
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
    # TOP PLACARES
    # =========================

    st.subheader("Placares Mais Prováveis")

    placares = []

    for gols_casa in range(4):

        for gols_fora in range(4):

            prob_placar = (
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

            placares.append(
                (
                    f"{gols_casa} x {gols_fora}",
                    prob_placar
                )
            )

    placares.sort(
        key=lambda x: x[1],
        reverse=True
    )

    top_placares = placares[:5]

    for placar, probabilidade in top_placares:

        st.write(
            f"{placar} = "
            f"{round(probabilidade * 100, 2)}%"
        )
     # =========================
# OVER/UNDER 2.5
# =========================

    total_gols_esperados = (
        gols_esperados_casa +
        gols_esperados_fora
    )

    # =========================
    # AJUSTE DA LIGA
    # =========================

    ajuste_liga_gols = (
        media_gols_liga / 2.50
    )

    total_gols_esperados *= (
        ajuste_liga_gols
    )

    prob_under25 = 0

    for gols in range(3):

        prob_under25 += poisson(
            total_gols_esperados,
            gols
        )

    prob_over25 = 1 - prob_under25

    st.subheader("Over/Under 2.5")

    st.write(
        f"Over 2.5: "
        f"{round(prob_over25 * 100, 2)}%"
    )

    st.write(
        f"Under 2.5: "
        f"{round(prob_under25 * 100, 2)}%"
    )   
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

    prob_casa_0 = poisson(
        gols_esperados_casa,
        0
    )

    prob_fora_0 = poisson(
        gols_esperados_fora,
        0
    )

    prob_btts_nao = (
        prob_casa_0 +
        prob_fora_0 -
        (prob_casa_0 * prob_fora_0)
    )

    prob_btts_sim = (

        (1 - prob_btts_nao)

        * media_btts_liga

        / 0.50
    )

    prob_btts_sim = min(
        prob_btts_sim,
        0.95
    )

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
    # MELHOR MERCADO
    # =========================

    st.subheader("Melhor Mercado")

    melhor_mercado = "Sem valor claro"

    mercados = {

        "🔥 Vitória Casa": edge_casa,
        "🤝 Empate": edge_empate,
        "🔥 Vitória Fora": edge_fora,

        "⚽ Over 2.5": edge_over25,
        "🛡️ Under 2.5": edge_under25,

        "🔥 BTTS SIM": edge_btts_sim,
        "❌ BTTS NÃO": edge_btts_nao
    }

    melhor_mercado = max(
        mercados,
        key=mercados.get
    )

    melhor_edge_mercado = mercados[
        melhor_mercado
    ]

    if melhor_edge_mercado > 0:

        st.success(
            f"Melhor Mercado: {melhor_mercado}"
        )

        st.write(
            f"Edge: "
            f"{round(melhor_edge_mercado * 100, 2)}%"
        )

    else:

        st.error(
            "Sem mercado de valor"
        )
        dados = {
    "data": data_jogo,
    "time_casa": time_casa,
    "time_fora": time_fora,

    "xg_casa": xg_casa,
    "xg_fora": xg_fora,

    "xga_casa": xga_casa,
    "xga_fora": xga_fora,

    "forma_casa": forma_casa,
    "forma_fora": forma_fora,

    "eficiencia_casa": eficiencia_casa,
    "eficiencia_fora": eficiencia_fora,

    "chutes_casa": chutes_casa,
    "chutes_fora": chutes_fora,

    "posicao_casa": posicao_casa,
    "posicao_fora": posicao_fora,

    "mercado": melhor_mercado,

    "odd": odd_escolhida,

    "ev": melhor_ev,

    "edge": melhor_edge,

    "confianca": confianca,

    "resultado": ""
}
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
    # TOP APOSTA
    # =========================

    st.subheader("Top Aposta do Jogo")

    mercados = {

        "Vitória Casa": edge_casa,
        "Empate": edge_empate,
        "Vitória Fora": edge_fora,

        "Over 2.5": edge_over25,
        "Under 2.5": edge_under25,

        "BTTS SIM": edge_btts_sim,
        "BTTS NÃO": edge_btts_nao
    }

    melhor_mercado = max(
        mercados,
        key=mercados.get
    )

    melhor_edge_final = mercados[
        melhor_mercado
    ]

    if melhor_edge_final > 0:

        st.success(
            f"🔥 Melhor Aposta: "
            f"{melhor_mercado}"
        )

        st.write(
            f"Edge: "
            f"{round(melhor_edge_final * 100, 2)}%"
        )

    else:

        st.error(
            "❌ Nenhuma aposta de valor encontrada"
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
    dados_aposta = {
        "ID": novo_id,

        "Time Casa": time_casa,

        "Time Fora": time_fora,

        "Campeonato": campeonato,

        "Mercado": st.session_state.get(
            "melhor_mercado",
            "N/A"
        ),

        "Odd Casa": odd_casa,

        "Odd Empate": odd_empate,

        "Odd Fora": odd_fora,

        "EV Casa": round(
            st.session_state.get(
                "ev_casa",
                0
            ),
            2
        ),

        "EV Empate": round(
            st.session_state.get(
                "ev_empate",
                0
            ),
            2
        ),

        "EV Fora": round(
            st.session_state.get(
                "ev_fora",
                0
            ),
            2
        ),

        "Edge Casa": round(
            st.session_state.get(
                "edge_casa",
                0
            ),
            4
        ),

        "Edge Empate": round(
            st.session_state.get(
                "edge_empate",
                0
            ),
            4
        ),

        "Edge Fora": round(
            st.session_state.get(
                "edge_fora",
                0
            ),
            4
        ),

        "Stake": st.session_state.get(
            "stake",
            0
        ),

        "Confiança": st.session_state.get(
            "confianca",
            0
        ),

        "Perfil": st.session_state.get(
            "perfil_jogo",
            "N/A"
        )
        
    "xg_casa": xg_casa,
    "xg_fora": xg_fora,

    "xga_casa": xga_casa,
    "xga_fora": xga_fora,

    "forma_casa": forma_casa,
    "forma_fora": forma_fora,

    "eficiencia_casa": eficiencia_casa,
    "eficiencia_fora": eficiencia_fora,

    "chutes_casa": chutes_casa,
    "chutes_fora": chutes_fora,

    "posicao_casa": posicao_casa,
    "posicao_fora": posicao_fora,
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

if os.path.exists(ARQUIVO_HISTORICO):

    try:

        historico_resultados = pd.read_csv(
            ARQUIVO_HISTORICO
        )

    except:

        historico_resultados = pd.DataFrame()

else:

    historico_resultados = pd.DataFrame()

# =========================
# SELECIONAR APOSTA
# =========================
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
# SALVAR RESULTADO
# =========================

if st.button("Salvar Resultado"):

    lucro = 0

    if resultado_aposta == "GREEN":

        lucro = (
            valor_stake * odd_aposta
        ) - valor_stake

    elif resultado_aposta == "RED":

        lucro = -valor_stake

    else:

        lucro = 0

    # =========================
    # PEGAR DADOS DA APOSTA SELECIONADA
    # =========================

    time_casa_resultado = aposta_selecionada.iloc[0]["Time Casa"]

    time_fora_resultado = aposta_selecionada.iloc[0]["Time Fora"]

    campeonato_resultado = aposta_selecionada.iloc[0]["Campeonato"]

    mercado_resultado = aposta_selecionada.iloc[0]["Mercado"]

    # =========================
    # DADOS RESULTADO
    # =========================

    dados_resultado = {

        "Time Casa": time_casa_resultado,

        "Time Fora": time_fora_resultado,

        "Campeonato": campeonato_resultado,

        "Mercado": mercado_resultado,

        "Resultado": resultado_aposta,

        "Stake R$": valor_stake,

        "Odd": odd_aposta,

        "Lucro": round(lucro, 2)
    }

    arquivo_resultados = "resultados_apostas.csv"

    df_novo = pd.DataFrame(
        [dados_resultado]
    )

    if os.path.exists(
        arquivo_resultados
    ):

        try:

            df_antigo = pd.read_csv(
                arquivo_resultados
            )

        except:

            df_antigo = pd.DataFrame()

        df_final = pd.concat(
            [
                df_antigo,
                df_novo
            ],
            ignore_index=True
        )

    else:

        df_final = df_novo

    df_final.to_csv(
        arquivo_resultados,
        index=False
    )

    salvar_no_github(
        arquivo_resultados
    )
    verificar_rodada()

    st.success(
        "✅ Resultado salvo"
    )

# =========================
# ESTATÍSTICAS DO BOT
# =========================

arquivo_resultados = "resultados_apostas.csv"

if os.path.exists(arquivo_resultados):

    try:

        df_stats = pd.read_csv(
            arquivo_resultados
        )

    except:

        df_stats = pd.DataFrame()

else:

    df_stats = pd.DataFrame()

# =========================
# PAINEL
# =========================

st.subheader("Performance do Bot")

st.write("PAINEL CARREGADO")

if not df_stats.empty:

    total_apostas = len(df_stats)

    greens = len(
        df_stats[
            df_stats["Resultado"] == "GREEN"
        ]
    )

    reds = len(
        df_stats[
            df_stats["Resultado"] == "RED"
        ]
    )

    voids = len(
        df_stats[
            df_stats["Resultado"] == "VOID"
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
        f"🟢 Greens: {greens}"
    )

    st.write(
        f"🔴 Reds: {reds}"
    )

    st.write(
        f"⚪ Voids: {voids}"
    )

    st.write(
        f"🎯 Winrate: {round(winrate, 2)}%"
    )

    st.write(
        f"💰 Lucro Total: R$ {round(lucro_total, 2)}"
    )

    st.write(
        f"📈 ROI: {round(roi, 2)}%"
    )

else:

    st.warning(
        "Nenhum resultado salvo ainda."
    )
