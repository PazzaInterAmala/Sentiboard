from pydantic import BaseModel

from app.schemas.query import QueryResponse


class SentimentNumbers(BaseModel):
    positive: float
    neutral: float
    negative: float


class SentimentCounts(BaseModel):
    positive: int
    neutral: int
    negative: int


class DayCounts(SentimentCounts):
    date: str  # YYYY-MM-DD


class WordCount(BaseModel):
    word: str
    count: int


class TopWords(BaseModel):
    positive: list[WordCount]
    neutral: list[WordCount]
    negative: list[WordCount]


class DashboardResponse(BaseModel):
    query: QueryResponse
    split: SentimentNumbers
    counts: SentimentCounts
    per_day: list[DayCounts]
    top_words: TopWords
