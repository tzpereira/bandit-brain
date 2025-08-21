from fastapi import APIRouter
from app.repositories.experiments import get_experiments
from app.models import Experiment
from app.utils import serialize_row

router = APIRouter()

@router.get("/experiments")
def list_experiments(limit: int = 10):
    rows, columns = get_experiments(limit)
    data = [Experiment(**serialize_row(row, columns)) for row in rows]
    return data
