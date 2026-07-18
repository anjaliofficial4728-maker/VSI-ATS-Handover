# app/main.py
"""
Main FastAPI application.
Updated for Phase 1 - includes email router.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import candidates, emails, oauth, booking

from app.scheduler.reminder_scheduler import scheduler


app = FastAPI(
    title="Candidate Follow-up Management System",
    description="Backend API for HR recruitment workflow",
    version="2.0"
)

# ============== CORS Configuration ==============
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Local development
        "http://localhost:5173",      # Vite development
        "https://vercel-deployed-frontend.vercel.app",  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== Route Registration ==============
# Candidate routes
app.include_router(candidates.router)

# Email routes (Phase 1)
app.include_router(emails.router)

app.include_router(oauth.router)

app.include_router(booking.router)

# ============== Health Check ==============
@app.get("/")
def root():
    """Root endpoint for health check"""
    return {
        "message": "Candidate Follow-up Management System API",
        "version": "2.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "scheduler_running": scheduler.running
    }


# ============== Scheduler Startup ==============
@app.on_event("startup")
def startup_event():
    """Start the background scheduler on application startup"""
    if not scheduler.running:
        scheduler.start()
        print("✅ Background scheduler started")


@app.on_event("shutdown")
def shutdown_event():
    """Shut down the background scheduler on application shutdown"""
    if scheduler.running:
        scheduler.shutdown()
        print("✅ Background scheduler stopped")


# ============== Swagger Documentation ==============
# Swagger docs automatically available at /docs
# ReDoc available at /redoc
