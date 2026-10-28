import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import engine, Base
from app.api import (
    auth,
    dashboard,
    borrowers,
    accounts,
    queue,
    payments,
    ptp,
    agents,
    campaigns,
    communications,
    field_visits,
    complaints,
    data_quality,
    reports
)

# Create tables if not existing
Base.metadata.create_all(bind=engine)

def seed_demo_users_if_needed():
    """Ensure standard demo accounts exist in development environments."""
    try:
        from app.core.database import SessionLocal
        from app.models.schema import User
        from app.core.security import get_password_hash
        db = SessionLocal()
        try:
            demo_accounts = [
                ("admin@credresolve.com", "Rajesh Sharma", "admin"),
                ("manager@credresolve.com", "Priya Nair", "manager"),
                ("agent@credresolve.com", "Anil Verma", "agent"),
                ("auditor@credresolve.com", "Kavita Rao", "auditor")
            ]
            for email, name, role in demo_accounts:
                user = db.query(User).filter(User.email == email).first()
                if not user:
                    user = User(
                        email=email,
                        hashed_password=get_password_hash("credresolve123"),
                        full_name=name,
                        role=role,
                        is_active=True
                    )
                    db.add(user)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass

seed_demo_users_if_needed()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise AI-Powered Collections & Recovery Platform for FinTech lenders, Banks, and Debt Resolution Agencies.",
    version="2.4.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
api_v1 = settings.API_V1_STR
app.include_router(auth.router, prefix=api_v1)
app.include_router(dashboard.router, prefix=api_v1)
app.include_router(borrowers.router, prefix=api_v1)
app.include_router(accounts.router, prefix=api_v1)
app.include_router(queue.router, prefix=api_v1)
app.include_router(payments.router, prefix=api_v1)
app.include_router(ptp.router, prefix=api_v1)
app.include_router(agents.router, prefix=api_v1)
app.include_router(campaigns.router, prefix=api_v1)
app.include_router(communications.router, prefix=api_v1)
app.include_router(field_visits.router, prefix=api_v1)
app.include_router(complaints.router, prefix=api_v1)
app.include_router(data_quality.router, prefix=api_v1)
app.include_router(reports.router, prefix=api_v1)

@app.get("/api/health")
def health():
    return {
        "platform": settings.PROJECT_NAME,
        "status": "operational",
        "version": "2.4.0",
        "database": "credresolve.db (indexed SQLite/Postgres ready)",
        "api_documentation": "/docs",
        "redoc": "/redoc"
    }

# Mount static frontend build if present for unified deployment
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "platform": settings.PROJECT_NAME,
            "status": "operational",
            "version": "2.4.0",
            "api_documentation": "/docs",
            "redoc": "/redoc"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
