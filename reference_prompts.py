MATERIALS_EXTRACTION_REF_PROMPT = """
    You are a scientific reading assistant. From the text below, list material names
    (compounds, alloys, doped variants like "Bi2Te3", "SnSe:Na", "PbTe-AgSbTe2", "TiS2", "PEDOT:PSS", etc.)
    that have ANY thermoelectric property mentioned close by (e.g., ZT, Seebeck S, electrical conductivity σ,
    resistivity ρ, power factor PF, thermal conductivity κ). 

    Rules:
    - Only include materials for which at least one thermo property is discussed.
    - Keep names as they appear (including dopants/phase labels when relevant).
    - Return a JSON object with a single array "materials".
    - Deduplicate.
    - Limit to the first {max_materials} items.

    Return JSON:
    {{
    "materials": ["...", "..."]
    }}

    Text:
    ```{fulltext}```
""".strip()

THERMO_PROPERTIES_EXTRACTION_REF_PROMPT = """
    You are a research extraction agent for thermoelectric materials.
    {material_hint}
    Extract per-material properties:
    - name only, nothing extra string labels.
    - ZT (figure of merit)
    - σ (electrical conductivity)
    - S (Seebeck coefficient)
    - PF (power factor)
    - κ (thermal conductivity)
    - ρ (electrical resistivity)

    For each property, extract **numeric values** along with **temperature** and **units** if mentioned.

    Instructions:
    - Place materials with fillev values at the top of the list.
    - Set missing values to null strictly.
    - Only include materials name nothing extra string labels.
    - Don't do any calculation or unit conversion on your own.
    - If multiple values exist, return all of them as separate dictionary entries.
    - If more than {thermo_mat_limit} materials are found, include only the first {thermo_mat_limit}.
    - All field names and string values must use **valid JSON syntax** (double quotes).
    - Keep numerical values unquoted (i.e., not strings).
    - Nothing else should be included in the output strictly.

    Return structured JSON:
    {{
    "materials": [
        {{
        "name": "...",
        "zt_values": [{{"value": ..., "ZT_temperature": ..., "ZT_temperature_unit": "..."}}],
        "electrical_conductivity": [{{"σ_value": ..., "σ_unit": "...", "σ_Temperature": "...", "σ_Temp_unit": "..."}}],
        "electrical_resistivity": [{{"ρ_value": ..., "ρ_unit": "...", "ρ_Temperature": "...", "ρ_Temp_unit": "..."}}],                                   
        "seebeck_coefficient": [{{"S_value": ..., "S_unit": "...",  "S_Temperature": "...", "S_Temp_unit": "..."}}],
        "power_factor": [{{"PF_value": ..., "PF_unit": "...", "PF_Temperature": "...", "PF_Temp_unit": "..."}}],
        "thermal_conductivity": [{{"κ_value": ..., "κ_unit": "...", "κ_Temperature": "...", "κ_Temp_unit": "..."}}]
        }}
    ]
    }}

    Text:
    ```{fulltext}```
""".strip()

STRUCTURE_PROPERTIES_EXTRACTION_REF_PROMPT = """
    You are a structural extraction agent for thermoelectric materials.
    {material_hint}
    For each material, extract:
    - name only, nothing extra string labels.
    - compound_type, crystal_structure, lattice_structure
    - space_group
    - doping_type and list of dopants
    - processing_method
    Instructions:
    - Set missing values to null strictly.
    - Only include materials name nothing extra string labels.
    - If more than 10 materials are found, include only the first 10.
    - All field names and string values must use **valid JSON syntax** (double quotes).
    - Set missing values to null strictly.
    - All field values must follow **valid JSON syntax** with double quotes.
    - Nothing else should be included in the output strictly.
                                            
    Return JSON:
    {{
    "materials": [
        {{
        "name": "...",
        "compound_type": "<type|null>",
        "crystal_structure": "<structure|null>",
        "lattice_structure": "<structure|null>",
        "space_group": "<group|null>",
        "doping": {{
            "doping_type": "<type|null>",
            "dopants": [<strings>]
        }},
        "processing_method": "<string|null>"
        }}
    ]
    }}

    Text:
    ```{fulltext}```
""".strip()

TABLE_DATA_EXTRACTION_REF_PROMPT = """
    You are a scientific table extraction agent working on thermoelectric materials.
    {material_hint}
    Below is a collection of tables and their captions from a scientific paper.

    Extract all materials mentioned across the tables and return the following properties for each:

    Thermoelectric:
    - ZT (figure of merit)
    - Seebeck coefficient (S)
    - Electrical conductivity (σ)
    - Electrical resistivity (ρ)
    - Power factor (PF)
    - Thermal conductivity (κ)

    Structural:
    - compound_type
    - crystal_structure
    - lattice_structure
    - space_group
    - doping_type and list of dopants
    - processing_method

    Instructions:
    - Set missing values to null strictly.
    - Only include materials name nothing extra string labels.
    - If more than 10 materials are found, include only the first 10.
    - All field names and string values must use **valid JSON syntax** (double quotes).
    - Set missing values to null strictly.
    - All field values must follow **valid JSON syntax** with double quotes.
    - Nothing else should be included in the output strictly.

    Return structured JSON like:
    {{
    "materials": [
        {{
        "name": "...",
        "zt_values": [{{"value": ..., "ZT_temperature": ..., "ZT_temperature_unit": "..."}}],
        "electrical_conductivity": [{{"σ_value": ..., "σ_unit": "...", "σ_Temperature": "...", "σ_Temp_unit": "..."}}],
        "electrical_resistivity": [{{"ρ_value": ..., "ρ_unit": "...", "ρ_Temperature": "...", "ρ_Temp_unit": "..."}}],
        "seebeck_coefficient": [{{"S_value": ..., "S_unit": "...",  "S_Temperature": "...", "S_Temp_unit": "..."}}],
        "power_factor": [{{"PF_value": ..., "PF_unit": "...", "PF_Temperature": "...", "PF_Temp_unit": "..."}}],
        "thermal_conductivity": [{{"κ_value": ..., "κ_unit": "...", "κ_Temperature": "...", "κ_Temp_unit": "..."}}],
        "compound_type": "<type|null>",
        "crystal_structure": "<structure|null>",
        "lattice_structure": "<structure|null>",
        "space_group": "<group|null>",
        "doping": {{
            "doping_type": "<type|null>",
            "dopants": [<strings>]
        }},
        "processing_method": "<string|null>"
        }}
    ]
    }}

    All missing values must be explicitly set as null strictly.

    ### Tables and Captions:
    {combined_block}
""".strip()

JUDGE_REF_PROMPT = """
    You are a scientific verifier.

    Given the full paper text, any tables with captions, and the extracted materials JSON,
    validate each **thermoelectric numeric property** and its **temperature context**.

    Thermoelectric properties to check only:
    - ZT (figure of merit)
    - Seebeck coefficient (S)
    - Electrical conductivity (σ)
    - Electrical resistivity (ρ)
    - Power factor (PF)
    - Thermal conductivity (κ)

    Rules for numeric validation:
    - For each numeric value, check whether the same or close value (and its temperature, if mentioned)
    appears in the text or tables.
    - If both value and temperature are consistent → mark as correct.
    - If value is correct but the temperature is inconsistent → mark as temp_mismatch.
    - If value not found or implausible → mark as incorrect.
    - If temperature is missing but value matches → mark as correct_no_temp.
    - Never invent, average, or modify numbers.

    Rules for structural validation:
    - For each material, check whether its structural fields (compound_type, crystal_structure,
    lattice_structure, space_group, doping_type, processing_method) exist and look syntactically valid.
    - If all these fields exist or are null (but properly formatted) → mark structure_ok.
    - Do not delete structural information.

    Return strictly valid JSON:
    {{
    "correct": {{
        "Material": {{"ZT": [1.2], "S": [220]}},
    }},
    "incorrect": {{
        "Material": {{"ZT": [3.5]}},
    }},
    "temp_mismatch": {{
        "Material": {{"ZT": [{{"value":1.2,"reported_T":300,"found_T":700}}]}},
    }},
    "structure_ok": ["MaterialA","MaterialB"],
    "notes": "short explanation"
    }}

    Always include all four top-level keys even if empty.
    Use double quotes for all keys and string values.
    Enclose entire output in {{ }}.

    ### Full Paper Text
    ```{fulltext}```

    ### Table Captions and Data
    ```{table_context}```

    ### Merged JSON of Extracted Values
    ```{merged_json}```
""".strip()
