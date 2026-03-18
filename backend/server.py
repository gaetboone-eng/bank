import os
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from core.config import CORS_ORIGINS
from routes.auth import router as auth_router
from routes.banks import router as banks_router
from routes.tenants import router as tenants_router
from routes.transactions import router as transactions_router
from routes.payments import router as payments_router
from routes.dashboard import router as dashboard_router
from routes.banking import router as banking_router
from routes.sync import router as sync_router, scheduler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Tenant Ledger - Banking Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers under /api prefix
from fastapi import APIRouter
api = APIRouter(prefix="/api")
api.include_router(auth_router)
api.include_router(banks_router)
api.include_router(tenants_router)
api.include_router(transactions_router)
api.include_router(payments_router)
api.include_router(dashboard_router)
api.include_router(banking_router)
api.include_router(sync_router)

app.include_router(api)


@app.get("/api/")
async def root():
    return {"message": "Tenant Ledger API", "version": "2.0.0"}


@app.on_event("startup")
async def startup_event():
    scheduler.start()
    logger.info("🚀 Scheduler started - will sync on 1st, 10th, 20th of each month at 8:00 AM")


@app.on_event("shutdown")
async def shutdown_db_client():
    scheduler.shutdown()
    logger.info("Server shutting down...")
