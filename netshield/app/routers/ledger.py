from fastapi import APIRouter, HTTPException, Depends
from app.blockchain.committee import BlockchainCommittee
from app.models import (
    BlockModel,
    TransactionRequest,
    TransactionResponse,
    LedgerVerifyResponse,
)
from app.dependencies import auth_required, require_admin

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/blocks", response_model=list[BlockModel])
async def get_blocks(_=Depends(auth_required)):
    committee = BlockchainCommittee()
    chain = await committee.get_ledger()
    if not chain:
        return []
    return [BlockModel(**block) for block in chain]


@router.post("/transact", response_model=TransactionResponse)
async def transact(req: TransactionRequest, _=Depends(auth_required), __=Depends(require_admin)):
    committee = BlockchainCommittee()
    block_data = {
        "action": req.action,
        "user": req.user,
        "data_hash": req.data_hash,
        "signature": req.signature,
    }
    try:
        result = await committee.transact(block_data)
        return TransactionResponse(block=BlockModel(**result))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/verify", response_model=LedgerVerifyResponse)
async def verify_ledger(_=Depends(auth_required)):
    committee = BlockchainCommittee()
    result = await committee.verify_ledger()
    return LedgerVerifyResponse(
        valid=result.get("valid", False),
        blocks_count=result.get("blocks", 0),
        errors=result.get("errors", []),
    )
