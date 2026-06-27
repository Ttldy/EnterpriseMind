from app.knowledge.query_normalizer import RuleQueryNormalizer


def test_normalizer_expands_common_vpn_synonyms() -> None:
    normalizer = RuleQueryNormalizer()

    queries = normalizer.normalize("vpn没有连接怎么办？")

    assert "vpn无法连接怎么办？" in queries
    assert "vpn没有连接怎么办？" not in queries


def test_normalizer_preserves_amount_name_and_date() -> None:
    normalizer = RuleQueryNormalizer()

    queries = normalizer.normalize("张三在2026-06-24报销失败，金额128.50元")

    assert "张三在2026-06-24报销失败，金额128.50元" not in queries
    assert queries
    assert all("张三" in query for query in queries)
    assert all("2026-06-24" in query for query in queries)
    assert all("128.50" in query for query in queries)
