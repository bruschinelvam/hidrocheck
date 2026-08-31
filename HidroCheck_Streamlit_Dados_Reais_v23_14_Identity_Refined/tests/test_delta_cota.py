from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from delta_cota import (  # noqa: E402
    CLASSIF_REFERENCIA_ALTERADA,
    STATUS_ACOMPANHAR,
    STATUS_CONFORME,
    STATUS_REVISAO,
    STATUS_SEM_ATUALIZACAO,
    analisar_serie,
    carregar_overrides_situacao,
    classificar_modo_monitoramento,
    filtrar_ativos_com_leitura_no_ano,
    inferir_data_corte,
    preprocessar_serie,
)


CORTE = pd.Timestamp("2026-08-27")


def serie(
    datas: pd.DatetimeIndex | list[pd.Timestamp],
    cotas: list[float] | np.ndarray,
    tipo: str = "Medido Automatico",
    ponto: str = "TESTE-INA-001",
) -> pd.DataFrame:
    return pd.DataFrame({
        "Ponto": ponto,
        "data": pd.to_datetime(datas),
        "cota_na_m": np.asarray(cotas, dtype=float),
        "tipo_dado": tipo,
    })


def serie_fisica(
    datas,
    cotas,
    cota_poco: float | list[float] = 1000.0,
    tipo: str = "Medido Automatico",
    ponto: str = "TESTE-INA-001",
) -> pd.DataFrame:
    """Serie com cota de boca e NA, para as checagens fisicas e de referencia."""
    base = serie(datas, cotas, tipo=tipo, ponto=ponto)
    base["cota_poco_m"] = np.asarray(
        cota_poco if isinstance(cota_poco, (list, np.ndarray)) else [cota_poco] * len(base),
        dtype=float,
    )
    base["na_m"] = base["cota_poco_m"] - base["cota_na_m"]
    return base


class DeltaCotaUnitTest(unittest.TestCase):
    def test_filtro_executivo_exige_ativo_com_leitura_no_ano(self):
        base = pd.DataFrame({
            "instrumento": ["ATIVO-2026", "ATIVO-2025", "INATIVO-2026"],
            "situacao_operacional": ["Ativo", "Ativo", "Descomissionado"],
            "ultima": ["2026-03-10", "2025-12-31", "2026-05-20"],
        })
        filtrada = filtrar_ativos_com_leitura_no_ano(base, CORTE)
        self.assertEqual(filtrada["instrumento"].tolist(), ["ATIVO-2026"])

    def test_data_corte_vem_da_base_e_desconsidera_pvirtual(self):
        dados = pd.concat([
            serie(pd.date_range("2026-08-20", periods=8, freq="D"), np.linspace(100, 99.8, 8)),
            serie([pd.Timestamp("2055-12-31")], [80.0], ponto="PVirtual_ALN_01"),
        ], ignore_index=True)
        self.assertEqual(inferir_data_corte(dados), CORTE)

    def test_instrumento_com_auto_recente_permanece_automatico_apos_qaqc_manual(self):
        auto = serie(pd.date_range("2026-08-18", periods=9, freq="D"), np.linspace(100, 99.9, 9))
        manual = serie([CORTE], [99.91], tipo="Medido Manual")
        dados = pd.concat([auto, manual], ignore_index=True)
        self.assertEqual(classificar_modo_monitoramento(dados, CORTE), "Automático")

    def test_automatico_normal_usa_mediana_dos_ultimos_sete_dias(self):
        datas = pd.date_range("2026-07-20", periods=39, freq="D")
        cotas = 100.0 + 0.02 * np.sin(np.arange(len(datas)))
        resultado = analisar_serie(serie(datas, cotas), CORTE)
        esperado = float(np.median(cotas[-7:]))
        self.assertEqual(resultado["status_qaqc"], STATUS_CONFORME)
        self.assertAlmostEqual(resultado["cota_atual_representativa_m"], esperado, places=9)

    def test_flatline_automatico_bloqueia_cota_atual(self):
        datas = pd.date_range("2026-08-10", periods=18, freq="D")
        cotas = list(np.linspace(100.2, 100.0, 13)) + [99.8] * 5
        resultado = analisar_serie(serie(datas, cotas), CORTE)
        self.assertEqual(resultado["status_qaqc"], STATUS_ACOMPANHAR)
        self.assertTrue(resultado["flatline_ativo"])
        self.assertTrue(pd.isna(resultado["cota_atual_representativa_m"]))

    def test_flatline_encerrado_exige_tres_leituras_coerentes(self):
        datas = pd.date_range("2026-08-08", periods=20, freq="D")
        cotas = list(np.linspace(100.2, 100.0, 13)) + [99.8] * 5 + [99.79, 99.78]
        resultado = analisar_serie(serie(datas, cotas), CORTE)
        self.assertTrue(resultado["pos_flatline_pendente"])
        self.assertEqual(resultado["status_qaqc"], STATUS_ACOMPANHAR)
        self.assertTrue(pd.isna(resultado["cota_atual_representativa_m"]))

    def test_salto_isolado_retorna_ao_regime_anterior(self):
        datas = pd.date_range("2026-07-19", periods=40, freq="D")
        cotas = 100.0 + 0.01 * np.sin(np.arange(40))
        cotas[-3] = 96.0
        cotas[-2:] = [100.01, 100.00]
        resultado = analisar_serie(serie(datas, cotas), CORTE)
        self.assertEqual(resultado["salto_tipo"], "salto_isolado")
        self.assertEqual(resultado["status_qaqc"], STATUS_ACOMPANHAR)

    def test_mudanca_sustentada_grande_nao_vira_alerta_por_magnitude(self):
        datas = pd.date_range("2026-07-19", periods=40, freq="D")
        cotas = np.r_[100.0 + 0.01 * np.sin(np.arange(32)), np.linspace(99.5, 96.0, 8)]
        resultado = analisar_serie(serie(datas, cotas), CORTE)
        self.assertEqual(resultado["status_qaqc"], STATUS_CONFORME)
        self.assertFalse(pd.isna(resultado["cota_atual_representativa_m"]))

    def test_mudanca_de_patamar_confirmada_e_representativa(self):
        datas = pd.date_range("2026-07-19", periods=40, freq="D")
        cotas = 100.0 + 0.01 * np.sin(np.arange(40))
        cotas[-5:] = [95.00, 95.02, 94.99, 95.01, 95.00]
        resultado = analisar_serie(serie(datas, cotas), CORTE)
        self.assertEqual(resultado["salto_tipo"], "patamar_confirmado")
        self.assertEqual(resultado["status_qaqc"], STATUS_CONFORME)
        self.assertAlmostEqual(resultado["cota_atual_representativa_m"], 95.01, delta=0.03)

    def test_ruido_recente_combina_oscilacao_relativa_e_magnitude(self):
        datas = pd.date_range("2026-06-29", periods=60, freq="D")
        historico = 100.0 + 0.01 * np.sin(np.arange(45))
        recente = 100.0 + np.array([0.35, -0.30, 0.40, -0.38, 0.36, -0.42, 0.39, -0.37, 0.41, -0.36, 0.38, -0.40, 0.37, -0.39, 0.40])
        resultado = analisar_serie(serie(datas, np.r_[historico, recente]), CORTE)
        self.assertIn(resultado["ruido_recente"], {"elevado", "severo"})
        # Ruido severo e prioritario; ruido elevado permanece em acompanhamento.
        esperado = (
            STATUS_REVISAO if resultado["ruido_recente"] == "severo" else STATUS_ACOMPANHAR
        )
        self.assertEqual(resultado["status_qaqc"], esperado)

    def test_automatico_com_mais_de_cinco_dias_sem_leitura(self):
        datas = pd.date_range("2026-07-20", periods=31, freq="D")
        resultado = analisar_serie(serie(datas, np.linspace(100, 99.8, len(datas))), CORTE)
        self.assertEqual(resultado["status_qaqc"], STATUS_SEM_ATUALIZACAO)
        self.assertTrue(pd.isna(resultado["cota_atual_representativa_m"]))

    def test_manual_repetido_e_valido_e_nao_e_flatline(self):
        datas = pd.to_datetime(["2025-08-25", "2026-05-20", "2026-06-20", "2026-07-20", "2026-08-20"])
        resultado = analisar_serie(serie(datas, [935.748] * 5, tipo="Medido Manual"), CORTE)
        self.assertEqual(resultado["status_qaqc"], STATUS_CONFORME)
        self.assertEqual(resultado["cota_atual_representativa_m"], 935.748)
        self.assertFalse(resultado["flatline_ativo"])

    # ------------------------------------------------------------------ v23.13
    def test_manual_com_campanha_fora_do_padrao_nao_vira_cota_atual(self):
        datas = pd.to_datetime([
            "2025-09-10", "2025-10-12", "2025-11-11", "2025-12-10",
            "2026-01-14", "2026-02-11", "2026-03-10", "2026-08-20",
        ])
        cotas = [100.00, 100.05, 99.98, 100.02, 100.06, 99.97, 100.03, 112.40]
        resultado = analisar_serie(serie(datas, cotas, tipo="Medido Manual"), CORTE)
        self.assertEqual(resultado["modo_monitoramento"], "Manual")
        self.assertIn("salto_manual_nao_confirmado", resultado["sinais_qaqc"])
        self.assertEqual(resultado["status_qaqc"], STATUS_ACOMPANHAR)
        self.assertTrue(pd.isna(resultado["cota_atual_representativa_m"]))

    def test_manual_campanha_isolada_e_descartada_e_serie_segue(self):
        datas = pd.to_datetime([
            "2025-09-10", "2025-10-12", "2025-11-11", "2025-12-10",
            "2026-01-14", "2026-02-11", "2026-06-10", "2026-07-15", "2026-08-20",
        ])
        cotas = [100.00, 100.05, 99.98, 100.02, 100.06, 99.97, 88.10, 100.01, 100.04]
        resultado = analisar_serie(serie(datas, cotas, tipo="Medido Manual"), CORTE)
        self.assertIn("salto_manual_isolado", resultado["sinais_qaqc"])
        self.assertAlmostEqual(resultado["cota_atual_representativa_m"], 100.04, places=2)

    def test_manual_sazonal_coerente_permanece_conforme(self):
        datas = pd.date_range("2025-09-15", periods=12, freq="30D")
        cotas = 100.0 + 1.5 * np.sin(np.linspace(0, 2 * np.pi, 12))
        resultado = analisar_serie(
            serie(datas[:-1].append(pd.DatetimeIndex([CORTE])), cotas, tipo="Medido Manual"),
            CORTE,
        )
        self.assertEqual(resultado["status_qaqc"], STATUS_CONFORME)
        self.assertFalse(pd.isna(resultado["cota_atual_representativa_m"]))

    def test_manual_no_mesmo_horario_do_automatico_nao_e_conflito(self):
        datas = pd.date_range("2026-08-01", periods=27, freq="D")
        auto = serie(datas, 100.0 + 0.01 * np.arange(27))
        conferencia = serie([datas[20]], [100.35], tipo="Medido Manual")
        preparada = preprocessar_serie(pd.concat([auto, conferencia]), CORTE)
        self.assertTrue(preparada.conflitos.empty)
        resultado = analisar_serie(pd.concat([auto, conferencia]), CORTE)
        self.assertNotIn("conflito_temporal", resultado["sinais_qaqc"])
        self.assertEqual(resultado["modo_monitoramento"], "Automático")

    def test_conflito_permanece_dentro_do_mesmo_tipo(self):
        datas = pd.date_range("2026-08-01", periods=27, freq="D")
        auto = serie(datas, 100.0 + 0.01 * np.arange(27))
        divergente = serie([datas[25]], [107.80])
        resultado = analisar_serie(pd.concat([auto, divergente]), CORTE)
        self.assertIn("conflito_temporal", resultado["sinais_qaqc"])

    def test_degrau_por_mudanca_de_boca_nao_vira_salto_de_na(self):
        datas = pd.date_range("2026-07-01", periods=58, freq="D")
        na = np.full(58, 30.0) + 0.01 * np.arange(58)
        boca = np.where(np.arange(58) < 40, 1000.0, 1008.5)
        dados = serie_fisica(datas, boca - na, cota_poco=list(boca))
        resultado = analisar_serie(dados, CORTE)
        self.assertIn("mudanca_referencia", resultado["sinais_qaqc"])
        self.assertNotIn("patamar", str(resultado["salto_tipo"]))
        self.assertAlmostEqual(resultado["salto_cota_boca_m"], 8.5, places=2)

    def test_delta_nao_compara_datums_diferentes(self):
        datas = pd.date_range("2025-08-01", periods=392, freq="D")
        # Variacao suave: sem ela a serie vira flatline e o teste nao chega ao Delta.
        na = 30.0 + 0.03 * np.sin(np.linspace(0, 12 * np.pi, 392))
        boca = np.where(datas < pd.Timestamp("2026-05-01"), 1000.0, 1000.9)
        resultado = analisar_serie(serie_fisica(datas, boca - na, cota_poco=list(boca)), CORTE)
        self.assertEqual(resultado["classificacao_12m"], CLASSIF_REFERENCIA_ALTERADA)
        self.assertTrue(pd.isna(resultado["delta_12m_m"]))
        self.assertTrue(resultado["referencia_alterada_12m"])

    def test_serie_inteira_fora_da_faixa_acusa_cadastro_nao_leituras(self):
        datas = pd.date_range("2026-06-01", periods=30, freq="3D")
        na = 35.0 + 0.05 * np.sin(np.arange(30))  # furo cadastrado com 32,75 m
        resultado = analisar_serie(
            serie_fisica(datas, 1044.38 - na, cota_poco=1044.38, tipo="Medido Manual"),
            CORTE,
            profundidade_m=32.75,
        )
        self.assertIn("profundidade_cadastro_suspeita", resultado["sinais_qaqc"])
        self.assertTrue(resultado["profundidade_cadastro_suspeita"])
        # As leituras permanecem: quem esta errado e o cadastro.
        self.assertFalse(pd.isna(resultado["cota_atual_representativa_m"]))
        self.assertNotEqual(resultado["status_qaqc"], STATUS_SEM_ATUALIZACAO)

    def test_na_abaixo_do_fundo_do_furo_e_descartado(self):
        datas = pd.date_range("2026-08-01", periods=27, freq="D")
        na = np.full(27, 20.0)
        na[24] = 95.0  # muito abaixo do fundo declarado
        resultado = analisar_serie(
            serie_fisica(datas, 1000.0 - na), CORTE, profundidade_m=50.0
        )
        self.assertEqual(resultado["leituras_fora_faixa"], 1)
        self.assertIn("fora_faixa_fisica", resultado["sinais_qaqc"])

    def test_na_acima_da_boca_e_sinalizado_mas_permanece(self):
        datas = pd.date_range("2026-08-01", periods=27, freq="D")
        na = np.full(27, 0.5)
        na[25] = -0.4  # artesianismo ou erro de sinal
        resultado = analisar_serie(
            serie_fisica(datas, 1000.0 - na), CORTE, profundidade_m=50.0
        )
        self.assertEqual(resultado["leituras_fora_faixa"], 1)
        self.assertIn("fora_faixa_fisica", resultado["sinais_qaqc"])
        self.assertFalse(pd.isna(resultado["ultima_leitura_cota_m"]))

    def test_dois_sinais_simultaneos_escalam_para_revisao(self):
        datas = pd.date_range("2026-07-01", periods=58, freq="D")
        na = np.full(58, 30.0)
        na[-1] = 29.0
        boca = np.where(np.arange(58) < 30, 1000.0, 1000.6)
        resultado = analisar_serie(serie_fisica(datas, boca - na, cota_poco=list(boca)), CORTE)
        self.assertGreaterEqual(len(set(resultado["sinais_qaqc"].split(" | "))), 2)
        self.assertEqual(resultado["status_qaqc"], STATUS_REVISAO)
        self.assertTrue(resultado["motivo_priorizacao"])
        self.assertTrue(str(resultado["motivos"]).startswith("Revisão recomendada"))

    def test_flatline_curto_nao_escala_para_revisao(self):
        datas = pd.date_range("2026-08-14", periods=14, freq="D")
        cotas = np.r_[100.0 + 0.02 * np.arange(8), np.full(6, 100.14)]
        resultado = analisar_serie(serie(datas, cotas), CORTE)
        self.assertEqual(resultado["status_qaqc"], STATUS_ACOMPANHAR)
        self.assertLess(resultado["dias_flatline"], 15)

    def test_override_de_situacao_vem_da_configuracao(self):
        overrides = carregar_overrides_situacao(ROOT / "config")
        self.assertEqual(overrides.get("G00-11PTR006"), "Tamponado")

    def test_override_le_csv_gravado_em_codificacao_windows(self):
        import tempfile

        linhas = (
            "instrumento,situacao,justificativa\n"
            'G00-11PTR006,Tamponado,"Exceção operacional aprovada"\n'
        )
        for codificacao in ("utf-8", "utf-8-sig", "cp1252", "utf-16"):
            with tempfile.TemporaryDirectory() as tmp:
                destino = Path(tmp) / "situacao_override.csv"
                destino.write_text(linhas, encoding=codificacao)
                overrides = carregar_overrides_situacao(tmp)
                self.assertEqual(
                    overrides.get("G00-11PTR006"), "Tamponado", msg=codificacao
                )

    def test_override_ausente_mantem_contingencia(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                carregar_overrides_situacao(tmp).get("G00-11PTR006"), "Tamponado"
            )

    def test_sem_referencia_nao_inventa_delta(self):
        datas = pd.date_range("2026-08-10", periods=18, freq="D")
        cotas = 100.0 + 0.01 * np.sin(np.arange(len(datas)))
        resultado = analisar_serie(serie(datas, cotas), CORTE)
        self.assertTrue(pd.isna(resultado["cota_referencia_12m_m"]))
        self.assertTrue(pd.isna(resultado["delta_12m_m"]))

    def test_horario_com_cotas_diferentes_e_acompanhado_sem_escolha(self):
        datas = list(pd.date_range("2026-08-20", periods=8, freq="D"))
        dados = serie(datas, np.linspace(100, 99.9, 8))
        conflito = serie([CORTE, CORTE], [98.0, 102.0])
        resultado = analisar_serie(pd.concat([dados, conflito], ignore_index=True), CORTE)
        self.assertEqual(resultado["status_qaqc"], STATUS_ACOMPANHAR)
        self.assertTrue(resultado["conflito_recente"])
        self.assertTrue(pd.isna(resultado["cota_atual_representativa_m"]))


class HGARealValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resultado = pd.read_csv(ROOT / "out" / "analise_delta_cota.csv")
        cls.resultado["instrumento"] = cls.resultado["instrumento"].astype(str)

    def ponto(self, nome: str) -> pd.Series:
        return self.resultado[self.resultado["instrumento"].eq(nome)].iloc[0]

    def test_casos_reais_principais(self):
        self.assertEqual(self.ponto("0027-INA-018")["status_qaqc"], STATUS_CONFORME)
        self.assertEqual(self.ponto("0027-INA-054")["sinais_qaqc"], "flatline")
        self.assertIn("pos_flatline", self.ponto("0027-INA-034")["sinais_qaqc"])
        self.assertIn("salto_isolado", self.ponto("0027-INA-107")["sinais_qaqc"])
        self.assertIn("patamar_nao_confirmado", self.ponto("30LI008")["sinais_qaqc"])
        self.assertEqual(self.ponto("0028-INA-086")["salto_tipo"], "patamar_confirmado")

    def test_reducao_sustentada_real_permanece_conforme(self):
        ponto = self.ponto("0029-INA-097")
        self.assertEqual(ponto["status_qaqc"], STATUS_CONFORME)
        self.assertLess(float(ponto["delta_90d_m"]), -2.0)

    def test_manual_repetido_real_permanece_conforme(self):
        ponto = self.ponto("0027-INA-130")
        self.assertEqual(ponto["modo_monitoramento"], "Manual")
        self.assertEqual(ponto["status_qaqc"], STATUS_CONFORME)
        self.assertEqual(float(ponto["delta_12m_m"]), 0.0)

    def test_sem_atualizacao_e_sem_referencia_real(self):
        self.assertEqual(self.ponto("0029-INA-133")["status_qaqc"], STATUS_SEM_ATUALIZACAO)
        self.assertTrue(self.resultado["delta_12m_m"].isna().any())
        self.assertTrue(self.resultado["delta_90d_m"].isna().any())

    def test_ruido_e_pontos_sem_delta_sao_preservados(self):
        self.assertTrue(self.resultado["ruido_recente"].notna().any())
        app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn("INA/PZ/PM sem comparação no período", app)
        self.assertIn('neutros = base[base["delta_m"].isna()]', app)

    def test_interface_corporativa_preserva_dados_essenciais(self):
        app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn("Dados da comparação", app)
        self.assertIn("Última cota (m)", app)
        self.assertIn("Cota atual (m)", app)
        self.assertIn("Referência (m)", app)
        self.assertIn("Δ Cota (m)", app)
        self.assertIn("Confiabilidade", app)
        self.assertIn("Instrumentos para acompanhamento", app)
        self.assertIn("Detalhes técnicos", app)
        self.assertIn('HOME_CAPA = ASSETS / "home_complexo_germano.png"', app)
        self.assertIn("background-position: center top", app)
        self.assertNotIn("home-crosshair", app)
        self.assertIn("DELTA_COTA_AJUDA", app)
        self.assertIn("REFERENCIA_AJUDA", app)
        self.assertIn("QAQC_AJUDA", app)
        self.assertIn("Condicionantes ICMBio", app)
        self.assertIn('with st.expander("Condicionantes ICMBio", expanded=False):', app)
        self.assertNotIn('name="Condicionante ICMBio"', app)
        self.assertIn('name="INA/PZ/PM sem comparação no período",\n            showlegend=False', app)
        self.assertIn('.kpi.down { border-top: 4px solid var(--down); }', app)
        self.assertIn('.kpi.up { border-top: 4px solid var(--up); }', app)
        self.assertIn('.kpi.ok { border-top: 4px solid #527800; }', app)
        self.assertIn('.kpi.warn { border-top: 4px solid #876D00; }', app)
        self.assertIn('.kpi.danger { border-top: 4px solid #245D86; }', app)
        self.assertIn('.kpi.info { border-top: 4px solid var(--navy); }', app)
        self.assertIn("help=ajuda_cota_atual", app)
        self.assertIn("help=REFERENCIA_AJUDA", app)
        self.assertNotIn('with st.popover("?", help=f"Sobre {title}")', app)
        self.assertNotIn("Situação — por que está assim", app)
        self.assertNotIn("Ação recomendada", app)

    def test_sintese_operacional_contem_apenas_instrumentos_ativos(self):
        data_corte = pd.to_datetime(self.resultado["data_corte"], errors="coerce").max()
        sintese = filtrar_ativos_com_leitura_no_ano(self.resultado, data_corte)
        situacao = sintese["situacao_operacional"].astype(str).str.strip().str.casefold()
        ultima = pd.to_datetime(sintese["ultima"], errors="coerce")
        self.assertTrue(situacao.eq("ativo").all())
        self.assertTrue(ultima.dt.year.eq(data_corte.year).all())
        self.assertNotIn("0027-INA-113", set(sintese["instrumento"]))
        instrumentos_nivel = sintese[
            sintese["natureza"].astype(str).str.strip().isin(
                ["INA", "Piezometro", "Piezômetro", "Poco Monitoramento", "Poço Monitoramento"]
            )
        ]
        self.assertEqual(len(instrumentos_nivel), 121)
        # 87 e nao 88 desde a v23.13: o QA/QC manual bloqueou a cota atual de
        # 1336-PM-013, cuja campanha mais recente ficou fora do padrao e ainda
        # nao foi confirmada por campanha posterior.
        self.assertEqual(
            pd.to_numeric(instrumentos_nivel["delta_12m_m"], errors="coerce").notna().sum(),
            87,
        )
        self.assertSetEqual(
            set(instrumentos_nivel["natureza"]),
            {"INA", "Piezometro", "Poco Monitoramento"},
        )
        app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn("Última leitura", app)
        self.assertIn("Detalhes de confiabilidade", app)
        self.assertIn("Possível travamento das leituras (flatline)", app)
        self.assertIn("Leitura isolada do padrão (possível outlier)", app)
        self.assertNotIn("<strong>Fonte:</strong>", app)

    def test_home_index_e_a_pagina_inicial(self):
        app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn('PAGINA_HOME = "Início"', app)
        self.assertIn(
            'PAGINAS_CONTEUDO = [\n'
            '    "Resultados",\n'
            '    "Confiabilidade dos dados",\n'
            '    "Explorar instrumento",\n'
            '    "Avaliação técnica",\n'
            '    "Metodologia",\n'
            ']',
            app,
        )
        self.assertIn('st.session_state["pagina_ativa"] = PAGINA_HOME', app)
        self.assertIn('(\"01\", \"Resultados\")', app)
        self.assertIn('(\"02\", \"Confiabilidade dos dados\")', app)
        self.assertIn('(\"03\", \"Explorar instrumento\")', app)
        self.assertIn('(\"04\", \"Avaliação técnica\")', app)
        self.assertIn('(\"05\", \"Metodologia\")', app)
        self.assertIn('<div class=\"home-title\">Visão geral</div>', app)
        self.assertNotIn('default="Avaliação técnica"', app)


if __name__ == "__main__":
    unittest.main()
