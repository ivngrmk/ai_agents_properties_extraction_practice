import os
import json
import pandas as pd
from typing import Any, Dict, List

def _dedupe_list(items: List[Any]) -> List[Any]:
    """Deduplicate list items, including dict/list items (stable order)."""
    seen = set()
    out = []
    for x in items:
        # make hashable key
        if isinstance(x, (dict, list)):
            key = json.dumps(x, sort_keys=True, ensure_ascii=False)
        else:
            key = str(x)
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out

def merge_values(a: Any, b: Any) -> Any:
    """
    Merge two values with rules:
    - None is neutral
    - list: concat + dedupe
    - dict: recursive merge
    - scalar: keep first non-None; if both non-None and different -> keep a (stable)
    """
    if a is None:
        return b
    if b is None:
        return a

    if isinstance(a, list) and isinstance(b, list):
        return _dedupe_list(a + b)

    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, vb in b.items():
            out[k] = merge_values(out.get(k), vb)
        return out

    # If types differ (e.g., list vs scalar), keep a, but if a is "empty-ish" and b not, take b.
    if type(a) != type(b):
        if a in ("", [], {}):
            return b
        return a

    # Scalars (str/int/float/bool): keep first non-None (a)
    return a

def normalize_name(name: Any) -> str:
    if not isinstance(name, str):
        return ""
    return " ".join(name.strip().split())

def compile_table(directory: str) -> None:
    t_json_path = os.path.join(directory, "t.json")
    with open(t_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    materials = data.get("materials", [])
    if not isinstance(materials, list):
        materials = []

    # --- merge by material name ---
    merged_by_name: Dict[str, Dict[str, Any]] = {}
    unnamed: List[Dict[str, Any]] = []

    for mat in materials:
        if not isinstance(mat, dict):
            continue
        name = normalize_name(mat.get("name"))
        if not name:
            unnamed.append(mat)
            continue

        if name not in merged_by_name:
            merged_by_name[name] = dict(mat)
        else:
            acc = merged_by_name[name]
            # ensure name preserved
            acc["name"] = name
            for k, v in mat.items():
                if k == "name":
                    continue
                acc[k] = merge_values(acc.get(k), v)

    merged_materials = list(merged_by_name.values()) + unnamed

    # --- make DataFrame (flatten: dict/list -> json string) ---
    flattened_rows = []
    for mat in merged_materials:
        row = {}
        for key, value in mat.items():
            if value is None:
                row[key] = None
            elif isinstance(value, (dict, list)):
                row[key] = json.dumps(value, ensure_ascii=False)
            else:
                row[key] = value
        flattened_rows.append(row)

    df = pd.json_normalize(flattened_rows)

    output_path = os.path.join(directory, "materials_output.csv")
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"Сохранено: {output_path}")
