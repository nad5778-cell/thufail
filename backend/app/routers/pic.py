import io

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.anomaly import detect_anomalies
from app.anomaly_export import build_dashboard_xlsx
from app.db import PIC_DETAIL_VIEW, PIC_SUMMARY_VIEW, fetch_all, fetch_member_national_identity

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


@router.get("/{pic_code}/anomalies/national-identity")
def get_national_identity_anomalies(pic_code: str):
    """Run rule + pattern-based anomaly detection on NATIONAL_IDENTITY for one PIC."""
    df = fetch_member_national_identity(pic_code)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No member records found for PIC {pic_code}")

    result = detect_anomalies(df)
    result = result.sort_values("anomaly_score", ascending=False)

    return {
        "pic_code": pic_code,
        "total": len(result),
        "anomaly_count": int(result["is_anomaly"].sum()),
        "rows": result.to_dict(orient="records"),
    }


@router.get("/{pic_code}/anomalies/national-identity.xlsx")
def download_national_identity_anomalies(pic_code: str):
    df = fetch_member_national_identity(pic_code)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No member records found for PIC {pic_code}")

    result = detect_anomalies(df)
    xlsx_bytes = build_dashboard_xlsx(result, pic_code)

    filename = f"anomaly_dashboard_{pic_code}.xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
