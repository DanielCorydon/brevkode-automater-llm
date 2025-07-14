from typing import TypedDict


class StringReplacementInput(TypedDict):
    text: str
    old: str
    new: str


class StringReplacementOutput(TypedDict):
    modified_text: str


def replace_string_in_text(
    input_dict: StringReplacementInput,
) -> StringReplacementOutput:
    """
    Replace all occurrences of a specific substring in a text with another substring.

    Args:
        input_dict (StringReplacementInput): Dictionary containing:
            text (str): The original text where replacements should be made.
            old (str): The substring you want to find and replace.
            new (str): The substring to insert in place of each occurrence of 'old'.

    Returns:
        StringReplacementOutput: Dictionary containing:
            modified_text (str): The modified text with all instances of 'old' replaced by 'new'.
    """
    print(
        f"[TOOL DEBUG] replace_string_in_text called with text='{input_dict['text'][:50]}...', "
        f"old='{input_dict['old']}', new='{input_dict['new']}'"
    )
    result = input_dict["text"].replace(input_dict["old"], input_dict["new"])
    print(f"[TOOL DEBUG] Result: '{result[:50]}...'")
    return {"modified_text": result}


def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b
