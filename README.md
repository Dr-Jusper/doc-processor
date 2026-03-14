# Doc Processor

AI-powered document processing API. Upload invoices, receipts, contracts, or any business document — get structured data back in seconds.

## What it does

- Accepts PDF and image files (JPG, PNG, WEBP)
- Converts documents to structured JSON using LLM vision
- Extracts fields like dates, amounts, vendor names, INN, contract numbers
- Stores results in a database with confidence scores
- Exposes a clean REST API

## Tech stack

- **FastAPI** — REST API framework
- **Claude Haiku** via OpenRouter — document understanding
- **PyMuPDF** — PDF to image conversion
- **SQLite** — storage
- **Docker** — containerization

## Quick start

### With Docker

```bash
git clone https://github.com/Dr-Jusper/doc-processor.git
cd doc-processor

# Create .env file
echo "OPENROUTER_API_KEY=your_key_here" > .env

# Build and run
docker build -t doc-processor .
docker run -p 8000:8000 --env-file .env doc-processor
```

### Local development

```bash
cd app
pip install -r ../requirements.txt
uvicorn main:app --reload
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents/upload` | Upload a document for processing |
| GET | `/documents` | List all documents |
| GET | `/documents/{id}` | Get document with extracted fields |

Interactive docs available at `http://localhost:8000/docs`

## Example

Upload an invoice:

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@invoice.pdf"
```

Response:

```json
{
  "id": 1,
  "filename": "invoice.pdf",
  "file_type": "pdf",
  "status": "done",
  "fields": [
    {"field_name": "invoice_number", "field_value": "6", "confidence": 0.95},
    {"field_name": "vendor_name", "field_value": "Company LLC", "confidence": 0.95},
    {"field_name": "total_amount", "field_value": "100000.00", "confidence": 0.95},
    {"field_name": "currency", "field_value": "RUB", "confidence": 0.95}
  ]
}
```

## Project structure

```
doc-processor/
├── app/
│   ├── main.py        # FastAPI app and endpoints
│   ├── extractor.py   # LLM integration and document parsing
│   └── database.py    # SQLite models and queries
├── Dockerfile
├── requirements.txt
└── README.md
```