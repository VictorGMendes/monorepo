import logging
import argparse
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from bsc_rpa_core.logs import configure_logging, log_func_call
from bsc_rpa_core.reporting import start_run

from bsc_rpa_adapter_outlook import Win32Outlook
from bsc_rpa_adapter_playwright import PlaywrightSession

from .config import Config, NOTIF_BODY_CONFIG
from .tasks import (
    realizar_login,
    baixar_relatorio_endossos,
    baixar_relatorio_frota_total,
    carregar_planilhas,
    processar_planilhas,
)
from .steps import mover_para_processados

logger = logging.getLogger(__name__)


def cli():
    parser = argparse.ArgumentParser(
        prog="RPA inclusao_exclusao_apolice",
        description="RPA inclusao_exclusao_apolice — extração e processamento de apólices GM Fleet",
    )
    parser.add_argument(
        "--config", "-c",
        help="Caminho para o arquivo de configuração. Padrão: 'config.yaml'.",
        required=False,
    )
    args = parser.parse_args()

    config_path = args.config or "config.yaml"
    config = Config.load(config_path)

    config.io.log_folder.mkdir(exist_ok=True, parents=True)
    log_path = config.io.log_folder / Path("log.jsonl")

    configure_logging(log_path.as_posix())

    main(config)


@log_func_call(logger, logging.INFO)
def main(config: Config):

    with (
        Win32Outlook() as outlook,
        PlaywrightSession(
            screenshot_folder=config.io.screenshot_folder.as_posix(),
            headless=config.playwright.headless,
            default_timeout_ms=config.playwright.timeout_ms,
            trace=config.playwright.trace,
        ) as pw,
        start_run(
            "bsc-rpa-inclusao_exclusao_apolice",
            config.reporting,
            NOTIF_BODY_CONFIG,
            None,
            # outlook  # descomentar para envio de e-mail
        ),
    ):
        # -----------------------------------------------------------------
        # ETAPA 1 — Extração via Playwright (comentar para rodar só planilhas)
        # -----------------------------------------------------------------
        # page = pw.new_page()

        # realizar_login(
        #     page,
        #     config.gmfleet.base_url,
        #     config.gmfleet.username,
        #     config.gmfleet.password,
        # )

        # baixar_relatorio_endossos(page, config.gmfleet.base_url)
        # baixar_relatorio_frota_total(page, config.gmfleet.base_url)

        # -----------------------------------------------------------------
        # ETAPA 2 — Processamento das planilhas
        # -----------------------------------------------------------------
        base_dir = os.getcwd()
        pasta_downloads = os.path.join(base_dir, "downloads")
        pasta_processados = os.path.join(base_dir, "processados")

        # 2.1 Carregar
        dados = carregar_planilhas(pasta_downloads)

        # 2.2 Processar
        resultado = processar_planilhas(dados)

        df_inclusao      = resultado["df_inclusao"]
        df_exclusao      = resultado["df_exclusao"]
        df_apolice_endosso = resultado["df_apolice_endosso"]
        divergencias     = resultado["divergencias"]

        # 2.3 Logar divergências
        if divergencias:
            logger.warning("=" * 60)
            logger.warning("DIVERGÊNCIAS ENCONTRADAS:")
            for d in divergencias:
                logger.warning(f"  {d}")
            logger.warning("=" * 60)
        else:
            logger.info("Nenhuma divergência encontrada entre Apólice e Exportações.")

        # 2.4 Gerar arquivo de saída
        hoje = datetime.now()
        nome_arquivo = f"Inclusao_{hoje.month}_{hoje.year}.xlsx"
        caminho_saida = os.path.join(base_dir, nome_arquivo)

        with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
            df_inclusao.to_excel(writer, sheet_name="Inclusão", index=False)
            df_apolice_endosso.to_excel(writer, sheet_name="Apólice Endosso", index=False)

        logger.info(f"Arquivo gerado: {caminho_saida}")
        logger.info(f"  Aba 'Inclusão':        {len(df_inclusao)} registros")
        logger.info(f"  Aba 'Apólice Endosso': {len(df_apolice_endosso)} registros")

        # 2.5 Mover arquivos para processados
        caminhos_arquivos = list(dados["caminhos"].values())
        mover_para_processados(caminhos_arquivos, pasta_processados)
        logger.info("Arquivos movidos para pasta 'processados'.")


if __name__ == "__main__":
    cli()
