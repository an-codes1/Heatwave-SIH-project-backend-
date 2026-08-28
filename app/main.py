from fastapi import FastAPI

app = FastAPI(
    title="Bhubaneswar Heat Health Early Warning API",
    description="Backend for SIH Problem Statement 83",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
