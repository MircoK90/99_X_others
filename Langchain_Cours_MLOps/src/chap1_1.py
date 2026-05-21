# # from src.prompts.prompts import classification_prompt    overwritting!
# from langchain_core.prompts import ChatPromptTemplate


# classification_prompt = ChatPromptTemplate.from_messages([
#     ("system", "You are an assistant that analyzes text and suggests a relevant category."),
#     ("human", "Text : {input}")
# ])

# messages = classification_prompt.format_messages(
#     input="LangChain is an open-source framework.",
# )
# print(messages)

from src.core.chains import (
    classification_chain,
    summary_chain,
    translation_chain
)
from src.core.parsers import (
    classification_parser,
    summary_parser,
    translation_parser
)

text = """
Artificial intelligence is a concept coined in the mid-1950s...
"""

print("\n--- Classification ---")
response = classification_chain.invoke({
    "input": text,
    "format_instructions": classification_parser.get_format_instructions()
})
print("Category:", response.category)
print("Confidence:", response.confidence)

print("\n--- Summary ---")
response = summary_chain.invoke({
    "input": text,
    "format_instructions": summary_parser.get_format_instructions()
})
print("Summary:", response.summary)

print("\n--- Translation ---")
response = translation_chain.invoke({
    "input": text,
    "format_instructions": translation_parser.get_format_instructions()
})
print("Translated:", response.translated_text)