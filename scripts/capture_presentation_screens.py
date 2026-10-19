#!/usr/bin/env python3
"""Captura telas locais usadas na apresentação final.

Pré-requisitos: API em :5000, frontend em :3000, Selenium e Firefox.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def authenticate() -> str:
    request = urllib.request.Request(
        "http://127.0.0.1:5000/createUser",
        data=json.dumps(
            {"id": 1, "name": "Arthur", "password": "senha-local-123"}
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)["access_token"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    token = authenticate()
    options = Options()
    options.add_argument("--headless")
    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)

    driver = webdriver.Firefox(options=options)
    try:
        driver.set_window_size(1440, 950)
        driver.get("http://127.0.0.1:3000/")
        driver.execute_script(
            "sessionStorage.setItem('newUserId', '1');"
            "sessionStorage.setItem('isAdmin', 'true');"
            "sessionStorage.setItem('accessToken', arguments[0]);",
            token,
        )

        driver.get("http://127.0.0.1:3000/home")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Todos os Livros')]"))
        )
        time.sleep(1)
        driver.save_screenshot(str(args.output / "sistema_catalogo.png"))

        driver.get("http://127.0.0.1:3000/simulacoes")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(), 'Laboratório de Resiliência')]")
            )
        )
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(), 'Impacto ao longo do tempo')]")
            )
        )
        time.sleep(1)
        driver.save_screenshot(str(args.output / "laboratorio_topo.png"))

        chart = driver.find_element(
            By.XPATH, "//*[contains(text(), 'Melhor resultado')]/ancestor::div[1]"
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'start'});", chart)
        time.sleep(1)
        driver.save_screenshot(str(args.output / "laboratorio_grafico.png"))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
