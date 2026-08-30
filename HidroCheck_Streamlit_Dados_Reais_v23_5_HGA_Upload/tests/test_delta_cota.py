from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from delta_cota import (  # noqa: E402
    STATUS_ACOMPANHAR,
    STATUS_CONFORME,
    STATUS_SEM_ATUALIZACAO,
    analisar_serie,
    classificar_modo_monitoramento,
    filtrar_ativos_com_leitura_no_ano,
    inferir_data_corte,
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
        self.assertEqual(resultado["status_qaqc"], STATUS_ACOMPANHAR)

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

    def test_interface_explica_comparacao_e_situacao(self):
        app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn("Situação — por que está assim", app)
        self.assertIn("Ação recomendada", app)
        self.assertIn("Último dado disponível", app)
        self.assertIn("Última cota registrada (m)", app)
        self.assertIn("Situação dos instrumentos ativos em", app)
        self.assertIn("pelo menos uma leitura válida em", app)
        self.assertIn("Itens ativos em", app)
        self.assertIn("instrumentos ativos com leitura válida em", app)
        self.assertIn("INA, PZ e PM ativos no ano", app)
        self.assertIn("Os três tipos participam do cálculo de Δ Cota", app)
        self.assertIn("possuem cota atual representativa e", app)

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
        self.assertEqual(
            pd.to_numeric(instrumentos_nivel["delta_12m_m"], errors="coerce").notna().sum(),
            88,
        )
        self.assertSetEqual(
            set(instrumentos_nivel["natureza"]),
            {"INA", "Piezometro", "Poco Monitoramento"},
        )
        app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn("Data da última leitura", app)
        self.assertIn("não é valor zero e não torna o instrumento inválido", app)
        self.assertIn("Possível travamento das leituras (flatline)", app)
        self.assertIn("Leitura isolada do padrão (possível outlier)", app)
        self.assertNotIn("<strong>Fonte:</strong>", app)

    def test_avaliacao_tecnica_e_a_pagina_inicial(self):
        app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn('paginas = [\n    "Avaliação técnica",\n    "Resultados"', app)
        self.assertIn('default="Avaliação técnica"', app)
        self.assertIn(') or "Avaliação técnica"', app)


if __name__ == "__main__":
    unittest.main()
