"""
SismoWatch Backend API
Entry point for REST API, SSE Streaming, Auth, and AI Agent endpoint.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

app = FastAPI(
    title="SismoWatch API",
    description="Real-Time Seismic Event Platform & AI Agent Gateway",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health"])
async def health_check():
    """Health status endpoint."""
    return {
        "status": "healthy",
        "service": "SismoWatch API",
        "version": "1.0.0",
        "database": "configured"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
