from playwright.sync_api import Page
from pathlib import Path
import pandas as pd
import time
import re
import os
import shutil

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
    # Espera carregamento completo
    page.wait_for_load_state("networkidle")
    error = page.locator("#gxErrorViewer")
    if error.count() > 0:
        texto = error.inner_text().strip()
        if texto:
            raise Exception(f"Erro de login: {texto}")
    page.wait_for_selector("#USERNAME_MPAGE", timeout=30000)

    try:
        page.wait_for_selector("#ACTIONLOGOUT_MPAGE", timeout=10000)
    except:
        pass



def acessar_modulo_seguros(page: Page):
    # limita o escopo ao grid correto
    container = page.locator("#Gridf_modulosContainerDiv")

    container.wait_for(state="visible", timeout=30000)

    # encontra o card certo pelo texto
    card = container.locator("span:has-text('Seguros')").first

    # sobe até o bloco do módulo e pega o link
    link = card.locator("xpath=ancestor::div[contains(@id, 'UNNAMEDTABLEFSGRIDF_MODULOS')]//a").first

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

    # mantém nome original
    caminho = download_dir / download.suggested_filename

    download.save_as(caminho)

    print(f"Arquivo salvo em: {caminho.resolve()}")

    return str(caminho)



def acessar_importacao_exportacao(page: Page):
    page.wait_for_selector(
        "text=Importação / Exportação Dados da Apólice",
        timeout=30000
    )

    page.get_by_role(
        "link",
        name="Importação / Exportação Dados da Apólice"
    ).click()

    page.wait_for_load_state("networkidle")

def salvar_download(download, pasta, prefixo):
    nome_original = download.suggested_filename

    # separa nome e extensão
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

    # ======================
    # 1º DOWNLOAD → EXPORTAÇÃO
    # ======================
    page.get_by_label("Operacao").select_option("EXP")

    with page.expect_download(timeout=20000) as dl:
        page.get_by_role("button", name=re.compile("Confirmar")).click()

    arquivo1 = salvar_download(dl.value, download_dir, "exportacao")
    downloads.append(arquivo1)

    # ======================
    # ESPERA
    # ======================
    page.wait_for_selector("#vTIPOENDOSSO", timeout=30000)
    time.sleep(2)

    # ======================
    # 2º DOWNLOAD → EXCLUSÃO
    # ======================
    page.get_by_label("Tipo Endosso").select_option("3")

    with page.expect_download(timeout=20000) as dl2:
        page.get_by_role("button", name=re.compile("Confirmar")).click()


    arquivo2 = salvar_download(dl2.value, download_dir, "exclusao")
    downloads.append(arquivo2)

    #volta pro menu
    page.locator("#HEADER_MPAGE").click()
    time.sleep(10)
    

    return downloads



def acessar_modulo_relatorios(page: Page):
    
    container = page.locator("span:has-text('Relatórios')").locator("xpath=ancestor::div[contains(@id,'Gridf_modulosContainerRow')]")
    
    container.locator("a").click()

    page.wait_for_load_state("networkidle")



def acessar_frota_total(page: Page):
    page.wait_for_selector("text=Frota Total", timeout=30000)
    try:
        page.get_by_role(
            "link",
            name=re.compile("Frota Total - NEW", re.IGNORECASE)
        ).click()
    except:
        page.get_by_role(
            "link",
            name=re.compile("^Frota Total$", re.IGNORECASE)
        ).click()

    page.wait_for_load_state("networkidle")



def baixar_frota_total(page: Page) -> str:
    download_dir = Path("downloads")
    download_dir.mkdir(exist_ok=True)

    page.wait_for_selector("#GridContainerRow_0001", timeout=30000)

    with page.expect_download(timeout=20000) as dl:
        page.locator("#GridContainerRow_0001") \
            .get_by_role("link", name=re.compile("Visualizar", re.IGNORECASE)) \
            .click()

    caminho = download_dir / dl.value.suggested_filename
    dl.value.save_as(caminho)

    return str(caminho)


############################################## PLANILHAS ##################################################


def carregar_planilhas(path_endosso, path_frota):
    df_endosso = carregar_excel_com_header_dinamico(path_endosso, "Placa")
    df_frota = carregar_excel_com_header_dinamico(path_frota, "Placa")

    return df_endosso, df_frota


def padronizar_dados(df):
    df.columns = df.columns.str.strip()

    # encontrar coluna placa mesmo que venha diferente
    col_placa = None

    for col in df.columns:
        if col.strip().lower() == "placa":
            col_placa = col
            break

    if not col_placa:
        raise Exception(f"Coluna Placa não encontrada. Colunas: {df.columns.tolist()}")

    df = df.rename(columns={col_placa: "Placa"})

    # detectar coluna de placa dinamicamente
    col_placa = None

    for col in df.columns:
        if "placa" in col:
            col_placa = col
            break

    if not col_placa:
        raise Exception(f"Coluna de placa não encontrada. Colunas: {df.columns.tolist()}")

    # padroniza
    df[col_placa] = df[col_placa].astype(str).str.strip().str.upper()

    if "Data Endosso" in df.columns:
        df["Data Endosso"] = pd.to_datetime(df["Data Endosso"], errors="coerce")

    return df


def remover_duplicados(df):
    df = df.sort_values("data endosso", ascending=False)
    df = df.drop_duplicates(subset=["Placa"], keep="first")
    return df


def separar_endossos(df):
    # encontrar coluna correta
    col_endosso = None

    for col in df.columns:
        if "endosso" in col.lower():
            col_endosso = col
            break

    if not col_endosso:
        raise Exception(f"Coluna de endosso não encontrada. Colunas: {df.columns.tolist()}")

    # renomeia padronizado
    df = df.rename(columns={col_endosso: "Endosso"})


    # encontrar coluna de endosso dinamicamente
    col_endosso = None

    for col in df.columns:
        if "endosso" in col:
            col_endosso = col
            break

    if not col_endosso:
        raise Exception(f"Coluna de endosso não encontrada. Colunas: {df.columns.tolist()}")

    # padroniza conteúdo
    df[col_endosso] = df[col_endosso].astype(str).str.upper()

    # filtra
    df_inclusao = df[df[col_endosso].str.contains("INCLUSAO", na=False)]
    df_exclusao = df[df[col_endosso].str.contains("EXCLUSAO", na=False)]


    return df_inclusao, df_exclusao


def buscar_arquivos(pasta_downloads):
    arquivos = os.listdir(pasta_downloads)

    path_endosso = None
    path_frota = None

    for arquivo in arquivos:
        nome_lower = arquivo.lower()

        # identificar endosso
        if "apolice" in nome_lower or "endosso" in nome_lower:
            path_endosso = os.path.join(pasta_downloads, arquivo)

        # identificar frota
        elif "frotatotal" in nome_lower:
            path_frota = os.path.join(pasta_downloads, arquivo)

    if not path_endosso:
        raise Exception("Arquivo de endosso não encontrado na pasta downloads")

    if not path_frota:
        raise Exception("Arquivo de frota não encontrado na pasta downloads")

    return path_endosso, path_frota


def mover_para_processados(caminhos_arquivos, pasta_processados):
    os.makedirs(pasta_processados, exist_ok=True)

    for caminho in caminhos_arquivos:
        nome_arquivo = os.path.basename(caminho)
        destino = os.path.join(pasta_processados, nome_arquivo)

        shutil.move(caminho, destino)

import pandas as pd


def carregar_excel_com_header_dinamico(path_arquivo, coluna_chave):
    df_raw = pd.read_excel(path_arquivo, engine="openpyxl", header=None)

    header_row = None

    for i, row in df_raw.iterrows():
        valores = [str(v).strip().lower() for v in row.values]

        if coluna_chave.lower() in valores:
            header_row = i
            break

    if header_row is None:
        raise Exception(
            f"Header com coluna '{coluna_chave}' não encontrado no arquivo: {path_arquivo}"
        )

    df = pd.read_excel(
        path_arquivo,
        engine="openpyxl",
        header=header_row
    )

    # limpar nomes das colunas
    df.columns = df.columns.str.strip()

    return df

def buscar_arquivos_completos(pasta_downloads):
    arquivos = os.listdir(pasta_downloads)

    path_endosso = None
    path_frota = None
    path_exp_inc = None
    path_exp_exc = None

    for arquivo in arquivos:
        nome = arquivo.lower()

        # normalizar acento
        nome_normalizado = nome.replace("ç", "c").replace("ã", "a")

        if "frotatotal" in nome_normalizado:
            path_frota = os.path.join(pasta_downloads, arquivo)

        elif "inclusao" in nome_normalizado:
            path_exp_inc = os.path.join(pasta_downloads, arquivo)

        elif "exclusao" in nome_normalizado:
            path_exp_exc = os.path.join(pasta_downloads, arquivo)

        elif "apolice" in nome_normalizado:
            path_endosso = os.path.join(pasta_downloads, arquivo)

    return path_endosso, path_frota, path_exp_inc, path_exp_exc

def normalizar_colunas(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
    )
    return df