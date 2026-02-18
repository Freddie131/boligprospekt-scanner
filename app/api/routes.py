from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.domain.models import Prospect
from app.domain.schemas import ProspectOut, ProspectOverrideUpdate
from app.jobs.weekly_job import WeeklyJobService

router = APIRouter(prefix="/api", tags=["prospects"])


@router.get("/prospects", response_model=list[ProspectOut])
def list_prospects(db: Session = Depends(get_db)):
    prospects = db.scalars(select(Prospect).order_by(Prospect.score.desc().nullslast())).all()
    return prospects


@router.patch("/prospects/{prospect_id}", response_model=ProspectOut)
def update_overrides(prospect_id: int, payload: ProspectOverrideUpdate, db: Session = Depends(get_db)):
    prospect = db.get(Prospect, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospekt ikke funnet")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prospect, field, value)
    db.commit()
    db.refresh(prospect)
    return prospect


@router.post("/jobs/weekly")
def trigger_weekly_job(db: Session = Depends(get_db)):
    service = WeeklyJobService(db, get_settings())
    run = service.run()
    return {
        "job_run_id": run.id,
        "status": run.status,
        "report_html_path": run.report_html_path,
        "report_pdf_path": run.report_pdf_path,
    }
