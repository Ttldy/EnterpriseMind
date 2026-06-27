class RuleQueryNormalizer:
    def normalize(
        self,
        query: str,
    ) -> list[str]:
        original = " ".join(query.split()).strip()
        if not original:
            return []

        variants: list[str] = []
        synonym_groups = (
            ("没有连接", "无法连接", "连不上", "连接失败"),
            ("报销失败", "无法报销", "报销不了"),
            ("密码忘记", "忘记密码", "密码重置"),
            ("账号锁定", "账户锁定", "账号被锁"),
        )

        for group in synonym_groups:
            for source in group:
                if source not in original:
                    continue
                for target in group:
                    if target != source:
                        variants.append(original.replace(source, target))

        return _dedupe(variants)


def _dedupe(
    values: list[str],
) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
