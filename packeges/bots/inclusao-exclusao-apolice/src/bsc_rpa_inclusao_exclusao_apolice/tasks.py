import logging

import pandas as pd
from playwright.sync_api import Page
from bsc_rpa_core.reporting import task

from .steps import (
    # Playwright
    acessar_frota_total,
    acessar_importacao_exportacao,
    acessar_menu_endossos,
    acessar_modulo_relatorios,
    acessar_modulo_seguros,
    acessar_portal,
    baixar_frota_total,
    clicar_confirmar,
    executar_exportacoes_apolice,
    exportar_relatorio,
    preencher_login,
    validar_login,
    # Planilhas
    buscar_arquivos_downloads,
    carregar_planilha,
    processar_apolice_endosso,
    processar_exportacao_exclusao,
    processar_exportacao_inclusao,
    mover_para_processados,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PLAYWRIGHT — tasks de extração
# =============================================================================

@task(
    record_args=("url", "username"),
    record_out=False,
)
def realizar_login(page: Page, url: str, username: str, password: str) -> None:
    logger.debug(f"Iniciando login | url={url!r} username={username!r}")
    acessar_portal(page, url)
    preencher_login(page, username, password)
    clicar_confirmar(page)
    validar_login(page)
    logger.debug(f"Login realizado | username={username!r}")


def baixar_relatorio_endossos(page: Page, base_url: str) -> None:
    logger.debug("Acessando módulo Seguros")
    acessar_modulo_seguros(page)

    logger.debug("Acessando menu Apólice Endosso")
    acessar_menu_endossos(page)

    logger.debug("Exportando relatório de endossos")
    arquivo = exportar_relatorio(page)
    logger.debug(f"Download: {arquivo}")

    logger.debug("Acessando Importação / Exportação Dados da Apólice")
    acessar_importacao_exportacao(page)

    logger.debug("Executando exportações (Inclusão e Exclusão)")
    arquivos = executar_exportacoes_apolice(page)
    logger.debug(f"Arquivos gerados: {arquivos}")


def baixar_relatorio_frota_total(page: Page, base_url: str) -> None:
    logger.debug("Acessando módulo Relatórios")
    acessar_modulo_relatorios(page)

    logger.debug("Acessando Frota Total")
    acessar_frota_total(page)

    logger.debug("Baixando arquivo de Frota Total")
    arquivo = baixar_frota_total(page)
    logger.debug(f"Arquivo baixado: {arquivo}")

    page.locator("#HEADER_MPAGE").click()


# =============================================================================
# PLANILHAS — tasks de processamento
# =============================================================================

def carregar_planilhas(pasta_downloads: str) -> dict:
    """
    Localiza e carrega os 4 arquivos da pasta de downloads.
    Retorna dict com DataFrames: endosso, frota, exp_inc, exp_exc.
    """
    logger.info(f"Buscando arquivos em: {pasta_downloads}")
    caminhos = buscar_arquivos_downloads(pasta_downloads)

    logger.info(f"Endosso:        {caminhos['endosso']}")
    logger.info(f"Frota Total:    {caminhos['frota']}")
    logger.info(f"Exp Inclusão:   {caminhos['exp_inc']}")
    logger.info(f"Exp Exclusão:   {caminhos['exp_exc']}")

    # Apólice Endosso — header na linha 4 (coluna chave: Placa)
    df_endosso = carregar_planilha(caminhos["endosso"], "Placa")

    # Frota Total — header na linha 1 (coluna chave: Placa)
    df_frota = carregar_planilha(caminhos["frota"], "Placa")

    # Exportação Inclusão — header na linha 1 (coluna chave: Placa)
    df_exp_inc = carregar_planilha(caminhos["exp_inc"], "Placa")

    # Exportação Exclusão — header na linha 1 (coluna chave: Chassi)
    df_exp_exc = carregar_planilha(caminhos["exp_exc"], "Chassi")

    logger.info(
        f"Planilhas carregadas | "
        f"endosso={df_endosso.shape} frota={df_frota.shape} "
        f"exp_inc={df_exp_inc.shape} exp_exc={df_exp_exc.shape}"
    )

    return {
        "endosso": df_endosso,
        "frota": df_frota,
        "exp_inc": df_exp_inc,
        "exp_exc": df_exp_exc,
        "caminhos": caminhos,
    }


def processar_planilhas(dados: dict) -> dict:
    """
    Executa todo o processamento de negócio:
      1. Separar Apólice Endosso em Inclusão / Exclusão (com dedup por data).
      2. Processar Exportação Inclusão (status + filtros + divergências).
      3. Processar Exportação Exclusão (placa via chassi + status + filtros + divergências).

    Retorna dict com os DataFrames finais e lista consolidada de divergências.
    """
    df_endosso = dados["endosso"]
    df_frota = dados["frota"]
    df_exp_inc = dados["exp_inc"]
    df_exp_exc = dados["exp_exc"]

    # 1. Apólice Endosso
    logger.info("Processando Apólice Endosso")
    df_apolice_inc, df_apolice_exc = processar_apolice_endosso(df_endosso)

    # 2. Exportação Inclusão
    logger.info("Processando Exportação Inclusão")
    df_final_inc, diverg_inc = processar_exportacao_inclusao(
        df_exp_inc, df_apolice_inc, df_frota
    )

    # 3. Exportação Exclusão
    logger.info("Processando Exportação Exclusão")
    df_final_exc, diverg_exc = processar_exportacao_exclusao(
        df_exp_exc, df_apolice_exc, df_frota
    )

    todas_divergencias = diverg_inc + diverg_exc

    if todas_divergencias:
        logger.warning(f"Total de divergências encontradas: {len(todas_divergencias)}")
    else:
        logger.info("Nenhuma divergência encontrada")

    return {
        "df_inclusao": df_final_inc,
        "df_exclusao": df_final_exc,
        "df_apolice_endosso": df_endosso,
        "divergencias": todas_divergencias,
    }
