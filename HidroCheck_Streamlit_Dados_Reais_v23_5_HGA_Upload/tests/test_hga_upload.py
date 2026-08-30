from __future__ import annotations

from io import BytesIO
import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hga_upload import (  # noqa: E402
    HGAUploadError,
    MENSAGEM_ARQUIVO_INVALIDO,
    executar_com_fallback_padrao,
    ler_validar_hga_xlsx,
    processar_upload_hga,
)


def cadastro_teste() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "TAG HGA": ["TESTE-INA-001"],
            "Nome Original": ["TESTE-INA-001"],
            "Natureza do Ponto": ["INA"],
            "Situacao Atual": ["Ativo"],
            "Proposito": ["Monitoramento Hidrogeologico"],
            "Localidade": ["Teste"],
            "X(m)": [655000.0],
            "Y(m)": [7765000.0],
            "Profundidade(m)": [100.0],
        }
    )


def hga_teste(cota_atual: float = 100.0, data_atual: str = "2026-08-27") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Ponto": ["TESTE-INA-001", "TESTE-INA-001"],
            "Natureza do Ponto": ["INA", "INA"],
            "Situacao Atual": ["Ativo", "Ativo"],
            "Data": pd.to_datetime(["2025-08-27", data_atual]),
            "Tipo_Dado": ["Medido Manual", "Medido Manual"],
            "Cota_NA_m": [101.0, cota_atual],
        }
    )


def xlsx_em_memoria(dados: pd.DataFrame) -> bytes:
    arquivo = BytesIO()
    with pd.ExcelWriter(arquivo, engine="openpyxl") as writer:
        dados.to_excel(writer, sheet_name="Sheet1", index=False)
    return arquivo.getvalue()


class HGAUploadTest(unittest.TestCase):
    def test_upload_valido(self):
        resultado = processar_upload_hga(
            xlsx_em_memoria(hga_teste()),
            "HGA-atualizada.xlsx",
            cadastro_teste(),
        )
        self.assertEqual(resultado.data_corte, pd.Timestamp("2026-08-27"))
        self.assertEqual(len(resultado.rede), 1)
        self.assertAlmostEqual(float(resultado.rede.iloc[0]["delta_12m_m"]), -1.0)

    def test_arquivo_sem_coluna_obrigatoria(self):
        dados = hga_teste().drop(columns="Situacao Atual")
        with self.assertRaises(HGAUploadError):
            ler_validar_hga_xlsx(xlsx_em_memoria(dados), "HGA.xlsx")

    def test_arquivo_corrompido_ou_ilegivel(self):
        with self.assertRaises(HGAUploadError):
            ler_validar_hga_xlsx(b"isto nao e uma planilha", "HGA.xlsx")

    def test_base_sem_linhas_validas(self):
        dados = hga_teste()
        dados["Data"] = "sem data"
        dados["Cota_NA_m"] = "sem cota"
        with self.assertRaises(HGAUploadError):
            ler_validar_hga_xlsx(xlsx_em_memoria(dados), "HGA.xlsx")

    def test_fallback_para_base_padrao(self):
        padrao = hga_teste(cota_atual=100.0)
        corte, usando_padrao, mensagem = executar_com_fallback_padrao(
            b"arquivo corrompido",
            "HGA.xlsx",
            padrao,
            lambda hga: pd.to_datetime(hga["Data"], errors="coerce").max().normalize(),
        )
        self.assertTrue(usando_padrao)
        self.assertEqual(corte, pd.Timestamp("2026-08-27"))
        self.assertEqual(mensagem, MENSAGEM_ARQUIVO_INVALIDO)

    def test_erro_durante_processamento_tambem_usa_fallback(self):
        padrao = hga_teste(cota_atual=99.0)

        def processador(hga: pd.DataFrame) -> float:
            atual = pd.to_numeric(hga.iloc[-1].get("cota_na_m", hga.iloc[-1].get("Cota_NA_m")))
            if atual == 100.0:
                raise RuntimeError("falha simulada")
            return float(atual)

        valor, usando_padrao, _ = executar_com_fallback_padrao(
            xlsx_em_memoria(hga_teste(cota_atual=100.0)),
            "HGA.xlsx",
            padrao,
            processador,
        )
        self.assertTrue(usando_padrao)
        self.assertEqual(valor, 99.0)

    def test_data_de_corte_e_atualizada_pelos_dados(self):
        resultado = processar_upload_hga(
            xlsx_em_memoria(hga_teste(data_atual="2026-09-03")),
            "qualquer-nome.xlsx",
            cadastro_teste(),
        )
        self.assertEqual(resultado.data_corte, pd.Timestamp("2026-09-03"))

    def test_calculos_mudam_quando_a_hga_muda(self):
        cadastro = cadastro_teste()
        base_a = processar_upload_hga(
            xlsx_em_memoria(hga_teste(cota_atual=100.0)), "HGA-A.xlsx", cadastro
        )
        base_b = processar_upload_hga(
            xlsx_em_memoria(hga_teste(cota_atual=98.0)), "HGA-B.xlsx", cadastro
        )
        delta_a = float(base_a.rede.iloc[0]["delta_12m_m"])
        delta_b = float(base_b.rede.iloc[0]["delta_12m_m"])
        self.assertEqual(delta_a, -1.0)
        self.assertEqual(delta_b, -3.0)
        self.assertNotEqual(delta_a, delta_b)


if __name__ == "__main__":
    unittest.main()
