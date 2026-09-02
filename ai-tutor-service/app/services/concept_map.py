"""AI Tutor が学習中に確認する重要概念の定義。"""

CONCEPT_MAP: dict[str, list[dict[str, str]]] = {
    "linear_functions": [
        {
            "id": "definition_and_form",
            "description": "一次関数の基本形 y=ax+b を理解している",
        },
        {
            "id": "slope",
            "description": "a が傾きを表すことを理解している",
        },
        {
            "id": "rate_of_change",
            "description": "傾きと変化の割合の関係を理解している",
        },
        {
            "id": "y_intercept",
            "description": "b が y 切片を表すことを理解している",
        },
        {
            "id": "equation_reading",
            "description": "一次関数の式から a と b を読み取れる",
        },
        {
            "id": "equation_and_graph",
            "description": "一次関数の式とグラフの関係を理解している",
        },
    ],
}


def get_concepts(topic: str) -> list[dict[str, str]]:
    """トピックに対応する確認概念を返す。"""
    return CONCEPT_MAP.get(topic, [])


def get_concept(topic: str, index: int) -> dict[str, str] | None:
    """指定されたconceptを返す。"""
    concepts = get_concepts(topic)

    if index < 0 or index >= len(concepts):
        return None

    return concepts[index]