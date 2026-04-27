import time
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Placeholder imports - will be replaced by actual implementations
# from agent.router import route_and_process

app = FastAPI(title="DocuParse OCR Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    # Internal service, but good practice to be explicit if needed
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Transcription(BaseModel):
    fields: Dict[str, str]
    required_fields: List[str]
    field_validation: Dict[str, Any]
    field_confidence: Optional[Dict[str, Any]] = None
    critical_field_scores: Optional[Dict[str, float]] = None
    low_confidence_fields: Optional[List[str]] = None
    low_confidence_critical_fields: Optional[Dict[str, str]] = None
    low_confidence_threshold: Optional[float] = None
    llm_should_run: Optional[bool] = None
    field_score: float
    ocr_confidence: float
    final_score: float
    fallback_needed: bool
    source: str
    fallback_engine: str
    fields_from_fallback: List[str]
    totals: Dict[str, Any]
    raw_text: Optional[str] = None
    raw_text_fallback: Optional[str] = None
    ocr_meta: Optional[Dict[str, Any]] = None
    field_positions: Optional[Dict[str, Any]] = None
    field_positions_meta: Optional[Dict[str, Any]] = None


class OCRResponse(BaseModel):
    filename: str
    detected_type: str
    tools_used: List[str]
    transcription: Transcription
    processing_time: str
    


class EngineOption(BaseModel):
    value: str
    label: str


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/engines", response_model=List[EngineOption])
def list_engines():
    engines = [
        {"value": "trocr", "label": "TrOCR"},
        {"value": "paddle", "label": "PaddleOCR"},
        {"value": "easyocr", "label": "EasyOCR"},
        {"value": "tesseract", "label": "Tesseract"},
        {"value": "docling", "label": "Docling"},
        {"value": "llamaparse", "label": "LlamaParse"},
        {"value": "deepseek", "label": "DeepSeek"},
        {"value": "paddle_easyocr", "label": "Paddle + EasyOCR (híbrido)"},
    ]
    return engines


@app.post("/process", response_model=OCRResponse)
async def process_document(
    file: UploadFile = File(...),
    engine: Optional[str] = Form(default=None),
):
    start_time = time.time()

    # try:
    contents = await file.read()
    filename = file.filename

    # Call the router
    from agent.router import route_and_process

    # 1) Classify + 2) Process with selected engine (or auto route)
    result = route_and_process(filename=filename, content=contents, selected_engine=engine)

    processing_time = result.get("_meta", {}).get(
        "processing_time_ms", (time.time() - start_time) * 1000)
    processing_time_seconds = processing_time / 1000

    return {
        "filename": filename,
        "detected_type": result.get("classification", "unknown"),
        "tools_used": result.get("tools_used", []),
        "transcription": result.get("transcription", {}),
        "processing_time": f"{processing_time_seconds:.1f}s",
    }

    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))
