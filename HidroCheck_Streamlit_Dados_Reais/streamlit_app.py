from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "out"
ASSETS = ROOT / "assets"
BASE_AEREA = ASSETS / "germano_base_aerea.jpg"
BASE_AEREA_BOUNDS = {"xmin": 648700.4479, "ymin": 7760701.2652, "xmax": 667298.2571, "ymax": 7773899.3678}
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qaqc_rede import salvar as rodar_qaqc, carregar_bases  # noqa: E402

# -----------------------------------------------------------------------------
# Configuração da página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Transformando dados em valor | Sistema de rebaixamento",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Identidade visual
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --navy: #0B2A3D;
        --navy-2: #143D52;
        --petrol: #176B72;
        --sky: #EAF3F6;
        --ink: #17212B;
        --muted: #64748B;
        --line: #E2E8F0;
        --surface: #FFFFFF;
        --surface-2: #F8FAFC;
        --ok: #2E7D32;
        --ok-bg: #EFF8F0;
        --warn: #B7791F;
        --warn-bg: #FFF8E7;
        --danger: #B42318;
        --danger-bg: #FFF1F0;
    }

    html, body, [class*="css"] {
        font-family: "Segoe UI", Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background: var(--surface-2);
    }

    .block-container {
        padding-top: 1.15rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    #MainMenu, footer {visibility: hidden;}

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0B2A3D 0%, #123A4E 100%);
        border-right: none;
    }
    section[data-testid="stSidebar"] * {
        color: #F8FAFC;
    }
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #D8E4EA;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,.16);
    }

    /* Botões */
    .stButton > button[kind="primary"] {
        background: var(--petrol);
        border: 1px solid var(--petrol);
        border-radius: 10px;
        font-weight: 700;
        min-height: 44px;
        box-shadow: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: #125B61;
        border-color: #125B61;
    }
    .stDownloadButton > button {
        border-radius: 10px;
        min-height: 42px;
        font-weight: 650;
    }

    /* Hero */
    .hero {
        background: linear-gradient(135deg, #0B2A3D 0%, #15495E 70%, #176B72 100%);
        color: white;
        border-radius: 18px;
        padding: 24px 28px 22px 28px;
        margin-bottom: 18px;
        position: relative;
        overflow: hidden;
    }
    .hero:after {
        content: "";
        position: absolute;
        right: -70px;
        top: -90px;
        width: 250px;
        height: 250px;
        border-radius: 50%;
        border: 1px solid rgba(255,255,255,.13);
        box-shadow: 0 0 0 38px rgba(255,255,255,.04), 0 0 0 80px rgba(255,255,255,.025);
    }
    .eyebrow {
        font-size: .76rem;
        letter-spacing: .12em;
        text-transform: uppercase;
        color: #CFE7EA;
        font-weight: 750;
        margin-bottom: 8px;
    }
    .hero h1 {
        margin: 0;
        color: white;
        font-size: clamp(1.65rem, 2.5vw, 2.45rem);
        line-height: 1.1;
        letter-spacing: -.025em;
    }
    .hero .subtitle {
        margin: 8px 0 0 0;
        color: #E8F1F4;
        font-size: 1rem;
        max-width: 900px;
    }
    .hero .tag {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-top: 14px;
        padding: 6px 10px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,.24);
        background: rgba(255,255,255,.08);
        color: #F4FAFB;
        font-size: .78rem;
        font-weight: 650;
    }

    /* Cards */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 4px 0 18px 0;
    }
    .kpi {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 16px 17px;
        min-height: 112px;
        box-shadow: 0 1px 2px rgba(15,23,42,.035);
    }
    .kpi .label {
        font-size: .76rem;
        text-transform: uppercase;
        letter-spacing: .055em;
        color: var(--muted);
        font-weight: 750;
        margin-bottom: 6px;
    }
    .kpi .value {
        font-size: 2rem;
        font-weight: 780;
        line-height: 1;
        color: var(--ink);
        letter-spacing: -.03em;
    }
    .kpi .detail {
        margin-top: 7px;
        color: var(--muted);
        font-size: .82rem;
    }
    .kpi.ok {border-top: 4px solid var(--ok);}
    .kpi.warn {border-top: 4px solid #E0A321;}
    .kpi.danger {border-top: 4px solid var(--danger);}
    .kpi.info {border-top: 4px solid var(--petrol);}

    /* Sections */
    .section-kicker {
        color: var(--petrol);
        text-transform: uppercase;
        letter-spacing: .09em;
        font-size: .72rem;
        font-weight: 800;
        margin-bottom: 2px;
    }
    .section-title {
        color: var(--ink);
        font-size: 1.3rem;
        font-weight: 760;
        line-height: 1.25;
        margin: 0 0 3px 0;
    }
    .section-sub {
        color: var(--muted);
        font-size: .9rem;
        margin-bottom: 12px;
    }
    .panel {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 16px 17px;
        box-shadow: 0 1px 2px rgba(15,23,42,.025);
    }
    .callout {
        padding: 12px 14px;
        border-radius: 11px;
        background: #F0F7F8;
        border: 1px solid #D6E9EB;
        color: #29434E;
        margin: 8px 0 16px 0;
        font-size: .9rem;
    }
    .callout strong {color: #174F56;}

    .sector-card {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 10px;
    }
    .sector-card .name {font-weight: 760; color: var(--ink); font-size: .95rem;}
    .sector-card .rate {font-size: 1.55rem; font-weight: 780; margin-top: 4px; letter-spacing: -.025em;}
    .sector-card .meaning {font-size: .78rem; font-weight: 750; text-transform: uppercase; letter-spacing: .05em;}
    .negative {color: #B42318;}
    .positive {color: #176B72;}
    .neutral {color: #64748B;}

    .status-pill {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 4px 9px;
        font-size: .75rem;
        font-weight: 750;
    }
    .pill-ok {background: var(--ok-bg); color: var(--ok);}
    .pill-warn {background: var(--warn-bg); color: var(--warn);}
    .pill-danger {background: var(--danger-bg); color: var(--danger);}

    .priority-row {
        background: var(--surface);
        border: 1px solid var(--line);
        border-left: 5px solid var(--danger);
        border-radius: 13px;
        padding: 14px 15px;
        margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(15,23,42,.025);
    }
    .priority-top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 8px;
    }
    .priority-id {display:flex; align-items:baseline; gap:8px; min-width:0;}
    .priority-row .rank {font-weight: 800; color: var(--danger); font-size:.78rem;}
    .priority-row .inst {font-weight: 800; color: var(--ink); font-size:1.03rem; overflow-wrap:anywhere;}
    .priority-meta {color: var(--muted); font-size:.77rem; margin-bottom:7px;}
    .priority-reason {color:#334155; font-size:.83rem; line-height:1.42;}

    .flow {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 8px;
        align-items: stretch;
        margin-top: 10px;
    }
    .flow-step {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 13px 12px;
        min-height: 105px;
        position: relative;
    }
    .flow-step .num {
        width: 24px; height: 24px;
        display: inline-flex; align-items: center; justify-content: center;
        border-radius: 50%;
        background: #E6F2F3;
        color: #155E65;
        font-weight: 800;
        font-size: .76rem;
        margin-bottom: 7px;
    }
    .flow-step b {display:block; color:var(--ink); font-size:.86rem; margin-bottom:3px;}
    .flow-step span {color:var(--muted); font-size:.77rem; line-height:1.35;}

    /* Tabs */
    button[data-baseweb="tab"] {
        font-weight: 700;
    }

    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 12px;
        overflow: hidden;
    }

    @media (max-width: 900px) {
        .kpi-grid {grid-template-columns: repeat(2, minmax(0, 1fr));}
        .flow {grid-template-columns: 1fr;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def b(v) -> bool:
    """Converte colunas heterogêneas para booleano com segurança."""
    if isinstance(v, bool):
        return v
    if pd.isna(v):
        return False
    return str(v).strip().lower() in {"true", "1", "sim", "yes", "y"}


def section(kicker: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="section-kicker">{kicker}</div>'
        f'<div class="section-title">{title}</div>'
        + (f'<div class="section-sub">{subtitle}</div>' if subtitle else ""),
        unsafe_allow_html=True,
    )


def kpi_cards(items: list[tuple[str, str, str, str]]) -> None:
    html = '<div class="kpi-grid">'
    for label, value, detail, cls in items:
        html += (
            f'<div class="kpi {cls}">'
            f'<div class="label">{label}</div>'
            f'<div class="value">{value}</div>'
            f'<div class="detail">{detail}</div>'
            '</div>'
        )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def sector_card(nome: str, taxa: float | None) -> str:
    if taxa is None or pd.isna(taxa):
        return (
            '<div class="sector-card">'
            f'<div class="name">{nome}</div>'
            '<div class="rate neutral">—</div>'
            '<div class="meaning neutral">sem resultado</div>'
            '</div>'
        )
    if taxa < -0.05:
        cls, meaning = "negative", "rebaixamento"
    elif taxa > 0.05:
        cls, meaning = "positive", "recuperação"
    else:
        cls, meaning = "neutral", "estável"
    sinal = "+" if taxa > 0 else ""
    return (
        '<div class="sector-card">'
        f'<div class="name">{nome}</div>'
        f'<div class="rate {cls}">{sinal}{taxa:.2f} <span style="font-size:.85rem;font-weight:650">m/ano</span></div>'
        f'<div class="meaning {cls}">{meaning}</div>'
        '</div>'
    )


def plot_clean(fig: go.Figure, height: int | None = None) -> go.Figure:
    # Cores explícitas para manter os gráficos legíveis mesmo quando o navegador
    # ou o Streamlit estiverem em tema escuro.
    fig.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Segoe UI, Arial", color="#17212B", size=12),
        margin=dict(l=24, r=24, t=28, b=24),
        legend_title_text="",
        legend=dict(font=dict(color="#17212B", size=12), bgcolor="rgba(255,255,255,0.92)"),
    )
    if height:
        fig.update_layout(height=height)
    axis_style = dict(
        showgrid=True,
        gridcolor="#DDE5EC",
        zeroline=False,
        linecolor="#94A3B8",
        tickfont=dict(color="#334155", size=12),
        title_font=dict(color="#334155", size=13),
    )
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)
    return fig


def mapa_saude_interativo(df: pd.DataFrame, key_prefix: str, height: int = 520) -> go.Figure:
    """Mapa QA/QC com filtro de localidade, rótulos e imagem aérea de Germano."""
    base = df.dropna(subset=["x", "y"]).copy()
    localidades = sorted([str(x) for x in base["localidade"].dropna().unique()])

    c_filtro, c_rotulo, c_base = st.columns([1.35, 1, 1.05])
    with c_filtro:
        local = st.selectbox(
            "Localidade",
            ["Todas"] + localidades,
            key=f"{key_prefix}_localidade",
        )
    with c_rotulo:
        modo_rotulo = st.selectbox(
            "Nomes no mapa",
            ["Somente alertas", "Todos", "Nenhum"],
            key=f"{key_prefix}_rotulos",
        )
    with c_base:
        mostrar_base = st.toggle(
            "Imagem aérea de Germano",
            value=False,
            key=f"{key_prefix}_base_aerea",
            disabled=not BASE_AEREA.exists(),
        )

    if local != "Todas":
        base = base[base["localidade"].astype(str) == local].copy()

    if modo_rotulo == "Todos":
        base["rotulo"] = base["instrumento"].astype(str)
    elif modo_rotulo == "Somente alertas":
        base["rotulo"] = base.apply(
            lambda r: str(r["instrumento"]) if r["status_qaqc"] != "OK" else "", axis=1
        )
    else:
        base["rotulo"] = ""

    ordem = ["PRIORITÁRIO", "ATENÇÃO", "OBSERVAR", "OK"]
    cores = {"PRIORITÁRIO": "#C6251E", "ATENÇÃO": "#E09A18", "OBSERVAR": "#5B6B7E", "OK": "#26843A"}
    fig = px.scatter(
        base,
        x="x", y="y", color="status_qaqc", text="rotulo", hover_name="instrumento",
        hover_data={
            "localidade": True, "natureza": True, "recebimento": True,
            "motivos": True, "x": ":.0f", "y": ":.0f", "rotulo": False
        },
        color_discrete_map=cores,
        category_orders={"status_qaqc": ordem},
        labels={"x": "UTM E (m)", "y": "UTM N (m)", "status_qaqc": "QA/QC"},
    )

    if mostrar_base and BASE_AEREA.exists():
        imagem = Image.open(BASE_AEREA)
        b = BASE_AEREA_BOUNDS
        fig.add_layout_image(
            dict(
                source=imagem,
                xref="x", yref="y",
                x=b["xmin"], y=b["ymax"],
                sizex=b["xmax"] - b["xmin"],
                sizey=b["ymax"] - b["ymin"],
                sizing="stretch",
                opacity=0.82,
                layer="below",
                xanchor="left", yanchor="top",
            )
        )

    fig.update_traces(
        marker=dict(size=11, line=dict(width=1.35, color="#FFFFFF"), opacity=0.98),
        textposition="top center",
        textfont=dict(size=10, color="#101820", family="Segoe UI Semibold, Segoe UI, Arial"),
        cliponaxis=False,
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    plot_clean(fig, height)
    if mostrar_base:
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False)
    fig.update_layout(
        hoverlabel=dict(bgcolor="white", font_color="#17212B", font_size=12),
        legend=dict(bgcolor="rgba(255,255,255,0.90)", bordercolor="#CBD5E1", borderwidth=1),
    )
    return fig


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 💧 HidroCheck")
    st.caption("QA/QC + diagnóstico da operação do rebaixamento")
    st.divider()
    st.markdown("**Projeto Aplicativo**")
    st.markdown("Transformando dados em valor")
    st.caption("Resultados da operação do sistema de rebaixamento")
    st.divider()
    st.caption("Escopo atual")
    st.markdown("**Instrumentos ativos de monitoramento hidrogeológico**")
    st.divider()
    st.caption("Fluxo")
    st.markdown("**Cadastro → leituras → QA/QC → tendência → decisão**")

# -----------------------------------------------------------------------------
# Hero
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">Projeto Aplicativo · Hidrogeologia</div>
        <h1>Transformando dados em valor</h1>
        <div class="subtitle"><b>Resultados da operação do sistema de rebaixamento</b> — diagnóstico reprodutível que verifica a saúde da rede antes de interpretar a resposta hidrogeológica.</div>
        <div class="tag">● Todos os instrumentos ativos · QA/QC · Tendências · Priorização</div>
    </div>
    """,
    unsafe_allow_html=True,
)

run_col, note_col = st.columns([1, 3], vertical_alignment="center")
with run_col:
    processar = st.button("↻  Atualizar QA/QC", type="primary", width="stretch")
with note_col:
    st.caption("Reprocessa **HGA-GERAL-06082026.xlsx** + **Coordenadas.xlsx**. Os alertas são uma triagem automática para revisão técnica; não significam defeito confirmado.")

if processar:
    with st.spinner("Analisando todos os instrumentos ativos..."):
        try:
            rodar_qaqc(ROOT / "data", OUT)
            st.cache_data.clear()
            st.success("QA/QC atualizado com sucesso.")
        except Exception as exc:
            st.error(f"Não foi possível processar a base: {exc}")

# -----------------------------------------------------------------------------
# Dados
# -----------------------------------------------------------------------------
qaqc_path = OUT / "qaqc_rede_atual.csv"
eventos_path = OUT / "qaqc_eventos_atual.csv"
taxas_path = ROOT / "taxas.csv"
mapa_path = ASSETS / "mapa_taxa_variacao.png"

if not qaqc_path.exists():
    with st.spinner("Gerando o primeiro QA/QC da rede..."):
        try:
            rodar_qaqc(ROOT / "data", OUT)
        except Exception as exc:
            st.error(f"Falha ao gerar QA/QC: {exc}")
            st.stop()

rede = pd.read_csv(qaqc_path)
for c in ["primeira", "ultima"]:
    rede[c] = pd.to_datetime(rede[c], errors="coerce")
for c in ["repeticao_no_fundo", "zero_auto_persistente"]:
    if c in rede:
        rede[c] = rede[c].map(b)

eventos = pd.read_csv(eventos_path) if eventos_path.exists() else pd.DataFrame()
if not eventos.empty:
    eventos["data"] = pd.to_datetime(eventos["data"], errors="coerce")

fisicos = rede[rede["status_qaqc"] != "NÃO AVALIADO"].copy()
prioritarios = fisicos[fisicos["status_qaqc"] == "PRIORITÁRIO"].copy()
atencao = fisicos[fisicos["status_qaqc"] == "ATENÇÃO"].copy()
observar = fisicos[fisicos["status_qaqc"] == "OBSERVAR"].copy()
ok = fisicos[fisicos["status_qaqc"] == "OK"].copy()
recebendo = fisicos[fisicos["recebimento"] == "RECEBENDO"].copy()

if taxas_path.exists():
    tx = pd.read_csv(taxas_path)
    tx["significativo"] = tx["significativo"].map(b)
    tx["bombeamento"] = tx["bombeamento"].map(b)
    tx_sig = tx[(tx["significativo"]) & (~tx["bombeamento"])].dropna(subset=["x", "y", "taxa"]).copy()
else:
    tx = pd.DataFrame()
    tx_sig = pd.DataFrame()

# KPIs executivos: primeiro a confiabilidade da rede; depois, na aba própria, os resultados do rebaixamento.
n_revisao = len(atencao) + len(observar) + len(prioritarios)
kpi_cards([
    ("Instrumentos avaliados", f"{len(fisicos)}", "rede física ativa no QA/QC", "info"),
    ("Recebendo dados", f"{len(recebendo)}", "cadência compatível com o histórico", "ok"),
    ("Para revisão", f"{n_revisao}", "atenção, observar ou prioridade", "warn"),
    ("Prioridade alta", f"{len(prioritarios)}", "revisão recomendada primeiro", "danger"),
])

aba_visao, aba_qc, aba_inst, aba_op, aba_metodo = st.tabs([
    "Visão geral",
    "Saúde da rede",
    "Explorar instrumento",
    "Resultados do rebaixamento",
    "Metodologia",
])

# -----------------------------------------------------------------------------
# Visão geral
# -----------------------------------------------------------------------------
with aba_visao:
    section(
        "Visão executiva",
        "Da confiabilidade do dado ao resultado da operação",
        "O HidroCheck começa pela saúde da rede, permite investigar cada instrumento e, só então, consolida o comportamento do sistema de rebaixamento.",
    )

    st.markdown(
        """
        <div class="flow">
            <div class="flow-step"><div class="num">1</div><b>Rede completa</b><span>Todos os instrumentos ativos de nível d’água entram na triagem.</span></div>
            <div class="flow-step"><div class="num">2</div><b>QA/QC</b><span>Recebimento, flatline, repetições, outliers e inconsistências.</span></div>
            <div class="flow-step"><div class="num">3</div><b>Exploração</b><span>Cada instrumento pode ser aberto e revisado em detalhe.</span></div>
            <div class="flow-step"><div class="num">4</div><b>Tendência</b><span>Theil–Sen + Mann–Kendall quantificam a evolução do nível d’água.</span></div>
            <div class="flow-step"><div class="num">5</div><b>Resultado</b><span>O comportamento espacial apoia a leitura da operação do rebaixamento.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    section(
        "1 · Confiabilidade",
        "O que merece atenção agora",
        "A triagem automática reduz o universo de revisão e direciona a equipe para os sinais mais relevantes.",
    )

    left, right = st.columns([1.45, 1], gap="large")
    with left:
        st.markdown("#### Saúde espacial da rede")
        st.caption(f"{len(fisicos)} instrumentos físicos avaliados. Filtre por localidade e, se desejar, ative a imagem aérea de Germano.")
        fig = mapa_saude_interativo(fisicos, "visao", 520)
        st.plotly_chart(fig, width="stretch")

    with right:
        st.markdown("#### Prioridades de revisão")
        if prioritarios.empty:
            st.success("Nenhum instrumento em prioridade alta.")
        else:
            for i, (_, row) in enumerate(prioritarios.head(5).iterrows(), 1):
                dt = row["ultima"].strftime("%d/%m/%Y") if pd.notna(row["ultima"]) else "—"
                motivo = str(row["motivos"]).replace(" | ", ". ")
                st.markdown(
                    f'<div class="priority-row">'
                    f'<div class="priority-top"><div class="priority-id"><span class="rank">#{i}</span><span class="inst">{row["instrumento"]}</span></div>'
                    f'<span class="status-pill pill-danger">Prioritário</span></div>'
                    f'<div class="priority-meta">Última leitura: {dt}</div>'
                    f'<div class="priority-reason">{motivo}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.caption("Abra a aba **Explorar instrumento** para revisar a série histórica e os motivos do QA/QC.")

    st.divider()
    section(
        "2 · Operação",
        "Resumo do comportamento do rebaixamento",
        "Depois da triagem de qualidade, a análise de tendência resume onde predomina rebaixamento ou recuperação.",
    )

    if not tx.empty and not tx_sig.empty:
        n_sig_monitor = int(((tx["significativo"]) & (~tx["bombeamento"])).sum())
        med_norte = tx_sig.loc[tx_sig["localidade"] == "Alegria Norte", "taxa"].median()
        med_sul = tx_sig.loc[tx_sig["localidade"] == "Alegria Sul", "taxa"].median()
        kpi_cards([
            ("Séries de tendência", f"{len(tx)}", "módulo histórico do rebaixamento", "info"),
            ("Tendências significativas", f"{n_sig_monitor}", "monitoramento · p < 0,05", "ok"),
            ("Alegria Norte", f"{med_norte:.2f} m/ano" if pd.notna(med_norte) else "—", "mediana · rebaixamento predominante", "danger"),
            ("Alegria Sul", f"+{med_sul:.2f} m/ano" if pd.notna(med_sul) and med_sul >= 0 else (f"{med_sul:.2f} m/ano" if pd.notna(med_sul) else "—"), "mediana · recuperação predominante", "ok"),
        ])
        st.info("O mapa completo, rankings e leitura por setor estão na aba **Resultados do rebaixamento**.")
    else:
        st.info("Os resultados históricos de tendência ainda não estão disponíveis nesta execução.")

# -----------------------------------------------------------------------------
# Saúde da rede
# -----------------------------------------------------------------------------
with aba_qc:
    section(
        "QA/QC",
        "Saúde da rede de monitoramento de nível d'água",
        "Todos os instrumentos ativos do cadastro são avaliados com regras transparentes e reprodutíveis.",
    )

    n_trav = int(fisicos["motivos"].str.contains("travado", case=False, na=False).sum())
    n_out = int((fisicos["outliers_fortes"] > 0).sum())
    n_zero = int(fisicos["zero_auto_persistente"].sum())
    n_fundo = int(fisicos["repeticao_no_fundo"].sum())
    kpi_cards([
        ("Flatline atual", str(n_trav), "sequência constante suspeita", "danger" if n_trav else "ok"),
        ("Com outlier forte", str(n_out), "instrumentos, sem exclusão automática", "warn"),
        ("Zero automático persistente", str(n_zero), "poços tubulares — conferir canal", "warn"),
        ("No limite de profundidade", str(n_fundo), "pode representar ponto seco", "info"),
    ])

    c1, c2 = st.columns([1, 1.5], gap="large")
    with c1:
        st.markdown("#### Situação QA/QC")
        ordem = ["PRIORITÁRIO", "ATENÇÃO", "OBSERVAR", "OK"]
        cont = fisicos["status_qaqc"].value_counts().reindex(ordem, fill_value=0).rename_axis("situação").reset_index(name="instrumentos")
        fig_bar = px.bar(
            cont, x="situação", y="instrumentos", text="instrumentos", color="situação",
            color_discrete_map={"PRIORITÁRIO": "#B42318", "ATENÇÃO": "#D89A20", "OBSERVAR": "#718096", "OK": "#2E7D32"},
        )
        fig_bar.update_traces(textposition="outside", marker_line_width=0)
        fig_bar.update_layout(showlegend=False)
        plot_clean(fig_bar, 370)
        st.plotly_chart(fig_bar, width="stretch")

    with c2:
        st.markdown("#### Recebimento por situação")
        rec_order = ["RECEBENDO", "ATRASADO", "INTERROMPIDO", "SEM DADOS"]
        rr = fisicos["recebimento"].value_counts().reindex(rec_order, fill_value=0).rename_axis("recebimento").reset_index(name="instrumentos")
        fig_rec = px.bar(
            rr, x="recebimento", y="instrumentos", text="instrumentos", color="recebimento",
            color_discrete_map={"RECEBENDO": "#2E7D32", "ATRASADO": "#D89A20", "INTERROMPIDO": "#B42318", "SEM DADOS": "#718096"},
        )
        fig_rec.update_traces(textposition="outside", marker_line_width=0)
        fig_rec.update_layout(showlegend=False)
        plot_clean(fig_rec, 370)
        st.plotly_chart(fig_rec, width="stretch")

    st.markdown("#### Mapa de saúde da instrumentação")
    st.caption(f"{len(fisicos)} instrumentos físicos com coordenadas estão no mapa. Em 'Todas', pontos muito próximos podem se sobrepor visualmente; filtre por localidade para inspecionar cada instrumento.")
    fig_map = mapa_saude_interativo(fisicos, "qaqc", 640)
    st.plotly_chart(fig_map, width="stretch")

    st.markdown("#### Lista de revisão")
    show = fisicos[fisicos["status_qaqc"].isin(["PRIORITÁRIO", "ATENÇÃO", "OBSERVAR"])].copy()
    cols = ["instrumento", "localidade", "natureza", "status_qaqc", "recebimento", "ultima", "motivos"]
    tab = show[cols].copy()
    tab.columns = ["Instrumento", "Localidade", "Tipo", "QA/QC", "Recebimento", "Última leitura", "Sinais identificados"]
    tab["Última leitura"] = pd.to_datetime(tab["Última leitura"], errors="coerce").dt.strftime("%d/%m/%Y")
    st.dataframe(tab, width="stretch", hide_index=True, height=500)

# -----------------------------------------------------------------------------
# Instrumentos
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _hga_ui():
    _, h = carregar_bases(ROOT / "data")
    return h

with aba_inst:
    section(
        "Exploração",
        "Abra um instrumento e entenda seu comportamento",
        "A série histórica fica ao lado do resultado do QA/QC, facilitando a revisão pela equipe técnica.",
    )

    busca = st.text_input("Buscar instrumento", placeholder="Ex.: 0027-INA-054")
    opcoes = rede["instrumento"].dropna().astype(str).tolist()
    if busca:
        filtradas = [x for x in opcoes if busca.lower() in x.lower()]
    else:
        filtradas = opcoes
    if not filtradas:
        st.info("Nenhum instrumento encontrado.")
    else:
        sel = st.selectbox("Instrumento", filtradas, index=0)
        row = rede[rede["instrumento"] == sel].iloc[0]
        st.markdown(
            f'<div class="callout"><strong>{sel}</strong> · {row.get("localidade", "—")} · {row.get("natureza", "—")}<br>'
            f'<strong>QA/QC:</strong> {row.get("status_qaqc", "—")} · <strong>Recebimento:</strong> {row.get("recebimento", "—")}<br>'
            f'{row.get("motivos", "")}</div>',
            unsafe_allow_html=True,
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Leituras", int(row.get("leituras", 0)))
        m2.metric("Dias sem leitura", "—" if pd.isna(row.get("dias_sem_leitura")) else int(row.get("dias_sem_leitura")))
        m3.metric("Repetição final", f'{int(row.get("repeticao_final_n", 0))} leituras')
        m4.metric("Outliers fortes", int(row.get("outliers_fortes", 0)))

        # Integra QA/QC e resultado histórico do rebaixamento no detalhe do instrumento.
        if not tx.empty:
            import re as _re_tx
            sid_tx = _re_tx.sub(r"\s+", "", str(sel)).upper()
            tx_row = tx[tx["inst_id"].astype(str).str.replace(r"\s+", "", regex=True).str.upper() == sid_tx]
            if not tx_row.empty:
                tr = tx_row.iloc[0]
                st.markdown("#### Tendência histórica do instrumento")
                t1, t2, t3, t4 = st.columns(4)
                taxa_val = tr.get("taxa")
                t1.metric("Taxa", "—" if pd.isna(taxa_val) else f"{float(taxa_val):+.2f} m/ano")
                t2.metric("Significativa", "Sim" if b(tr.get("significativo")) else "Não")
                p_val = tr.get("p")
                t3.metric("p-valor", "—" if pd.isna(p_val) else f"{float(p_val):.3g}")
                anos_val = tr.get("anos")
                t4.metric("Janela", "—" if pd.isna(anos_val) else f"{float(anos_val):.1f} anos")

        h = _hga_ui()
        import re as _re
        sid = _re.sub(r"\s+", "", str(sel)).upper()
        serie = h[h["inst_id"] == sid].copy()
        serie = serie[(serie["data"].notna()) & (serie["data"] <= pd.Timestamp("2026-08-06")) & serie["cota_na_m"].notna()]
        if serie.empty:
            st.warning("Não há série de Cota_NA disponível para este instrumento na HGA atual.")
        else:
            fig_s = px.line(
                serie.sort_values("data"), x="data", y="cota_na_m", color="tipo_dado",
                labels={"data": "Data", "cota_na_m": "Cota do NA (m)", "tipo_dado": "Origem"},
            )
            fig_s.update_traces(mode="lines+markers", marker=dict(size=4))
            if not eventos.empty:
                evs = eventos[(eventos["instrumento"].astype(str) == sel) & (eventos["evento"] == "Outlier pontual forte")].dropna(subset=["data", "cota_na_m"])
                if not evs.empty:
                    fig_s.add_trace(go.Scatter(x=evs["data"], y=evs["cota_na_m"], mode="markers", name="Outlier para revisão", marker=dict(size=10, symbol="x")))
            plot_clean(fig_s, 520)
            st.plotly_chart(fig_s, width="stretch")

    st.download_button(
        "⬇  Exportar QA/QC completo",
        data=rede.to_csv(index=False).encode("utf-8-sig"),
        file_name="HidroCheck_QAQC_rede.csv",
        mime="text/csv",
    )

# -----------------------------------------------------------------------------
# Resultado do rebaixamento
# -----------------------------------------------------------------------------
with aba_op:
    section(
        "Operação",
        "Resultados da operação do sistema de rebaixamento",
        "Depois da triagem de qualidade, a análise de tendência mostra onde a rede registra rebaixamento, recuperação ou ausência de tendência significativa.",
    )

    if tx.empty:
        st.info("O arquivo taxas.csv ainda não está disponível.")
    else:
        kpi_cards([
            ("Séries analisadas", f"{len(tx)}", "instrumentos do módulo de tendência", "info"),
            ("Tendências significativas", f"{int(tx['significativo'].sum())}", "Mann–Kendall, p < 0,05", "ok"),
            ("Poços de bombeamento", f"{int(tx['bombeamento'].sum())}", "identificados separadamente", "info"),
            ("Janela máxima", f"{tx['anos'].max():.1f} anos", "histórico disponível", "info"),
        ])

        c_map, c_side = st.columns([1.65, 1], gap="large")
        with c_map:
            st.markdown("#### Mapa de taxa de variação")
            if mapa_path.exists():
                st.image(str(mapa_path), width="stretch")
            elif not tx_sig.empty:
                fig_tx = px.scatter(
                    tx_sig, x="x", y="y", color="taxa", hover_name="inst_id",
                    hover_data={"localidade": True, "taxa": ":.2f", "p": ":.3g", "anos": ":.1f"},
                    color_continuous_scale="RdBu", color_continuous_midpoint=0,
                    labels={"x": "UTM E (m)", "y": "UTM N (m)", "taxa": "m/ano"},
                )
                fig_tx.update_traces(marker=dict(size=10, line=dict(width=.7, color="white")))
                fig_tx.update_yaxes(scaleanchor="x", scaleratio=1)
                plot_clean(fig_tx, 580)
                st.plotly_chart(fig_tx, width="stretch")
        with c_side:
            st.markdown("#### Leitura por setor")
            if not tx_sig.empty:
                med = tx_sig.groupby("localidade")["taxa"].median()
                for nome in ["Alegria Norte", "Alegria Sul", "Alegria Centro", "Cava Germano"]:
                    if nome in med.index:
                        st.markdown(sector_card(nome, float(med.loc[nome])), unsafe_allow_html=True)
                st.caption("Valores negativos = rebaixamento; positivos = recuperação.")

        if not tx_sig.empty:
            st.markdown("#### Instrumentos com maiores taxas significativas")
            c_down, c_up = st.columns(2, gap="large")
            cols_show = ["inst_id", "localidade", "taxa", "p", "anos"]
            with c_down:
                st.markdown("**Maior rebaixamento**")
                d = tx_sig.nsmallest(8, "taxa")[cols_show].copy()
                d.columns = ["Instrumento", "Setor", "Taxa (m/ano)", "p", "Anos"]
                st.dataframe(d, width="stretch", hide_index=True)
            with c_up:
                st.markdown("**Maior recuperação**")
                u = tx_sig.nlargest(8, "taxa")[cols_show].copy()
                u.columns = ["Instrumento", "Setor", "Taxa (m/ano)", "p", "Anos"]
                st.dataframe(u, width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# Metodologia
# -----------------------------------------------------------------------------
with aba_metodo:
    section(
        "Rastreabilidade",
        "Critérios explícitos, parametrizados e revisáveis",
        "O algoritmo sinaliza padrões; a confirmação e a interpretação continuam sendo responsabilidade da equipe de hidrogeologia.",
    )

    st.markdown(
        """
        <div class="flow">
            <div class="flow-step"><div class="num">1</div><b>Escopo</b><span>Ativos + Monitoramento Hidrogeológico; cavas fora do denominador.</span></div>
            <div class="flow-step"><div class="num">2</div><b>Cadência</b><span>Calculada por instrumento a partir do histórico recente.</span></div>
            <div class="flow-step"><div class="num">3</div><b>Flatline</b><span>Sequências idênticas são avaliadas considerando fonte e duração.</span></div>
            <div class="flow-step"><div class="num">4</div><b>Outlier</b><span>Somente picos isolados fortes; nenhum dado é removido automaticamente.</span></div>
            <div class="flow-step"><div class="num">5</div><b>Prioridade</b><span>Reservada a sinais atuais e acionáveis.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    criterios = pd.DataFrame([
        ["Recebimento automático", "Atraso comparado à cadência do próprio instrumento", "Evita limiar único para toda a rede"],
        ["Recebimento manual", "Janela mais ampla, também adaptada à cadência histórica", "Não penaliza campanha manual como se fosse telemetria"],
        ["Flatline automático", "≥ 10 leituras idênticas e ≥ 10 dias", "Prioridade de revisão"],
        ["Flatline manual", "≥ 6 leituras idênticas e ≥ 90 dias", "Sinal de revisão"],
        ["Limite de profundidade", "NA repetido ≈ profundidade do instrumento", "Tratado como possível ponto seco, não como sensor travado"],
        ["Outlier", "Pico isolado forte com retorno ao patamar anterior", "Somente sinaliza; não exclui"],
        ["Poço tubular", "Outlier não é aplicado; zero automático persistente é destacado separadamente", "Evita confundir efeito operacional com falha"],
    ], columns=["Regra", "Critério", "Por quê"])
    st.dataframe(criterios, width="stretch", hide_index=True)
    st.info("Os limiares são uma primeira parametrização técnica e devem ser validados com a equipe antes de qualquer uso operacional definitivo.")
