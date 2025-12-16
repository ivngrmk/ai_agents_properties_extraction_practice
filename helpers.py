import re
import ast
import json
import json5

class JSONParsingError(Exception):
    pass

def safe_doi(doi: str) -> str:
    # Remove "/" and other forbidden chars, keep dots and dashes.
    return re.sub(r"[^\w\-.]", "", doi)

def normalize_quotes(s: str) -> str:
    # “умные” одинарные и двойные кавычки + разные похожие апострофы
    table = str.maketrans({
        "\u2018": "'",  # ‘
        "\u2019": "'",  # ’
        "\u201A": "'",  # ‚
        "\u201B": "'",  # ‛
        "\u2032": "'",  # ′ (prime)
        "\u2035": "'",  # ‵ (reversed prime)
        "\u02BC": "'",  # ʼ (modifier letter apostrophe)
        "\uFF07": "'",  # ＇ (fullwidth apostrophe)

        "\u201C": '"',  # “
        "\u201D": '"',  # ”
        "\u201E": '"',  # „
        "\u201F": '"',  # ‟
        "\u2033": '"',  # ″ (double prime)
        "\u2036": '"',  # ‶ (reversed double prime)
        "\uFF02": '"',  # ＂ (fullwidth quotation mark)
    })
    return s.translate(table)

def robust_json_parse(text: str) -> dict:
    """Tries multiple strategies to recover valid JSON from LLM output."""
    if hasattr(text, "content"):
        text = text.content
    text = normalize_quotes(text)

    # Strip Markdown formatting
    text = text.strip().removeprefix("```json").removesuffix("```").strip()

    # Try to extract first complete JSON object or array
    match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    if match:
        text = match.group(1)

    # Clean trailing commas
    text = re.sub(r',\s*([\]}])', r'\1', text)

    # Replace invalid constructs
    text = text.replace("None", "null")
    text = text.replace("'", '"')

    # Try standard JSON parse
    try:
        return json.loads(text)
    except:
        pass

    # Try JSON5
    try:
        return json5.loads(text)
    except:
        pass

    # Try Python literal eval (if it looks like a dict)
    try:
        return ast.literal_eval(text)
    except Exception as e:
        print("❌ JSON parse failed completely:", e)
        raise JSONParsingError
        return {"materials": []}
