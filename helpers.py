import re
import ast
import json
import json5

def safe_doi(doi: str) -> str:
    # Remove "/" and other forbidden chars, keep dots and dashes.
    return re.sub(r"[^\w\-.]", "", doi)

def robust_json_parse(text: str) -> dict:
    """Tries multiple strategies to recover valid JSON from LLM output."""
    if hasattr(text, "content"):
        text = text.content

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
        return {"materials": []}
