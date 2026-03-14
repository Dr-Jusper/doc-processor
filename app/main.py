import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException

from database import init_db, create_document, update_status, save_extraction, get_document, get_all_documents
from extractor import extract

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}

app = FastAPI(
    title="Doc Processor",
    description="Upload documents and extract structured data using AI",
    version="1.0.0"
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"status": "ok", "message": "Doc Processor API is running"}


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document (PDF or image) for processing."""

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    file_type = "pdf" if suffix == ".pdf" else "image"

    # Создаём запись в БД
    doc_id = create_document(file.filename, file_type)

    # Сохраняем файл
    filepath = UPLOAD_DIR / f"{doc_id}_{file.filename}"
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Меняем статус на processing
    update_status(doc_id, "processing")

    # Извлекаем данные через LLM
    try:
        result = extract(str(filepath))
        fields = [
            {
                "name": f["name"],
                "value": str(f.get("value", "")),
                "confidence": f.get("confidence"),
            }
            for f in result["fields"]
        ]
        # Добавляем тип документа как отдельное поле
        fields.insert(0, {
            "name": "document_type",
            "value": result["document_type"],
            "confidence": 1.0,
        })
        save_extraction(doc_id, result["raw_text"], fields)
    except Exception as e:
        import traceback
        traceback.print_exc()
        update_status(doc_id, "error", str(e))
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    return get_document(doc_id)


@app.get("/documents")
def list_documents():
    """List all uploaded documents."""
    return get_all_documents()


@app.get("/documents/{doc_id}")
def get_doc(doc_id: int):
    """Get document by ID with all extracted fields."""
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc