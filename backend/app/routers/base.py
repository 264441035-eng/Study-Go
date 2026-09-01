"""拠点(base)機能に関するエンドポイント。

新しい機能を追加するときは、この routers/ 配下に
このファイルのような <機能名>.py を作成し、
main.py で `app.include_router(...)` を1行追加するだけで良い。
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/bases", tags=["base"])


class Base(BaseModel):
    name: str
    level: int = 1


class BaseOut(Base):
    id: int


# TODO: 現状はメモリ上に保持するだけの仮実装。
# DBを導入したら SQLAlchemy 等のリポジトリ層に置き換える。
_bases: list[BaseOut] = []
_next_id = 1


@router.get("")
def list_bases() -> list[BaseOut]:
    return _bases


@router.get("/{base_id}")
def get_base(base_id: int) -> BaseOut | None:
    return next((b for b in _bases if b.id == base_id), None)


@router.post("", status_code=201)
def create_base(base: Base) -> BaseOut:
    global _next_id
    created = BaseOut(id=_next_id, **base.model_dump())
    _bases.append(created)
    _next_id += 1
    return created
