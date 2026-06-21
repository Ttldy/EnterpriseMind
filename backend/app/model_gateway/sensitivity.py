from dataclasses import dataclass

from app.agents.contracts import Sensitivity

_ORDER = {
    Sensitivity.PUBLIC: 0,
    Sensitivity.INTERNAL: 1,
    Sensitivity.SENSITIVE: 2,
}

_SENSITIVE_WORDS = (
    "工资",
    "薪资",
    "身份证",
    "银行卡",
    "绩效",
    "奖金",
    "报销金额",
    "员工名单",
    "手机号",
    "家庭住址",
)

_PUBLIC_WORDS = (
    "公司地址",
    "办公时间",
    "客服电话",
    "公开招聘",
)


@dataclass(frozen=True)
class SensitivityDecision:
    level: Sensitivity
    reason: str


def classify_question(
    question: str,
) -> SensitivityDecision:
    normalized = question.strip().lower()

    if any(word in normalized for word in _SENSITIVE_WORDS):
        return SensitivityDecision(
            level=Sensitivity.SENSITIVE,
            reason="question_contains_sensitive_keyword",
        )

    if any(word in normalized for word in _PUBLIC_WORDS):
        return SensitivityDecision(
            level=Sensitivity.PUBLIC,
            reason="question_matches_public_topic",
        )

    return SensitivityDecision(
        level=Sensitivity.INTERNAL,
        reason="question_defaults_to_internal",
    )


def highest_sensitivity(
    *levels: Sensitivity | str,
) -> Sensitivity:
    result = Sensitivity.PUBLIC

    for raw_level in levels:
        try:
            level = Sensitivity(raw_level)
        except ValueError:
            return Sensitivity.SENSITIVE

        if _ORDER[level] > _ORDER[result]:
            result = level

    return result
