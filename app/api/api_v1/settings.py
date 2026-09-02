from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.config import settings
from app.db.session import get_db
from app.models.system_setting import SystemSetting
from app.models.user import User, UserRole
from app.api.deps import require_roles, get_current_active_user

router = APIRouter()


class ThresholdsUpdate(BaseModel):
    FACE_MATCH_THRESHOLD: Optional[float] = None
    LOW_LIGHT_THRESHOLD: Optional[float] = None
    BLUR_THRESHOLD: Optional[float] = None
    LIVENESS_THRESHOLD: Optional[float] = None
    SPOOF_THRESHOLD: Optional[float] = None
    ENROLLMENT_MIN_SAMPLES: Optional[int] = None


@router.get("")
def get_system_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve active system thresholds and settings."""
    db_settings = db.query(SystemSetting).all()
    res = {s.key: s.value for s in db_settings}

    res.setdefault("FACE_MATCH_THRESHOLD", str(settings.FACE_MATCH_THRESHOLD))
    res.setdefault("LOW_LIGHT_THRESHOLD", str(settings.LOW_LIGHT_THRESHOLD))
    res.setdefault("BLUR_THRESHOLD", str(settings.BLUR_THRESHOLD))
    res.setdefault("LIVENESS_THRESHOLD", str(settings.LIVENESS_THRESHOLD))
    res.setdefault("SPOOF_THRESHOLD", str(settings.SPOOF_THRESHOLD))
    res.setdefault("ENROLLMENT_MIN_SAMPLES", str(settings.ENROLLMENT_MIN_SAMPLES))
    res["PROJECT_VERSION"] = settings.PROJECT_VERSION

    return res


@router.put("")
def update_system_settings(
    data: Dict[str, Any],
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Update system thresholds dynamically (ADMIN only)."""
    for key, value in data.items():
        val_str = str(value)
        record = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if record:
            record.value = val_str
        else:
            db.add(SystemSetting(key=key, value=val_str))

        if hasattr(settings, key):
            try:
                target_type = type(getattr(settings, key))
                setattr(settings, key, target_type(value))
            except Exception:
                pass

    db.commit()
    return {"status": "success", "message": "Settings updated successfully"}
