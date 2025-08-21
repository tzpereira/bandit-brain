from fastapi import FastAPI
from app.routes.experiments import router as experiments_router
from app.routes.allocations import router as allocations_router

app = FastAPI()

app.include_router(experiments_router)
app.include_router(allocations_router)

if __name__ == "__main__":
	import uvicorn
	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
