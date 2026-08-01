from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.import_job import ImportJob
from app.models.user import User
from app.schemas.import_job import ImportJobOut
from app.services.letterboxd_import import run_import_job, validate_export_zip

router = APIRouter(prefix="/api/import", tags=["import"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB — Letterboxd exports are almost always well under this


@router.post("/letterboxd", response_model=ImportJobOut, status_code=status.HTTP_202_ACCEPTED)
async def import_letterboxd(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="That export is larger than we can accept (50 MB max)."
        )

    try:
        validate_export_zip(contents)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    job = ImportJob(user_email=current_user.email, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_import_job, job.id, contents)

    return job


@router.get("/letterboxd/{job_id}", response_model=ImportJobOut)
def get_import_job(
    job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    job = db.get(ImportJob, job_id)
    if job is None or job.user_email != current_user.email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    return job
