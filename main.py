from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid

app = FastAPI()

# Allow frontend (index.html) to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local testing, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class NoteCreate(BaseModel):
    title: str
    content: str

class Note(BaseModel):
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str

# --- In-memory database ---
notes_db: List[Note] = []

# --- Routes ---
@app.get("/notes", response_model=List[Note])
def get_notes():
    return sorted(notes_db, key=lambda n: n.updated_at, reverse=True)

@app.post("/notes", response_model=Note)
def create_note(note: NoteCreate):
    now = datetime.utcnow().isoformat()
    new_note = Note(
        id=str(uuid.uuid4()),
        title=note.title,
        content=note.content,
        created_at=now,
        updated_at=now
    )
    notes_db.append(new_note)
    return new_note

@app.put("/notes/{note_id}", response_model=Note)
def update_note(note_id: str, note: NoteCreate):
    for idx, n in enumerate(notes_db):
        if n.id == note_id:
            updated = Note(
                id=n.id,
                title=note.title,
                content=note.content,
                created_at=n.created_at,
                updated_at=datetime.utcnow().isoformat()
            )
            notes_db[idx] = updated
            return updated
    raise HTTPException(status_code=404, detail="Note not found")

@app.delete("/notes/{note_id}")
def delete_note(note_id: str):
    global notes_db
    new_notes = [n for n in notes_db if n.id != note_id]
    if len(new_notes) == len(notes_db):
        raise HTTPException(status_code=404, detail="Note not found")
    notes_db = new_notes
    return {"ok": True}
