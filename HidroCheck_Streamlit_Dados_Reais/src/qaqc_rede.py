from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re

import numpy as np
import pandas as pd

DATA_REF = pd.Timestamp('2026-08-28')
JANELA_QAQC_OUTLIER_DIAS = 180
JANELA_QAQC_AUTO_DIAS = 90
JANELA_QAQC_MANUAL_DIAS = 180

# Escopo espacial do Complexo Germano, definido pela extensão da imagem aérea
# fornecida para o projeto (SIRGAS 2000 / UTM 23S, EPSG:31983).
GERMANO_XMIN = 648700.4479
GERMANO_YMIN = 7760701.2652
GERMANO_XMAX = 667298.2571
GERMANO_YMAX = 7773899.3678

# Ajustes operacionais temporários informados pela equipe.
# Mantemos o status original do cadastro/HGA para rastreabilidade, mas o QA/QC
# usa o status operacional efetivo até a base oficial ser atualizada.
STATUS_OPERACIONAL_OVERRIDE = {
    'G00-11PTR006': 'Tamponado',
}

def _situacao_operacional(tag: object, situacao_cadastro: object) -> str:
    inst = _norm_tag(tag)
    return STATUS_OPERACIONAL_OVERRIDE.get(inst, str(situacao_cadastro or '').strip())


def _filtrar_complexo_germano(cad: pd.DataFrame) -> pd.DataFrame:
    x = pd.to_numeric(cad['X(m)'], errors='coerce')
    y = pd.to_numeric(cad['Y(m)'], errors='coerce')
    mask = x.between(GERMANO_XMIN, GERMANO_XMAX) & y.between(GERMANO_YMIN, GERMANO_YMAX)
    return cad.loc[mask].copy()


def _norm_tag(value: object) -> str:
    return re.sub(r'\s+', '', str(value or '')).upper()


def _maior_fonte_recente(g: pd.DataFrame) -> str:
    if g.empty:
        return 'Histórico'
    rec = g[g['data'] >= DATA_REF - pd.Timedelta(days=90)]
    if rec.empty:
        return 'Histórico'
    ca = int((rec['tipo_dado'] == 'Medido Automatico').sum())
    cm = int((rec['tipo_dado'] == 'Medido Manual').sum())
    if ca >= max(3, cm):
        return 'Automático'
    if cm:
        return 'Manual'
    return 'Automático' if ca else 'Histórico'


def _terminal_run(s: pd.DataFrame, col: str = 'na_m') -> tuple[int, int, float | None]:
    s = s.dropna(subset=[col]).sort_values('data')
    if s.empty:
        return 0, 0, None
    vals = s[col].to_numpy(float)
    dates = s['data'].to_numpy()
    v = vals[-1]
    j = len(vals) - 1
    while j > 0 and math.isclose(vals[j - 1], v, rel_tol=0, abs_tol=1e-9):
        j -= 1
    n = len(vals) - j
    span = int((pd.Timestamp(dates[-1]) - pd.Timestamp(dates[j])).days)
    return n, span, float(v)


def _conservative_outliers(g: pd.DataFrame, min_jump: float = 2.0) -> pd.DataFrame:
    """Detecta apenas picos isolados fortes; não remove dados automaticamente."""
    x = g.dropna(subset=['cota_na_m']).sort_values('data').copy()
    if len(x) < 8:
        return x.iloc[0:0]

    # Um valor por dia para não confundir manual e automático no mesmo dia.
    d = x.groupby('data', as_index=False)['cota_na_m'].median()
    vals = d['cota_na_m'].to_numpy(float)
    if len(vals) < 8:
        return d.iloc[0:0]

    diff = np.diff(vals)
    med = float(np.median(diff))
    mad = float(np.median(np.abs(diff - med)))
    scale = 1.4826 * mad
    lim = max(float(min_jump), float(np.median(np.abs(diff))) + 10 * scale)

    idx = []
    mag = []
    for i in range(1, len(vals) - 1):
        d1 = vals[i] - vals[i - 1]
        d2 = vals[i + 1] - vals[i]
        retorno = abs(vals[i + 1] - vals[i - 1]) <= max(min_jump, 0.20 * max(abs(d1), abs(d2)))
        if d1 * d2 < 0 and abs(d1) > lim and abs(d2) > lim and retorno:
            idx.append(i)
            mag.append(max(abs(d1), abs(d2)))
    if not idx:
        return d.iloc[0:0]
    out = d.iloc[idx].copy()
    out['magnitude_aprox_m'] = mag
    return out


def _ptr_mais_proximo(c: pd.Series, cad: pd.DataFrame) -> tuple[str, float | None]:
    """Retorna o poço tubular ativo mais próximo como contexto hidrogeológico.

    A proximidade NÃO altera o status de QA/QC; serve apenas para interpretar
    tendências de rebaixamento/recuperação junto à operação.
    """
    x = pd.to_numeric(c.get('X(m)'), errors='coerce')
    y = pd.to_numeric(c.get('Y(m)'), errors='coerce')
    if pd.isna(x) or pd.isna(y):
        return '', None
    cad = cad.copy()
    cad['_situacao_operacional'] = cad.apply(lambda r: _situacao_operacional(r.get('TAG HGA'), r.get('Situacao Atual')), axis=1)
    ptr = cad[(cad['_situacao_operacional'].astype(str).str.casefold() == 'ativo') & (cad['Natureza do Ponto'] == 'Poco Tubular')].copy()
    if ptr.empty:
        return '', None
    px = pd.to_numeric(ptr['X(m)'], errors='coerce')
    py = pd.to_numeric(ptr['Y(m)'], errors='coerce')
    d = np.sqrt((px - float(x)) ** 2 + (py - float(y)) ** 2)
    if d.isna().all():
        return '', None
    idx = d.idxmin()
    tag = str(ptr.loc[idx, 'TAG HGA'])
    return tag, float(d.loc[idx])


def carregar_bases(dir_dados: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = Path(dir_dados)
    cad = pd.read_excel(p / 'Coordenadas.xlsx', sheet_name='Sheet1')
    hga = pd.read_excel(p / 'HGA-28082026.xlsx', sheet_name='Sheet1')

    cad['inst_id'] = cad['TAG HGA'].map(_norm_tag)
    hga['inst_id'] = hga['Ponto'].map(_norm_tag)

    # O HidroCheck desta versão é dedicado ao Complexo Germano. O filtro é
    # aplicado antes do QA/QC e antes da exploração das séries, garantindo que
    # todas as páginas trabalhem com o mesmo universo espacial.
    cad = _filtrar_complexo_germano(cad)

    # Escopo operacional do HidroCheck: SOMENTE instrumentos ativos.
    # Qualquer item tamponado, descomissionado, inativo, destruído ou com
    # override operacional diferente de 'Ativo' é excluído antes de todas as
    # análises e não aparece em mapas, indicadores, exploração ou tendências.
    cad['situacao_operacional'] = cad.apply(
        lambda r: _situacao_operacional(r.get('TAG HGA'), r.get('Situacao Atual')), axis=1
    )
    cad = cad[cad['situacao_operacional'].astype(str).str.strip().str.casefold() == 'ativo'].copy()

    ids_ativos = set(cad['inst_id'].dropna().astype(str))
    hga = hga[hga['inst_id'].isin(ids_ativos)].copy()

    raw_data = hga['DATA_']
    if pd.api.types.is_datetime64_any_dtype(raw_data):
        hga['data'] = pd.to_datetime(raw_data, errors='coerce')
    else:
        num = pd.to_numeric(raw_data, errors='coerce')
        hga['data'] = pd.to_datetime(num, errors='coerce', origin='1899-12-30', unit='D')
        mask = hga['data'].isna()
        if mask.any():
            hga.loc[mask, 'data'] = pd.to_datetime(raw_data[mask], errors='coerce')

    hga = hga.rename(columns={
        'NA_m': 'na_m',
        'Cota_NA_m': 'cota_na_m',
        'Cota_Poco_m': 'cota_poco_m',
        'Tipo_Dado': 'tipo_dado',
        'Tipo_NA': 'tipo_na',
    })
    return cad, hga


def diagnosticar(dir_dados: str | Path = 'data') -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cad, hga = carregar_bases(dir_dados)

    # Escopo = somente instrumentos ATIVOS de monitoramento hidrogeológico do
    # Complexo Germano. Inativos, tamponados, descomissionados e destruídos já
    # foram excluídos em carregar_bases() e não entram em nenhuma saída do app.
    escopo = cad[(cad['Proposito'] == 'Monitoramento Hidrogeologico') &
                 (cad['Natureza do Ponto'] != 'Cava') &
                 (~cad['inst_id'].astype(str).str.contains('PVIRTUAL', case=False, na=False))].copy()

    rows = []
    eventos = []

    for _, c in escopo.iterrows():
        inst = c['inst_id']
        tag = str(c.get('TAG HGA', ''))
        natureza = str(c.get('Natureza do Ponto', ''))
        situacao_cadastro = str(c.get('Situacao Atual', '') or '').strip()
        situacao_operacional = _situacao_operacional(tag, situacao_cadastro)
        ativo = situacao_operacional.casefold() == 'ativo'
        virtual = 'PVIRTUAL' in inst
        g_all = hga[hga['inst_id'] == inst].copy()
        futuras = g_all[g_all['data'] > DATA_REF].copy()
        g = g_all[(g_all['data'].notna()) & (g_all['data'] <= DATA_REF) &
                  (g_all['na_m'].notna() | g_all['cota_na_m'].notna())].copy()
        g = g.sort_values('data')
        situacao_hga_ultima = ''
        if len(g) and 'Situacao Atual' in g.columns:
            vals_status = g['Situacao Atual'].dropna().astype(str)
            if len(vals_status):
                situacao_hga_ultima = vals_status.iloc[-1].strip()

        fonte = _maior_fonte_recente(g)
        if fonte == 'Automático':
            primary = g[g['tipo_dado'] == 'Medido Automatico'].copy()
        elif fonte == 'Manual':
            primary = g[g['tipo_dado'] == 'Medido Manual'].copy()
        else:
            primary = g.copy()

        datas = pd.Series(primary['data'].dropna().drop_duplicates().sort_values())
        primeira = datas.iloc[0] if len(datas) else pd.NaT
        ultima = datas.iloc[-1] if len(datas) else pd.NaT
        dias_sem = int((DATA_REF - ultima).days) if pd.notna(ultima) else np.nan
        if len(datas) >= 2:
            intv = datas.diff().dt.days.dropna()
            intv = intv[intv > 0].tail(100)
            cadencia = float(intv.median()) if len(intv) else np.nan
        else:
            cadencia = np.nan

        if virtual:
            recebimento = 'VIRTUAL'
        elif not ativo:
            recebimento = 'FORA DE OPERAÇÃO'
        elif pd.isna(ultima):
            recebimento = 'SEM DADOS'
        else:
            if fonte == 'Automático':
                warn = max(5, 4 * (cadencia if pd.notna(cadencia) else 1))
                crit = max(15, 10 * (cadencia if pd.notna(cadencia) else 1))
            else:
                warn = max(45, 4 * (cadencia if pd.notna(cadencia) else 30))
                crit = max(120, 8 * (cadencia if pd.notna(cadencia) else 30))
            recebimento = 'INTERROMPIDO' if dias_sem > crit else ('ATRASADO' if dias_sem > warn else 'RECEBENDO')

        profundidade = pd.to_numeric(c.get('Profundidade(m)'), errors='coerce')

        # O QA/QC operacional olha para o estado ATUAL do instrumento, e não para
        # toda a série histórica. A série completa fica preservada para a análise
        # hidrogeológica (rebaixamento, recuperação, chuva, bombeamento etc.).
        janela_flat = JANELA_QAQC_AUTO_DIAS if fonte == 'Automático' else JANELA_QAQC_MANUAL_DIAS
        primary_recente = primary[primary['data'] >= DATA_REF - pd.Timedelta(days=janela_flat)].copy()
        rep_n, rep_dias, rep_val = _terminal_run(primary_recente, 'na_m')
        rep_fundo = bool(pd.notna(profundidade) and rep_val is not None and abs(rep_val - profundidade) <= 0.10)

        # Poços tubulares têm comportamento operacional próprio. Zero automático persistente
        # é reportado como integração/semântica do canal, e não como "sensor travado".
        zero_auto = False
        travado = False
        if ativo and natureza == 'Poco Tubular':
            ga = g[(g['tipo_dado'] == 'Medido Automatico') & g['na_m'].notna() &
                   (g['data'] >= DATA_REF - pd.Timedelta(days=JANELA_QAQC_AUTO_DIAS))].copy()
            z_n, z_dias, z_val = _terminal_run(ga, 'na_m')
            zero_auto = bool(z_val is not None and abs(z_val) < 1e-9 and z_n >= 7 and z_dias >= 7)
        elif ativo and not virtual and not rep_fundo:
            if fonte == 'Automático':
                travado = rep_n >= 10 and rep_dias >= 10
            elif fonte == 'Manual':
                travado = rep_n >= 6 and rep_dias >= 90

        # Outliers também são um alerta RECENTE. Eventos antigos permanecem visíveis
        # na série histórica, mas não geram alerta operacional atual.
        if (not ativo) or natureza == 'Poco Tubular':
            out = g.iloc[0:0].copy()
        else:
            recent_outlier = primary[primary['data'] >= DATA_REF - pd.Timedelta(days=JANELA_QAQC_OUTLIER_DIAS)].copy()
            out = _conservative_outliers(recent_outlier, min_jump=2.0)

        ptr_proximo, dist_ptr_m = _ptr_mais_proximo(c, cad)

        na_neg = int((pd.to_numeric(g['na_m'], errors='coerce') < 0).sum()) if len(g) else 0
        mismatch = 0
        if len(g):
            test = g[['na_m', 'cota_poco_m', 'cota_na_m']].apply(pd.to_numeric, errors='coerce').dropna()
            if len(test):
                mismatch = int((((test['cota_poco_m'] - test['na_m']) - test['cota_na_m']).abs() > 0.05).sum())

        motivos = []
        score = 0
        if virtual:
            motivos.append('Ponto virtual do modelo — fora do QA/QC de instrumentação')
        elif not ativo:
            motivos.append(f'Situação operacional: {situacao_operacional or "não informada"} — fora do QA/QC operacional atual')
        else:
            if recebimento == 'SEM DADOS':
                motivos.append('Ativo no cadastro, sem leituras encontradas na HGA')
                score += 4
            elif recebimento == 'INTERROMPIDO':
                motivos.append(f'Recebimento interrompido ({dias_sem} dias sem leitura); confirmar se o instrumento permanece ativo em campo antes de tratar como falha de transmissão')
                score += 5
            elif recebimento == 'ATRASADO':
                motivos.append(f'Recebimento atrasado ({dias_sem} dias sem leitura)')
                score += 3

            if travado:
                motivos.append(f'Últimas leituras possivelmente travadas: {rep_n} valores idênticos consecutivos por {rep_dias} dias')
                score += 7
            if rep_fundo and rep_n >= 4:
                motivos.append(f'Leitura repetida no limite de profundidade ({rep_val:.2f} m ≈ {profundidade:.2f} m); pode indicar ponto seco')
                score += 1
            if zero_auto:
                motivos.append('Zero automático persistente em poço tubular; conferir significado/integração do canal')
                score += 3
            if len(out):
                motivos.append(f'{len(out)} outlier(s) forte(s) nas últimas {JANELA_QAQC_OUTLIER_DIAS} dias para revisão')
                score += 1 if len(out) <= 2 else 2
            if len(futuras):
                motivos.append(f'{len(futuras)} registro(s) com data futura')
                score += 3
            if na_neg:
                motivos.append(f'{na_neg} leitura(s) de NA negativa(s)')
                score += 3
            if mismatch:
                motivos.append(f'{mismatch} inconsistência(s) entre NA, cota do poço e cota de NA')
                score += 2

        # Prioridade alta é reservada a sinal atual e diretamente acionável:
        # flatline em instrumento de monitoramento ou interrupção recente de canal automático.
        interrupcao_auto_recente = bool(
            ativo and recebimento == 'INTERROMPIDO' and fonte == 'Automático'
            and pd.notna(dias_sem) and dias_sem <= 365
        )
        if virtual:
            status = 'NÃO AVALIADO'
        elif not ativo:
            status = 'FORA DE OPERAÇÃO'
        elif travado or interrupcao_auto_recente:
            status = 'PRIORITÁRIO'
        elif score >= 3:
            status = 'ATENÇÃO'
        elif score > 0:
            status = 'OBSERVAR'
        else:
            status = 'OK'

        rows.append({
            'instrumento': tag,
            'nome_original': c.get('Nome Original', ''),
            'natureza': natureza,
            'situacao_cadastro': situacao_cadastro,
            'situacao_operacional': situacao_operacional,
            'situacao_hga_ultima': situacao_hga_ultima,
            'data_atualizacao_cadastro': c.get('Data Atualizacao', pd.NaT),
            'localidade': c.get('Localidade', ''),
            'x': pd.to_numeric(c.get('X(m)'), errors='coerce'),
            'y': pd.to_numeric(c.get('Y(m)'), errors='coerce'),
            'profundidade_m': profundidade,
            'fonte_recente': fonte,
            'leituras': int(len(g)),
            'primeira': primeira,
            'ultima': ultima,
            'dias_sem_leitura': dias_sem,
            'cadencia_mediana_dias': cadencia,
            'recebimento': recebimento,
            'repeticao_final_n': rep_n,
            'repeticao_final_dias': rep_dias,
            'repeticao_no_fundo': rep_fundo,
            'zero_auto_persistente': zero_auto,
            'outliers_fortes': int(len(out)),
            'datas_futuras': int(len(futuras)),
            'na_negativo': na_neg,
            'inconsistencia_cota': mismatch,
            'janela_qaqc_dias': int(janela_flat),
            'ptr_mais_proximo': ptr_proximo,
            'dist_ptr_m': dist_ptr_m,
            'status_qaqc': status,
            'score': int(score),
            'motivos': ' | '.join(motivos) if motivos else 'Sem sinais automáticos relevantes',
        })

        for _, rr in out.iterrows():
            eventos.append({
                'instrumento': tag,
                'data': rr['data'],
                'cota_na_m': rr['cota_na_m'],
                'evento': 'Outlier pontual forte',
                'magnitude_aprox_m': rr.get('magnitude_aprox_m', np.nan),
            })
        for _, rr in futuras.iterrows():
            eventos.append({
                'instrumento': tag,
                'data': rr['data'],
                'cota_na_m': rr.get('cota_na_m', np.nan),
                'evento': 'Data futura',
                'magnitude_aprox_m': np.nan,
            })

    diag = pd.DataFrame(rows).sort_values(['score', 'instrumento'], ascending=[False, True])
    ev = pd.DataFrame(eventos)
    return diag, ev, hga


def salvar(dir_dados: str | Path = 'data', dir_saida: str | Path = 'out') -> pd.DataFrame:
    diag, ev, _ = diagnosticar(dir_dados)
    o = Path(dir_saida)
    o.mkdir(parents=True, exist_ok=True)
    diag.to_csv(o / 'qaqc_rede_atual.csv', index=False, encoding='utf-8-sig')
    ev.to_csv(o / 'qaqc_eventos_atual.csv', index=False, encoding='utf-8-sig')
    return diag


if __name__ == '__main__':
    d = salvar('data', 'out')
    print(d['status_qaqc'].value_counts(dropna=False).to_string())
