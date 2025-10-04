from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import uuid
import json
import os

app = FastAPI()

# --- Configuration ---
DATA_FILE = "notes_data.json"

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---
class NoteCreate(BaseModel):
    title: str
    content: str
    category: str

class Note(BaseModel):
    id: str
    title: str
    content: str
    category: str
    created_at: str
    updated_at: str

class UserLogin(BaseModel):
    user_id: str

class CategoryPassword(BaseModel):
    category: str
    password: str

# --- Persistence Functions ---

def load_data():
    """Loads notes and passwords from JSON file."""
    global user_notes, user_passwords
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                # Deserialize notes correctly, handling the case where 'notes' might be None or missing
                notes_data = data.get('notes', {})
                user_notes = {}
                for user_id, notes_list in notes_data.items():
                    # Ensure each note is converted to the Pydantic Note model
                    user_notes[user_id] = [Note(**note) for note in notes_list]
                
                user_passwords = data.get('passwords', {})
        except json.JSONDecodeError:
            print(f"Warning: Could not decode {DATA_FILE}. Starting with empty data.")
            user_notes = {}
            user_passwords = {}
    else:
        user_notes = {}
        user_passwords = {}

def save_data():
    """Saves notes and passwords to JSON file."""
    try:
        with open(DATA_FILE, 'w') as f:
            # Convert Pydantic models back to dicts for JSON serialization
            serializable_notes = {
                user_id: [note.model_dump() for note in notes]
                for user_id, notes in user_notes.items()
            }
            json.dump(
                {'notes': serializable_notes, 'passwords': user_passwords},
                f,
                indent=4
            )
    except Exception as e:
        print(f"Error saving data to file: {e}")

# --- In-Memory Storage (Initialized on load) ---
user_notes: Dict[str, List[Note]] = {} 
user_passwords: Dict[str, Dict[str, Optional[str]]] = {} 
load_data() # Load data when the server starts

# --- Routes ---

@app.post("/login")
def login(user: UserLogin):
    user_id = user.user_id.strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    if user_id not in user_notes:
        user_notes[user_id] = []
        # Initialize password storage for the new user
        user_passwords[user_id] = {"Personal": None, "Diary": None, "Office": None, "Study": None, "Schedule": None}
        save_data() # Save new user data
    
    return {"message": f"User {user_id} logged in successfully."}

@app.post("/password/{user_id}")
def set_password(user_id: str, data: CategoryPassword):
    if user_id not in user_passwords:
        raise HTTPException(status_code=404, detail="User not found")
    
    if data.category not in ["Personal", "Diary"]:
        raise HTTPException(status_code=400, detail="Password setting is only supported for Personal and Diary categories.")

    if user_passwords[user_id][data.category] is not None:
        raise HTTPException(status_code=400, detail=f"A password already exists for {data.category}. Use the 'verify' route to access.")

    if not data.password:
        raise HTTPException(status_code=400, detail="Password cannot be empty.")
        
    user_passwords[user_id][data.category] = data.password
    save_data()
    return {"message": f"Password set for {data.category}."}

@app.post("/verify_password/{user_id}")
def verify_password(user_id: str, data: CategoryPassword):
    if user_id not in user_passwords:
        raise HTTPException(status_code=404, detail="User not found")

    stored_pw = user_passwords[user_id].get(data.category)

    if stored_pw is None:
        raise HTTPException(status_code=404, detail=f"No password set for category: {data.category}")

    if stored_pw != data.password:
        raise HTTPException(status_code=401, detail="Invalid password")

    return {"message": "Password verified"}

@app.get("/notes/{user_id}", response_model=List[Note])
def get_notes(user_id: str):
    if user_id not in user_notes:
        return []
    # Use list comprehension to ensure returned objects are standard Notes
    return sorted(user_notes[user_id], key=lambda n: n.updated_at, reverse=True)

@app.post("/notes/{user_id}", response_model=Note)
def create_note(user_id: str, note: NoteCreate):
    if user_id not in user_notes:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.utcnow().isoformat()
    new_note = Note(
        id=str(uuid.uuid4()),
        title=note.title,
        content=note.content,
        category=note.category,
        created_at=now,
        updated_at=now
    )

    user_notes[user_id].append(new_note)
    save_data()
    return new_note

@app.delete("/notes/{user_id}/{note_id}")
def delete_note(user_id: str, note_id: str):
    if user_id not in user_notes:
        raise HTTPException(status_code=404, detail="User not found")

    notes_list = user_notes[user_id]
    initial_length = len(notes_list)
    
    user_notes[user_id] = [n for n in notes_list if n.id != note_id]

    if len(user_notes[user_id]) == initial_length:
        raise HTTPException(status_code=404, detail="Note not found")

    save_data()
    return {"ok": True}
