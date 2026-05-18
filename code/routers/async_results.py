# routers/async_results.py

"""GET async SCIM operation results by transaction id (RFC 9967 §2.5.1.1)."""

from fastapi import APIRouter, Depends, HTTPException, status

from auth import api_key_auth
from events.async_jobs import get_async_result
from routers import BASE_PATH, SCIM_Response, SCIM_Route

router = APIRouter(
    prefix=BASE_PATH + "/Async",
    tags=["Async"],
    route_class=SCIM_Route,
    dependencies=[Depends(api_key_auth)],
)


@router.get(
    "/{txn}",
    response_class=SCIM_Response,
    summary="Retrieve async SCIM operation result",
)
async def get_async_operation_result(txn: str):
    result = await get_async_result(txn)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No async result for transaction: {txn}",
        )
    return result
