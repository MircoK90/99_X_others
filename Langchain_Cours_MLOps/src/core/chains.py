from .llm import llm
from src.prompts.prompts import (
    classification_prompt,
    summary_prompt,
    translation_prompt
)
from src.core.parsers import (
    classification_parser,
    summary_parser,
    translation_parser
)

# Classification
classification_chain = classification_prompt | llm | classification_parser

# Summary
summary_chain = summary_prompt | llm | summary_parser

# Translation
translation_chain = translation_prompt | llm | translation_parser