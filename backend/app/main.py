from fastapi import FastAPI


app = FastAPI(title="Bounty Pool API")


@app.get("/health")
def health_check():
    return {"status": "ok"}
