"""DynamoDB 実装 (DATABASE_MODE=local|aws)。

計画 §1-⑤ の on-demand 2テーブル構成。local/aws はコードが同一で、
endpoint_url の有無だけが違う (local = DynamoDB Local)。

Sessions テーブル (single-table, TTLあり):
  PK=SESSION#<id>, SK=META            … Session メタ (+ GSI1 で日次集計)
  PK=SESSION#<id>, SK=MSG#<ts>#<seq>  … 1メッセージ=1アイテム
  PK=SESSION#<id>, SK=ASSESS          … Assessment
StudentModels テーブル (TTLなし):
  PK=USER#<user_id>, SK=SUBJECT#<subject>#TOPIC#<topic>

複雑な項目は Pydantic の JSON を `data` 属性に格納し往復させる
(Decimal 変換や入れ子の煩雑さを避ける)。GSI キーだけ最上位に展開する。
"""

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

import boto3
from boto3.dynamodb.conditions import Key

from app.config import Settings
from app.models import Assessment, ConversationMessage, Session
from app.repositories.interface import SessionRepository, StudentModelRepository

TTL_DAYS = 60


def _ttl_epoch() -> int:
    return int((datetime.now(timezone.utc) + timedelta(days=TTL_DAYS)).timestamp())


@lru_cache
def _resource(endpoint_url: str | None, region: str):
    kwargs: dict = {"region_name": region}
    if endpoint_url:
        # DynamoDB Local はダミー認証情報で受け付ける。
        kwargs.update(
            endpoint_url=endpoint_url,
            aws_access_key_id="dummy",
            aws_secret_access_key="dummy",
        )
    return boto3.resource("dynamodb", **kwargs)


def get_resource(settings: Settings):
    return _resource(settings.dynamodb_endpoint_url, settings.bedrock_region)


def ensure_tables(settings: Settings) -> None:
    """テーブルを作成する (存在すれば何もしない)。local / テスト用。

    本番 (aws) は Terraform 等でプロビジョニングする想定なので通常は使わない。
    """
    resource = get_resource(settings)
    existing = {t.name for t in resource.tables.all()}

    if settings.sessions_table not in existing:
        table = resource.create_table(
            TableName=settings.sessions_table,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "gsi1pk", "AttributeType": "S"},
                {"AttributeName": "gsi1sk", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "gsi1pk", "KeyType": "HASH"},
                        {"AttributeName": "gsi1sk", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "KEYS_ONLY"},
                }
            ],
        )
        table.wait_until_exists()
        # TTL 有効化 (DynamoDB Local が未対応でも致命的でないため握りつぶす)。
        try:
            resource.meta.client.update_time_to_live(
                TableName=settings.sessions_table,
                TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
            )
        except Exception:  # noqa: BLE001 - local/moto 差異を許容
            pass

    if settings.student_models_table not in existing:
        table = resource.create_table(
            TableName=settings.student_models_table,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
        )
        table.wait_until_exists()


def _session_pk(session_id: str) -> str:
    return f"SESSION#{session_id}"


class DynamoDBSessionRepository(SessionRepository):
    def __init__(self, settings: Settings) -> None:
        self._table = get_resource(settings).Table(settings.sessions_table)

    def create_session(self, session: Session) -> None:
        self.update_session(session)

    def get_session(self, session_id: str) -> Session | None:
        resp = self._table.get_item(
            Key={"PK": _session_pk(session_id), "SK": "META"}
        )
        item = resp.get("Item")
        return Session.model_validate_json(item["data"]) if item else None

    def update_session(self, session: Session) -> None:
        self._table.put_item(
            Item={
                "PK": _session_pk(session.session_id),
                "SK": "META",
                "data": session.model_dump_json(),
                # 日次セッション集計用の疎GSI (META のみ)。
                "gsi1pk": f"USER#{session.user_id}",
                "gsi1sk": session.created_at.isoformat(),
                "ttl": _ttl_epoch(),
            }
        )

    def add_message(self, message: ConversationMessage) -> None:
        # ts 前方一致で時系列ソートされる。同一 ts 衝突用に短い seq を付与。
        seq = uuid.uuid4().hex[:8]
        sk = f"MSG#{message.timestamp.isoformat()}#{seq}"
        self._table.put_item(
            Item={
                "PK": _session_pk(message.session_id),
                "SK": sk,
                "data": message.model_dump_json(),
                "ttl": _ttl_epoch(),
            }
        )

    def get_messages(self, session_id: str) -> list[ConversationMessage]:
        messages: list[ConversationMessage] = []
        kwargs: dict = {
            "KeyConditionExpression": Key("PK").eq(_session_pk(session_id))
            & Key("SK").begins_with("MSG#"),
        }
        while True:
            resp = self._table.query(**kwargs)
            messages.extend(
                ConversationMessage.model_validate_json(i["data"])
                for i in resp.get("Items", [])
            )
            last = resp.get("LastEvaluatedKey")
            if not last:
                break
            kwargs["ExclusiveStartKey"] = last
        return messages

    def save_assessment(self, assessment: Assessment) -> None:
        self._table.put_item(
            Item={
                "PK": _session_pk(assessment.session_id),
                "SK": "ASSESS",
                "data": assessment.model_dump_json(),
                "ttl": _ttl_epoch(),
            }
        )

    def get_assessment(self, session_id: str) -> Assessment | None:
        resp = self._table.get_item(
            Key={"PK": _session_pk(session_id), "SK": "ASSESS"}
        )
        item = resp.get("Item")
        return Assessment.model_validate_json(item["data"]) if item else None

    def count_user_sessions_on(self, user_id: str, on: date) -> int:
        start = f"{on.isoformat()}T00:00:00"
        end = f"{on.isoformat()}T23:59:59.999999+00:00"
        resp = self._table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("gsi1pk").eq(f"USER#{user_id}")
            & Key("gsi1sk").between(start, end),
            Select="COUNT",
        )
        return resp.get("Count", 0)


class DynamoDBStudentModelRepository(StudentModelRepository):
    def __init__(self, settings: Settings) -> None:
        self._table = get_resource(settings).Table(settings.student_models_table)

    @staticmethod
    def _sk(subject: str, topic: str) -> str:
        return f"SUBJECT#{subject}#TOPIC#{topic}"

    def upsert_topic(
        self,
        user_id: str,
        subject: str,
        topic: str,
        *,
        score: int,
        confidence: float,
        weaknesses: list[str],
        last_assessed_at: str,
    ) -> None:
        self._table.put_item(
            Item={
                "PK": f"USER#{user_id}",
                "SK": self._sk(subject, topic),
                "subject": subject,
                "topic": topic,
                # 数値の Decimal 変換を避けるため data は JSON 文字列で保持。
                "data": json.dumps(
                    {
                        "score": score,
                        "confidence": confidence,
                        "weaknesses": weaknesses,
                        "last_assessed_at": last_assessed_at,
                    }
                ),
            }
        )

    def get_topic(self, user_id: str, subject: str, topic: str) -> dict | None:
        resp = self._table.get_item(
            Key={"PK": f"USER#{user_id}", "SK": self._sk(subject, topic)}
        )
        item = resp.get("Item")
        return json.loads(item["data"]) if item else None
