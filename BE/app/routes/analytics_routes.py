"""/api/analytics — overview + breakdowns, scoped to the user's track."""
from fastapi import APIRouter, Depends

from app.services import analytics
from app.deps import current_user

router = APIRouter(prefix="/api")


@router.get("/analytics")
def get_analytics(user: dict = Depends(current_user)):
    return analytics.summary(user.get("track"))


@router.get("/analytics/market")
def get_market(user: dict = Depends(current_user)):
    """Skill-demand market, skills-by-category, title categories, locations."""
    return analytics.rich(user.get("track"))
