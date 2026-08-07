from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .config import ALLOWED_ORIGINS
from .errors import GenerationError
from .export import render_pdf
from .generation import generate_beat
from .schemas import BeatRequest, BeatResponse, PdfExportRequest

app = FastAPI(title="The Great Automatic Grammatizator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/generate/beat", response_model=BeatResponse)
def generate_beat_endpoint(req: BeatRequest):
    try:
        return generate_beat(req)
    except GenerationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        )


@app.post("/api/export/pdf")
def export_pdf_endpoint(req: PdfExportRequest):
    try:
        pdf_bytes = render_pdf(req)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"code": "pdf_render_failed", "message": "The binding press has jammed — try again."},
        )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="grammatizator-manuscript.pdf"'},
    )


@app.exception_handler(Exception)
async def catch_all_exception_handler(request: Request, exc: Exception):
    # Never leak exception detail (which, for BYOK requests, could echo request internals)
    # to the client or into logs.
    return JSONResponse(
        status_code=500,
        content={"detail": {"code": "internal_error", "message": "Something went wrong inside the machine."}},
    )
