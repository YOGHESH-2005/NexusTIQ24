import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="TrustTrace AI — Transaction Risk Investigation Assistant",
    description="Evidence-grounded transaction risk investigation for banking fraud desks.",
    version="1.0.0"
)

# Import API endpoints
from src.api import router as api_router
app.include_router(api_router)

# Serve static directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "TrustTrace AI Backend Active. Front-end index.html not found."}

if __name__ == "__main__":
    print("=" * 60)
    print("TrustTrace AI — Transaction Risk Investigation Assistant")
    print("Serving on http://localhost:8000")
    print("TRACK_ID=PS6")
    print("=" * 60)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
