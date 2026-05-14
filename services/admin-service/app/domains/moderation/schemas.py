from pydantic import BaseModel, Field


class DecisionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)
