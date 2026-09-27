from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth import get_current_user, hash_password, verify_password
from database import Base, engine, get_db
from models import Board, Card, Reminder, Session as SessionModel, User
from queue_client import publish_plantilla, publish_reminder
from schemas import (
    BoardCreate,
    BoardOut,
    CardCreate,
    CardOut,
    CardUpdate,
    LoginRequest,
    PlantillaExportRequest,
    RegisterRequest,
    TokenResponse,
)
from storage import presigned_download_url, upload_attachment

app = FastAPI(title="Gestor de tareas colaborativo")

Base.metadata.create_all(bind=engine)

app.mount("/estaticos", StaticFiles(directory="static"), name="estaticos")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/salud")
def salud(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/auth/registro", response_model=TokenResponse)
def registro(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Ese correo ya esta registrado")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    session = SessionModel(user_id=user.id)
    db.add(session)
    db.commit()
    return TokenResponse(token=session.token)


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales invalidas")

    session = SessionModel(user_id=user.id)
    db.add(session)
    db.commit()
    return TokenResponse(token=session.token)


@app.post("/boards", response_model=BoardOut)
def crear_tablero(
    payload: BoardCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    board = Board(name=payload.name, owner_id=user.id)
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


@app.get("/boards", response_model=list[BoardOut])
def listar_tableros(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(Board).filter(Board.owner_id == user.id).all()


@app.post("/boards/{board_id}/cards", response_model=CardOut)
def crear_tarjeta(
    board_id: str,
    payload: CardCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    board = db.get(Board, board_id)
    if board is None or board.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Tablero no encontrado")

    card = Card(board_id=board_id, **payload.model_dump())
    db.add(card)
    db.commit()
    db.refresh(card)

    due = payload.due_date.isoformat() if payload.due_date else None
    publish_reminder(card.id, card.title, due)

    return card


@app.get("/boards/{board_id}/cards", response_model=list[CardOut])
def listar_tarjetas(
    board_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(Card).filter(Card.board_id == board_id).all()


@app.patch("/cards/{card_id}", response_model=CardOut)
def actualizar_tarjeta(
    card_id: str,
    payload: CardUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = db.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(card, field, value)

    db.commit()
    db.refresh(card)
    return card


@app.post("/cards/{card_id}/adjunto")
async def subir_adjunto(
    card_id: str,
    archivo: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = db.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    content = await archivo.read()
    key = upload_attachment(card_id, archivo.filename, content)
    card.attachment_key = key
    db.commit()
    return {"key": key}


@app.get("/cards/{card_id}/adjunto")
def descargar_adjunto(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = db.get(Card, card_id)
    if card is None or not card.attachment_key:
        raise HTTPException(status_code=404, detail="No hay adjunto")

    return {"url": presigned_download_url(card.attachment_key)}


@app.post("/cards/{card_id}/exportar-plantilla")
def exportar_plantilla(
    card_id: str,
    payload: PlantillaExportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = db.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    publish_plantilla(
        titulo=card.title,
        descripcion=card.description,
        etiquetas=[],
        usuario_id=payload.usuario_id,
    )
    return {"status": "publicada"}


@app.get("/cards/{card_id}/recordatorios")
def listar_recordatorios(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reminders = db.query(Reminder).filter(Reminder.card_id == card_id).all()
    return [{"mensaje": r.message, "enviado": r.sent_at} for r in reminders]
