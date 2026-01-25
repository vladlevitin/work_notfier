"""FastAPI application for Facebook Work Notifier dashboard."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import posts

app = FastAPI(title="Facebook Work Notifier API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(posts.router, prefix="/api", tags=["posts"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Facebook Work Notifier API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
