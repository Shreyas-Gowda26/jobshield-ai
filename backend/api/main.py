
"""
api/main.py

FastAPI application entry point for JobShield AI.
"""

from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from backend.crews.verification_crew import verify_company


app = FastAPI(
    title="JobShield AI",
    description="Evidence-based job and company verification API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
class VerificationRequest(BaseModel):
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Company name to investigate",
    )
    cin: str = Field(
        default="",
        max_length=30,
        description="Optional Corporate Identification Number",
    )
    website: str = Field(
        default="",
        max_length=2048,
        description="Optional company website or domain",
    )
    offer_text: str = Field(
        default="",
        max_length=30000,
        description="Optional job description or recruiter message",
    )


@app.get("/health")
def health_check():
    """Basic application health check."""
    return {"status": "ok", "service": "JobShield AI"}


@app.post("/api/verify")
def verify(request: VerificationRequest):
    """Run company and job-offer verification."""
    result = verify_company(
        company_name=request.company_name,
        cin=request.cin,
        website=request.website,
        offer_text=request.offer_text,
    )

    if result.get("status") == "invalid_input":
        raise HTTPException(status_code=422, detail=result["error"])

    return result
