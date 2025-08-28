"""
Automação
Roda no Chrome já aberto (porta 9222), percorre os municípios,
aplica o filtro e baixa os dados em CSV.

Abrir o webdrive, fazer login no gov.br:

"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="C:\ChromeDebug"

"""

from __future__ import annotations

import time
import logging
from typing import Callable

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)



DEBUGGER_ADDRESS = "127.0.0.1:9222"
DEFAULT_TIMEOUT = 20

"""
XPaths copiados diretamente

"""

XPATHS = {
    "dropdown_municipio": "//*[@id='municipio']/span",
    "btn_area_filtros": "//*[@id='pn_id_2_content']/app-search-bar/div/div/div[2]/button",
    "accordion_grupo": "/html/body/app-root/app-layout/div/main/div/div/div/div/app-qualidade/div/div/p-tabview/div/div[2]/p-tabpanel[1]/div/app-search-bar/div/div[2]/div/div[1]/accordion/div/div/div/div[4]",
    "btn_aplicar_busca": "//*[@id='pn_id_2_content']/app-search-bar/div/button",
    "btn_exportar": "//*[@id='pn_id_2_content']/div[2]/app-exportacao-relatorio/button/span",
    "btn_modal_csv": "/html/body/div/div/div/button[1]",
}

MUNICIPIOS = [
    "ÁGUA CLARA", "ALCINÓPOLIS", "AMAMBAI", "ANASTÁCIO", "ANAURILÂNDIA", "ANGÉLICA",
    "ANTÔNIO JOÃO", "APARECIDA DO TABOADO", "AQUIDAUANA", "ARAL MOREIRA", "BANDEIRANTES",
    "BATAGUASSU", "BATAYPORÃ", "BELA VISTA", "BODOQUENA", "BONITO", "BRASILÂNDIA", "CAARAPÓ",
    "CAMAPUÃ", "CAMPO GRANDE", "CARACOL", "CASSILÂNDIA", "CHAPADÃO DO SUL", "CORGUINHO",
    "CORONEL SAPUCAIA", "CORUMBÁ", "COSTA RICA", "COXIM", "DEODÁPOLIS", "DOIS IRMÃOS DO BURITI",
    "DOURADINA", "DOURADOS", "ELDORADO", "FÁTIMA DO SUL", "FIGUEIRÃO", "GLÓRIA DE DOURADOS",
    "GUIA LOPES DA LAGUNA", "IGUATEMI", "INOCÊNCIA", "ITAPORÃ", "ITAQUIRAÍ", "IVINHEMA", "JAPORÃ",
    "JARAGUARI", "JARDIM", "JATEÍ", "JUTI", "LADÁRIO", "LAGUNA CARAPÃ", "MARACAJU", "MIRANDA",
    "MUNDO NOVO", "NAVIRAÍ", "NIOAQUE", "NOVA ALVORADA DO SUL", "NOVA ANDRADINA",
    "NOVO HORIZONTE DO SUL", "PARANAÍBA", "PARANHOS", "PEDRO GOMES", "PONTA PORÃ", "PORTO MURTINHO",
    "RIBAS DO RIO PARDO", "RIO BRILHANTE", "RIO NEGRO", "RIO VERDE DE MATO GROSSO", "ROCHEDO",
    "SANTA RITA DO PARDO", "SÃO GABRIEL DO OESTE", "SELVÍRIA", "SETE QUEDAS", "SIDROLÂNDIA",
    "SONORA", "TACURU", "TAQUARUSSU", "TERENOS", "TRÊS LAGOAS", "VICENTINA",
]


def setup_driver() -> tuple[webdriver.Chrome, WebDriverWait]:
    opts = webdriver.ChromeOptions()
    opts.debugger_address = DEBUGGER_ADDRESS
    driver = webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, DEFAULT_TIMEOUT)
    return driver, wait


def retry_click(driver: webdriver.Chrome, wait: WebDriverWait, xpath: str, attempts: int = 3, scroll: bool = True) -> None:

    last_exc: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            el = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            if scroll:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.2)
            el.click()
            return
        except (StaleElementReferenceException, ElementClickInterceptedException) as exc:
            last_exc = exc
            time.sleep(0.3 * i)

    el = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    el.click()


def wait_visible(wait: WebDriverWait, xpath: str):
    return wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))


def escolher_municipio(driver: webdriver.Chrome, wait: WebDriverWait, nome: str) -> None:
    retry_click(driver, wait, XPATHS["dropdown_municipio"])

    item_xpath = f"//*[normalize-space(text())='{nome}']"
    retry_click(driver, wait, item_xpath)
    time.sleep(0.5)


def aplicar_filtro_indicador(driver: webdriver.Chrome, wait: WebDriverWait) -> None:

    retry_click(driver, wait, XPATHS["btn_area_filtros"])
    retry_click(driver, wait, XPATHS["accordion_grupo"])
    retry_click(driver, wait, XPATHS["btn_aplicar_busca"])

    time.sleep(2)


def baixar_csv(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    retry_click(driver, wait, XPATHS["btn_exportar"])
    retry_click(driver, wait, XPATHS["btn_modal_csv"])

    time.sleep(3)


def processar_municipio(driver: webdriver.Chrome, wait: WebDriverWait, nome: str) -> None:
    escolher_municipio(driver, wait, nome)
    aplicar_filtro_indicador(driver, wait)
    baixar_csv(driver, wait)

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    driver, wait = setup_driver()

    for nome in MUNICIPIOS:
        logging.info("Processando município: %s", nome)
        try:
            time.sleep(1.0)
            processar_municipio(driver, wait, nome)
            logging.info("Concluído: %s", nome)
        except TimeoutException as e:
            logging.warning("Timeout em %s: %s", nome, e)
        except Exception as e:
            logging.error("Erro em %s: %s: %s", nome, type(e).__name__, e)
    
    logging.info("Execução finalizada.")


if __name__ == "__main__":
    main()
