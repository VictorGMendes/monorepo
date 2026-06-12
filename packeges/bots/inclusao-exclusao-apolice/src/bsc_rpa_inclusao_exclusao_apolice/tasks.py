import logging

from playwright.sync_api import Page
from bsc_rpa_core.reporting import task

from .steps import (
    acessar_frota_total,
    acessar_menu_endossos,
    acessar_modulo_relatorios,
    acessar_modulo_seguros,
    acessar_portal,
    baixar_frota_total,
    executar_exportacoes_apolice,
    exportar_relatorio,
    preencher_login,
    clicar_confirmar,
    validar_login,
    acessar_importacao_exportacao
    
)

logger = logging.getLogger(__name__)


@task(
    record_args=("base_url", "username"),
    record_out=False,
)
def realizar_login(
    page: Page,
    url: str,
    username: str,
    password: str,
) -> None:
    logger.debug(
        f"Iniciando login com url={url!r}, username={username!r}"
    )

    acessar_portal(page, url)
    preencher_login(page, username, password)
    clicar_confirmar(page)
    validar_login(page)

    logger.debug(
        f"Login realizado com sucesso para username={username!r}"
    )



def baixar_relatorio_endossos(page: Page, base_url: str):
    logger.debug("Entrando no módulo Seguros")

    acessar_modulo_seguros(page)

    logger.debug("Acessando menu de endossos")

    acessar_menu_endossos(page)

    logger.debug("Exportando relatório")

    arquivo = exportar_relatorio(page)

    logger.debug(f"Download realizado: {arquivo}")
    
    logger.debug("Indo para tela de importação/exportação")

    acessar_importacao_exportacao(page)
    
    logger.debug("Executando exportação da apólice")

    
    logger.debug("Executando exportações da apólice")

    arquivos = executar_exportacoes_apolice(page)

    logger.debug(f"Arquivos gerados: {arquivos}")




def baixar_relatorio_frota_total(page: Page, base_url: str):
    logger.debug("Entrando no módulo Relatórios")

    acessar_modulo_relatorios(page)

    logger.debug("Acessando Frota Total (com fallback de ambiente)")

    acessar_frota_total(page)

    logger.debug("Baixando último arquivo de Frota Total")

    arquivo = baixar_frota_total(page)

    logger.debug(f"Arquivo baixado: {arquivo}")

    # volta para o menu
    page.locator("#HEADER_MPAGE").click()



def tratar_inclusao(df_inclusao, df_frota):
    logger.info("Iniciando tratamento de inclusão")

    df_frota["placa"] = df_frota["placa"].astype(str).str.strip().str.upper()

    df = df_inclusao.merge(
        df_frota[["placa", "Status Veículo Contrato"]],
        on="placa",
        how="left"
    )

    logger.info(f"Após merge inclusão: {len(df)} registros")

    df = df[
        (df["Status Veículo Contrato"].notna()) &
        (df["Status Veículo Contrato"] != "Devolvido")
    ]

    logger.info(f"Inclusões válidas após filtro: {len(df)} registros")

    return df


def tratar_exclusao(df_exclusao, df_frota):
    logger.info("Iniciando tratamento de exclusão")

    df_frota["placa"] = df_frota["placa"].astype(str).str.strip().str.upper()

    df = df_exclusao.merge(
        df_frota[["placa", "Status Veículo Contrato"]],
        on="placa",
        how="left"
    )

    logger.info(f"Após merge exclusão: {len(df)} registros")

    df = df[
        (df["Status Veículo Contrato"].notna()) &
        (df["Status Veículo Contrato"] != "Ativo")
    ]

    logger.info(f"Exclusões válidas após filtro: {len(df)} registros")

    return df

def tratar_exportacao_inclusao(df_exp, df_apolice_inc, df_frota):
    logger.info("Tratando exportação inclusão")

    df_exp["placa"] = df_exp["placa"].astype(str).str.strip().str.upper()

    # remover duplicados
    df_exp = df_exp.drop_duplicates(subset=["placa"])

    # cruzar com frota (status)
    df = df_exp.merge(
        df_frota[["placa", "Status Veículo Contrato"]],
        on="placa",
        how="left"
    )

    # manter só placas da apólice inclusão
    placas_validas = df_apolice_inc["placa"].unique()

    df = df[df["placa"].isin(placas_validas)]

    # remover devolvido / vazio
    df = df[
        (df["Status Veículo Contrato"].notna()) &
        (df["Status Veículo Contrato"] != "Devolvido")
    ]

    logger.info(f"Inclusão final: {len(df)} registros")
    return df

def tratar_exportacao_exclusao(df_exp_exc, df_apolice_exc, df_frota):
    logger.info("Tratando exportação exclusão")

    # ➜ merge por chassi → pegar placa
    df = df_exp_exc.merge(
        df_frota[["Chassi", "placa"]],
        on="Chassi",
        how="left"
    )

    # remover sem placa
    df = df[df["placa"].notna()]

    df["placa"] = df["placa"].astype(str).str.strip().str.upper()

    # remover duplicados
    df = df.drop_duplicates(subset=["placa"])

    # status
    df = df.merge(
        df_frota[["placa", "Status Veículo Contrato"]],
        on="placa",
        how="left"
    )

    # limitar ao que existe na apólice exclusão
    placas_validas = df_apolice_exc["placa"].unique()
    df = df[df["placa"].isin(placas_validas)]

    # remover ativo / vazio
    df = df[
        (df["Status Veículo Contrato"].notna()) &
        (df["Status Veículo Contrato"] != "Ativo")
    ]

    logger.info(f"Exclusão final: {len(df)} registros")
    return df