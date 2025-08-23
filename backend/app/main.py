from fastapi import FastAPI

from app.routes.get.experiments import router as get_experiments_router
from app.routes.get.metrics import router as get_metrics_router
from app.routes.post.ingest import router as ingest_experiments_router
from app.routes.get.allocations import router as get_allocations_router

app = FastAPI()

# Experiment routes
app.include_router(get_experiments_router)
app.include_router(ingest_experiments_router)
app.include_router(get_metrics_router)

# Allocation routes
app.include_router(get_allocations_router)


if __name__ == "__main__":
	import uvicorn
	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
