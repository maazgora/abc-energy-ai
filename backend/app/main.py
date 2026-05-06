import uvicorn
import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from app.services.orchestrator import DialogueOrchestrator
from app.models.database import engine
from sqlmodel import SQLModel
from app.models.database import engine

SQLModel.metadata.create_all(engine)

app = FastAPI(title="ABC Energy Lead Gen PoC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = {}

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message")
    session_id = data.get("session_id", "default-session")

    if session_id not in sessions:
        sessions[session_id] = DialogueOrchestrator(session_id)
    
    orchestrator = sessions[session_id]

    async def event_generator():
    
        async for token in orchestrator.process_message(user_message):
            yield f"data: {token}\n\n"
        
        state_json = json.dumps(orchestrator.current_state)
                
        yield f"data: [METADATA]{state_json}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)