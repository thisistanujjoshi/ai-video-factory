from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Publication, Video
from app.schemas.analytics import MetricOut, VideoAnalyticsOut
from app.services.analytics import latest_metrics_for_video, sum_totals

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _video_analytics(db: Session, video: Video) -> VideoAnalyticsOut:
    metrics = latest_metrics_for_video(db, video.id)
    metrics_out = [MetricOut.from_metric(m) for m in metrics]
    return VideoAnalyticsOut(
        video_id=video.id, title=video.title, metrics=metrics_out, totals=sum_totals(metrics)
    )


@router.get("", response_model=list[VideoAnalyticsOut])
def list_analytics(db: Session = Depends(get_db)) -> list[VideoAnalyticsOut]:
    video_ids = [row.video_id for row in db.query(Publication.video_id).distinct()]
    videos = db.query(Video).filter(Video.id.in_(video_ids)).all() if video_ids else []
    return [_video_analytics(db, video) for video in videos]


@router.get("/videos/{video_id}", response_model=VideoAnalyticsOut)
def get_video_analytics(video_id: int, db: Session = Depends(get_db)) -> VideoAnalyticsOut:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    return _video_analytics(db, video)
