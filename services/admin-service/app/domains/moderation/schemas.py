from pydantic import BaseModel, ConfigDict, Field


class DecisionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"comment": "Документы проверены, реквизиты подтверждены"}]
        }
    )
