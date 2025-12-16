import os
import json
import traceback
import pandas as pd
from pathlib import Path
from typing import Any, TypedDict, Optional, List, Dict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from abc import ABC, abstractmethod

class State(TypedDict):
    folder: Path
    fulltext: Optional[str]
    llm: Optional[Any]
    material_names: Optional[list]
    thermo: Optional[dict]
    structure: Optional[dict]
    retries: int
    table_data: Optional[list]
    table_json_output: Optional[dict]
    total_table_rows: Optional[int]
    skip: bool

class BasePropertiesExtractor(ABC):
    TIME_DELAYS = True
    SHORT_TIME_DELAY_MIN_S = 4
    SHORT_TIME_DELAY_MAX_S = 10
    LONG_TIME_DELAY_S = 60

    MAX_MATERIALS = 30
    FIND_MATERIALS_MAX_TOKENS = 512*100
    DEFAULT_TOKEN_COUNT = 999*2

    def __init__(self) -> None:
        self.state : Optional[State] = None
        self.app = self.build_app()

        self.model_name = os.getenv("OPENAI_MODEL")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.api_key = os.getenv("OPENAI_API_KEY")

        missing = [k for k, v in {
            "OPENAI_MODEL": self.model_name,
            "OPENAI_BASE_URL": self.base_url,
            "OPENAI_API_KEY": self.api_key,
        }.items() if not v]

        if missing:
            raise RuntimeError(f"Missing required env variables: {', '.join(missing)}")

    @abstractmethod
    def extract_material_candidates(self, fulltext: str, llm, max_materials: int = 20) -> List[str]:
        raise NotImplementedError
    
    @abstractmethod
    def extract_thermo_properties(self, fulltext: str, llm, material_names: Optional[List[str]] = None) -> Dict:
        raise NotImplementedError
    
    @abstractmethod
    def extract_structural_properties(self, fulltext: str, llm, material_names: list = None) -> Dict:
        raise NotImplementedError
    
    @abstractmethod
    def extract_from_tables(self, table_data: list, llm, material_names: list = None) -> dict:
        raise NotImplementedError
    
    @abstractmethod
    def judge_verify_properties(self,
                            fulltext: str,
                            thermo_json: dict = None,
                            structure_json: dict = None,
                            table_json: dict = None,
                            llm=None,
                            folder_name: str = None) -> dict:
        raise NotImplementedError
    
    @staticmethod
    def read_fulltext(file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def extract_properties(self, paper_folder: Path) -> None:
        self.state = self._generate_empty_state(paper_folder)
        self.app.invoke(self.state)

    def build_app(self) -> StateGraph:
        # === Graph Wiring ===
        graph = StateGraph(State)
        graph.add_node("read_file", self._read_fulltext_node)
        graph.add_node("set_tokens", self._set_tokens_node)
        graph.add_node("Find_materials", self._find_materials_node)
        graph.add_node("Thermoelectric_prop", self._extract_thermo_node)
        graph.add_node("Structural_prop", self._extract_structure_node)
        graph.add_node("Plan_table_tokens", self._count_table_and_plan_tokens_node)
        graph.add_node("Extract_table_JSON", self._extract_table_json_node)
        graph.add_node("Judge_verification", self._judge_node)
        graph.add_node("Write_json", self._write_node)
        # === Define Edges ===
        graph.set_entry_point("read_file")
        graph.add_edge("read_file", "set_tokens")

        graph.add_conditional_edges("set_tokens", self._skip_if_zero_tokens, {
            END: END,
            "Find_materials": "Find_materials"
        })

        graph.add_conditional_edges("Find_materials", self._skip_if_no_materials, {
            END: END,
            "Thermoelectric_prop": "Thermoelectric_prop"
        })

        graph.add_edge("Thermoelectric_prop", "Structural_prop")
        graph.add_edge("Structural_prop", "Plan_table_tokens")



        graph.add_conditional_edges("Plan_table_tokens", self._table_branch, {
            "has_tables": "Extract_table_JSON",
            "no_tables": "Judge_verification"
        })

        graph.add_edge("Extract_table_JSON", "Judge_verification")
        graph.add_edge("Judge_verification", "Write_json")
        graph.add_edge("Write_json", END)

        # === Compile ===
        app = graph.compile()
        print("📊 Graph compiled.")
        return app

    @staticmethod
    def _generate_empty_state(paper_folder : str) -> State:
        return State(
            folder = paper_folder,
            fulltext = None,
            llm = None,
            material_names = None,
            thermo = None,
            structure = None,
            retries = 0,
            skip = False,
            table_data = None,
            table_json_output = None,
            total_table_rows = 0
        )

    def _read_fulltext_node(self, state: State) -> State:
        text = self.read_fulltext(os.path.join(state["folder"],"fulltext.txt"))
        return {**state, "fulltext": text, "retries": 0}

    def _set_tokens_node(self, state: State) -> State:
        folder = state["folder"]
        token_count = self.DEFAULT_TOKEN_COUNT

        if token_count == 0:
            print(f"⏭️ Skipping {os.path.basename(folder)} due to token_count = 0")
            return {**state, "skip": True}

        # Compute max_tokens
        max_tok = self._token_estimation(token_count)
        print(f"🧠 Setting max_tokens = {max_tok} for {os.path.basename(folder)} (token_count = {token_count})")

        dynamic_llm = ChatOpenAI(
            model=self.model_name,
            base_url=self.base_url,
            api_key=self.api_key,
            temperature=0.001,
            max_tokens=max_tok
        )
        return {**state, "llm": dynamic_llm, "skip": False}

    def _find_materials_node(self, state: State) -> State:
        # Use a small fixed-token LLM just for this step
        small_llm = ChatOpenAI(
            model=self.model_name,
            base_url=self.base_url,
            api_key=self.api_key,
            temperature=0.001,
            max_tokens=self.FIND_MATERIALS_MAX_TOKENS   # fixed small cap for efficiency
        )
        candidates = self.extract_material_candidates(state["fulltext"], llm=small_llm, max_materials=self.MAX_MATERIALS)
        if candidates:
            print(f"🧪 Candidate materials (thermo-mentioned): {len(candidates)} → {candidates}")
            return {**state, "material_names": candidates, "skip": False}

        print("🛑 No thermo-related materials found → skipping downstream extraction.")
        return {**state, "material_names": [], "skip": True}

    def _extract_thermo_node(self, state: State) -> State:
        thermo = self.extract_thermo_properties(
            state["fulltext"],
            llm=state["llm"],
            material_names=state.get("material_names") or None
        )
        if not thermo.get("materials") or not isinstance(thermo["materials"], list):
            raise ValueError("❌ Thermo extraction returned no valid materials.")
        return {**state, "thermo": thermo}

    def _extract_structure_node(self, state: State) -> State:
        # Prefer the candidate list; if thermo produced better names, you can also merge.
        hint_names = state.get("material_names") or []
        # Optional improvement: union with names discovered by thermo to tighten recall.
        thermo_names = [m.get("name") for m in state.get("thermo", {}).get("materials", []) if m.get("name")]
        merged = list(dict.fromkeys([*hint_names, *thermo_names]))  # preserve order & dedupe
        struct = self.extract_structural_properties(state["fulltext"], llm=state["llm"], material_names=merged or None)
        if not struct.get("materials"):
            raise ValueError("❌ Structure JSON parse failed or empty.")
        return {**state, "structure": struct, "material_names": merged}

    def _count_table_and_plan_tokens_node(self, state: State) -> State:
        folder = state["folder"]
        table_data = []
        total_rows = 0
        i = 1

        while True:
            csv_path = os.path.join(folder,f"table{i}.csv")
            caption_path = os.path.join(folder,f"table{i}_caption.txt")
            if not os.path.isfile(csv_path) or not os.path.isfile(caption_path):
                break
            try:
                df = pd.read_csv(csv_path)
                with open(caption_path, "r", encoding="utf-8") as f:
                    caption = f.read().strip()
                row_count = len(df)
                table_data.append({
                    "filename": f"table{i}.csv",
                    "caption": caption,
                    "rows": df.to_dict(orient="records"),
                    "row_count": row_count
                })
                total_rows += row_count
            except Exception as e:
                print(f"⚠️ Failed reading {os.path.basename(csv_path)}: {e}")
            i += 1

        # Initialize max_tokens based on row count
        if total_rows == 0:
            max_tokens = 512*2  # Default to 512 if no rows are found
        else:
            max_tokens = min(512*2 + total_rows * 325, 2*5120)  # Heuristic calculation

        # Ensure dynamic_llm always gets updated with max_tokens
        dynamic_llm = ChatOpenAI(
            model=self.model_name,
            base_url=self.base_url,
            api_key=self.api_key,
            temperature=0.001,
            max_tokens=max_tokens
        )

        print(f"📊 Found {len(table_data)} tables with {total_rows} rows → max_tokens = {max_tokens}")

        return {
            **state,
            "table_data": table_data,
            "total_table_rows": total_rows,
            "llm": dynamic_llm  # override with expanded LLM
        }

    def _extract_table_json_node(self, state: State) -> State:
        if not state.get("table_data"):
            return {**state, "table_json_output": {"materials": []}}

        output = self.extract_from_tables(
            table_data=state["table_data"],
            llm=state["llm"],
            material_names=state.get("material_names")
        )
        return {**state, "table_json_output": output}

    def _judge_node(self, state: State) -> State:
        folder = state["folder"]
        llm_judge = ChatOpenAI(
            model=self.model_name,
            base_url=self.base_url,
            api_key=self.api_key,
            temperature=0.0,
            max_tokens=self.FIND_MATERIALS_MAX_TOKENS
        )
        try:
            print(f"🧠 Running property-level LLM Judge for {os.path.basename(folder)}...")
            judged = self.judge_verify_properties(
                fulltext=state["fulltext"],
                thermo_json=state.get("thermo"),
                structure_json=state.get("structure"),
                table_json=state.get("table_json_output"),
                llm=llm_judge,
                folder_name=os.path.basename(folder)
            )
            return {**state, "thermo": judged}

        except Exception as e:
            # absolute fallback – never let error escape
            log_path = "judge_error_log.txt"
            with open(log_path, "a", encoding="utf-8") as log:
                log.write("\n" + "=" * 60 + "\n")
                #log.write(f"TIME: {datetime.datetime.now().isoformat()}\n")
                log.write(f"FOLDER: {os.path.basename(folder)}\n")
                log.write(f"ERROR TYPE: {type(e).__name__}\n")
                log.write(f"DETAILS: {repr(e)}\n")
                log.write(f"TRACEBACK:\n{traceback.format_exc()}\n")
                log.write("=" * 60 + "\n")
            print(f"⚠️ Judge node crashed in {os.path.basename(folder)}: {e}")
            return state  # continue pipeline unchanged

    def _write_node(self, state: State) -> State:
        folder = state["folder"]
        with open(os.path.join(folder,"t.json"), "w", encoding='utf-8') as f:
            json.dump(state["thermo"], f, indent=2)
        with open(os.path.join(folder,"s.json"), "w", encoding='utf-8') as f:
            json.dump(state["structure"], f, indent=2)
        if state.get("table_json_output") and state["table_json_output"].get("materials"):
            with open(os.path.join(folder,"tables_output.json"), "w", encoding='utf-8') as f:
                json.dump(state["table_json_output"], f, indent=2)
        print(f"✅ Done: {os.path.basename(folder)}")
        return state

    # === Retry Decision Function ===
    @staticmethod
    def _skip_if_zero_tokens(state: State) -> str:
        return END if state.get("skip") else "Find_materials"

    @staticmethod
    def _skip_if_no_materials(state: State) -> str:
        return END if state.get("skip") else "Thermoelectric_prop"

    @staticmethod
    def _table_branch(state: State) -> str:
        return "has_tables" if state.get("table_data") else "no_tables"

    @classmethod
    def _token_estimation(cls, token_count):
        if token_count <= 1000:
            max_tok = 786
        elif token_count <= 3000:
            max_tok = 1024
        else:
            extra = (token_count - 3000) // 1000
            max_tok = 1024 + (512 * (extra + 1))
            max_tok = min(max_tok, 5120)
        max_tok = cls.FIND_MATERIALS_MAX_TOKENS
        return max_tok
