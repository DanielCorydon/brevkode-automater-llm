# This file will contain all the langgraphs function tools that our agent will have access to.


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
