from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import json
from database import engine, get_db
import models
from auth import get_current_user, SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from websocket_manager import manager
from routers import auth, contacts, conversations

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Signal Clone API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(conversations.router)

# Serve uploaded files
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
def root():
    return {"message": "Signal Clone API", "status": "running"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    # Validate token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_user_id = int(payload.get("sub", -1))
        if token_user_id != user_id:
            await websocket.close(code=1008)
            return
    except JWTError:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)

    # Mark user as online
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.is_online = True
        db.commit()

    # Notify contacts about online status
    await _broadcast_presence(user_id, True, db)

    try:
        while True:
            data = await websocket.receive_text()
            event = json.loads(data)

            if event.get("type") == "typing":
                conv_id = event.get("conversation_id")
                is_typing = event.get("is_typing", False)
                from routers.conversations import _get_participant_ids
                participant_ids = _get_participant_ids(conv_id, db)
                for pid in participant_ids:
                    if pid != user_id:
                        await manager.send_to_user(pid, {
                            "type": "typing",
                            "conversation_id": conv_id,
                            "user_id": user_id,
                            "is_typing": is_typing,
                        })

            elif event.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, user_id)
        if user:
            from sqlalchemy.sql import func
            user.is_online = False
            user.last_seen = func.now()
            db.commit()
        await _broadcast_presence(user_id, False, db)


async def _broadcast_presence(user_id: int, is_online: bool, db: Session):
    """Notify all contacts of this user about their presence change."""
    contacts = db.query(models.Contact).filter(
        models.Contact.contact_user_id == user_id
    ).all()
    for contact in contacts:
        await manager.send_to_user(contact.user_id, {
            "type": "presence",
            "user_id": user_id,
            "is_online": is_online,
        })
