
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    psi_id: str = Field(min_length=1)
    doi: str | None = None
    page: int = Field(gt=0)
    quote: str = Field(min_length=1)


class Insight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    evidence_status: Literal["supported", "insufficient_data"]
    confidence: Literal["high", "medium", "low"] | None = None
    citations: list[Citation] = Field(default_factory=list)
    explanation: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_evidence(self):
        if self.evidence_status == "supported":
            if not self.citations:
                raise ValueError(
                    "Supported insights must include at least one citation."
                )

            if self.confidence is None:
                raise ValueError(
                    "Supported insights must include a confidence level."
                )

        elif self.evidence_status == "insufficient_data":
            if self.citations:
                raise ValueError(
                    "Insights with insufficient data must not include citations."
                )

            if self.confidence is not None:
                raise ValueError(
                    "Insights with insufficient data must have confidence=None."
                )

        return self


class InsightsDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    insights: list[Insight] = Field(min_length=1)
