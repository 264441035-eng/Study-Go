from app import taxonomy


def test_math_is_populated():
    assert "math" in taxonomy.subjects()
    assert "quadratic_functions" in taxonomy.topics("math")
    assert "completing_the_square" in taxonomy.subtopics("math", "quadratic_functions")


def test_unknown_subject_is_empty_not_error():
    assert taxonomy.topics("history") == []
    assert taxonomy.subtopics("history", "whatever") == []


def test_normalize_topic_falls_back_to_other():
    assert taxonomy.normalize_topic("math", "quadratic_functions") == "quadratic_functions"
    assert taxonomy.normalize_topic("math", "made_up_topic") == taxonomy.OTHER
    assert taxonomy.normalize_topic("history", "anything") == taxonomy.OTHER


def test_normalize_subtopic_falls_back_to_other():
    assert (
        taxonomy.normalize_subtopic("math", "quadratic_functions", "vertex_form")
        == "vertex_form"
    )
    assert (
        taxonomy.normalize_subtopic("math", "quadratic_functions", "nope")
        == taxonomy.OTHER
    )


def test_allowed_topics_includes_other():
    allowed = taxonomy.allowed_topics("math")
    assert taxonomy.OTHER in allowed
    assert "quadratic_functions" in allowed
