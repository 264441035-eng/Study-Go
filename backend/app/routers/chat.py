"""チャット(chat)機能に関するエンドポイント。

新しい機能を追加するときは、この routers/ 配下に
このファイルのような <機能名>.py を作成し、
main.py で `app.include_router(...)` を1行追加するだけで良い。
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    sender: str
    content: str


class ChatMessageOut(ChatMessage):
    id: int


# TODO: 現状はメモリ上に保持するだけの仮実装。
# DBを導入したら SQLAlchemy 等のリポジトリ層に置き換える。
_messages: list[ChatMessageOut] = []
_next_id = 1


@router.get("")
def list_messages() -> list[ChatMessageOut]:
    return _messages


@router.post("", status_code=201)
def create_message(message: ChatMessage) -> ChatMessageOut:
    global _next_id
    created = ChatMessageOut(id=_next_id, **message.model_dump())
    _messages.append(created)
    _next_id += 1
    return created
