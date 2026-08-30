from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable, TypeVar

import pandas as pd

from delta_cota import (
    TIPO_AUTOMATICO,
    TIPO_MANUAL,
    _aplicar_situacao_hga,
    _filtrar_complexo_germano,
    _norm_tag,
    diagnosticar_dataframes,
    inferir_data_corte,
    normalizar_hga,
)


COLUNAS_HGA_OBRIGATORIAS = frozenset(
    {
        "Ponto",
        "Natureza do Ponto",
        "Situacao Atual",
        "Data",
        "Tipo_Dado",
        "Cota_NA_m",
    }
)

MENSAGEM_ARQUIVO_INVALIDO = (
    "Arquivo não reconhecido. Verifique se foi utilizada a estrutura padrão da HGA."
)


class HGAUploadError(ValueError):
    """Erro de validação controlado; os detalhes não são exibidos na interface."""


@dataclass
class BaseHGAProcessada:
    cadastro: pd.DataFrame
    hga: pd.DataFrame
    rede: pd.DataFrame
    eventos: pd.DataFrame
    data_corte: pd.Timestamp
    usando_padrao: bool = False
    mensagem: str | None = None


def _conteudo_em_bytes(conteudo: bytes | bytearray | memoryview | object) -> bytes:
    if isinstance(conteudo, bytes):
        return conteudo
    if isinstance(conteudo, (bytearray, memoryview)):
        return bytes(conteudo)
    if hasattr(conteudo, "getvalue"):
        valor = conteudo.getvalue()
        if isinstance(valor, bytes):
            return valor
    if hasattr(conteudo, "read"):
        valor = conteudo.read()
        if isinstance(valor, bytes):
            return valor
    raise HGAUploadError(MENSAGEM_ARQUIVO_INVALIDO)


def ler_validar_hga_xlsx(
    conteudo: bytes | bytearray | memoryview | object,
    nome_arquivo: str | None = None,
) -> pd.DataFrame:
    """Lê e valida uma HGA completa sem gravar o arquivo enviado em disco."""
    if nome_arquivo and Path(nome_arquivo).suffix.casefold() != ".xlsx":
        raise HGAUploadError(MENSAGEM_ARQUIVO_INVALIDO)

    dados = _conteudo_em_bytes(conteudo)
    if not dados:
        raise HGAUploadError(MENSAGEM_ARQUIVO_INVALIDO)

    try:
        hga = pd.read_excel(BytesIO(dados), sheet_name="Sheet1", engine="openpyxl")
    except Exception as exc:
        raise HGAUploadError(MENSAGEM_ARQUIVO_INVALIDO) from exc

    ausentes = COLUNAS_HGA_OBRIGATORIAS.difference(hga.columns)
    if ausentes or hga.empty:
        raise HGAUploadError(MENSAGEM_ARQUIVO_INVALIDO)

    normalizada = normalizar_hga(hga)
    ponto_util = normalizada["Ponto"].astype("string").fillna("").str.strip().ne("")
    tipo_util = normalizada["tipo_dado"].isin([TIPO_AUTOMATICO, TIPO_MANUAL])
    linha_util = (
        ponto_util
        & normalizada["data"].notna()
        & normalizada["cota_na_m"].notna()
        & tipo_util
    )
    if not linha_util.any():
        raise HGAUploadError(MENSAGEM_ARQUIVO_INVALIDO)

    try:
        inferir_data_corte(normalizada)
    except Exception as exc:
        raise HGAUploadError(MENSAGEM_ARQUIVO_INVALIDO) from exc
    return normalizada


def preparar_hga_para_cadastro(
    cadastro: pd.DataFrame,
    hga: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    """Aplica à HGA dinâmica o mesmo catálogo e escopo espacial da versão padrão."""
    cad = cadastro.copy()
    if "inst_id" not in cad.columns:
        cad["inst_id"] = cad["TAG HGA"].map(_norm_tag)
    cad = _filtrar_complexo_germano(cad)

    dados = normalizar_hga(hga)
    ids_catalogo = set(cad["inst_id"].dropna().astype(str))
    dados = dados[dados["inst_id"].isin(ids_catalogo)].copy()
    data_corte = inferir_data_corte(dados)
    cad = _aplicar_situacao_hga(cad, dados, data_corte)
    return cad, dados, data_corte


def processar_hga(cadastro: pd.DataFrame, hga: pd.DataFrame) -> BaseHGAProcessada:
    """Recalcula integralmente a rede em memória usando uma única fonte HGA."""
    cad, dados, data_corte = preparar_hga_para_cadastro(cadastro, hga)
    rede, eventos = diagnosticar_dataframes(cad, dados)
    if rede.empty:
        raise HGAUploadError(MENSAGEM_ARQUIVO_INVALIDO)
    return BaseHGAProcessada(
        cadastro=cad,
        hga=dados,
        rede=rede,
        eventos=eventos,
        data_corte=pd.Timestamp(data_corte).normalize(),
    )


def processar_upload_hga(
    conteudo: bytes | bytearray | memoryview | object,
    nome_arquivo: str,
    cadastro: pd.DataFrame,
) -> BaseHGAProcessada:
    hga = ler_validar_hga_xlsx(conteudo, nome_arquivo)
    return processar_hga(cadastro, hga)


T = TypeVar("T")


def executar_com_fallback_padrao(
    conteudo: bytes | bytearray | memoryview | object,
    nome_arquivo: str,
    hga_padrao: pd.DataFrame,
    processador: Callable[[pd.DataFrame], T],
) -> tuple[T, bool, str | None]:
    """Executa o upload e, diante de qualquer falha, retorna o processamento padrão."""
    try:
        hga = ler_validar_hga_xlsx(conteudo, nome_arquivo)
        return processador(hga), False, None
    except Exception:
        return processador(hga_padrao.copy()), True, MENSAGEM_ARQUIVO_INVALIDO
