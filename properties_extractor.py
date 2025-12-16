import datetime
import json
import os
from typing import Dict, List, Optional, TypedDict

from langchain_core.prompts import PromptTemplate

from .base_properies_extractor import BasePropertiesExtractor
from .helpers import robust_json_parse

class PromptNotImplementedError(Exception):
    pass

class PropertiesExtractor(BasePropertiesExtractor):
    THERMO_MAT_LIMIT = 15

    def __init__(self) -> None:
        super().__init__()

        self.fulltext : str = ""
        self.combined_block : str = ""

        self.materials_extraction_prompt : Optional[str] = None
        self.materials_extraction_in : Optional[str] = None
        self.materials_extraction_out : Optional[str] = None
        self.materials_extraction_llm_output : Optional[str] = None

        self.thermo_properties_extraction_prompt : Optional[str] = None
        self.thermo_properties_extraction_in : Optional[str] = None
        self.thermo_properties_extraction_out : Optional[str] = None
        self.thermo_properties_extraction_llm_output : Optional[str] = None

        self.structure_properties_extraction_prompt : Optional[str] = None
        self.structure_properties_extraction_in : Optional[str] = None
        self.structure_properties_extraction_out : Optional[str] = None
        self.structure_properties_extraction_llm_output : Optional[str] = None

        self.table_data_extraction_prompt : Optional[str] = None
        self.table_data_extraction_in : Optional[str] = None
        self.table_data_extraction_out : Optional[str] = None
        self.table_data_extraction_llm_output : Optional[str] = None

        self.judge_prompt : Optional[str] = None
        self.judge_in : Optional[str] = None
        self.judge_out : Optional[str] = None
        self.judge_llm_output : Optional[str] = None

    def reset(self) -> None:
        self.materials_extraction_llm_output = None
        self.thermo_properties_extraction_llm_output = None
        self.structure_properties_extraction_llm_output = None
        self.table_data_extraction_llm_output = None
        self.judge_llm_output = None

    def set_materials_extraction_prompt(self, prompt : str) -> None:
        self.materials_extraction_prompt = prompt

    def set_thermo_properties_extraction_prompt(self, prompt : str) -> None:
        self.thermo_properties_extraction_prompt = prompt

    def set_structure_properties_extraction_prompt(self, prompt : str) -> None:
        self.structure_properties_extraction_prompt = prompt

    def set_table_data_extraction_prompt(self, prompt : str) -> None:
        self.table_data_extraction_prompt = prompt

    def set_judge_prompt(self, prompt : str) -> None:
        self.judge_prompt = prompt

    def get_materials_hint(self, material_names: List[str]) -> str:
        formatted = ", ".join(f'"{name}"' for name in material_names)
        material_hint = (
            "Only extract entries for the following materials: "
            f"{formatted}.\n"
        )
        return material_hint

    def extract_material_candidates(self, fulltext: str, llm, max_materials: int = 20) -> List[str]:
        """
        Returns a deduplicated list of material names that have ANY thermoelectric
        property mentioned nearby in the text (ZT, S, σ, ρ, PF, κ).
        This is a lightweight pre-filter used to seed material hints downstream.
        """
        self.fulltext = fulltext
        if self.materials_extraction_prompt is None:
            raise PromptNotImplementedError("materials_extraction_prompt is not yet defined")
        prompt = PromptTemplate.from_template(self.materials_extraction_prompt)
        final_prompt = prompt.format(fulltext=fulltext, max_materials=max_materials)
        # mp_prompt_f_path = "material_candidates_prompt.txt"
        # if not os.path.isfile(mp_prompt_f_path):
        #     with open(mp_prompt_f_path, "w", encoding='utf-8') as f:
        #         f.write(final_prompt)
        
        self.materials_extraction_in = final_prompt
        if self.materials_extraction_llm_output is not None:
            print("Using saved llm output without actual request for materials extraction node.")
            out = self.materials_extraction_llm_output
        else:
            out = llm.invoke(final_prompt)
        self.materials_extraction_out = out.content

        data = robust_json_parse(out.content)
        mats = data.get("materials", [])
        # Normalize to unique list of non-empty strings
        seen = set()
        result = []
        for m in mats:
            if not m or not isinstance(m, str):
                continue
            key = m.strip()
            if key and key not in seen:
                seen.add(key)
                result.append(key)
        self.materials_extraction_llm_output = out
        return result

    def extract_thermo_properties(self, fulltext: str, llm, material_names: Optional[List[str]] = None) -> Dict:
        self.fulltext = fulltext
        material_hint = ""
        if material_names:
            material_hint = self.get_materials_hint(material_names)

        if self.thermo_properties_extraction_prompt is None:
            raise PromptNotImplementedError("thermo_properties_extraction_prompt is not yet defined")
        prompt = PromptTemplate.from_template(self.thermo_properties_extraction_prompt)
        final_prompt = prompt.format(fulltext=fulltext, material_hint=material_hint, thermo_mat_limit=self.THERMO_MAT_LIMIT)

        self.thermo_properties_extraction_in = final_prompt
        if self.thermo_properties_extraction_llm_output is not None:
            print("Using saved llm output without actual request for therm. properties extraction node.")
            output = self.thermo_properties_extraction_llm_output
        else:
            output = llm.invoke(final_prompt)
        self.thermo_properties_extraction_out = output.content
        json_parsed = robust_json_parse(output.content)
        self.thermo_properties_extraction_llm_output = output
        return json_parsed
    
    def extract_structural_properties(self, fulltext: str, llm, material_names: Optional[List[str]] = None) -> Dict:
        self.fulltext = fulltext
        material_hint = ""
        if material_names:
            material_hint = self.get_materials_hint(material_names)
        if self.structure_properties_extraction_prompt is None:
            raise PromptNotImplementedError("structure_properties_extraction_prompt is not yet defined")
        prompt = PromptTemplate.from_template(self.structure_properties_extraction_prompt)
        final_prompt = prompt.format(fulltext=fulltext, material_hint=material_hint)
        self.structure_properties_extraction_in = final_prompt
        if self.structure_properties_extraction_llm_output is not None:
            print("Using saved llm output without actual request for structural properties extraction node.")
            output = self.structure_properties_extraction_llm_output
        else:
            output = llm.invoke(final_prompt)
        self.structure_properties_extraction_out = output.content
        json_parsed = robust_json_parse(output.content)
        self.structure_properties_extraction_llm_output = output
        return json_parsed

    def extract_from_tables(self, table_data: list, llm, material_names: Optional[List[str]] = None) -> dict:
        """Combine all tables and captions, and extract both thermo and structural fields."""
        if not table_data:
            return {"materials": []}

        # Material hint
        material_hint = ""
        if material_names:
            material_hint = self.get_materials_hint(material_names)

        # Combine all tables into one long string
        combined_block = ""
        for i, table in enumerate(table_data, 1):
            combined_block += f"### Table {i} Caption:\n{table['caption']}\n\n"
            combined_block += f"### Table {i} CSV Data:\n{json.dumps(table['rows'], indent=2)}\n\n"
        self.combined_block = combined_block

        # Prompt
        if self.table_data_extraction_prompt is None:
            raise PromptNotImplementedError("table_data_extraction_prompt is not yet defined")
        final_prompt = self.table_data_extraction_prompt.format(material_hint = material_hint, combined_block = combined_block)
        try:
            self.table_data_extraction_in = final_prompt
            if self.table_data_extraction_llm_output is not None:
                print("Using saved llm output without actual request for table data extraction node.")
                output = self.table_data_extraction_llm_output
            else:
                output = llm.invoke(final_prompt)
            self.table_data_extraction_out = output.content

            json_parsed = robust_json_parse(output.content)
            self.table_data_extraction_llm_output = output
            return json_parsed
        except Exception as e:
            print("❌ Table extraction failed:", e)
            return {"materials": []}

    def judge_verify_properties(self, fulltext: str, thermo_json: dict = None, structure_json: dict = None, table_json: dict = None, llm=None, folder_name: str = None) -> dict:
        """
        Validates thermoelectric numeric values (ZT, S, σ, ρ, PF, κ) and their temperature context
        against the full text and table data.  Also confirms each material has valid structural fields.
        Keeps all materials; removes only numeric values judged incorrect or temperature-mismatched.
        Logs [ok], [removed], [temp-mismatch], and [structure_ok] to judge_validation_log.txt.
        """

        # --- Merge all extracted JSON blocks ---
        merged = {"materials": []}
        for block in (thermo_json, structure_json, table_json):
            if block and block.get("materials"):
                merged["materials"].extend(block["materials"])

        if not merged["materials"]:
            return {"materials": [], "deleted": [], "notes": "No materials to judge."}

        # --- Build table context (captions + rows) if available ---
        table_context = ""
        try:
            if table_json and "table_data" in table_json:
                all_tables = table_json["table_data"]
            else:
                all_tables = []
        except Exception:
            all_tables = []

        if all_tables:
            table_context += "\n\n### Table Contexts (from paper):\n"
            for i, t in enumerate(all_tables, 1):
                caption = t.get("caption", "")
                rows = json.dumps(t.get("rows", []), indent=2)
                table_context += f"\nTable {i} Caption:\n{caption}\n\nRows:\n{rows}\n"

        # --- Prompt: thermoelectric numeric + temperature + structural verification ---
        if self.judge_prompt is None:
            raise PromptNotImplementedError("judge_prompt is not yet defined")
        final_prompt = PromptTemplate.from_template(self.judge_prompt).format(fulltext=fulltext,table_context=table_context,merged_json=json.dumps(merged, indent=2))

        # --- Run model ---
        self.judge_in = final_prompt
        if self.judge_llm_output is not None:
            print("Using saved llm output without actual request for judge node.")
            res = self.judge_llm_output
        else:
            res = llm.invoke(final_prompt)
        self.judge_out = res.content

        # --- Parse output safely ---
        try:
            verdict = robust_json_parse(res.content)
            if not isinstance(verdict, dict):
                raise ValueError("Judge output is not a dict")

            correct = verdict.get("correct", {}) or {}
            incorrect = verdict.get("incorrect", {}) or {}
            temp_mismatch = verdict.get("temp_mismatch", {}) or {}
            structure_ok = verdict.get("structure_ok", []) or []
            notes = verdict.get("notes", "")
        except Exception as e:
            with open("judge_error_log.txt", "a", encoding="utf-8") as log:
                log.write("\n" + "=" * 60 + "\n")
                log.write(f"TIME: {datetime.datetime.now().isoformat()}\n")
                log.write(f"FOLDER: {folder_name or os.getcwd()}\n")
                log.write(f"ERROR: {repr(e)}\n")
                log.write(f"RAW OUTPUT:\n{res.content if hasattr(res, 'content') else str(res)}\n")
                log.write("=" * 60 + "\n")
            print(f"⚠️ Judge parsing failed → {e}")
            return merged  # fallback: keep everything

        # --- Local filtering + validation logging ---
        cleaned = []
        log_lines = []

        for mat in merged["materials"]:
            name = mat.get("name", "")

            mat_incorrect = incorrect.get(name, {})
            mat_temp_mismatch = temp_mismatch.get(name, {})
            mat_correct = correct.get(name, {})

            # Remove incorrect numeric values
            for key, bad_values in mat_incorrect.items():
                for prop_key in list(mat.keys()):
                    if key.lower() in prop_key.lower() and isinstance(mat[prop_key], list):
                        before = len(mat[prop_key])
                        mat[prop_key] = [
                            v for v in mat[prop_key]
                            if not any(
                                (isinstance(bad, (int, float)) and bad == v.get("value"))
                                or (isinstance(bad, (int, float)) and bad == v.get(f"{key}_value"))
                                for bad in bad_values
                            )
                        ]
                        after = len(mat[prop_key])
                        if before > after:
                            for val in bad_values:
                                log_lines.append(f"[removed] {name}.{key}={val}")

            # Remove temperature-mismatched values
            for key, mismatch_list in mat_temp_mismatch.items():
                for prop_key in list(mat.keys()):
                    if key.lower() in prop_key.lower() and isinstance(mat[prop_key], list):
                        for bad in mismatch_list:
                            val = bad.get("value")
                            mat[prop_key] = [
                                v for v in mat[prop_key]
                                if val != v.get("value") and val != v.get(f"{key}_value")
                            ]
                            log_lines.append(f"[temp-mismatch] {name}.{key} value={val} "
                                            f"reported_T={bad.get('reported_T')} found_T={bad.get('found_T')}")

            # Log correct and structural info
            for key, ok_values in mat_correct.items():
                for val in ok_values:
                    log_lines.append(f"[ok] {name}.{key}={val}")

            if name in structure_ok:
                log_lines.append(f"[structure_ok] {name}")

            cleaned.append(mat)

        # --- Write validation log ---
        with open("judge_validation_log.txt", "a", encoding="utf-8") as log:
            log.write("\n" + "=" * 60 + "\n")
            log.write(f"TIME: {datetime.datetime.now().isoformat()}\n")
            log.write(f"FOLDER: {folder_name or os.path.basename(os.getcwd())}\n")
            log.write("\n".join(log_lines))
            log.write("\n" + "=" * 60 + "\n")

        print(f"🧾 Judge log: {len(log_lines)} entries validated for this folder.")
        self.judge_llm_output = res
        return {"materials": cleaned, "notes": notes}

    def hide_fulltext(self, text : str, n : int = 30) -> str:
        if not self.fulltext:
            return text  # чтобы не делать бесконечные "вхождения" пустой строки

        if self.fulltext in text:
            shortened = self.fulltext if len(self.fulltext) <= 2 * n else (self.fulltext[:n] + "... FILTERED ARTICLE TEXT ..." + self.fulltext[-n:])
            return text.replace(self.fulltext, shortened)

        return text
    
    def hide_combined_block(self, text : str, n : int = 30) -> str:
        if not self.combined_block:
            return text  # чтобы не делать бесконечные "вхождения" пустой строки

        if self.combined_block in text:
            shortened = self.combined_block if len(self.combined_block) <= 2 * n else (self.combined_block[:n] + "... TABLES COMBINED BLOCK ..." + self.combined_block[-n:])
            return text.replace(self.combined_block, shortened)
