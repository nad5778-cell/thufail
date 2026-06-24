from fastapi import APIRouter, Query

from app.db import PIC_DETAIL_VIEW, PIC_SUMMARY_VIEW, fetch_all

router = APIRouter(prefix="/api/pic", tags=["pic"])


@router.get("/summary")
def list_pic_summary():
    """One row per PIC (insurance company) with aggregate metrics."""
    sql = f"SELECT * FROM {PIC_SUMMARY_VIEW} ORDER BY pic_name"
    return fetch_all(sql)


@router.get("/{pic_code}/records")
def list_pic_records(
    pic_code: str,
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
):
    """Drill-down: underlying records for a single PIC, paginated."""
    sql = f"""
        SELECT *
        FROM {PIC_DETAIL_VIEW}
        WHERE pic_code = :pic_code
        ORDER BY 1
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """
    rows = fetch_all(sql, {"pic_code": pic_code, "offset": offset, "limit": limit})
    return {"pic_code": pic_code, "offset": offset, "limit": limit, "rows": rows}
