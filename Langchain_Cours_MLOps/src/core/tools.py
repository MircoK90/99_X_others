from langchain.tools import tool

@tool
def word_count(text: str) -> int:
    """Counts the number of words in a text."""
    return len(text.split())

@tool
def char_count(text: str) -> int:
    """Counts the number of characters in a text."""
    return len(text)