import logging
import os
import re
import shutil
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import Page

logger = logging.getLogger(__name__)

# =============================================================================
# PLAYWRIGHT — steps de navegação (não alterar)
# =============================================================================

def acessar_portal(page: Page, base_url: str):
    page.goto(base_url)
    page.wait_for_load_state("domcontentloaded")


def preencher_login(page: Page, username: str, password: str):
    page.wait_for_selector("#vUSERNAME", timeout=50000)
    page.fill("#vUSERNAME", username)
    page.fill("#vUSERPASSWORD", password)


def clicar_confirmar(page: Page):
    page.click("input[name='BTNENTER']")


def validar_login(page: Page):
    page.wait_for_load_state("networkidle")
    error = page.locator("#gxErrorViewer")
    if error.count() > 0:
        texto = error.inner_text().strip()
        if texto:
            raise Exception(f"Erro de login: {texto}")
    page.wait_for_selector("#USERNAME_MPAGE", timeout=30000)
    try:
        page.wait_for_selector("#ACTIONLOGOUT_MPAGE", timeout=10000)
    except Exception:
        pass


def acessar_modulo_seguros(page: Page):
    container = page.locator("#Gridf_modulosContainerDiv")
    container.wait_for(state="visible", timeout=30000)
    card = container.locator("span:has-text('Seguros')").first
    link = card.locator(
        "xpath=ancestor::div[contains(@id, 'UNNAMEDTABLEFSGRIDF_MODULOS')]//a"
    ).first
    link.click()
    page.wait_for_load_state("networkidle")


def acessar_menu_endossos(page: Page):
    page.wait_for_selector("text=Apólice Endosso", timeout=30000)
    page.get_by_role("link", name="Apólice Endosso").click()
    page.wait_for_load_state("networkidle")


def exportar_relatorio(page: Page) -> str:
    download_dir = Path("downloads")
    download_dir.mkdir(exist_ok=True)
    with page.expect_download(timeout=20000) as dl:
        page.get_by_role("button", name="Exportar à Excel").click()
    download = dl.value
    caminho = download_dir / download.suggested_filename
    download.save_as(caminho)
    logger.debug(f"Arquivo salvo em: {caminho.resolve()}")
    return str(caminho)


def acessar_importacao_exportacao(page: Page):
    page.wait_for_selector(
        "text=Importação / Exportação Dados da Apólice",
        timeout=30000,
    )
    page.get_by_role(
        "link", name="Importação / Exportação Dados da Apólice"
    ).click()
    page.wait_for_load_state("networkidle")


def salvar_download(download, pasta: Path, prefixo: str) -> str:
    nome_original = download.suggested_filename
    if "." in nome_original:
        base, ext = nome_original.rsplit(".", 1)
        nome_final = f"{prefixo}_{base}.{ext}"
    else:
        nome_final = f"{prefixo}_{nome_original}"
    caminho = pasta / nome_final
    download.save_as(caminho)
    return str(caminho)


def executar_exportacoes_apolice(page: Page):
    downloads = []
    download_dir = Path("downloads")
    download_dir.mkdir(exist_ok=True)

    time.sleep(15)

    # 1º download — Exportação Inclusão
    page.get_by_label("Operacao").select_option("EXP")
    with page.expect_download(timeout=20000) as dl:
        page.get_by_role("button", name=re.compile("Confirmar")).click()
    arquivo1 = salvar_download(dl.value, download_dir, "exportacao")
    downloads.append(arquivo1)

    page.wait_for_selector("#vTIPOENDOSSO", timeout=30000)
    time.sleep(2)

    # 2º download — Exportação Exclusão
    page.get_by_label("Tipo Endosso").select_option("3")
    with page.expect_download(timeout=20000) as dl2:
        page.get_by_role("button", name=re.compile("Confirmar")).click()
    arquivo2 = salvar_download(dl2.value, download_dir, "exclusao")
    downloads.append(arquivo2)

    page.locator("#HEADER_MPAGE").click()
    time.sleep(10)

    return downloads


def acessar_modulo_relatorios(page: Page):
    container = page.locator("span:has-text('Relatórios')").locator(
        "xpath=ancestor::div[contains(@id,'Gridf_modulosContainerRow')]"
    )
    container.locator("a").click()
    page.wait_for_load_state("networkidle")


def acessar_frota_total(page: Page):
    page.wait_for_selector("text=Frota Total", timeout=30000)
    try:
        page.get_by_role(
            "link", name=re.compile("Frota Total - NEW", re.IGNORECASE)
        ).click()
    except Exception:
        page.get_by_role(
            "link", name=re.compile("^Frota Total$", re.IGNORECASE)
        ).click()
    page.wait_for_load_state("networkidle")


def baixar_frota_total(page: Page) -> str:
    download_dir = Path("downloads")
    download_dir.mkdir(exist_ok=True)
    page.wait_for_selector("#GridContainerRow_0001", timeout=30000)
    with page.expect_download(timeout=20000) as dl:
        page.locator("#GridContainerRow_0001").get_by_role(
            "link", name=re.compile("Visualizar", re.IGNORECASE)
        ).click()
    caminho = download_dir / dl.value.suggested_filename
    dl.value.save_as(caminho)
    return str(caminho)


# =============================================================================
# PLANILHAS — utilitários de I/O
# =============================================================================

def buscar_arquivos_downloads(pasta_downloads: str) -> dict:
    """
    Localiza os 4 arquivos na pasta de downloads pelo nome.
    Retorna dict com chaves: endosso, frota, exp_inc, exp_exc.
    Levanta exceção se algum não for encontrado.
    """
    arquivos = os.listdir(pasta_downloads)

    resultado = {
        "endosso": None,
        "frota": None,
        "exp_inc": None,
        "exp_exc": None,
    }

    for arquivo in arquivos:
        nome = arquivo.lower()
        # normalizar acentos para comparação
        nome_norm = (
            nome.replace("ç", "c")
                .replace("ã", "a")
                .replace("á", "a")
                .replace("é", "e")
                .replace("ó", "o")
        )

        if "frotatotal" in nome_norm or "frota total" in nome_norm:
            resultado["frota"] = os.path.join(pasta_downloads, arquivo)
        elif "exportacao inclusao" in nome_norm or "exportacaoinclusao" in nome_norm or (
            "inclusao" in nome_norm and "apolice" in nome_norm
        ):
            resultado["exp_inc"] = os.path.join(pasta_downloads, arquivo)
        elif "exportacao exclusao" in nome_norm or "exportacaoexclusao" in nome_norm or (
            "exclusao" in nome_norm and "apolice" in nome_norm
        ):
            resultado["exp_exc"] = os.path.join(pasta_downloads, arquivo)
        elif "apolice" in nome_norm or "endosso" in nome_norm:
            resultado["endosso"] = os.path.join(pasta_downloads, arquivo)

    for chave, caminho in resultado.items():
        if caminho is None:
            raise FileNotFoundError(
                f"Arquivo '{chave}' não encontrado na pasta: {pasta_downloads}"
            )

    return resultado


def _encontrar_linha_header(path_arquivo: str, coluna_chave: str) -> int:
    """
    Detecta a linha do cabeçalho procurando pela coluna_chave (case-insensitive,
    com strip). Levanta exceção se não encontrar nas primeiras 20 linhas.
    """
    df_raw = pd.read_excel(path_arquivo, engine="openpyxl", header=None, nrows=20)
    chave_lower = coluna_chave.strip().lower()

    for i, row in df_raw.iterrows():
        valores = [str(v).strip().lower() for v in row.values]
        if chave_lower in valores:
            return i

    raise ValueError(
        f"Coluna '{coluna_chave}' não encontrada nas primeiras 20 linhas de: {path_arquivo}"
    )


def carregar_planilha(path_arquivo: str, coluna_chave: str) -> pd.DataFrame:
    """
    Carrega um Excel detectando automaticamente a linha do cabeçalho.
    Normaliza os nomes das colunas: strip de espaços (mantém capitalização original).
    """
    header_row = _encontrar_linha_header(path_arquivo, coluna_chave)
    df = pd.read_excel(path_arquivo, engine="openpyxl", header=header_row)
    # strip espaços nos nomes — sem alterar capitalização (usamos nomes originais)
    df.columns = df.columns.str.strip()
    logger.debug(f"Carregado '{path_arquivo}' | header={header_row} | shape={df.shape}")
    return df


def normalizar_placa(serie: pd.Series) -> pd.Series:
    """Padroniza placa: strip + upper. Trata NaN como string vazia."""
    return serie.fillna("").astype(str).str.strip().str.upper()


def normalizar_chassi(serie: pd.Series) -> pd.Series:
    """Padroniza chassi: strip + upper. Trata NaN como string vazia."""
    return serie.fillna("").astype(str).str.strip().str.upper()


def is_status_vazio(serie: pd.Series) -> pd.Series:
    """Retorna máscara True onde o status é considerado vazio/ausente."""
    s = serie.fillna("").astype(str).str.strip()
    return s.isin(["", "nan", "None", "NaN"])


def mover_para_processados(caminhos: list, pasta_processados: str) -> None:
    os.makedirs(pasta_processados, exist_ok=True)
    for caminho in caminhos:
        nome = os.path.basename(caminho)
        destino = os.path.join(pasta_processados, nome)
        shutil.move(caminho, destino)
        logger.debug(f"Movido: {caminho} → {destino}")


# =============================================================================
# PLANILHAS — processamento de negócio
# =============================================================================

def processar_apolice_endosso(df_endosso: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    A partir do DataFrame de Apólice Endosso:
      1. Remove duplicatas de Placa dentro de cada tipo, mantendo o registro
         com Data Endosso mais recente.
      2. Separa em df_inclusao e df_exclusao pelo campo 'Tipo Endosso'.

    Retorna: (df_inclusao, df_exclusao)
    """
    df = df_endosso.copy()
    df["Placa"] = normalizar_placa(df["Placa"])
    df["Data Endosso"] = pd.to_datetime(df["Data Endosso"], errors="coerce")

    # Ordenar do mais recente para o mais antigo e deduplicar por Tipo + Placa
    df = df.sort_values("Data Endosso", ascending=False)
    df = df.drop_duplicates(subset=["Tipo Endosso", "Placa"], keep="first")
    df = df.sort_index()  # restaurar ordem original após dedup

    # Separar por tipo (valores reais: 'Inclusão' e 'Exclusão')
    df_inclusao = df[df["Tipo Endosso"].astype(str).str.strip() == "Inclusão"].copy()
    df_exclusao = df[df["Tipo Endosso"].astype(str).str.strip() == "Exclusão"].copy()

    logger.info(
        f"Apólice Endosso processado | Inclusão={len(df_inclusao)} | Exclusão={len(df_exclusao)}"
    )
    return df_inclusao, df_exclusao


def enriquecer_com_status(
    df: pd.DataFrame,
    df_frota: pd.DataFrame,
    chave_df: str = "Placa",
    chave_frota: str = "Placa",
) -> pd.DataFrame:
    """
    Adiciona (ou atualiza) a coluna 'Status Veículo Contrato' em df via merge
    com df_frota usando as colunas chave informadas.
    Se a coluna já existir em df, ela é substituída pela da Frota Total.
    """
    df = df.copy()
    df_frota = df_frota.copy()

    # Normalizar chaves
    df[chave_df] = normalizar_placa(df[chave_df]) if "Placa" in chave_df else normalizar_chassi(df[chave_df])
    df_frota[chave_frota] = normalizar_placa(df_frota[chave_frota]) if "Placa" in chave_frota else normalizar_chassi(df_frota[chave_frota])

    # Remover coluna de status antiga se existir (vai vir do merge)
    if "Status Veículo Contrato" in df.columns:
        df = df.drop(columns=["Status Veículo Contrato"])

    frota_lookup = (
        df_frota[[chave_frota, "Status Veículo Contrato"]]
        .drop_duplicates(subset=[chave_frota])
    )

    df = df.merge(
        frota_lookup.rename(columns={chave_frota: chave_df}),
        on=chave_df,
        how="left",
    )

    return df


def obter_placa_via_chassi(df: pd.DataFrame, df_frota: pd.DataFrame) -> pd.DataFrame:
    """
    Para registros da Exportação Exclusão que não possuem Placa (ou Placa vazia),
    tenta preencher a partir do Chassi cruzando com a Frota Total.
    Se a Placa já existir no registro, ela é mantida.
    """
    df = df.copy()
    df_frota = df_frota.copy()

    df["Chassi"] = normalizar_chassi(df["Chassi"])
    df_frota["Chassi"] = normalizar_chassi(df_frota["Chassi"])
    df_frota["Placa"] = normalizar_placa(df_frota["Placa"])

    chassi_to_placa = (
        df_frota[df_frota["Placa"] != ""][["Chassi", "Placa"]]
        .drop_duplicates(subset=["Chassi"])
        .set_index("Chassi")["Placa"]
        .to_dict()
    )

    # Preencher Placa ausente via chassi
    if "Placa" not in df.columns:
        df["Placa"] = ""
    df["Placa"] = normalizar_placa(df["Placa"])

    mask_sem_placa = df["Placa"] == ""
    df.loc[mask_sem_placa, "Placa"] = df.loc[mask_sem_placa, "Chassi"].map(chassi_to_placa).fillna("")

    qtd_preenchida = mask_sem_placa.sum()
    if qtd_preenchida > 0:
        logger.info(f"Placa preenchida via Chassi: {qtd_preenchida} registros")

    return df


def processar_exportacao_inclusao(
    df_exp_inc: pd.DataFrame,
    df_apolice_inc: pd.DataFrame,
    df_frota: pd.DataFrame,
) -> tuple[pd.DataFrame, list]:
    """
    Regras Exportação Inclusão:
      1. Remover duplicatas de Placa (manter primeira ocorrência).
      2. Adicionar coluna Status Veículo Contrato via Frota Total (chave: Placa).
      3. Descartar status Devolvido e vazio.
      4. Resultado deve conter apenas placas presentes em Apólice Endosso → Inclusão.
      5. Identificar divergências.

    Retorna: (df_resultado, lista_divergencias)
    """
    df = df_exp_inc.copy()
    df["Placa"] = normalizar_placa(df["Placa"])

    # 1. Remover duplicatas
    df = df.drop_duplicates(subset=["Placa"], keep="first")

    # 2. Enriquecer com status
    df = enriquecer_com_status(df, df_frota, chave_df="Placa", chave_frota="Placa")

    # 3. Filtrar status inválidos
    mask_vazio = is_status_vazio(df["Status Veículo Contrato"])
    mask_devolvido = df["Status Veículo Contrato"].astype(str).str.strip() == "Devolvido"
    df = df[~mask_vazio & ~mask_devolvido].copy()

    # 4. Limitar às placas da Apólice Inclusão
    placas_apolice = set(df_apolice_inc["Placa"].unique())
    placas_exp = set(df["Placa"].unique())

    df = df[df["Placa"].isin(placas_apolice)].copy()

    # 5. Divergências
    divergencias = []
    apenas_apolice = placas_apolice - placas_exp
    apenas_exp = placas_exp - placas_apolice

    if apenas_apolice:
        divergencias.append(
            f"INCLUSÃO — {len(apenas_apolice)} placa(s) na Apólice mas NÃO na Exportação: "
            + ", ".join(sorted(apenas_apolice))
        )
    if apenas_exp:
        divergencias.append(
            f"INCLUSÃO — {len(apenas_exp)} placa(s) na Exportação mas NÃO na Apólice: "
            + ", ".join(sorted(apenas_exp))
        )

    logger.info(f"Exportação Inclusão processada | {len(df)} registros finais")
    if divergencias:
        for d in divergencias:
            logger.warning(d)

    return df, divergencias


def processar_exportacao_exclusao(
    df_exp_exc: pd.DataFrame,
    df_apolice_exc: pd.DataFrame,
    df_frota: pd.DataFrame,
) -> tuple[pd.DataFrame, list]:
    """
    Regras Exportação Exclusão:
      1. Garantir Placa: usar campo Placa existente; se vazio, buscar via Chassi na Frota Total.
      2. Remover duplicatas de Placa.
      3. Adicionar coluna Status Veículo Contrato via Frota Total (chave: Placa).
      4. Descartar status Ativo e vazio.
      5. Resultado deve conter apenas placas presentes em Apólice Endosso → Exclusão.
      6. Identificar divergências.

    Retorna: (df_resultado, lista_divergencias)
    """
    df = df_exp_exc.copy()

    # 1. Garantir Placa (via Chassi se necessário)
    df = obter_placa_via_chassi(df, df_frota)

    # 2. Remover duplicatas
    df = df.drop_duplicates(subset=["Placa"], keep="first")
    df = df[df["Placa"] != ""].copy()  # remover sem placa

    # 3. Enriquecer com status
    df = enriquecer_com_status(df, df_frota, chave_df="Placa", chave_frota="Placa")

    # 4. Filtrar status inválidos
    mask_vazio = is_status_vazio(df["Status Veículo Contrato"])
    mask_ativo = df["Status Veículo Contrato"].astype(str).str.strip() == "Ativo"
    df = df[~mask_vazio & ~mask_ativo].copy()

    # 5. Limitar às placas da Apólice Exclusão
    placas_apolice = set(df_apolice_exc["Placa"].unique())
    placas_exp = set(df["Placa"].unique())

    df = df[df["Placa"].isin(placas_apolice)].copy()

    # 6. Divergências
    divergencias = []
    apenas_apolice = placas_apolice - placas_exp
    apenas_exp = placas_exp - placas_apolice

    if apenas_apolice:
        divergencias.append(
            f"EXCLUSÃO — {len(apenas_apolice)} placa(s) na Apólice mas NÃO na Exportação: "
            + ", ".join(sorted(apenas_apolice))
        )
    if apenas_exp:
        divergencias.append(
            f"EXCLUSÃO — {len(apenas_exp)} placa(s) na Exportação mas NÃO na Apólice: "
            + ", ".join(sorted(apenas_exp))
        )

    logger.info(f"Exportação Exclusão processada | {len(df)} registros finais")
    if divergencias:
        for d in divergencias:
            logger.warning(d)

    return df, divergencias
