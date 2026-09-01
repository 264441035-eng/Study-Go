"""キャラクター(character)機能に関するエンドポイント。

新しい機能を追加するときは、この routers/ 配下に
このファイルのような <機能名>.py を作成し、
main.py で `app.include_router(...)` を1行追加するだけで良い。
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/characters", tags=["character"])


class Character(BaseModel):
    name: str
    level: int = 1
    hp: int = 100


class CharacterOut(Character):
    id: int


# TODO: 現状はメモリ上に保持するだけの仮実装。
# DBを導入したら SQLAlchemy 等のリポジトリ層に置き換える。
_characters: list[CharacterOut] = []
_next_id = 1


@router.get("")
def list_characters() -> list[CharacterOut]:
    return _characters


@router.get("/{character_id}")
def get_character(character_id: int) -> CharacterOut | None:
    return next((c for c in _characters if c.id == character_id), None)


@router.post("", status_code=201)
def create_character(character: Character) -> CharacterOut:
    global _next_id
    created = CharacterOut(id=_next_id, **character.model_dump())
    _characters.append(created)
    _next_id += 1
    return created
