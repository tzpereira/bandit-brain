from fastapi import FastAPI

from app.routes.get.experiments import router as get_experiments_router
from app.routes.get.allocations import router as get_allocations_router
from app.routes.get.metrics import router as get_metrics_router
from app.routes.post.ingest import router as ingest_experiments_router
from app.routes.post.recommend import router as recommend_router
from app.routes.delete.experiments import router as delete_experiments_router
from app.routes.delete.allocations import router as delete_allocations_router


app = FastAPI()

# Get routes
app.include_router(get_experiments_router)
app.include_router(get_metrics_router)
app.include_router(get_allocations_router)

# Post routes
app.include_router(ingest_experiments_router)
app.include_router(recommend_router)

# Delete routes
app.include_router(delete_experiments_router)
app.include_router(delete_allocations_router)

if __name__ == "__main__":
	import uvicorn
	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
