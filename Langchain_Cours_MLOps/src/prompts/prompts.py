from langchain_core.prompts import ChatPromptTemplate

# Classification
classification_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an assistant that suggests a relevant category for a text."),

    ("human", "Text: 'Deep neural networks are revolutionizing machine learning.'"),
    ("ai", '{{"category": "Artificial Intelligence", "confidence": 0.95}}'),

    ("human", "Text: 'Docker and Kubernetes make it easier to deploy applications in the cloud.'"),
    ("ai", '{{"category": "Cloud", "confidence": 0.9}}'),

    ("human",
     "Analyze the following text and propose ONLY one suitable category:\n\n"
     "Text: {input}\n\n"
     "{format_instructions}")
])

# Summary
summary_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an assistant that summarizes texts."),
    ("human",
     "Summarize the following text and make sure to keep the most important keywords.\n\n"
     "IMPORTANT: Respond ONLY with valid JSON, no text outside the JSON.\n\n"
     "Text: {input}\n\n"
     "{format_instructions}")
])

# Translation
translation_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a professional translator."),
    ("human",
     "Translate this text into French: {input}\n\n"
     "IMPORTANT: Respond ONLY with valid JSON. "
     "Use double quotes for the JSON string values. "
     "Do not escape apostrophes inside text. "
     "If the text contains quotes, escape them with a backslash (\\\")."
     "{format_instructions}")
])