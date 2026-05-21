# env loaded?
# from dotenv import load_dotenv
# import os

# load_dotenv()  # Load environment variables from .env file

# print(os.getenv("GROQ_API_KEY"))



from langchain_core.prompts import ChatPromptTemplate

# Classification 
classification_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an assistant that analyzes text and suggests a relevant category."),

    # Example 1
    ("human", "Text: 'The neural network was trained on medical images.'"),
    ("ai", "AI"),

    # Example 2
    ("human", "Text: 'We stored patient data on a Hadoop cluster.'"),
    ("ai", "Databases"),

    # Example 3
    ("human", "Text: 'AWS provides computing and storage services.'"),
    ("ai", "Cloud"),

    # New text to classify
    ("human", "Text: {input}")
])