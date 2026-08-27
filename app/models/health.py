"""
Pydantic models for Health and Metadata endpoints (/v1/healthz, /v1/metadata).
"""

from typing import List
from pydantic import BaseModel, Field


class ContextCounts(BaseModel):
    category: int = Field(0, ge=0, description="Number of unique category contexts loaded")
    merchant: int = Field(0, ge=0, description="Number of unique merchant contexts loaded")
    customer: int = Field(0, ge=0, description="Number of unique customer contexts loaded")
    trigger: int = Field(0, ge=0, description="Number of unique trigger contexts loaded")


class HealthResponse(BaseModel):
    status: str = Field("ok", description="Health status string")
    uptime_seconds: int = Field(..., ge=0, description="Seconds since service start")
    contexts_loaded: ContextCounts = Field(..., description="Counts of loaded contexts per scope")


class MetadataResponse(BaseModel):
    team_name: str = Field(..., description="Team name")
    team_members: List[str] = Field(..., description="List of team member names")
    model: str = Field(..., description="Underlying model identifier")
    approach: str = Field(..., description="High-level architecture approach description")
    contact_email: str = Field(..., description="Primary contact email for submission")
    version: str = Field(..., description="Submission or service version")
    submitted_at: str = Field(..., description="Submission ISO 8601 timestamp")
