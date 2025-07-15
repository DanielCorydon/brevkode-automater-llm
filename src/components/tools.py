"""
Tool functions for document processing and mapping replacements.
"""

import os
import pandas as pd


# --- Minimal Excel mapping loader ---
def load_excel_mapping(path):
    try:
        df = pd.read_excel(path, sheet_name=None)
        # Try to find the right sheet ("query" or first sheet)
        sheet = df["query"] if "query" in df else next(iter(df.values()))
        # Expect columns: "Titel" and "Nøgle"
        if "Titel" in sheet.columns and "Nøgle" in sheet.columns:
            return dict(zip(sheet["Titel"], sheet["Nøgle"]))
    except Exception:
        pass
    return {}


# Path to default mapping Excel (relative to this file)
DEFAULT_MAPPING_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "documents",
    "Liste over alle nøgler.xlsx",
)
MAPPINGS_DICT = load_excel_mapping(DEFAULT_MAPPING_PATH)


def search_and_replace(text: str, search: str, replace: str) -> str:
    """
    Search for all occurrences of 'search' in 'text' and replace them with 'replace'.

    Args:
        text (str): The input text.
        search (str): The substring to search for.
        replace (str): The substring to replace with.

    Returns:
        str: The modified text with replacements.
    """
    return text.replace(search, replace)


# --- New tool: Replace any occurrence of a Title (Titel) with its corresponding Nøgle ---
def replace_titels_with_nogle(text: str, replacement_template: str) -> str:
    """
    Replace all occurrences of each 'Titel' in the mapping Excel with the replacement_template.
    If '<NØGLE>' is present in the template, it is replaced with the corresponding key (Nøgle).

    Args:
        text (str): The input text.
        replacement_template (str): The template to replace each Titel. Use '<NØGLE>' to insert the key.

    Returns:
        str: The modified text.
    """
    result = text
    for titel, nøgle in MAPPINGS_DICT.items():
        if titel:
            if "<NØGLE>" in replacement_template:
                replacement = replacement_template.replace("<NØGLE>", str(nøgle))
            else:
                replacement = replacement_template
            result = result.replace(str(titel), replacement)
    return result
