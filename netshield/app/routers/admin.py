import os
import time
import psutil
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from app.blockchain.committee import BlockchainCommittee
from app.dependencies import auth_required, require_admin
from app.models import HealthResponse, MetricsResponse, ResetResponse
from app.config import get_settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/health", response_model=HealthResponse)
async def health_check(_=Depends(auth_required), __=Depends(require_admin)):
    committee = BlockchainCommittee()
    statuses = await committee.health_check()
    overall = "healthy" if all(s == "healthy" for s in statuses.values()) else "degraded"
    return HealthResponse(
        node1=statuses.get("node1", "unknown"),
        node2=statuses.get("node2", "unknown"),
        node3=statuses.get("node3", "unknown"),
        overall=overall,
    )


_start_time = time.time()
_transaction_count = 0
_total_latency = 0.0


def record_transaction(latency: float):
    global _transaction_count, _total_latency
    _transaction_count += 1
    _total_latency += latency


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(_=Depends(auth_required), __=Depends(require_admin)):
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    avg_latency = (_total_latency / _transaction_count) if _transaction_count > 0 else 0.0
    return MetricsResponse(
        total_transactions=_transaction_count,
        average_latency_ms=round(avg_latency * 1000, 2),
        memory_usage_mb=round(memory_mb, 2),
    )


@router.post("/reset_simulation", response_model=ResetResponse)
async def reset_simulation(_=Depends(auth_required), __=Depends(require_admin)):
    settings = get_settings()
    if not settings.mock_blockchain:
        raise HTTPException(
            status_code=400,
            detail="Reset is only available in simulation mode (MOCK_BLOCKCHAIN=true)",
        )
    committee = BlockchainCommittee()
    await committee.reset()
    logger.warning("Simulation state reset")
    return ResetResponse(message="Simulation state has been reset (ledger, fragments, and keys)")
