from langchain_core.messages import HumanMessage, SystemMessage
from src.core.llm import llm
from src.core.tools import word_count, char_count

print("\n=== Chapter 1: Core Components ===\n")

print("\n--- INVOKE ---")
response = llm.invoke([
    SystemMessage(content="You are an expert Machine Learning Assistant"),
    HumanMessage(content="Explain the Random Forest model")
])
print(response.content)
print("\n--- Response Analysis with Tools ---")
print("Word count      :", word_count.invoke(response.content)) 
print("Character count :", char_count.invoke(response.content))

print("\n\n--- BATCH ---")
batch_inputs = [
    [
        SystemMessage(content="You are a Synonym Assistant"),
        HumanMessage(content="Give me a synonym for 'fast'.")
    ],
    [
        SystemMessage(content="You are a Mathematician Assistant"),
        HumanMessage(content="Give me the value of pi")
    ]
]
batch_outputs = llm.batch(batch_inputs)
for i, r in enumerate(batch_outputs, 1):
    print(f"\nResponse {i} :", r.content)
    print("Word count      :", word_count.invoke(r.content))
    print("Character count :", char_count.invoke(r.content))

print("\n\n--- STREAMING ---")
stream_text = ""
for chunk in llm.stream([
    SystemMessage(content="You are a Writing Assistant"),
    HumanMessage(content="Write me a blog about AI")
]):
    print(chunk.content, end="", flush=True)
    stream_text += chunk.content
print("\nWord count      :", word_count.invoke(stream_text))
print("Character count :", char_count.invoke(stream_text))

print("\n\n--- RETRY ---")
safe_llm = llm.with_retry()
retry_response = safe_llm.invoke([
    SystemMessage(content="You are an Assistant"),
    HumanMessage(content="Say 'Hello' after a retry.")
])
print(retry_response.content)
print("Word count      :", word_count.invoke(retry_response.content))
print("Character count :", char_count.invoke(retry_response.content))