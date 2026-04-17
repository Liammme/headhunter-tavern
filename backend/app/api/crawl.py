from fastapi import APIRouter

router = APIRouter(prefix="/crawl", tags=["crawl"])


@router.post("/trigger")
def trigger_crawl():
    return {"status": "triggered"}
