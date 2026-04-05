import json


def evaluate_qualification(rules: list[dict], answers: list[dict]) -> bool:
    """Returns True if qualified (not disqualified by any rule)."""
    if not rules:
        return True

    answers_map = {str(a["question_id"]): a["value"] for a in answers}

    for rule in rules:
        qid = str(rule["question_id"])
        answer = answers_map.get(qid)
        if answer is None:
            continue

        question_type = rule.get("question_type", "text")

        if question_type in ("single_choice", "multiple_choice"):
            disqualify_values = rule.get("disqualify_values") or []
            if isinstance(disqualify_values, str):
                disqualify_values = json.loads(disqualify_values)
            if isinstance(answer, list):
                if any(v in disqualify_values for v in answer):
                    return False
            elif answer in disqualify_values:
                return False

        elif question_type == "text":
            min_length = rule.get("min_length")
            if min_length and len(str(answer)) < min_length:
                return False
            keywords = rule.get("contains_keywords") or []
            if isinstance(keywords, str):
                keywords = json.loads(keywords)
            if keywords:
                answer_lower = str(answer).lower()
                if any(kw.lower() in answer_lower for kw in keywords):
                    return False

        elif question_type == "number":
            min_value = rule.get("min_value")
            if min_value is not None:
                try:
                    if float(answer) < float(min_value):
                        return False
                except (ValueError, TypeError):
                    pass

    return True
