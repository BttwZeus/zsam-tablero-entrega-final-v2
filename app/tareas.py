from database import SessionLocal
from models import Board, Card

PLANTILLA_BOARD_NAME = "Importadas"


def _obtener_o_crear_tablero(db, usuario_id: str) -> Board:
    board = (
        db.query(Board)
        .filter(Board.owner_id == usuario_id, Board.name == PLANTILLA_BOARD_NAME)
        .first()
    )
    if board is None:
        board = Board(name=PLANTILLA_BOARD_NAME, owner_id=usuario_id)
        db.add(board)
        db.commit()
        db.refresh(board)
    return board


def crear_tarea_desde_plantilla(titulo: str, descripcion: str, etiquetas: list, usuario_id: str) -> Card:
    """Crea una tarjeta a partir de una plantilla importada desde la cola,
    dentro de un tablero dedicado a las tareas importadas del usuario."""
    db = SessionLocal()
    try:
        board = _obtener_o_crear_tablero(db, usuario_id)

        descripcion_completa = descripcion
        if etiquetas:
            descripcion_completa += f"\nEtiquetas: {', '.join(etiquetas)}"

        card = Card(board_id=board.id, title=titulo, description=descripcion_completa)
        db.add(card)
        db.commit()
        db.refresh(card)
        return card
    finally:
        db.close()
