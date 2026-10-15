# mypy: ignore-errors
from fastapi import APIRouter, FastAPI
from flask import Blueprint, Flask

app = FastAPI()
router = APIRouter(prefix="/api")


@router.get("/loans/{loan_id}")
def get_loan(loan_id: str) -> dict[str, str]:
    return {"id": loan_id}


@app.post("/webhooks")
def create_webhook() -> dict[str, str]:
    return {"ok": "1"}


flask_app = Flask(__name__)
bp = Blueprint("fees", __name__, url_prefix="/fees")


@bp.route("/items/<int:item_id>", methods=["GET"])
def get_fee(item_id: int) -> str:
    return str(item_id)
