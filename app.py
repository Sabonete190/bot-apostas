import streamlit as st
import math
import pandas as pd
import os
import requests
import base64
import json
from datetime import datetime

com open("pesos.json", "r") as f:
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

def calcular_kelly(probabilidade, ímpar):

    se ímpar <= 1:
        retornar 0

    b = ímpar - 1

    Kelly = (
        (probabilidade * b)
        - (1 -?)
    ) / b

    retornar max(kelly, 0)
#CONFIGURAÇAO DA PÁ GINA
st.set_page_config(
    título_da_página="Bot de Apostas",
    layout="centralizado"
)

# =========================
# ESTADO DA SESSÃO
# =========================

se "melhor_mercado" não estiver em st.session_state:

    st.session_state["melhor_mercado"] = "N/A"

# TÃ TULO
st.title("ðŸ“Š Bot de Apostas Profissionais")

st.write("Preencha os dados da partida.")
# =========================
# HISTÓRICO CSV
# =========================

ARQUIVO_HISTÓRICO = "historico_apostas.csv"
ARQUIVO_RESULTADOS = "resultados_apostas.csv"

# =========================
#ESQUEMA DE COLUNAS (CONTEXTO COMPLETO DA APOSTA)
# =========================
# Conjunto único de campos de contexto, usado tanto no histórico
# quanto no registro de resultados, na ordem definida pelo usuário.

CONTEXTO_COLUNAS = [
    "Dados",
    "Campeonato",
    "Time Casa",
    "Tempo Fora",
    "Mercado",
    "Resultado Mercado",
    "Probabilidade Modelo",
    "Mercado Ímpar",
    "Odd Justa",
    "EV",
    "Borda",
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
# selectbox de "Selecione a aposta", então "ID" é desligado como a
# Única coluna extra além do contexto pedido.
COLUNAS_HISTÓRICO = ["ID"] + COLUNAS_CONTEXTO

# resultados_apostas.csv precisa de Stake/Lucro para o painel de
# performance (winrate, ROI) e para o cálculo de banco, então essas
# duas colunas são mantidas além do contexto pedido.
COLUNAS_RESULTADOS = COLUNAS_CONTEXTO + ["Stake R$", "Lucro"]

# =========================
# CARREGAMENTO TOLERANTE A ESQUEMA ANTIGO
# =========================
# CSVs salvos antes da migração de colunas (ex.: com "Resultado" em
# vez de "Resultado Mercado", ou sem "Placar Final") não tem como
#colunas novas. Esta função sempre devolve um DataFrame com todos
# as colunas interessantes presentes, para nenhuma leitura/filtro do
# tipo df["Resultado Mercado"] quebra com KeyError.

MAPA_COLUNAS_LEGADAS = {
    "Resultado": "Resultado Mercado",
    "Estranho": "Mercado Estranho",
}


def carregar_csv_com_esquema(caminho, colunas_esperadas, mapa_legado=Nenhum):

    se não os.path.exists(caminho):
        retornar pd.DataFrame(colunas=colunas_esperadas)

    tentar:
        df = pd.read_csv(caminho)
    exceto Exceção:
        retornar pd.DataFrame(colunas=colunas_esperadas)

    se mapa_legado:
        para coluna_antiga, coluna_nova em mapa_legado.items():
            se coluna_antiga estiver em df.columns e coluna_nova não estiver em df.columns:
                df = df.rename(colunas={coluna_antiga: coluna_nova})

    # Garante que toda coluna esperada existe. NaN (em vez de "")
    # para não quebrar .mean()/agregações nas colunas numéricas;
    # comparações como df["Resultado Mercado"] == "GREEN" continua
    # funcionando normalmente (dÃ£o False, nÃ£o erro).
    para coluna em colunas_esperadas:
        se a coluna não estiver em df.columns:
            df[coluna] = pd.NA

    retornar df

# =========================
# GITHUB
# =========================

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_USER = st.secrets["GITHUB_USER"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]

def salvar_no_github(nome_arquivo):

    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{nome_arquivo}"

    cabeçalhos = {
        "Autorização": f"token {GITHUB_TOKEN}"
    }

    com open(nome_arquivo, "rb") como arquivo:
        conteúdo = base64.b64encode(arquivo.read()).decode()

    resposta = requests.get(url, headers=headers)

    sha = Nenhum

    Se response.status_code == 200:
        sha = response.json()["sha"]

    dados = {
        "message": f"Atualizando {nome_arquivo}",
        "conteúdo": conteúdo,
        "ramo": "principal"
    }

    se sha:
        dados["sha"] = sha

    solicitações.put(
        URL,
        cabeçalhos=cabeçalhos,
        json=dados
    )

def salvar_aposta(dados):

    df_novo = pd.DataFrame([dados])

    se os.path.exists(ARQUIVO_HISTORICO):

        tentar:

            df_antigo = pd.read_csv(
                ARQUIVO_HISTÓRICO
            )

        exceto:

            df_antigo = pd.DataFrame()

        df_final = pd.concat(
            [df_antigo, df_novo],
            ignore_index=True
        )

    outro:

        df_final = df_novo

    # Garantir a ordem e o conjunto exato de colunas do esquema,
    # mesmo que o CSV antigo tenha colunas diferentes.
    df_final = df_final.reindex(
        colunas=COLUNAS_HISTÓRICAS
    )

    df_final.to_csv(
        ARQUIVO_HISTÓRICO,
        índice=Falso
    )


def salvar_resultado(dados):

    df_novo = pd.DataFrame([dados])

    se os.path.exists(ARQUIVO_RESULTADOS):

        tentar:

            df_antigo = pd.read_csv(
                ARQUIVO_RESULTADOS
            )

        exceto:

            df_antigo = pd.DataFrame()

        df_final = pd.concat(
            [df_antigo, df_novo],
            ignore_index=True
        )

    outro:

        df_final = df_novo

    df_final = df_final.reindex(
        colunas=COLUNAS_RESULTADOS
    )

    df_final.to_csv(
        ARQUIVO_RESULTADOS,
        índice=Falso
    )
def salvar_pesos():

    # Mantéma estrutura aninhada original do pesos.json
    # (1x2 / acima de 25 / abaixo de 25 / btts). Só o bloco "1x2" é
    # atualizado, pois é o único ajustado por atualizar_pesos().
    pesos_atualizados = {
        "1x2": {
            "peso_xg": PESO_XG,
            "peso_chutes": PESO_CHUTES,
            "peso_eficiencia": PESO_EFICIENCIA,
            "peso_tabela": PESO_TABELA,
            "peso_forma": PESO_FORMA,
            "peso_forca": PESO_FORCA
        },
        "acima de 25 anos": pesos_acima de 25 anos,
        "menores de 25 anos": pesos_menores_de_25_anos
        "btts": pesos_btts
    }

    com open("pesos.json", "w") as f:
        json.dump(pesos_atualizados, f, indent=4)

    salvar_no_github("pesos.json")

def atualizar_pesos():

    global PESO_XG, PESO_CHUTES, PESO_EFICIENCIA, PESO_TABELA, PESO_FORMA

    df = carregar_csv_com_esquema(
        ARQUIVO_RESULTADOS,
        COLUNAS_RESULTADOS,
        mapa_legado=MAPA_COLUNAS_LEGADAS
    )

    se df.vazio:
        retornar

    se não os.path.exists(ARQUIVO_HISTORICO):
        retornar

    # resultados_apostas.csv agora já traz o contexto completo (xG,
    # chutes, forma etc.), então não é mais necessário fazer merge
    # com o historico_apostas.csv para obter essas estatísticas.
    # carregar_csv_com_esquema já garante que todas as colunas do
    # esquema existe (mesmo que vazios), então não é preciso
    # verifique a coluna aqui.

    ultimos = df.tail(10)

    # Separa por mercado
    mercados = {
        "1x2": ["Vitória Casa", "Empate", "Vitória Fora"],
        "mais de 25": ["Mais de 2,5"],
        "menos de 25": ["Menos de 2,5"],
        "btts": ["BTTS SIM", "BTTS NÃƒO"]
    }

    para nome_mercado, nomes em mercados.items():

        resultados_mercado = últimos[
            ultimos["Mercado"].isin(nomes)
        ]

        se resultados_mercado.vazio:
            continuar

        verdes = len(
            resultados_mercado[
                resultados_mercado["Resultado Mercado"] == "VERDE"
            ]
        )

        vermelhos = len(
            resultados_mercado[
                resultados_mercado["Resultado Mercado"] == "VERMELHO"
            ]
        )

        saldo = verdes - vermelhos

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
        se não pd.isna(media_xg):
            PESO_XG += ajuste * media_xg * 0,10
            PESO_XG = máx(0,10, mín(PESO_XG, 3))

        se não pd.isna(media_chutes):
            PESO_CHUTES += ajuste * media_chutes * 0,05
            PESO_CHUTES = máx(0,10, min(PESO_CHUTES, 3))

        se não pd.isna(media_eficiencia):
            PESO_EFICIENCIA += ajuste * media_eficiencia * 0,10
            PESO_EFICIENCIA = máx(0,10, min(PESO_EFICIENCIA, 3))

        se não pd.isna(media_forma):
            PESO_FORMA += ajuste * media_forma * 0,20
            PESO_FORMA = máx(0,10, mín(PESO_FORMA, 3))

    salvar_pesos()
def verificar_rodada():

    df = carregar_csv_com_esquema(
        ARQUIVO_RESULTADOS,
        COLUNAS_RESULTADOS,
        mapa_legado=MAPA_COLUNAS_LEGADAS
    )

    se df.vazio:
        retornar

    jogos = len(
        df[
            df["Resultado Mercado"].isin(
              ["VERDE", "VERMELHO"]
            )
        ]
    )

    se jogos % 10 == 0:
        atualizar_pesos()
        
# =========================
# ODDS 1X2
# =========================

st.subheader("Mercado 1X2")

odd_casa = st.number_input(
    "Casa Estranha",
    valor_mínimo=1,0,
    passo=0,01
)

ímpar_empate = st.number_input(
    "Empate Ímpar",
    valor_mínimo=1,0,
    passo=0,01
)

odd_fora = st.number_input(
    "Fora Ímpar",
    valor_mínimo=1,0,
    passo=0,01
)

# =========================
# ACIMA / ABAIXO
# =========================

st.subheader("Acima/Abaixo")

ímpar_acima_de_15 = st.número_entrada(
    "Ímpar acima de 1,5",
    valor_mínimo=1,0,
    passo=0,01
)

ímpar_acima_de_25 = st.número_entrada(
    "Ímpar acima de 2,5",
    valor_mínimo=1,0,
    passo=0,01
)

ímpar_acima_de_35 = st.número_entrada(
    "Ímpar acima de 3,5",
    valor_mínimo=1,0,
    passo=0,01
)

odd_under25 = st.number_input(
    "Ímpar Menos de 2,5",
    valor_mínimo=1,0,
    passo=0,01
)

odd_under35 = st.number_input(
    "Ímpar abaixo de 3,5",
    valor_mínimo=1,0,
    passo=0,01
)


# =========================
# BTTS
# =========================

st.subheader("BTTS")

odd_btts_sim = st.number_input(
    "SIM BTTS ímpar",
    valor_mínimo=1,0,
    passo=0,01
)

odd_btts_nao = st.number_input(
    "Odd BTTS NÃƒO",
    valor_mínimo=1,0,
    passo=0,01
)


# =========================
# GOLS POR EQUIPE
# =========================

st.subheader("Gols por Equipe")

odd_casa_marca_1 = st.number_input(
    "Odd Casa marca 1+ gol",
    valor_mínimo=1,0,
    passo=0,01
)

odd_fora_marca_1 = st.number_input(
    "Odd Fora marca 1+ gol",
    valor_mínimo=1,0,
    passo=0,01
)

odd_casa_marca_2 = st.number_input(
    "Casa marca 2+ gols",
    valor_mínimo=1,0,
    passo=0,01
)

odd_fora_marca_2 = st.number_input(
    "Odd Fora marca 2+ gols",
    valor_mínimo=1,0,
    passo=0,01
)

odd_casa_over05 = st.number_input(
    "Casa Ímpar Acima de 0,5",
    valor_mínimo=1,0,
    passo=0,01
)

odd_casa_over15 = st.number_input(
    "Casa Ímpar Acima de 1,5",
    valor_mínimo=1,0,
    passo=0,01
)

odd_casa_over25 = st.number_input(
    "Casa Ímpar Acima de 2,5",
    valor_mínimo=1,0,
    passo=0,01
)

odd_fora_over05 = st.number_input(
    "Ímpar Fora Acima de 0,5",
    valor_mínimo=1,0,
    passo=0,01
)

odd_fora_over15 = st.number_input(
    "Odd Fora Acima de 1.5",
    valor_mínimo=1,0,
    passo=0,01
)

odd_fora_over25 = st.number_input(
    "Odd Fora Mais de 2,5",
    valor_mínimo=1,0,
    passo=0,01
)


# =========================
# DUPLA CHANCE
# =========================

st.subheader("Dupla Chance")

odd_dupla_1x = st.number_input(
    "Odd Dupla Chance 1X",
    valor_mínimo=1,0,
    passo=0,01
)

odd_dupla_x2 = st.number_input(
    "Odd Dupla Chance X2",
    valor_mínimo=1,0,
    passo=0,01
)

odd_dupla_12 = st.number_input(
    "Odd Dupla Chance 12",
    valor_mínimo=1,0,
    passo=0,01
)


# =========================
# EMPATE ANULA APOSTA - DNB
# =========================

st.subheader("Empate Anula a Aposta - DNB")

odd_dnb_casa = st.number_input(
    "Casa DNB ímpar",
    valor_mínimo=1,0,
    passo=0,01
)

odd_dnb_fora = st.number_input(
    "Odd DNB Fora",
    valor_mínimo=1,0,
    passo=0,01
)


# =========================
# MERCADOS COMBINADOS
# =========================

st.subheader("Mercados Combinados")

horário_ímpar_marca_primeiro = st.número_input(
    "Odd Time marca primeiro",
    valor_mínimo=1,0,
    passo=0,01
)

odd_casa_vence_over15 = st.number_input(
    "Odd Casa vence + Mais de 1.5",
    valor_mínimo=1,0,
    passo=0,01
)

odd_fora_vence_over15 = st.number_input(
    "Ímpar Fora vence + Mais de 1,5",
    valor_mínimo=1,0,
    passo=0,01
)

odd_btts_over25 = st.number_input(
    "Ímpar BTTS + Mais de 2,5",
    valor_mínimo=1,0,
    passo=0,01
)

odd_btts_over35 = st.number_input(
    "Ímpar BTTS + Mais de 3,5",
    valor_mínimo=1,0,
    passo=0,01
)


# =========================
# POSIÇÃO NA TABELA
# =========================

st.subheader("Tabela Brasileirão")

posicao_casa = st.number_input(
    "Posição Time Casa",
    valor_mínimo=1,
    valor_máximo=20,
    valor=10
)

posicao_fora = st.number_input(
    "Posição Time Fora",
    valor_mínimo=1,
    valor_máximo=20,
    valor=10
)
# =========================
# DADOS DOS TIMES
# =========================

st.subheader("Dados dos Tempos")

xg_casa = st.number_input(
    "xG Casa",
    valor_mínimo=0,0,
    passo=0,1
)

xg_fora = st.number_input(
    "xG Fora",
    valor_mínimo=0,0,
    passo=0,1
)

xga_casa = st.number_input(
    "xGA Casa",
    valor_mínimo=0,0,
    passo=0,1
)

xga_fora = st.number_input(
    "xGA Fora",
    valor_mínimo=0,0,
    passo=0,1
)

sofridos_casa = st.number_input(
    "Gols Sofridos Casa",
    valor_mínimo=0,0,
    passo=0,1
)

sofridos_fora = st.number_input(
    "Gols Sofridos Fora",
    valor_mínimo=0,0,
    passo=0,1
)

chutes_casa = st.number_input(
    "Chutes no Gol Casa",
    valor_mínimo=0,0,
    passo=0,1
)

chutes_fora = st.number_input(
    "Chutes no Gol Fora",
    valor_mínimo=0,0,
    passo=0,1
)

eficiência_casa = st.número_input(
    "Eficiência Casa",
    valor_mínimo=0,0,
    passo=0,1
)

eficiência_fora = st.number_input(
    "Eficiência Fora",
    valor_mínimo=0,0,
    passo=0,1
)
# =========================
# FORMA RECENTE
# =========================

st.subheader("Forma Recente")

forma_casa = st.number_input(
    "Forma Casa (últimos 5 jogos)",
    valor_mínimo=0,
    valor_máximo=15,
    passo=1
)

forma_fora = st.number_input(
    "Forma Fora (últimos 5 jogos)",
    valor_mínimo=0,
    valor_máximo=15,
    passo=1
)

# =========================
# FORÃ‡A AUTOMÃ TICA
# =========================

def honior_forca(ímpar):

    se ímpar <= 1,70:
        retorno 1,35, "Muito Forte"

    elif odd <= 2.10:
        retornar 1,20, "Forte"

    senão se ímpar <= 2,80:
        retornar 1.00, "Médio"

    senão se ímpar <= 4,00:
        retorno 0,80, "Fraco"

    outro:
        retorno 0,65, "Muito Fraco"

força_casa_valor, nivel_casa = calcular_forca(
    casa_estranha
)

força_fora_valor, nivel_fora = calcular_forca(
    ímpar_fora
)

st.subheader("Força Automática")

st.escrever(
    f"Força Casa: {nivel_casa}"
)

st.escrever(
    f"Força Fora: {nivel_fora}"
)
# =========================
# IDENTIFICAÇÃO DO JOGO
# =========================

tempo_casa = st.text_input(
    "Time Casa"
)

time_fora = st.text_input(
    "Tempo Fora"
)

campeonato = st.text_input(
    "Campeonato"
)

# =========================
# DADOS DO BRASILEIRÃO
# =========================

media_gols_liga = 2,63

media_btts_liga = 0,57

media_over35_liga = 0,49

media_mandante_liga = 0,47

media_visitante_liga = 0,24

media_empate_liga = 0,29

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

    eficiência_casa * PESO_EFICIENCIA +

    forca_tabela_casa * PESO_TABELA +

    (forma_casa/15) *PESO_FORMA +

    força_casa_valor * PESO_FORCA

    )

    ataque_fora = (

    xg_fora * PESO_XG +

    paraquedas_fora * PESO_CHUTES +

    eficiência_fora * PESO_EFICIENCIA +

    forca_tabela_fora * PESO_TABELA +

    (forma_fora / 15) * PESO_FORMA +

    força_fora_valor * PESO_FORCA

    )

    # =========================
    # FORÃ‡A DEFENSIVA
    # =========================

    defesa_casa = (
        xga_casa * 0.6 +
        s_casa * 0,4
    )

    (
        xga_fora * 0.6 +
        s_fora * 0,4
    )

    # =========================
    # FORÃ‡A DE GOL
    # =========================

    forca_gol = (
        (ataque_casa / (defesa_fora + 0.5)) +
        (ataque_fora / (defesa_casa + 0,5))
    ) / 2

    st.subheader("Análise Estatística")

    st.write(f"Ataque Casa: {round(ataque_casa, 2)}")
    st.write(f"Ataque Fora: {round(ataque_fora, 2)}")

    st.write(f"Defesa Casa: {round(defesa_casa, 2)}")
    st.write(f"Defesa Fora: {round(defesa_fora, 2)}")

    st.write(f"Força de Gol: {round(força_gol, 2)}")
    # =========================
    # GOLS ESPERADOS
    # =========================

    gols_esperados_casa = (
        ataque_casa / (defesa_fora + 0,5)
    )

    gols_esperados_fora = (
        ataque_fora / (defesa_casa + 0,5)
    )

    st.subheader("Gols Esperados")

    st.escrever(
        f"Gols Esperados Casa: {round(gols_esperados_casa, 2)}"
    )

    st.escrever(
        f"Gols Esperados Fora: {round(gols_esperados_fora, 2)}"
    )

    # Guardados aqui porque o botão "Salvar Aposta" roda num rerun
    # separado do Streamlit, onde as variáveis ​​locais deste bloco
    # ("Analisar Jogo") não existem mais.
    st.session_state["gols_esperados_casa"] = gols_esperados_casa
    st.session_state["gols_esperados_fora"] = gols_esperados_fora

    # =========================
    # VENENO
    # =========================

    def poisson(gols_esperados, gols):
        retornar (
            (math.exp(-gols_esperados) *
            gols_esperados ** gols)
            / math.factorial(gols)
        )

    st.subheader("Poisson")

    para i em range(4):

        prob_casa_gols = poisson(
            gols_esperados_casa,
            eu
        )

        prob_fora_gols = poisson(
            gols_esperados_fora,
            eu
        )

        st.escrever(
            f"Casa marcar {i} gols: "
            f"{rodada(prob_casa_gols * 100, 2)}%"
        )

        st.escrever(
            f"Fora marcar {i} gols: "
            f"{rodada(prob_fora_gols * 100, 2)}%"
        )

        st.write("---")
        
    # =========================
    # MATRIZ COMPLETA DE POISSON
    # =========================

    # Limite de gols utilizados na matriz
    MAX_GOLS = 10

    matriz_placares = []

    para gols_casa no intervalo(MAX_GOLS + 1):

        para gols_fora no intervalo(MAX_GOLS + 1):

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
    # MELHORES LUGARES
    # =========================

    st.subheader("Placares Mais Prováveis")

    placas_ordenadas = ordenado(
        matriz_placares,
        key=lambda x: x["probabilidade"],
        reverso=Verdadeiro
    )

    top_placares = placares_ordenados[:5]

    para placa em top_placares:

        st.escrever(
            f'{placar["gols_casa"]} x '
            f'{placar["gols_fora"]} = '
            f'{rodada(placar["probabilidade"] * 100, 2)}%'
        )


    # =========================
    # FUNÃ‡ÃƒO PARA SOMAR
    # PROBABILIDADES DOS PLACARES
    # =========================

    def zo_mercado(
        condicao
    ):

        probabilidade = 0

        para placar em matriz_placares:

            se condicionao(
                placa["gols_casa"],
                placa["gols_fora"]
            ):

                probabilidade += (
                    placa["probabilidade"]
                )

        retornar


    # =========================
    # ACIMA / ABAIXO
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
        casa >= 1 e fora >= 1
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
        modelo_prob_empate
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
        mercado_de_praça(
            lambda casa, fora:
            casa > 0 e casa > fora
        )
        +
        mercado_de_praça(
            lambda casa, fora:
            fora > 0 e fora > casa
        )
    )


    # =========================
    # CASA VENCE + MAIS DE 1,5
    # =========================

    prob_casa_vence_over15 = (
        mercado_de_praça(
            lambda casa, fora:
            casa > fora
            e casa + fora >= 2
        )
    )


    # =========================
    # FORA VENCE + MAIS DE 1,5
    # =========================

    prob_fora_vence_acima_de_15 = (
        mercado_de_praça(
            lambda casa, fora:
            fora > casa
            e casa + fora >= 2
        )
    )


    # =========================
    # Ambas as equipes marcam + Mais de 2,5
    # =========================

    prob_btts_acima de 25 = (
        mercado_de_praça(
            lambda casa, fora:
            casa >= 1
            e fora >= 1
            e casa + fora >= 3
        )
    )


    # =========================
    # Ambas as equipes marcam + Mais de 3,5
    # =========================

    prob_btts_acima_de_35 = (
        mercado_de_praça(
            lambda casa, fora:
            casa >= 1
            e fora >= 1
            e casa + fora >= 4
        )
    )
        # =========================
    # ODDS JUSTAS, EV, EDGE E KELLY
    # NOVOS MERCADOS
    # =========================

    def_odd_justa(probabilidade):

        se <= 0:
            retornar 0

        retornar 1 /


    def calcular_ev(probabilidade, ímpar):

        se ímpar <= 1:
            retornar 0

        retornar (
            probabilidade * ímpar
        ) - 1


    def calcular_edge(probabilidade, ímpar):

        se ímpar <= 1:
            retornar 0

        retornar (
            probabilidade -
            (1 / ímpar)
        )


    defª_kelly_mercado(
        não,
        chance
    ):

        se ímpar <= 1:
            retornar 0

        b = ímpar - 1

        Kelly = (
            (
                co * b
            )
            -
            (
                1 -
            )
        ) / b

        retornar máximo(
            Kelly,
            0
        )
            # =========================
    #RESULTADOS DOS NOVOS MERCADOS
    # ODDS JUSTAS, EV, EDGE E KELLY
    # =========================

    resultados_mercados = {

        # =========================
        # ACIMA / ABAIXO
        # =========================

        "Mais de 1,5": {
            "probabilidade": prob_acima_de_15,
            "ímpar": ímpar_acima_de_15
        },

        "Mais de 2,5": {
            "probabilidade": prob_acima_de_25,
            "ímpar": ímpar_acima_de_25
        },

        "Mais de 3,5": {
            "probabilidade": prob_acima_de_35,
            "ímpar": ímpar_acima_de_35
        },

        "Menos de 2,5": {
            "probabilidade": prob_under25,
            "ímpar": ímpar_menores_de_25
        },

        "Menos de 3,5": {
            "probabilidade": prob_under35,
            "ímpar": ímpar_menores_de_35
        },


        # =========================
        # BTTS
        # =========================

        "BTTS SIM": {
            "probabilidade": prob_btts_sim,
            "ímpar": sim_btts_ímpar
        },

        "BTTS NÃƒO": {
            "probabilidade": prob_btts_nao,
            "ímpar": ímpar_btts_nao
        },


        # =========================
        # GOLS POR EQUIPE
        # =========================

        "Casa marca 1+ gol": {
            "probabilidade": prob_casa_marca_1,
            "ímpar": ímpar_casa_marca_1
        },

        "Fora marca 1+ gol": {
            "probabilidade": prob_fora_marca_1,
            "ímpar": odd_fora_marca_1
        },

        "Casa marca 2+ gols": {
            "probabilidade": prob_casa_marca_2,
            "ímpar": ímpar_casa_marca_2
        },

        "Fora marca 2+ gols": {
            "probabilidade": prob_fora_marca_2,
            "ímpar": odd_fora_marca_2
        },

        "Casa Acima de 0,5": {
            "probabilidade": prob_casa_over05,
            "ímpar": odd_casa_over05
        },

        "Casa Over 1.5": {
            "probabilidade": prob_casa_over15,
            "ímpar": casa_ímpar_acima_de_15
        },

        "Casa Over 2.5": {
            "probabilidade": prob_casa_over25,
            "ímpar": casa_ímpar_acima_de_25
        },

        "Fora Acima de 0,5": {
            "probabilidade": prob_fora_over05,
            "ímpar": ímpar_para_mais_de_05
        },

        "Fora Over 1.5": {
            "probabilidade": prob_fora_over15,
            "ímpar": ímpar_para_mais_de_15
        },

        "Fora Over 2.5": {
            "probabilidade": prob_fora_over25,
            "ímpar": ímpar_para_mais_de_25
        },


        # =========================
        # DUPLA CHANCE
        # =========================

        "Dupla Chance 1X": {
            "probabilidade": prob_dupla_1x,
            "ímpar": ímpar_dupla_1x
        },

        "Dupla Chance X2": {
            "probabilidade": prob_dupla_x2,
            "ímpar": ímpar_dupla_x2
        },

        "Dupla Chance 12": {
            "probabilidade": prob_dupla_12,
            "ímpar": ímpar_dupla_12
        },


        # =========================
        # DNB
        # =========================

        "DNB Casa": {
            "probabilidade": prob_dnb_casa,
            "ímpar": odd_dnb_casa
        },

        "DNB Fora": {
            "probabilidade": prob_dnb_fora,
            "ímpar": ímpar_dnb_fora
        },


        # =========================
        # MERCADOS COMBINADOS
        # =========================

        "Time marca primeiro": {
            "probabilidade": prob_time_marca_primeiro,
            "ímpar": odd_time_marca_primeiro
        },

        "Casa vence + Mais de 1,5": {
            "probabilidade": prob_casa_vence_over15,
            "ímpar": odd_casa_vence_over15
        },

        "Fora vence + Mais de 1.5": {
            "probabilidade": prob_fora_vence_over15,
            "ímpar": ímpar_para_vence_acima_de_15
        },

        "BTTS + Mais de 2,5": {
            "probabilidade": prob_btts_over25,
            "ímpar": ímpar_btts_acima_de_25
        },

        "BTTS + Mais de 3,5": {
            "probabilidade": prob_btts_over35,
            "ímpar": ímpar_btts_acima_de_35
        }
    }
    # =========================
    # RESULTADOS DOS MERCADOS
    # =========================

    resultados_completos = {}

    para mercado, dados em resultados_mercados.items():

        probabilidade = dados["probabilidade"]
        ímpar = dados["ímpar"]

        ímpar_justa = calcular_odd_justa(probabilidade)
        ev = calcular_ev(probabilidade, ímpar)
        borda = calcular_edge(probabilidade, ímpar)
        Kelly = calcular_kelly_mercado(
            não,
            chance
        )

        resultados_completos[mercado] = {

            "probabilidade": probabilidade,
            "ímpar": ímpar,
            "odd_justa": odd_justa,
            "ev": ev,
            "borda": borda,
            "Kelly": Kelly
        }
            # =========================
    # MERCADO MELHOR
    # =========================

    st.subheader("ðŸ † Melhor Mercado")

    melhor_mercado = Nenhum
    melhores_dados = Nenhum

    para nome, dados em resultados_completos.items():

        se (
            melhor_dados é Nenhum
            ou dados["ev"] > melhores_dados["ev"]
        ):

            melhor_mercado = nome
            melhores_dados = dados


    se (
        melhor_dados não é None
        e melhor_dados["ev"] > 0
    ):

        st.sucesso(
            f"ðŸ”¥ Melhor Mercado: {melhor_mercado}"
        )

        st.escrever(
            f"Probabilidade: "
            f"{round(melhor_dados['probabilidade'] * 100, 2)}%"
        )

        st.escrever(
            f"Mercado Ímpar: "
            f"{rodada(melhor_dados['ímpar'], 2)}"
        )

        st.escrever(
            f"Odd ​​Justa: "
            f"{round(melhor_dados['odd_justa'], 2)}"
        )

        st.escrever(
            f"EV: "
            f"{round(melhor_dados['ev'] * 100, 2)}%"
        )

        st.escrever(
            f"Borda: "
            f"{round(melhor_dados['edge'] * 100, 2)}%"
        )

        st.escrever(
            f"Kelly: "
            f"{round(melhor_dados['kelly'] * 100, 2)}%"
        )

        st.session_state["melhor_mercado"] = melhor_mercado

        st.session_state["melhor_probabilidade"] = (
            melhores_dados["probabilidade"]
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

    outro:

        st.erro(
            "Â Nenhum mercado possui valor positivo."
            )


        # =========================
        # EXIBIR RESULTADOS
        # =========================

        st.subheader(
            "Análise Completa dos Mercados"
        )


        para mercado, dados em resultados_completos.items():

            st.escrever(
                f"### {mercado}"
            )

            st.escrever(
                f"Probabilidade Modelo: "
                f"{round(dados['probabilidade'] * 100, 2)}%"
            )

            st.escrever(
                f"Odd ​​Justa: "
                f"{round(dados['odd_justa'], 2)}"
            )

            st.escrever(
                f"Mercado Ímpar: "
                f"{round(dados['odd'], 2)}"
            )

            st.escrever(
                f"EV: "
                f"{round(dados['ev'] * 100, 2)}%"
            )

            st.escrever(
                f"Borda: "
                f"{round(dados['edge'] * 100, 2)}%"
            )

            st.escrever(
                f"Kelly: "
                f"{round(dados['kelly'] * 100, 2)}%"
            )

            st.write("---")

        # =========================
        # ODDS JUSTAMENTE ACIMA/ABAIXO
        # =========================

        odd_justa_over25 = (
            1 / prob_acima_de_25
        )

        odd_justa_under25 = (
            1 / prob_under25
        )

        st.subheader("Odds Justas Over/Under")

        st.escrever(
            f"Ímpar Justa Acima de 2,5: "
            f"{round(odd_justa_over25, 2)}"
        )

        st.escrever(
            f"Ímpar Justa Abaixo de 2,5: "
            f"{round(odd_justa_under25, 2)}"
        )
             # =========================
        # BTTS
        # =========================

        prob_btts_sim = 0

        para gols_casa em range(8):

            para gols_fora em range(8):

                if gols_casa >= 1 e gols_fora >= 1:

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

        st.escrever(
            f"BTTS SIM: "
            f"{round(prob_btts_sim * 100, 2)}%"
        )

        st.escrever(
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

        st.escrever(
            f"Odd ​​Justa BTTS SIM: "
            f"{round(odd_justa_btts_sim, 2)}"
        )

        st.escrever(
            f"Odd ​​Justa BTTS NÃƒO: "
            f"{round(odd_justa_btts_nao, 2)}"
        )
        # =========================
        # EV ACIMA/ABAIXO
        # =========================

        ev_acima de 25 = (
            probabilidade_acima_de_25 * ímpar_acima_de_25
        ) - 1

        ev_under25 = (
            prob_under25 * odd_under25
        ) - 1

        st.subheader("EV Over/Under")

        st.escrever(
            f"EV acima de 2,5: "
            f"{round(ev_over25, 2)}"
        )

        st.escrever(
            f"EV abaixo de 2,5: "
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

        st.escrever(
            f"EV BTTS SIM: "
            f"{round(ev_btts_sim, 2)}"
        )

        st.escrever(
            f"EV BTTS NÃƒO: "
            f"{round(ev_btts_nao, 2)}"
        )
        # =========================
        # EDGE OVER/BTTS
        # =========================

        borda_acima25 = (
            prob_acima_de_25 -
            (1 / ímpar_acima_de_25)
        )

        borda_abaixo_de_25 = (
            prob_under25 -
            (1 / ímpar_abaixo_de_25)
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

        st.escrever(
            f"Borda acima de 2,5: "
            f"{round(edge_over25 * 100, 2)}%"
        )

        st.escrever(
            f"Borda abaixo de 2,5: "
            f"{round(edge_under25 * 100, 2)}%"
        )

        st.escrever(
            f"Edge BTTS SIM: "
            f"{round(edge_btts_sim * 100, 2)}%"
        )

        st.escrever(
            f"Edge BTTS NÃƒO: "
            f"{round(edge_btts_nao * 100, 2)}%"
        )
        # =========================
        # KELLY OVER/BTTS
        # =========================

        kelly_over25 = calcular_kelly(
            prob_acima_de_25,
            ímpar_acima_de_25
        )

        kelly_under25 = calcular_kelly(
            prob_menores_de_25,
            ímpar_menos_de_25
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

        st.escrever(
            f"Kelly Mais de 2,5: "
            f"{round(kelly_over25 * 100, 2)}%"
        )

        st.escrever(
            f"Kelly Menos de 2,5: "
            f"{round(kelly_under25 * 100, 2)}%"
        )

        st.escrever(
            f"Kelly BTTS SIM: "
            f"{round(kelly_btts_sim * 100, 2)}%"
        )

        st.escrever(
            f"Kelly BTTS NÃƒO: "
            f"{round(kelly_btts_nao * 100, 2)}%"
        )
     # =========================
        # PROBABILIDADES PRÓPRIAS
        # =========================

        força_total = ataque_casa + ataque_fora + defesa_casa + defesa_fora

        prob_casa_modelo = (
            ataque_casa + defesa_fora
        ) / total_forca

        prob_fora_modelo = (
            ataque_fora + defesa_casa
        ) / total_forca

        equilíbrio = abs(prob_casa_modelo - prob_fora_modelo)

        prob_empate_modelo = 0,30 - (equilíbrio * 0,2)

        prob_empate_modelo = max(0,10, prob_empate_modelo)

        soma_modelo = (
            prob_casa_modelo +
            prob_fora_modelo +
            modelo_prob_empate
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
            1 / modelo_prob_empate
        )

        odd_justa_fora = (
            1 / prob_fora_modelo
        )

        st.subheader("Odds Justas")

        st.escrever(
            f"Odd ​​Justa Casa: "
            f"{round(odd_justa_casa, 2)}"
        )

        st.escrever(
            f"Odd ​​Justa Empate: "
            f"{rodada(odd_justa_empate, 2)}"
        )

        st.escrever(
            f"Odd ​​Justa Fora: "
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
            prob_casa_modelo * casa_ímpar
        ) - 1

        ev_empate = (
            prob_empate_modelo * ímpar_empate
        ) - 1

        ev_fora = (
            prob_fora_modelo * odd_fora
        ) - 1

        st.subheader("EV do Modelo")

        st.escrever(
            f"EV Casa: {round(ev_casa, 2)}"
        )

        st.escrever(
            f"EV Empate: {round(ev_empate, 2)}"
        )

        st.escrever(
            f"EV Fora: {round(ev_fora, 2)}"
        )
        # =========================
        # BORDA 1X2
        # =========================

        edge_casa = (
            prob_casa_modelo -
            (1 / casa_ímpar)
        )

        borda_empate = (
            prob_empate_modelo -
            (1 / ímpar_empate)
        )

        borda_fora = (
            prob_fora_modelo -
            (1 / ímpar_fora)
        )

        st.subheader("Borda 1X2")

        st.escrever(
            f"Edge Casa: "
            f"{round(edge_casa * 100, 2)}%"
        )

        st.escrever(
            f"Edge Empate: "
            f"{round(edge_empate * 100, 2)}%"
        )

        st.escrever(
            f"Edge Fora: "
            f"{round(edge_fora * 100, 2)}%"
        )
        # =========================
        # BORDA
        # =========================

        edge_casa = (
            prob_casa_modelo - prob_casa
        )

        borda_empate = (
            prob_empate_modelo -prob_empate
        )

        borda_fora = (
            prob_fora_modelo - prob_fora
        )

        st.subheader("Edge do Modelo")

        st.escrever(
            f"Edge Casa: {round(edge_casa * 100, 2)}%"
        )

        st.escrever(
            f"Edge Empate: {round(edge_empate * 100, 2)}%"
        )

        st.escrever(
            f"Aresta Fora: {round(aresta_fora * 100, 2)}%"
        )
        # =========================
        # KELLY CRITERION
        # =========================

        def calcular_kelly(probabilidade, ímpar):

            se ímpar <= 1:
                retornar 0

            Kelly = (
                (
                    ímpar *
                ) - 1
            ) / (ímpar - 1)

            retornar max(kelly, 0)

        kelly_casa = calcular_kelly(
            prob_casa_modelo,
            casa_estranha
        )

        kelly_empate = calcular_kelly(
            prob_empate_modelo,
            ímpar_empate
        )

        kelly_fora = calcular_kelly(
            prob_fora_modelo,
            ímpar_fora
        )

        st.subheader("Critério de Kelly")

        st.escrever(
            f"Kelly Casa: "
            f"{round(kelly_casa * 100, 2)}%"
        )

        st.escrever(
            f"Kelly Empate: "
            f"{round(kelly_empate * 100, 2)}%"
        )

        st.escrever(
            f"Kelly Fora: "
            f"{round(kelly_fora * 100, 2)}%"
        )
        # =========================
        # CONFIANA DO MODELO
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
            (borda_maior * 20)
            +
            (maior_ev * 10)
        )

        confianca = max(
            0,
            min(confianca, 10)
        )

        st.subheader("Confiança do Modelo")

        st.escrever(
            f"Confiança: {round(confianca, 1)}/10"
        )
        # =========================
        # DECISÃO INTELIGENTE
        # =========================

        st.subheader("Decisão do Modelo")

        melhor_borda = max(
            edge_casa,
            borda_empate,
            borda_fora
        )

        melhor_ev = max(
            ev_casa,
            ev_empate,
            ev_fora
        )

        se (
            melhor_edge >= 0,10
            e melhor_ev >= 0,10
            e confianca >= 7
        ):

            st.sucesso(
                "ðŸ”¥ Entrada Forte Detectada"
            )

        elif (
            melhor_edge >= 0,05
            e melhor_ev >= 0,05
            e confianca >= 5
        ):

            aviso de st(
                "âš ï¸ Entrada Moderada"
            )

        outro:

            st.erro(
                "â Œ Jogo Sem Valor"
            )

        # =========================
        # GESTÃO DE ESTEIRA
        # =========================

        st.subheader("Stake Sugerida")

        participação = 0

        se (
            melhor_edge >= 0,10
            e melhor_ev >= 0,10
            e confianca >= 7
        ):

            aposta = 5

        elif (
            melhor_edge >= 0,05
            e melhor_ev >= 0,05
            e confianca >= 5
        ):

            aposta = 2

        outro:

            participação = 0

        st.escrever(
            f"Stake Recomendada: {stake}% da banca"
        )
    # =========================
        # PERFIL DO JOGO
        # =========================

        st.subheader("Perfil da Partida")

        perfil_jogo = "âš–ï¸ Equilibrado"

        total_xg = (
            gols_esperados_casa +
            gols_esperados_fora
        )

        diferença_força = abs(
            ataque_casa - ataque_fora
        )

        # Jogo de mãos

        se (
            total_xg >= 3
            e prob_acima_de_25 >= 0,65
        ):

            perfil_jogo = "ðŸ”¥ Jogo Explosivo"

        # Jogo defensivo

        elif (
            total_xg <= 2
            e prob_under25 >= 0,55
        ):

            perfil_jogo = "ðŸ§± Jogo Defensivo"

        # Favorito forte

        elif (
            diferença_força >= 1
            e confianca >= 7
        ):

            perfil_jogo = "ðŸŽ¯ Favorito Forte"

        # BTTS forte

        elif (
            prob_btts_sim >= 0,65
        ):

            perfil_jogo = "âš”ï¸ Jogo Aberto"

        st.sucesso(
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
        st.session_state["confiana"] = confiável
        st.session_state["perfil_jogo"] = perfil_jogo    
    
# =========================
# SALVAR APOSTA
# =========================

if st.button("Salvar Aposta"):

    se os.path.exists(ARQUIVO_HISTORICO):

        tentar:

            df_ids = pd.read_csv(
                ARQUIVO_HISTÓRICO
            )

            novo_id = len(df_ids) + 1

        exceto:

            novo_id = 1

    outro:

        novo_id = 1

    # =========================
    #RECUPERAR DADOS DA ANÃ LISE
    # =========================

    mercado_salvo = st.session_state.get(
        "melhor_mercado",
        "N / D"
    )

    # =========================
    # DEFINIR ODD DO MERCADO
    # =========================

    probabilidades_mercados = {

        "ðŸ”¥ Vitória Casa": odd_casa,
        "ðŸ¤ Empate": odd_empate,
        "ðŸ”¥ Vitória Fora": odd_fora,

        "✓ Acima de 2,5": odd_over25,
        "ðŸ›¡ï¸ Menos de 2,5": odd_under25,

        "ðŸ”¥ BTTS SIM": odd_btts_sim,
        "â Œ BTTS NÃƒO": odd_btts_nao,

        "Vitória Casa": casa_estranha,
        "Empate": odd_empate,
        "Vitéria Fora": odd_fora,

        "Mais de 2,5": odd_over25,
        "Menos de 2,5": odd_under25,

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
    # COLUNAS_HISTÓRICO / COLUNAS_CONTEXTO)
    # =========================

    dados_aposta = {

        "ID": novo_id,

        "Dados": datetime.now().strftime("%d/%m/%Y"),

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

        "Mercado Ímpar": odd_escolhida,

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

        "Eficiência Casa": eficiência_casa,

        "Eficiência Fora": eficiência_fora,

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
        ARQUIVO_HISTÓRICO
    )

    st.sucesso(
        "âœ… Aposta salva no histórico"
    )

# =========================
# RESULTADO DAS APOSTAS
# =========================

st.subheader("Resultado da Aposta")
# =========================
# CARREGAR HISTÓRICO
# =========================

histórico_resultados = carregar_csv_com_esquema(
    ARQUIVO_HISTÓRICO,
    COLUNAS_HISTÓRICAS,
    mapa_legado=MAPA_COLUNAS_LEGADAS
)

# =========================
# SELECIONAR APOSTA
# =========================

# Garantir que a variável sempre exista, mesmo sem histórico ainda
aposta_selecionada = Nenhum

se (
    não histórico_resultados.empty
    e "ID" em historico_resultados.columns
):

    id_aposta = st.selectbox(
        "Selecione a aposta",
        resultados_históricos["ID"]
    )

outro:

    aviso de st(
        "Nenhuma aposta com ID encontrado."
    )

if "ID" em historico_resultados.columns:

    aposta_selecionada = histórico_resultados[
        histórico_resultados["ID"] == id_aposta
    ]

    mercado_atual = aposta_selecionada.iloc[0]["Mercado"]
    st.info(
    f"Mercado Atual: {mercado_atual}"
)
    st.write("Aposta selecionada:")

    st.escrever(
        aposta_selecionada[
            [
                "Time Casa",
                "Tempo Fora",
                "Mercado"
            ]
        ]
    )

outro:

    aviso de st(
        "Salve uma nova aposta para gerar IDs."
    )
resultado_aposta = st.selectbox(
    "Resultado",
    [
        "VERDE",
        "VERMELHO",
        "VAZIO"
    ]
)

valor_stake = st.number_input(
    "Valor da Stake (R$)",
    valor_mínimo=0,0,
    valor=100,0,
    passo=10,0
)

# =========================
# ÍMPAR DA APOSTA FEITA
# =========================

odd_aposta = st.number_input(
    "Estranho das apostas",
    valor_mínimo=1,01,
    valor=2,00,
    passo=0,01
)

# =========================
# PLACAR FINAL
# =========================

gols_casa_final = st.number_input(
    "Gols Casa (Placar Final)",
    valor_mínimo=0,
    passo=1
)

gols_fora_final = st.number_input(
    "Gols Fora (Placar Final)",
    valor_mínimo=0,
    passo=1
)

# =========================
# SALVAR RESULTADO
# =========================

if st.button("Salvar Resultado"):

    se aposta_selecionada for None ou aposta_selecionada.empty:

        aviso de st(
            "Selecione uma aposta salva antes de registrar o resultado."
        )

    outro:

        lucro = 0

        if resultado_aposta == "VERDE":

            lucro = (
                valor_stake * aposta_ímpar
            ) - valor_stake

        elif resultado_aposta == "VERMELHO":

            lucro = -valor_stake

        outro:

            lucro = 0

        placar_final = f"{gols_casa_final} x {gols_fora_final}"

        # =========================
        # DADOS RESULTADOS
        # (contexto completo herdado da aposta salva no histórico,
        # sobrescrevendo apenas o que muda no momento do resultado:
        # Resultado Mercado, Odd Mercado real, Placar Final)
        # =========================

        aposta_linha = aposta_selecionada.iloc[0]

        dados_resultado = {}

        para coluna em COLUNAS_CONTEXTO:
            dados_resultado[coluna] = aposta_linha.get(coluna, "")

        dados_resultado["Resultado Mercado"] = resultado_aposta

        dados_resultado["Mercado Ímpar"] = ímpar_aposta

        dados_resultado["Placar Final"] = placar_final

        dados_resultado["Stake R$"] = valor_stake

        dados_resultado["Lucro"] = round(lucro, 2)

        salvar_resultado(
            dados_resultado
        )

        salvar_no_github(
            ARQUIVO_RESULTADOS
        )

        tentar:

          df_hist = pd.read_csv(
            ARQUIVO_HISTÓRICO
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
          ] = placa_final

          df_hist.to_csv(
            ARQUIVO_HISTÓRICO,
            índice=Falso
          )

          salvar_no_github(
             ARQUIVO_HISTÓRICO
          )

        exceto Exception como e:

          st.erro(
             f"Erro ao atualizar histórico: {e}"
          )
    
        verificar_rodada()

        st.sucesso(
            "âœ… Resultado salvo"
        )

# =========================
# ESTATÍSTICAS DO BOT
# =========================

df_stats = carregar_csv_com_esquema(
    ARQUIVO_RESULTADOS,
    COLUNAS_RESULTADOS,
    mapa_legado=MAPA_COLUNAS_LEGADAS
)

# =========================
# PAINEL
# =========================

st.subheader("Desempenho do Bot")

st.write("PAINEL CARREGADO")

se df_stats não estiver vazio:

    total_apostas = len(df_stats)

    verdes = len(
        df_stats[
            df_stats["Resultado Mercado"] == "VERDE"
        ]
    )

    vermelhos = len(
        df_stats[
            df_stats["Resultado Mercado"] == "VERMELHO"
        ]
    )

    vazios = len(
        df_stats[
            df_stats["Resultado Mercado"] == "VOID"
        ]
    )

    taxa de vitória = (
        (verdes/total_apostas) * 100
    )

    lucro_total = (
        df_stats["Lucro"].sum()
    )

    total_apostas = (
        df_stats["Stake R$"].sum()
    )

    se total_apostas > 0:

        roi = (
            lucro_total / total_de_apostas
        ) * 100

    outro:

        roi = 0

    st.escrever(
        f"Total de apostas: {total_apostas}"
    )

    st.escrever(
        f"ðŸŸ¢ Verdes: {verdes}"
    )

    st.escrever(
        f"ðŸ”´ Vermelhos: {vermelhos}"
    )

    st.escrever(
        f"âšª Voids: {voids}"
    )

    st.escrever(
        f"ðŸŽ¯ Taxa de vitórias: {round(winrate, 2)}%"
    )

    st.escrever(
        f"ðŸ'° Lucro Total: R$ {round(lucro_total, 2)}"
    )

    st.escrever(
        f"ðŸ“ˆ ROI: {round(roi, 2)}%"
    )

outro:

    aviso de st(
        "Nenhum resultado salvo ainda."
    )
