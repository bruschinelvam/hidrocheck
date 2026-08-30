from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re

import numpy as np
import pandas as pd


TIPO_AUTOMATICO = "Medido Automatico"
TIPO_MANUAL = "Medido Manual"

STATUS_CONFORME = "Conforme"
STATUS_ACOMPANHAR = "Acompanhar"
STATUS_REVISAO = "Revisão recomendada"
STATUS_SEM_ATUALIZACAO = "Sem atualização recente"

JANELA_ATUAL_AUTO_DIAS = 7
MIN_DATAS_AUTO = 3
TOLERANCIA_REFERENCIA_AUTO_DIAS = 14
TOLERANCIA_REFERENCIA_MANUAL_DIAS = 30
LIMIAR_ESTAVEL_M = 0.10
RAIO_VIZINHOS_M = 250.0

# Escopo espacial do Complexo Germano, correspondente à base aérea do projeto.
GERMANO_XMIN = 648700.4479
GERMANO_YMIN = 7760701.2652
GERMANO_XMAX = 667298.2571
GERMANO_YMAX = 7773899.3678

MENSAGEM_CONFORME = "Conforme — Nenhum sinal recente requer acompanhamento pela rotina automática."
MENSAGEM_FLATLINE = "Acompanhar — Leituras consecutivas permaneceram constantes por período prolongado."
MENSAGEM_POS_FLATLINE = "Acompanhar — A série voltou a variar recentemente e ainda aguarda leituras adicionais coerentes."
MENSAGEM_SALTO = (
    "Acompanhar — Leitura recente distinta do comportamento habitual. "
    "A continuidade da série permitirá avaliar sua representatividade."
)
MENSAGEM_MUDANCA = "Acompanhar — Mudança recente no comportamento das leituras."
MENSAGEM_RUIDO = "Acompanhar — As leituras recentes apresentam maior oscilação em relação ao comportamento habitual."
MENSAGEM_CONFLITO = "Acompanhar — Há leituras distintas registradas para o mesmo horário."
MENSAGEM_SEM_ATUALIZACAO = "Sem atualização recente — Não há leitura atual dentro da cadência considerada."


def _norm_tag(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "")).upper()


def _filtrar_complexo_germano(cad: pd.DataFrame) -> pd.DataFrame:
    x = pd.to_numeric(cad["X(m)"], errors="coerce")
    y = pd.to_numeric(cad["Y(m)"], errors="coerce")
    mask = x.between(GERMANO_XMIN, GERMANO_XMAX) & y.between(GERMANO_YMIN, GERMANO_YMAX)
    return cad.loc[mask].copy()


def filtrar_ativos_com_leitura_no_ano(
    base: pd.DataFrame,
    data_corte: pd.Timestamp,
) -> pd.DataFrame:
    """Mantém instrumentos ativos com ao menos uma cota válida no ano do snapshot."""
    x = base.copy()
    colunas_necessarias = {"situacao_operacional", "ultima"}
    if x.empty or not colunas_necessarias.issubset(x.columns):
        return x.iloc[0:0].copy()

    corte = pd.to_datetime(data_corte, errors="coerce")
    if pd.isna(corte):
        return x.iloc[0:0].copy()

    ultima = pd.to_datetime(x["ultima"], errors="coerce")
    inicio_ano = pd.Timestamp(year=int(corte.year), month=1, day=1)
    fim_snapshot = pd.Timestamp(corte).normalize() + pd.Timedelta(days=1)
    ativo = (
        x["situacao_operacional"]
        .astype(str)
        .str.strip()
        .str.casefold()
        .eq("ativo")
    )
    leitura_valida_no_ano = ultima.ge(inicio_ano) & ultima.lt(fim_snapshot)
    return x.loc[ativo & leitura_valida_no_ano].copy()


def _datetime_excel_ou_texto(values: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(values):
        return pd.to_datetime(values, errors="coerce")
    parsed = pd.to_datetime(values, errors="coerce", dayfirst=True)
    numeric = pd.to_numeric(values, errors="coerce")
    mask = parsed.isna() & numeric.notna()
    if mask.any():
        parsed.loc[mask] = pd.to_datetime(
            numeric.loc[mask], errors="coerce", origin="1899-12-30", unit="D"
        )
    return parsed


def normalizar_hga(hga: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nomes, horário e cota sem descartar o histórico para exibição."""
    x = hga.copy()
    renomear = {
        "NA_m": "na_m",
        "Cota_NA_m": "cota_na_m",
        "Cota_Poco_m": "cota_poco_m",
        "Tipo_Dado": "tipo_dado",
        "Tipo_NA": "tipo_na",
    }
    x = x.rename(columns={k: v for k, v in renomear.items() if k in x.columns and v not in x.columns})
    if "inst_id" not in x.columns:
        x["inst_id"] = x["Ponto"].map(_norm_tag)
    else:
        x["inst_id"] = x["inst_id"].map(_norm_tag)

    # "Data" preserva hora quando disponível. DATA_ é contingência.
    if "Data" in x.columns:
        data = _datetime_excel_ou_texto(x["Data"])
    elif "data" in x.columns:
        data = _datetime_excel_ou_texto(x["data"])
    else:
        data = pd.Series(pd.NaT, index=x.index, dtype="datetime64[ns]")
    if "DATA_" in x.columns:
        fallback = _datetime_excel_ou_texto(x["DATA_"])
        data = data.where(data.notna(), fallback)
    x["data"] = data
    x["cota_na_m"] = pd.to_numeric(x.get("cota_na_m"), errors="coerce")
    x["tipo_dado"] = x.get("tipo_dado", "").astype(str).str.strip()
    return x


def _mascara_instrumento_incluido(inst_id: pd.Series) -> pd.Series:
    ids = inst_id.astype(str).map(_norm_tag)
    return (~ids.str.contains("PVIRTUAL", case=False, na=False)) & ids.ne("COTA-NA-REJEITO")


def inferir_data_corte(hga: pd.DataFrame) -> pd.Timestamp:
    """Retorna a data máxima dos registros medidos e incluídos no snapshot."""
    x = normalizar_hga(hga)
    validos = x[
        x["data"].notna()
        & x["cota_na_m"].notna()
        & x["tipo_dado"].isin([TIPO_AUTOMATICO, TIPO_MANUAL])
        & _mascara_instrumento_incluido(x["inst_id"])
    ]
    if validos.empty:
        raise ValueError("A base não contém data válida para definir o snapshot.")
    return pd.Timestamp(validos["data"].max()).normalize()


def _aplicar_situacao_hga(
    cad: pd.DataFrame,
    hga: pd.DataFrame,
    data_corte: pd.Timestamp | None = None,
) -> pd.DataFrame:
    cad = cad.copy()
    hga = normalizar_hga(hga)
    data_corte = pd.Timestamp(data_corte or inferir_data_corte(hga))
    cad["situacao_cadastro"] = cad["Situacao Atual"].astype("string").fillna("").str.strip()

    if "Situacao Atual" not in hga.columns:
        cad["situacao_hga_atual"] = ""
        cad["situacao_operacional"] = cad["situacao_cadastro"]
        cad["fonte_situacao_operacional"] = "Coordenadas.xlsx"
    else:
        status = hga[["inst_id", "Situacao Atual", "data"]].copy()
        status["situacao_hga_atual"] = status["Situacao Atual"].astype("string").fillna("").str.strip()
        status = status[
            status["data"].notna()
            & status["data"].lt(data_corte + pd.Timedelta(days=1))
            & status["situacao_hga_atual"].ne("")
        ]
        status = (
            status.sort_values(["inst_id", "data"])
            .drop_duplicates("inst_id", keep="last")
            .set_index("inst_id")
        )
        cad["situacao_hga_atual"] = cad["inst_id"].map(status["situacao_hga_atual"]).fillna("")
        tem_hga = cad["situacao_hga_atual"].ne("")
        cad["situacao_operacional"] = cad["situacao_hga_atual"].where(
            tem_hga, cad["situacao_cadastro"]
        )
        cad["fonte_situacao_operacional"] = np.where(
            tem_hga, "HGA do snapshot", "Coordenadas.xlsx"
        )

    # Exceção operacional já aprovada e existente nas versões anteriores.
    override = cad["inst_id"].eq("G00-11PTR006")
    cad.loc[override, "situacao_operacional"] = "Tamponado"
    cad.loc[override, "fonte_situacao_operacional"] = "Override operacional HidroCheck"
    return cad


def carregar_bases(dir_dados: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = Path(dir_dados)
    cad = pd.read_excel(p / "Coordenadas.xlsx", sheet_name="Sheet1")
    hga = pd.read_excel(p / "HGA-28082026.xlsx", sheet_name="Sheet1")
    cad["inst_id"] = cad["TAG HGA"].map(_norm_tag)
    cad = _filtrar_complexo_germano(cad)
    hga = normalizar_hga(hga)
    ids = set(cad["inst_id"].dropna().astype(str))
    hga = hga[hga["inst_id"].isin(ids)].copy()
    data_corte = inferir_data_corte(hga)
    cad = _aplicar_situacao_hga(cad, hga, data_corte)
    return cad, hga


def classificar_modo_monitoramento(g: pd.DataFrame, data_corte: pd.Timestamp) -> str:
    x = normalizar_hga(g)
    x = x[
        x["data"].notna()
        & x["data"].lt(pd.Timestamp(data_corte) + pd.Timedelta(days=1))
        & x["cota_na_m"].notna()
        & x["tipo_dado"].isin([TIPO_AUTOMATICO, TIPO_MANUAL])
    ]
    auto = x[x["tipo_dado"].eq(TIPO_AUTOMATICO)]
    manual = x[x["tipo_dado"].eq(TIPO_MANUAL)]
    if not auto.empty:
        ultima_auto = auto["data"].max()
        ultima_manual = manual["data"].max() if not manual.empty else pd.NaT
        recente = ultima_auto >= pd.Timestamp(data_corte) - pd.DateOffset(years=5)
        ainda_operacional = pd.isna(ultima_manual) or ultima_auto >= ultima_manual - pd.Timedelta(days=365)
        if recente or ainda_operacional:
            return "Automático"
    return "Manual" if not manual.empty else "Histórico"


@dataclass
class SeriePreparada:
    dados: pd.DataFrame
    conflitos: pd.DataFrame


def preprocessar_serie(g: pd.DataFrame, data_corte: pd.Timestamp) -> SeriePreparada:
    x = normalizar_hga(g)
    fim = pd.Timestamp(data_corte) + pd.Timedelta(days=1)
    x = x[
        x["data"].notna()
        & x["data"].lt(fim)
        & x["cota_na_m"].notna()
        & x["tipo_dado"].isin([TIPO_AUTOMATICO, TIPO_MANUAL])
    ].copy()
    x = x.sort_values(["data", "tipo_dado", "cota_na_m"])
    x = x.drop_duplicates(["data", "tipo_dado", "cota_na_m"], keep="first")
    diferentes = x.groupby("data")["cota_na_m"].nunique(dropna=True)
    horas_conflito = diferentes[diferentes > 1].index
    conflitos = x[x["data"].isin(horas_conflito)].copy()
    x = x[~x["data"].isin(horas_conflito)].copy()
    return SeriePreparada(x, conflitos)


def _serie_diaria(x: pd.DataFrame) -> pd.DataFrame:
    if x.empty:
        return pd.DataFrame(columns=["data", "cota_na_m", "valor_exato"])
    y = x.copy()
    y["dia"] = y["data"].dt.normalize()
    diario = y.groupby("dia")["cota_na_m"].agg(
        cota_na_m="median",
        n_valores="size",
        n_distintos="nunique",
        primeiro="first",
    ).reset_index().rename(columns={"dia": "data"})
    diario["valor_exato"] = diario["primeiro"].where(diario["n_distintos"].eq(1))
    return diario.sort_values("data").reset_index(drop=True)


def _runs_flatline(diario: pd.DataFrame) -> list[tuple[int, int, float]]:
    runs: list[tuple[int, int, float]] = []
    inicio = 0
    valores = diario.get("valor_exato", pd.Series(dtype=float)).to_numpy(float)
    for i in range(1, len(valores) + 1):
        encerra = i == len(valores)
        if not encerra:
            a, b = valores[i - 1], valores[i]
            encerra = not (np.isfinite(a) and np.isfinite(b) and a == b)
        if encerra:
            valor = valores[i - 1] if i else np.nan
            if np.isfinite(valor) and i - inicio >= 5:
                runs.append((inicio, i - 1, float(valor)))
            inicio = i
    return runs


def _limiar_adaptativo(diffs: np.ndarray, nivel: float) -> float:
    valores = np.abs(np.asarray(diffs, dtype=float))
    valores = valores[np.isfinite(valores)]
    piso_resolucao = max(0.03, abs(float(nivel)) * 0.00003)
    if len(valores) < 4:
        return piso_resolucao
    med = float(np.median(valores))
    mad = float(np.median(np.abs(valores - med)))
    q95 = float(np.quantile(valores, 0.95))
    return max(piso_resolucao, q95 * 1.5, med + 8.0 * 1.4826 * mad)


def _mudanca_sustentada(diffs: np.ndarray, indice: int) -> bool:
    ini = max(0, indice - 3)
    fim = min(len(diffs), indice + 4)
    trecho = np.asarray(diffs[ini:fim], dtype=float)
    trecho = trecho[np.isfinite(trecho) & (np.abs(trecho) > 1e-12)]
    if len(trecho) < 4:
        return False
    sinal = np.sign(diffs[indice])
    mesma_direcao = np.mean(np.sign(trecho) == sinal)
    if mesma_direcao < 0.75:
        return False
    mags = np.abs(trecho[np.sign(trecho) == sinal])
    if len(mags) < 4:
        return False
    magnitude_candidata = abs(float(diffs[indice]))
    outras = np.delete(mags, int(np.argmin(np.abs(mags - magnitude_candidata))))
    # Uma mudança sustentada tem vários incrementos de escala comparável. Dois
    # degraus muito maiores que toda a vizinhança continuam sendo avaliados.
    return magnitude_candidata <= max(float(np.median(outras)) * 4.0, 0.10)


def _avaliar_salto(diario: pd.DataFrame, data_corte: pd.Timestamp) -> dict[str, object]:
    resultado: dict[str, object] = {
        "tipo": "",
        "data": pd.NaT,
        "magnitude": np.nan,
        "excluir_datas": set(),
    }
    if len(diario) < 8:
        return resultado
    vals = diario["cota_na_m"].to_numpy(float)
    diffs = np.diff(vals)
    datas_diff = diario["data"].iloc[1:].reset_index(drop=True)
    inicio_recente = pd.Timestamp(data_corte) - pd.Timedelta(days=21)
    hist_mask = datas_diff < inicio_recente
    hist = diffs[hist_mask.to_numpy()]
    if len(hist) < 8:
        hist = diffs[:-5] if len(diffs) > 8 else diffs[:-1]
    limiar = _limiar_adaptativo(hist, float(np.median(vals)))
    candidatos = [
        i for i, (d, data) in enumerate(zip(diffs, datas_diff))
        if pd.Timestamp(data) >= inicio_recente and abs(float(d)) > limiar and not _mudanca_sustentada(diffs, i)
    ]
    if not candidatos:
        return resultado
    if len(candidatos) >= 2:
        ida, volta = candidatos[-2], candidatos[-1]
        mag_ida, mag_volta = float(diffs[ida]), float(diffs[volta])
        razao = abs(mag_ida) / max(abs(mag_volta), 1e-12)
        if volta == ida + 1 and mag_ida * mag_volta < 0 and 0.5 <= razao <= 2.0:
            regime_anterior = float(np.median(vals[max(0, ida - 4): ida + 1]))
            posteriores = vals[volta + 1:]
            tolerancia = max(limiar, 0.10)
            if len(posteriores) >= 2 and int((np.abs(posteriores - regime_anterior) <= tolerancia).sum()) >= 2:
                data_salto = pd.Timestamp(diario.iloc[ida + 1]["data"])
                resultado.update({
                    "tipo": "salto_isolado",
                    "data": data_salto,
                    "magnitude": mag_ida,
                    "limiar": limiar,
                    "excluir_datas": {data_salto},
                })
                return resultado
    i = candidatos[-1]
    data_salto = pd.Timestamp(diario.iloc[i + 1]["data"])
    antes = vals[max(0, i - 4): i + 1]
    depois = vals[i + 1:]
    posteriores = vals[i + 2:]
    regime_anterior = float(np.median(antes))
    tolerancia = max(limiar, 2.5 * float(np.median(np.abs(np.diff(antes)))) if len(antes) > 1 else limiar)
    retornos = np.abs(posteriores - regime_anterior) <= tolerancia

    resultado.update({"data": data_salto, "magnitude": float(diffs[i]), "limiar": limiar})
    if len(posteriores) >= 2 and int(retornos.sum()) >= 2:
        resultado["tipo"] = "salto_isolado"
        resultado["excluir_datas"] = {data_salto}
        return resultado

    # Três leituras posteriores coerentes confirmam o novo patamar.
    if len(posteriores) >= 3:
        pos = depois
        dispersao = float(np.median(np.abs(np.diff(pos)))) if len(pos) > 1 else 0.0
        if dispersao <= max(limiar, 0.10):
            resultado["tipo"] = "patamar_confirmado"
            return resultado

    resultado["tipo"] = "salto_nao_confirmado" if i == len(diffs) - 1 else "patamar_nao_confirmado"
    return resultado


def _avaliar_ruido(diario: pd.DataFrame, data_corte: pd.Timestamp) -> str:
    if len(diario) < 24:
        return ""
    recente = diario[diario["data"] >= pd.Timestamp(data_corte) - pd.Timedelta(days=14)]["cota_na_m"].to_numpy(float)
    historico = diario[
        (diario["data"] < pd.Timestamp(data_corte) - pd.Timedelta(days=14))
        & (diario["data"] >= pd.Timestamp(data_corte) - pd.Timedelta(days=365))
    ]["cota_na_m"].to_numpy(float)
    if len(recente) < 7 or len(historico) < 14:
        return ""
    dr = np.diff(recente)
    dh = np.diff(historico)
    # Uma sequência predominantemente monotônica é uma mudança sustentada, não ruído.
    sinais = np.sign(dr[np.abs(dr) > 1e-12])
    if len(sinais) and max(np.mean(sinais > 0), np.mean(sinais < 0)) >= 0.85:
        return ""
    rr = dr - np.median(dr)
    rh = dh - np.median(dh)
    amp_recente = float(np.median(np.abs(rr)))
    amp_historica = float(np.median(np.abs(rh)))
    alternancia = float(np.mean(np.sign(rr[1:]) != np.sign(rr[:-1]))) if len(rr) > 2 else 0.0
    if alternancia < 0.45:
        return ""
    amplitude_recente = float(np.max(recente) - np.min(recente))
    if (
        amp_recente > 6.0 * max(amp_historica, 1e-6)
        and amp_recente > 0.15
        and amplitude_recente > 0.75
    ):
        return "severo"
    if (
        amp_recente > 1.75 * max(amp_historica, 1e-6)
        and (amp_recente > 0.02 or amplitude_recente > 0.15)
    ):
        return "elevado"
    return ""


def _coerencia_pos_flatline(diario: pd.DataFrame, fim_run: int) -> bool:
    pos = diario.iloc[fim_run + 1:]
    if len(pos) < 3 or pos["cota_na_m"].nunique() < 2:
        return False
    diffs = np.diff(pos["cota_na_m"].to_numpy(float))
    anterior = np.diff(diario.iloc[: fim_run + 1]["cota_na_m"].to_numpy(float))
    limiar = _limiar_adaptativo(anterior, float(pos["cota_na_m"].median()))
    return bool(np.all(np.abs(diffs) <= max(limiar * 2.0, 0.10)))


def _referencia_manual(diario: pd.DataFrame, alvo: pd.Timestamp) -> tuple[float, pd.Timestamp] | tuple[float, pd.NaT]:
    if diario.empty:
        return np.nan, pd.NaT
    x = diario.copy()
    x["dist"] = (x["data"] - pd.Timestamp(alvo)).abs().dt.days
    x = x[x["dist"] <= TOLERANCIA_REFERENCIA_MANUAL_DIAS].sort_values(
        ["dist", "data"], ascending=[True, False]
    )
    if x.empty:
        return np.nan, pd.NaT
    r = x.iloc[0]
    return float(r["cota_na_m"]), pd.Timestamp(r["data"])


def _referencia_automatica(diario: pd.DataFrame, alvo: pd.Timestamp) -> tuple[float, pd.Timestamp] | tuple[float, pd.NaT]:
    if diario.empty:
        return np.nan, pd.NaT
    candidatos = diario[(diario["data"] - pd.Timestamp(alvo)).abs().dt.days <= TOLERANCIA_REFERENCIA_AUTO_DIAS].copy()
    if len(candidatos) < MIN_DATAS_AUTO:
        return np.nan, pd.NaT
    melhores: list[tuple[int, float, pd.DataFrame]] = []
    for centro in candidatos["data"]:
        trecho = candidatos[(candidatos["data"] >= centro - pd.Timedelta(days=3)) & (candidatos["data"] <= centro + pd.Timedelta(days=3))]
        if len(trecho) >= MIN_DATAS_AUTO:
            distancia = float((trecho["data"] - pd.Timestamp(alvo)).abs().dt.days.median())
            melhores.append((len(trecho), -distancia, trecho))
    if not melhores:
        return np.nan, pd.NaT
    trecho = sorted(melhores, key=lambda item: (item[0], item[1]), reverse=True)[0][2]
    if _runs_flatline(trecho):
        return np.nan, pd.NaT
    vals = trecho["cota_na_m"].to_numpy(float)
    if len(vals) >= 6:
        diffs = np.diff(vals)
        limiar = _limiar_adaptativo(diffs[:-1], float(np.median(vals)))
        if np.max(np.abs(diffs)) > max(4.0 * limiar, 0.50):
            return np.nan, pd.NaT
    return float(np.median(vals)), pd.Timestamp(trecho["data"].median()).normalize()


def classificar_delta(valor: object) -> str:
    delta = pd.to_numeric(valor, errors="coerce")
    if pd.isna(delta):
        return "Sem comparação disponível"
    if delta < -LIMIAR_ESTAVEL_M:
        return "Tendência de redução da cota"
    if delta > LIMIAR_ESTAVEL_M:
        return "Tendência de elevação da cota"
    return "Comportamento estável"


def analisar_serie(
    g: pd.DataFrame,
    data_corte: pd.Timestamp,
    modo: str | None = None,
) -> dict[str, object]:
    """Avalia uma série e retorna valores auditáveis para o app e os testes."""
    data_corte = pd.Timestamp(data_corte).normalize()
    modo = modo or classificar_modo_monitoramento(g, data_corte)
    preparada = preprocessar_serie(g, data_corte)
    tipo = TIPO_AUTOMATICO if modo == "Automático" else TIPO_MANUAL
    primaria = preparada.dados[preparada.dados["tipo_dado"].eq(tipo)].copy()
    diario = _serie_diaria(primaria)
    ultima = pd.Timestamp(diario["data"].max()) if not diario.empty else pd.NaT
    ultima_cota = float(diario.iloc[-1]["cota_na_m"]) if not diario.empty else np.nan
    dias_sem = int((data_corte - ultima).days) if pd.notna(ultima) else np.nan
    if len(diario) >= 2:
        intervalos = pd.to_datetime(diario["data"], errors="coerce").diff().dt.days.dropna()
        intervalos = intervalos[intervalos > 0].tail(24)
    else:
        intervalos = pd.Series(dtype=float)
    cadencia = float(intervalos.median()) if len(intervalos) else np.nan

    if modo == "Automático":
        limite_atualizacao = 5
    else:
        limite_atualizacao = int(max(45, 4.0 * (cadencia if pd.notna(cadencia) else 30.0)))
    sem_atualizacao = pd.isna(ultima) or dias_sem > limite_atualizacao

    sinais: list[str] = []
    mensagem = MENSAGEM_CONFORME
    flatline_ativo = False
    pos_flatline_pendente = False
    salto = {"tipo": "", "data": pd.NaT, "magnitude": np.nan, "excluir_datas": set()}
    ruido = ""

    conflito_recente = False
    if not preparada.conflitos.empty:
        janela_conflito = 7 if modo == "Automático" else max(30, limite_atualizacao)
        conflito_recente = preparada.conflitos["data"].max() >= data_corte - pd.Timedelta(days=janela_conflito)

    cota_atual = np.nan
    n_atual = 0
    if modo == "Automático":
        runs = [
            run for run in _runs_flatline(diario)
            if pd.Timestamp(diario.iloc[run[1]]["data"]) >= data_corte - pd.Timedelta(days=30)
        ]
        if runs:
            _, fim_run, _ = runs[-1]
            flatline_ativo = fim_run == len(diario) - 1
            pos_flatline_pendente = not flatline_ativo and not _coerencia_pos_flatline(diario, fim_run)
        salto = _avaliar_salto(diario, data_corte)
        ruido = _avaliar_ruido(diario, data_corte)

        bloqueio = (
            sem_atualizacao
            or conflito_recente
            or flatline_ativo
            or pos_flatline_pendente
            or salto["tipo"] in {"salto_nao_confirmado", "patamar_nao_confirmado"}
            or ruido == "severo"
        )
        atual = diario[diario["data"] >= data_corte - pd.Timedelta(days=JANELA_ATUAL_AUTO_DIAS - 1)].copy()
        excluir = salto.get("excluir_datas", set())
        if excluir:
            atual = atual[~atual["data"].isin(excluir)]
        n_atual = int(atual["data"].nunique())
        if not bloqueio and n_atual >= MIN_DATAS_AUTO:
            cota_atual = float(atual["cota_na_m"].median())

        if flatline_ativo:
            sinais.append("flatline")
            mensagem = MENSAGEM_FLATLINE
        elif pos_flatline_pendente:
            sinais.append("pos_flatline")
            mensagem = MENSAGEM_POS_FLATLINE
        elif salto["tipo"] in {"salto_nao_confirmado", "salto_isolado"}:
            sinais.append(str(salto["tipo"]))
            mensagem = MENSAGEM_SALTO
        elif salto["tipo"] == "patamar_nao_confirmado":
            sinais.append("patamar_nao_confirmado")
            mensagem = MENSAGEM_MUDANCA
        elif ruido:
            sinais.append(f"ruido_{ruido}")
            mensagem = MENSAGEM_RUIDO
        if ruido and not any(s.startswith("ruido_") for s in sinais):
            sinais.append(f"ruido_{ruido}")
    elif modo == "Manual" and not diario.empty and not sem_atualizacao:
        cota_atual = ultima_cota
        n_atual = 1

    if conflito_recente:
        sinais.insert(0, "conflito_temporal")
        mensagem = MENSAGEM_CONFLITO

    if sem_atualizacao:
        status = STATUS_SEM_ATUALIZACAO
        mensagem = MENSAGEM_SEM_ATUALIZACAO
        cota_atual = np.nan
    elif sinais:
        status = STATUS_ACOMPANHAR
    else:
        status = STATUS_CONFORME

    ref: dict[str, object] = {}
    for chave, deslocamento in (("12m", pd.DateOffset(months=12)), ("90d", pd.Timedelta(days=90))):
        alvo = data_corte - deslocamento
        if modo == "Automático":
            valor_ref, data_ref = _referencia_automatica(diario, alvo)
        else:
            valor_ref, data_ref = _referencia_manual(diario, alvo)
        delta = float(cota_atual - valor_ref) if pd.notna(cota_atual) and pd.notna(valor_ref) else np.nan
        ref.update({
            f"cota_referencia_{chave}_m": valor_ref,
            f"data_referencia_{chave}": data_ref,
            f"delta_{chave}_m": delta,
            f"classificacao_{chave}": classificar_delta(delta),
        })

    return {
        "modo_monitoramento": modo,
        "ultima": ultima,
        "ultima_leitura_cota_m": ultima_cota,
        "dias_sem_leitura": dias_sem,
        "cadencia_mediana_dias": cadencia,
        "limite_atualizacao_dias": limite_atualizacao,
        "recebimento": "SEM ATUALIZAÇÃO RECENTE" if sem_atualizacao else "RECEBENDO",
        "cota_atual_representativa_m": cota_atual,
        "n_atual_validas": n_atual,
        "status_qaqc": status,
        "motivos": mensagem,
        "sinais_qaqc": " | ".join(sinais),
        "flatline_ativo": flatline_ativo,
        "pos_flatline_pendente": pos_flatline_pendente,
        "salto_tipo": salto.get("tipo", ""),
        "salto_data": salto.get("data", pd.NaT),
        "variacao_ultima_m": salto.get("magnitude", np.nan),
        "ruido_recente": ruido,
        "conflitos_temporais": int(preparada.conflitos["data"].nunique()),
        "conflito_recente": conflito_recente,
        **ref,
    }


def _ptr_mais_proximo(c: pd.Series, cad: pd.DataFrame) -> tuple[str, float | None]:
    x = pd.to_numeric(c.get("X(m)"), errors="coerce")
    y = pd.to_numeric(c.get("Y(m)"), errors="coerce")
    if pd.isna(x) or pd.isna(y):
        return "", None
    situacao = cad.get("situacao_operacional", cad.get("Situacao Atual", pd.Series("", index=cad.index)))
    ptr = cad[
        situacao.astype(str).str.strip().str.casefold().eq("ativo")
        & cad["Natureza do Ponto"].astype(str).eq("Poco Tubular")
    ].copy()
    if ptr.empty:
        return "", None
    px = pd.to_numeric(ptr["X(m)"], errors="coerce")
    py = pd.to_numeric(ptr["Y(m)"], errors="coerce")
    dist = np.sqrt((px - float(x)) ** 2 + (py - float(y)) ** 2)
    if dist.isna().all():
        return "", None
    idx = dist.idxmin()
    return str(ptr.loc[idx, "TAG HGA"]), float(dist.loc[idx])


def _adicionar_contexto_vizinhos(resultado: pd.DataFrame) -> pd.DataFrame:
    out = resultado.copy()
    for periodo in ("12m", "90d"):
        delta_col = f"delta_{periodo}_m"
        med_col = f"mediana_vizinhos_{periodo}_m"
        dif_col = f"diferenca_vizinhos_{periodo}_m"
        out[med_col] = np.nan
        out[dif_col] = np.nan
        for idx, row in out.iterrows():
            x = pd.to_numeric(row.get("x"), errors="coerce")
            y = pd.to_numeric(row.get("y"), errors="coerce")
            delta = pd.to_numeric(row.get(delta_col), errors="coerce")
            if pd.isna(x) or pd.isna(y) or pd.isna(delta):
                continue
            dx = pd.to_numeric(out["x"], errors="coerce") - float(x)
            dy = pd.to_numeric(out["y"], errors="coerce") - float(y)
            dist = np.sqrt(dx * dx + dy * dy)
            viz = pd.to_numeric(out.loc[(dist > 0) & (dist <= RAIO_VIZINHOS_M), delta_col], errors="coerce").dropna()
            if len(viz):
                mediana = float(viz.median())
                out.at[idx, med_col] = mediana
                out.at[idx, dif_col] = float(delta - mediana)
    return out


def diagnosticar_dataframes(cad: pd.DataFrame, hga: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    hga = normalizar_hga(hga)
    data_corte = inferir_data_corte(hga)
    cad = cad.copy()
    if "inst_id" not in cad.columns:
        cad["inst_id"] = cad["TAG HGA"].map(_norm_tag)
    cad = _filtrar_complexo_germano(cad)
    cad = _aplicar_situacao_hga(cad, hga, data_corte)
    cad_ativos = cad[cad["situacao_operacional"].astype(str).str.strip().str.casefold().eq("ativo")].copy()
    ids = cad_ativos["inst_id"].astype(str)
    escopo = cad_ativos[
        cad_ativos["Proposito"].astype(str).eq("Monitoramento Hidrogeologico")
        & ~cad_ativos["Natureza do Ponto"].astype(str).eq("Cava")
        & _mascara_instrumento_incluido(ids)
    ].copy()

    rows: list[dict[str, object]] = []
    eventos: list[dict[str, object]] = []
    for _, c in escopo.iterrows():
        inst = str(c["inst_id"])
        g = hga[hga["inst_id"].eq(inst)].copy()
        modo = classificar_modo_monitoramento(g, data_corte)
        analise = analisar_serie(g, data_corte, modo)
        if str(c.get("Natureza do Ponto", "")) == "Poco Tubular":
            for periodo in ("12m", "90d"):
                analise[f"cota_referencia_{periodo}_m"] = np.nan
                analise[f"data_referencia_{periodo}"] = pd.NaT
                analise[f"delta_{periodo}_m"] = np.nan
                analise[f"classificacao_{periodo}"] = "Contexto operacional"
        ptr, dist_ptr = _ptr_mais_proximo(c, cad_ativos)
        row = {
            "instrumento": str(c.get("TAG HGA", "")),
            "inst_id": inst,
            "nome_original": c.get("Nome Original", ""),
            "natureza": str(c.get("Natureza do Ponto", "")),
            "situacao_cadastro": str(c.get("Situacao Atual", "") or ""),
            "situacao_operacional": str(c.get("situacao_operacional", "") or ""),
            "fonte_situacao_operacional": c.get("fonte_situacao_operacional", ""),
            "localidade": c.get("Localidade", ""),
            "x": pd.to_numeric(c.get("X(m)"), errors="coerce"),
            "y": pd.to_numeric(c.get("Y(m)"), errors="coerce"),
            "profundidade_m": pd.to_numeric(c.get("Profundidade(m)"), errors="coerce"),
            "data_corte": data_corte,
            "ptr_mais_proximo": ptr,
            "dist_ptr_m": dist_ptr,
            "leituras": int(len(g)),
            "fonte_recente": modo,
            **analise,
        }
        rows.append(row)
        if analise["sinais_qaqc"]:
            eventos.append({
                "instrumento": row["instrumento"],
                "data": analise.get("salto_data", analise.get("ultima")),
                "cota_na_m": analise.get("ultima_leitura_cota_m"),
                "evento": analise["motivos"],
                "magnitude_aprox_m": analise.get("variacao_ultima_m"),
            })

    resultado = pd.DataFrame(rows)
    if not resultado.empty:
        resultado = _adicionar_contexto_vizinhos(resultado)
        ordem = {STATUS_SEM_ATUALIZACAO: 0, STATUS_REVISAO: 1, STATUS_ACOMPANHAR: 2, STATUS_CONFORME: 3}
        resultado["_ordem"] = resultado["status_qaqc"].map(ordem).fillna(9)
        resultado = resultado.sort_values(["_ordem", "instrumento"]).drop(columns="_ordem")
    return resultado, pd.DataFrame(eventos, columns=["instrumento", "data", "cota_na_m", "evento", "magnitude_aprox_m"])


def diagnosticar(dir_dados: str | Path = "data") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cad, hga = carregar_bases(dir_dados)
    resultado, eventos = diagnosticar_dataframes(cad, hga)
    return resultado, eventos, hga


def salvar(dir_dados: str | Path = "data", dir_saida: str | Path = "out") -> pd.DataFrame:
    resultado, eventos, _ = diagnosticar(dir_dados)
    saida = Path(dir_saida)
    saida.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(saida / "analise_delta_cota.csv", index=False, encoding="utf-8-sig")
    resultado.to_csv(saida / "qaqc_rede_atual.csv", index=False, encoding="utf-8-sig")
    eventos.to_csv(saida / "qaqc_eventos_atual.csv", index=False, encoding="utf-8-sig")
    return resultado


if __name__ == "__main__":
    diagnostico = salvar("data", "out")
    print(diagnostico["status_qaqc"].value_counts(dropna=False).to_string())
