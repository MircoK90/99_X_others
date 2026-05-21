import os
from langchain_litellm import ChatLiteLLM

def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("LITELLM_MODEL", "groq/llama-3.3-70b-versatile")
    fallback_model = os.getenv("FALLBACK_MODEL", "groq/llama-3-8b-instant")

    try:
        return ChatLiteLLM(model=model, api_key=api_key)     
    except Exception:
        return ChatLiteLLM(model=fallback_model, api_key=api_key)

llm = get_llm()