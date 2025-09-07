from fastapi import FastAPI
from app.integrations.messaging import router as messaging_router

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "service": "ameth", "version": "v1.6"}

# Monta el router de messaging
app.include_router(messaging_router)
