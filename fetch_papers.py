import os
import requests
from typing import Optional
import pandas as pd
from .helpers import safe_doi

TIMEOUT = 30

def load_api_key() -> str:
    """
    Загружает Elsevier API key из окружения (.env).
    """
    api_key = os.getenv("ELSEVIER_API_KEY")
    if not api_key:
        raise RuntimeError("ELSEVIER_API_KEY not found in environment")
    return api_key

def load_api_base() -> str:
    """
    Загружает базовый URL для API Elsevier.
    """
    api_base = os.getenv("ELSEVIER_API_BASE")
    if not api_base:
        raise RuntimeError("ELSEVIER_API_BASE not found in environment")

def fetch_elsevier_xml(doi: str) -> str:
    """
    Делает запрос к Elsevier Article Retrieval API
    и возвращает XML как строку.

    Бросает исключение, если ответ не 200.
    """
    api_key = load_api_key()
    api_base = load_api_base()
    url = api_base + doi

    headers = {
        "X-ELS-APIKey": api_key,
        "Accept": "application/xml",
        "User-Agent": "elsevier-oa-test-script",
    }

    response = requests.get(url, headers=headers, timeout=TIMEOUT)

    if response.status_code != 200:
        raise RuntimeError(
            f"Elsevier API error {response.status_code}: {response.text[:500]}"
        )

    return response.text

def has_fulltext_body(xml_text: str) -> bool:
    """
    Минимальная проверка:
    есть ли в XML признаки полного текста статьи.
    """
    return (
        "<body" in xml_text
        or "<ce:section" in xml_text
        or "<ce:sections" in xml_text
    )

def get_elsevier_fulltext_xml(doi: str) -> Optional[str]:
    """
    Возвращает XML статьи, только если это реально full-text.
    Иначе возвращает None.
    """
    xml = fetch_elsevier_xml(doi)

    if not has_fulltext_body(xml):
        return None

    return xml

if __name__ == "__main__":
    XML_DIR = "../Agentic_data_extraction/elsevier_xml_data"
    thermo_df = pd.read_csv("./thermo_full_11927.csv")
    dois = thermo_df["doi_key"].to_list()
    xml_dois = []
    nobody_dois = []
    err_dois = []
    total = len(dois)

    for idx, doi in enumerate(dois, start=1):
        print(f"[{idx}/{total}] Processing DOI: {doi}")
        try:
            fulltext_xml = get_elsevier_fulltext_xml(doi)
        except RuntimeError as rt_err:
            print(f"  Error: {rt_err}")
            err_dois.append(doi)
            continue
        if fulltext_xml is None:
            print(f"  -> No full-text body found")
            nobody_dois.append(doi)
            continue
        xml_dois.append(doi)
        # Сохранение XML
        filename = safe_doi(doi) + ".xml"
        filepath = os.path.join(XML_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as xml_f:
            xml_f.write(fulltext_xml)
        print(f"  -> Full-text saved: {filename}")

    # Вывод статистики
    with_fulltext = len(xml_dois)
    no_body = len(nobody_dois)
    errors = len(err_dois)

    print("\n" + "="*50)
    print("СТАТИСТИКА СКАНИРОВАНИЯ DOI")
    print("="*50)
    print(f"Общее количество DOI:          {total}")
    print(f"Успешно получены (полный текст): {with_fulltext}")
    print(f"Нет полного текста (<body>):    {no_body}")
    print(f"Ошибки при запросе:             {errors}")
    print("="*50)
    success_rate = (with_fulltext / total) * 100 if total > 0 else 0
    print(f"Процент успешных загрузок:     {success_rate:.2f}%")
    print("="*50)
