import os
from typing import Optional, Dict, Union, List
from lxml import etree
import re
import unicodedata
import csv
import csv
from io import BytesIO
from typing import Union
from lxml import etree

import nltk
from nltk.tokenize import sent_tokenize

from .helpers import safe_doi
from .mat_patterns import RETAIN_PATTERNS

RETAIN_RE = [re.compile(pat, re.IGNORECASE) for pat in RETAIN_PATTERNS]

class XMLPaperParser():
    NS = {
        "ce": "http://www.elsevier.com/xml/common/elssce",
        "xocs": "http://www.elsevier.com/xml/xocs/dtd",
        "dc": "http://purl.org/dc/elements/1.1/",
        "prism": "http://prismstandard.org/namespaces/basic/2.0/",
        "cals": "http://www.elsevier.com/xml/common/cals/dtd",
    }

    def __init__(self, storage_dir : str) -> None:
        nltk.download('punkt_tab')
        self.storage_dir = storage_dir

    def parse_xml(self, xml_text : str):
        os.makedirs(self.storage_dir, exist_ok=True)

        article_data = self._extract_data(xml_text)
        if article_data is None or article_data.get("doi") in (None, "", "N/A"):
            print("[ERROR] Failed to extract article data or DOI. Skipping.")
            return None

        doi = article_data["doi"]
        doi_folder = safe_doi(doi)
        article_output_dir = os.path.join(self.storage_dir, doi_folder)
        os.makedirs(article_output_dir, exist_ok=True)

        # 1) fulltext_raw.txt
        raw_fulltext = self._compile_raw_fulltext(article_data)
        raw_path = os.path.join(article_output_dir, "fulltext_raw.txt")
        try:
            self._dump_text(raw_path, raw_fulltext)
        except OSError as e:
            print(f"[ERROR] Failed to write fulltext_raw.txt for {doi_folder}: {e}")
            return None

        # 2) fulltext.txt (filtered)
        try:
            filtered_sentences = self._filter_raw_fulltext(raw_fulltext)
            filtered_text = "\n".join(filtered_sentences).strip() + ("\n" if filtered_sentences else "")
            filtered_path = os.path.join(article_output_dir, "fulltext.txt")
            self._dump_text(filtered_path, filtered_text)
        except Exception as e:
            print(f"[ERROR] Filtering failed for {doi_folder}: {e}")
            # still keep raw; proceed to tables
        else:
            print(f"[OK] Saved: {doi_folder}/fulltext_raw.txt and fulltext.txt")

        # 3) tables (csv + cleaned caption + raw xml fragment)
        n_tables = self._extract_elsevier_tables_from_xml(xml_text, article_output_dir)
        if n_tables:
            print(f"[OK] Extracted {n_tables} table(s) for {doi_folder}")
        else:
            print(f"ℹ[NOTIFICATION] No tables extracted for {doi_folder}")

        print("\n[OK] Processing complete.")

    @staticmethod
    def _compile_raw_fulltext(article_data: Dict) -> str:
        parts: List[str] = []
        parts.append(f"Title: {article_data.get('title', 'N/A')}\n")
        parts.append(f"DOI: {article_data.get('doi', 'N/A')}\n")
        parts.append("\nAbstract:\n")
        parts.append(f"{article_data.get('abstract', 'N/A')}\n")

        sections = article_data.get("sections", {}) or {}
        for section, paras in sections.items():
            parts.append(f"\n=== {section} ===\n")
            for para in paras:
                parts.append(f"{para}\n")
        return "\n".join(parts).strip() + "\n"

    @staticmethod
    def _clean(text: Optional[str]) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFKD", text.strip())
        return re.sub(r"\s+", " ", text)
    
    @staticmethod
    def _dump_text(path: str, text: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    @staticmethod
    def _is_material_related(sentence: str) -> bool:
        return any(pat.search(sentence) for pat in RETAIN_RE)


    @classmethod
    def _extract_text_from_elem(cls, elem: etree._Element) -> str:
        return cls._clean(" ".join(t.strip() for t in elem.itertext() if t and t.strip()))
    
    @classmethod
    def _filter_raw_fulltext(cls, text: str) -> List[str]:
        sentences = sent_tokenize(text)
        filtered_senstences = [s for s in sentences if cls._is_material_related(s)]
        return filtered_senstences

    @classmethod
    def _extract_data(cls, xml_text: Union[str, bytes]) -> Optional[Dict]:
        if isinstance(xml_text, str):
            xml_bytes = xml_text.encode("utf-8", errors="replace")
        else:
            xml_bytes = xml_text

        try:
            # парсим напрямую из строки/байтов
            root = etree.fromstring(xml_bytes)
        except etree.XMLSyntaxError as e:
            print(f"[ERROR] XML parse error (string input): {e}")
            return None

        doi_element = root.find(".//prism:doi", namespaces=cls.NS)
        doi = cls._clean(doi_element.text) if doi_element is not None and doi_element.text else "N/A"

        title_element = root.find(".//dc:title", namespaces=cls.NS)
        title = cls._clean(title_element.text) if title_element is not None and title_element.text else "N/A"

        abstract_element = root.find(".//dc:description", namespaces=cls.NS)
        abstract = cls._clean(abstract_element.text) if abstract_element is not None and abstract_element.text else "N/A"

        sections: Dict[str, List[str]] = {}
        current_section = "Introduction"
        sections[current_section] = []

        for elem in root.iter():
            try:
                tag = etree.QName(elem.tag).localname
            except Exception:
                continue

            if tag == "section-title":
                section_title_text = cls._extract_text_from_elem(elem)
                if section_title_text:
                    current_section = section_title_text
                    sections.setdefault(current_section, [])
            elif tag == "para":
                para_text = cls._extract_text_from_elem(elem)
                if para_text:
                    sections.setdefault(current_section, []).append(para_text)
            elif tag == "abstract":
                if abstract == "N/A":
                    abs_text = cls._extract_text_from_elem(elem)
                    if abs_text:
                        abstract = abs_text

        return {"doi": doi, "title": title, "abstract": abstract, "sections": sections}

    @staticmethod
    def _findall_local(elem, name: str):
        # ищет элементы независимо от namespace
        return elem.findall(f".//{{*}}{name}")
    
    @staticmethod
    def _find_tables_any_ns_etree(root):
        return root.findall(".//{*}table")
    
    @staticmethod
    def _clean_caption_by_removing_cells(caption: str, rows: List[List[str]]) -> str:
        """
        Remove pasted table ROWS from caption (not individual cells).

        Rule:
        - join each table row into a single string
        - if that full row string appears in caption, remove it
        - finally normalize whitespace

        This preserves material names and method names that legitimately appear in captions.
        """
        if not caption:
            return ""

        out = caption

        for row in rows:
            row_text = " ".join((c or "").strip() for c in row if (c or "").strip())
            if row_text and row_text in out:
                out = out.replace(row_text, " ")

        out = re.sub(r"\s+", " ", out).strip()
        return out

    @classmethod
    def _extract_elsevier_tables_from_xml(cls, xml_text: Union[str, bytes], output_dir: str) -> int:
        """
        Extract tables from XML *content* (string/bytes) and write:
        - table{i}.csv
        - table{i}_caption.txt
        - table{i}.xml   (raw fragment if available)
        Returns number of tables successfully written.
        """
        # Keep parsing behavior close to etree.parse(path) by using etree.parse(file-like)
        if isinstance(xml_text, str):
            xml_bytes = xml_text.encode("utf-8", errors="replace")
        else:
            xml_bytes = xml_text

        try:
            tree = etree.parse(BytesIO(xml_bytes))
            root = tree.getroot()
        except etree.XMLSyntaxError as e:
            print(f"[ERROR] XML parse error (tables, string input): {e}")
            return 0

        tables = cls._find_tables_any_ns_etree(root)
        if not tables:
            return 0

        written = 0
        for idx, table in enumerate(tables, start=1):
            # Caption
            caption_text = ""
            caption_elem = table.find(".//{*}caption")  # вместо ce:caption
            if caption_elem is not None:
                caption_text = cls._extract_text_from_elem(caption_elem)

            # Rows / Entries (CALS)
            rows = []
            for row_elem in cls._findall_local(table, "row"):          # вместо ce:row
                row_cells = []
                entries = [e for e in row_elem.findall("./{*}entry")]  # entry обычно прямые дети row
                if not entries:
                    row_text = cls._extract_text_from_elem(row_elem)
                    if row_text:
                        row_cells = [row_text]
                else:
                    for cell in entries:
                        row_cells.append(cls._extract_text_from_elem(cell))
                if row_cells:
                    rows.append(row_cells)

            # Clean caption using exact cell removals (integrated)
            cleaned_caption = cls._clean_caption_by_removing_cells(caption_text, rows)

            # Write files
            csv_path = os.path.join(output_dir, f"table{idx}.csv")
            cap_path = os.path.join(output_dir, f"table{idx}_caption.txt")
            xml_frag_path = os.path.join(output_dir, f"table{idx}.xml")

            try:
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    if rows:
                        writer.writerows(rows)

                cls._dump_text(cap_path, cleaned_caption)

                # Raw XML fragment (maximally "full" / lossless)
                xml_str = etree.tostring(table, encoding="unicode")
                cls._dump_text(xml_frag_path, xml_str)

                written += 1
            except OSError as e:
                print(f"[ERROR] Failed to write table{idx} files in {output_dir}: {e}")
                continue

        return written
