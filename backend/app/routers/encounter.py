"""すれちがい通信(encounter)機能に関するエンドポイント。

新しい機能を追加するときは、この routers/ 配下に
このファイルのような <機能名>.py を作成し、
main.py で `app.include_router(...)` を1行追加するだけで良い。
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/encounters", tags=["encounter"])


class Encounter(BaseModel):
    partner_name: str


class EncounterOut(Encounter):
    id: int
    reward_claimed: bool = False


# TODO: 現状はメモリ上に保持するだけの仮実装。
# DBを導入したら SQLAlchemy 等のリポジトリ層に置き換える。
_encounters: list[EncounterOut] = []
_next_id = 1


@router.get("")
def list_encounters() -> list[EncounterOut]:
    return _encounters


@router.post("", status_code=201)
def create_encounter(encounter: Encounter) -> EncounterOut:
    global _next_id
    created = EncounterOut(id=_next_id, **encounter.model_dump())
    _encounters.append(created)
    _next_id += 1
    return created
