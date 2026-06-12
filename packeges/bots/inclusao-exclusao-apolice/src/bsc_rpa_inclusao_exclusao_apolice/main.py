import logging
import argparse
from pathlib import Path
import os

import pandas as pd
from datetime import datetime

from bsc_rpa_core.logs import configure_logging, log_func_call
from bsc_rpa_core.reporting import start_run

from bsc_rpa_adapter_outlook import Win32Outlook
from bsc_rpa_adapter_playwright import PlaywrightSession

from .config import Config, NOTIF_BODY_CONFIG
from .tasks import ( baixar_relatorio_frota_total, 
                    realizar_login, 
                    baixar_relatorio_endossos, tratar_exportacao_exclusao, tratar_exportacao_inclusao,
                    tratar_inclusao, 
                    tratar_exclusao 
)


from .steps import (
    buscar_arquivos_completos,
    carregar_excel_com_header_dinamico,
    carregar_planilhas,
    normalizar_colunas,
    padronizar_dados,
    remover_duplicados,
    separar_endossos,
    buscar_arquivos,
    mover_para_processados
)




logger = logging.getLogger(__name__)


def cli():
    parser = argparse.ArgumentParser(
        prog="RPA inclusao_exclusao_apolice",
        description="RPA inclusao_exclusao_apolice is a bot that performs login and manages policies"
    )

    parser.add_argument(
        '--config', '-c',
        help="Path to the config file. Defaults to 'config.yaml'.",
        required=False
    )

    args = parser.parse_args()

    config_path = args.config or 'config.yaml'
    
    config = Config.load(config_path)

    config.io.log_folder.mkdir(exist_ok=True, parents=True)
    log_path = config.io.log_folder / Path('log.jsonl')

    configure_logging(
        log_path.as_posix(),
        # Sugestão padrão do template
        # {'loggers': {'urllib3': {'level': 'INFO'}}}
    )

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
            None
            #outlook
        )
    ):
        
        # page = pw.new_page()

        # realizar_login(
        #     page,
        #     config.gmfleet.base_url,
        #     config.gmfleet.username,
        #     config.gmfleet.password,
            
        # )
        
    
        # baixar_relatorio_endossos(
        #     page,
        #     config.gmfleet.base_url,
        # )

        
        # baixar_relatorio_frota_total(page, config.gmfleet.base_url)

        
        base_dir = os.getcwd()

        pasta_downloads = os.path.join(base_dir, "downloads")
        pasta_processados = os.path.join(base_dir, "processados")

        # 🔎 buscar TODOS os arquivos
        path_endosso, path_frota, path_exp_inc, path_exp_exc = buscar_arquivos_completos(pasta_downloads)

        logging.info(f"Endosso: {path_endosso}")
        logging.info(f"Frota: {path_frota}")
        logging.info(f"Exp Inclusão: {path_exp_inc}")
        logging.info(f"Exp Exclusão: {path_exp_exc}")

        # 📥 carregar
        df_endosso, df_frota = carregar_planilhas(path_endosso, path_frota)
        df_exp_inc = carregar_excel_com_header_dinamico(path_exp_inc, "Placa")
        df_exp_exc = carregar_excel_com_header_dinamico(path_exp_exc, "Chassi")

        
        df_endosso = normalizar_colunas(df_endosso)
        df_exp_inc = normalizar_colunas(df_exp_inc)
        df_exp_exc = normalizar_colunas(df_exp_exc)
        df_frota   = normalizar_colunas(df_frota)


        # 🧹 padronizar
        df_endosso = padronizar_dados(df_endosso)
        df_frota = padronizar_dados(df_frota)
        df_exp_inc = padronizar_dados(df_exp_inc)

        # 🔄 tratar apólice
        df_endosso = remover_duplicados(df_endosso)
        df_apolice_inc, df_apolice_exc = separar_endossos(df_endosso)

        # ✅ regra correta
        df_final_inclusao = tratar_exportacao_inclusao(df_exp_inc, df_apolice_inc, df_frota)
        df_final_exclusao = tratar_exportacao_exclusao(df_exp_exc, df_apolice_exc, df_frota)

        # 📅 nome do arquivo
        hoje = datetime.now()
        nome_arquivo = f"Inclusao_{hoje.month}_{hoje.year}.xlsx"
        caminho_saida = os.path.join(base_dir, nome_arquivo)

        # 💾 salvar
        with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
            df_final_inclusao.to_excel(writer, sheet_name="Inclusão", index=False)
            df_final_exclusao.to_excel(writer, sheet_name="Exclusão", index=False)
            df_endosso.to_excel(writer, sheet_name="Apólice Endosso", index=False)

        logging.info(f"Arquivo gerado: {caminho_saida}")

        # 📦 mover arquivos
        mover_para_processados(
            [path_endosso, path_frota, path_exp_inc, path_exp_exc],
            pasta_processados
        )

        logging.info("Arquivos movidos para pasta processados ✅")




if __name__ == "__main__":
    cli()