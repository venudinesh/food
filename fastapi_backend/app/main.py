"""
Smart Food Customization and Ordering System - FastAPI Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI(
    title="Smart Food Ordering API",
    description="Complete backend API for Smart Food Customization and Ordering System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "smart-food-api"}

# API version info
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Smart Food Customization and Ordering System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }