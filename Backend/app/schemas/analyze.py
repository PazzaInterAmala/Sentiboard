from pydantic import BaseModel, Field, field_validator

from app.models.prediction import SentimentLabel


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    compare: bool = False

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text cannot be empty or contain only whitespace")
        return value


class PredictionResponse(BaseModel):
    model: str
    label: SentimentLabel
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[SentimentLabel, float]


class AnalyzeResponse(BaseModel):
    query_id: int
    results: list[PredictionResponse]
