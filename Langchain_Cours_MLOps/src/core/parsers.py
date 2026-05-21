from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

# Classification
class ClassificationResult(BaseModel):
    category: str = Field(..., description="Category assigned to the text")
    confidence: float = Field(..., description="Confidence score between 0 and 1")

classification_parser = PydanticOutputParser(pydantic_object=ClassificationResult)

# Summary
class SummaryResult(BaseModel):
    summary: str = Field(..., description="Summarized text")

summary_parser = PydanticOutputParser(pydantic_object=SummaryResult)

# Translation
class TranslationResult(BaseModel):
    translated_text: str = Field(..., description="Text translated into French")

translation_parser = PydanticOutputParser(pydantic_object=TranslationResult)
