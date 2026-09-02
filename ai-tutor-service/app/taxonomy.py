"""Topic / Subtopic taxonomy (計画 §1-②)。

器は多教科対応の 3 階層 (subject -> topic -> subtopic)。
Phase1 は数学 (math) のみ中身を充填する。他教科は後で足せる (既存データ移行不要)。

Assessment の Structured Output はこの taxonomy の enum で制約し、
Student Model のキーを安定させる。範囲外は "other" に落とす。
"""

OTHER = "other"

# subject -> topic -> [subtopics]
TAXONOMY: dict[str, dict[str, list[str]]] = {
    "math": {
        "numbers_and_expressions": [
            "factoring",
            "expansion",
            "rationalization",
            "absolute_value",
        ],
        "quadratic_functions": [
            "completing_the_square",
            "vertex_form",
            "discriminant",
            "roots_and_factoring",
            "graph_and_parabola",
            "max_min",
        ],
        "linear_functions": [
            "definition_and_form",
            "slope",
            "rate_of_change",
            "y_intercept",
            "equation_and_graph",
        ],
        "sets_and_logic": [
            "sets",
            "necessary_sufficient_condition",
            "proposition_and_contrapositive",
        ],
        "permutations_combinations": [
            "permutations",
            "combinations",
            "repetition",
        ],
        "probability": [
            "basic_probability",
            "conditional_probability",
            "independent_events",
            "expected_value",
        ],
        "trigonometry": [
            "trig_ratios",
            "sine_cosine_rule",
            "trig_functions",
            "addition_theorem",
        ],
        "exponential_logarithm": [
            "exponent_rules",
            "logarithm_rules",
            "exp_log_functions",
        ],
        "sequences": [
            "arithmetic_sequence",
            "geometric_sequence",
            "sigma_notation",
            "recurrence",
        ],
        "vectors": [
            "vector_operations",
            "inner_product",
            "position_vector",
        ],
        "differentiation": [
            "derivative_definition",
            "tangent_line",
            "increase_decrease",
            "max_min",
        ],
        "integration": [
            "indefinite_integral",
            "definite_integral",
            "area",
        ],
        "complex_numbers": [
            "complex_operations",
            "polar_form",
        ],
        "data_analysis": [
            "mean_variance",
            "correlation",
            "boxplot",
        ],
    },
}


def subjects() -> list[str]:
    """中身が充填されている教科の一覧。"""
    return list(TAXONOMY.keys())


def topics(subject: str) -> list[str]:
    """教科の既知トピック一覧 (未知教科なら空)。"""
    return list(TAXONOMY.get(subject, {}).keys())


def subtopics(subject: str, topic: str) -> list[str]:
    """トピックの既知 subtopic 一覧 (未知なら空)。"""
    return list(TAXONOMY.get(subject, {}).get(topic, []))


def is_known_topic(subject: str, topic: str) -> bool:
    return topic in TAXONOMY.get(subject, {})


def is_known_subtopic(subject: str, topic: str, subtopic: str) -> bool:
    return subtopic in TAXONOMY.get(subject, {}).get(topic, [])


def normalize_topic(subject: str, topic: str) -> str:
    """既知トピックはそのまま、未知は OTHER に落とす。"""
    return topic if is_known_topic(subject, topic) else OTHER


def normalize_subtopic(subject: str, topic: str, subtopic: str) -> str:
    return subtopic if is_known_subtopic(subject, topic, subtopic) else OTHER


def allowed_topics(subject: str) -> list[str]:
    """LLM の enum 制約に渡すトピック候補 (OTHER を含む)。

    リクエストごとに該当教科の分だけ渡す想定 (トークン節約)。
    """
    return [*topics(subject), OTHER]
