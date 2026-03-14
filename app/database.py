import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = "doc_processor.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # доступ к полям по имени
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT NOT NULL,
            file_type   TEXT NOT NULL,       -- pdf | image
            status      TEXT NOT NULL DEFAULT 'pending',
                                             -- pending | processing | done | error
            raw_text    TEXT,                -- сырой текст от LLM
            error_msg   TEXT,                -- сообщение об ошибке если status=error
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS document_fields (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            field_name  TEXT NOT NULL,       -- например: total_amount, date, vendor
            field_value TEXT,
            confidence  REAL,               -- 0.0 - 1.0
            FOREIGN KEY (document_id) REFERENCES documents(id)
        );

        CREATE INDEX IF NOT EXISTS idx_fields_document
            ON document_fields(document_id);
    """)
    conn.commit()
    conn.close()


def create_document(filename: str, file_type: str) -> int:
    """Создаёт запись документа со статусом pending. Возвращает id."""
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO documents (filename, file_type, status, created_at, updated_at) "
        "VALUES (?, ?, 'pending', ?, ?)",
        (filename, file_type, now, now)
    )
    doc_id = cur.lastrowid
    conn.commit()
    conn.close()
    return doc_id


def update_status(doc_id: int, status: str, error_msg: str = None):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute(
        "UPDATE documents SET status = ?, error_msg = ?, updated_at = ? WHERE id = ?",
        (status, error_msg, now, doc_id)
    )
    conn.commit()
    conn.close()


def save_extraction(doc_id: int, raw_text: str, fields: list[dict]):
    """Сохраняет результат извлечения. fields = [{name, value, confidence}]"""
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute(
        "UPDATE documents SET raw_text = ?, status = 'done', updated_at = ? WHERE id = ?",
        (raw_text, now, doc_id)
    )
    conn.executemany(
        "INSERT INTO document_fields (document_id, field_name, field_value, confidence) "
        "VALUES (?, ?, ?, ?)",
        [(doc_id, f["name"], f["value"], f.get("confidence")) for f in fields]
    )
    conn.commit()
    conn.close()


def get_document(doc_id: int) -> dict | None:
    conn = get_conn()
    doc = conn.execute(
        "SELECT * FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    if not doc:
        conn.close()
        return None

    fields = conn.execute(
        "SELECT field_name, field_value, confidence FROM document_fields WHERE document_id = ?",
        (doc_id,)
    ).fetchall()
    conn.close()

    return {
        **dict(doc),
        "fields": [dict(f) for f in fields]
    }


def get_all_documents() -> list[dict]:
    conn = get_conn()
    docs = conn.execute(
        "SELECT id, filename, file_type, status, created_at FROM documents ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(d) for d in docs]