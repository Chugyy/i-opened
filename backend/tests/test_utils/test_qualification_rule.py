import pytest
from app.core.utils.qualification_rule import validate_rule, apply_operator, evaluate_qualification


# --- validate_rule ---

def test_validate_rule_text_eq():
    assert validate_rule("=", "text") is True


def test_validate_rule_text_contient():
    assert validate_rule("contient", "text") is True


def test_validate_rule_text_numeric_op_raises():
    with pytest.raises(ValueError, match="incompatible"):
        validate_rule("<", "text")


def test_validate_rule_single_choice_eq():
    assert validate_rule("=", "single_choice") is True


def test_validate_rule_single_choice_contient_raises():
    with pytest.raises(ValueError, match="incompatible"):
        validate_rule("contient", "single_choice")


def test_validate_rule_multiple_choice_contient():
    assert validate_rule("contient", "multiple_choice") is True


def test_validate_rule_multiple_choice_eq_raises():
    with pytest.raises(ValueError, match="incompatible"):
        validate_rule("=", "multiple_choice")


def test_validate_rule_number_all_ops():
    for op in ["=", "!=", "<", ">", "<=", ">="]:
        assert validate_rule(op, "number") is True


def test_validate_rule_unknown_type_raises():
    with pytest.raises(ValueError, match="Unknown field type"):
        validate_rule("=", "unknown_type")


# --- apply_operator ---

def test_apply_eq_text():
    assert apply_operator("hello", "=", "hello", "text") is True
    assert apply_operator("hello", "=", "world", "text") is False


def test_apply_neq_text():
    assert apply_operator("hello", "!=", "world", "text") is True
    assert apply_operator("hello", "!=", "hello", "text") is False


def test_apply_contient():
    assert apply_operator("hello world", "contient", "world", "text") is True
    assert apply_operator("hello world", "contient", "foo", "text") is False


def test_apply_contient_case_insensitive():
    assert apply_operator("Hello World", "contient", "hello", "text") is True


def test_apply_ne_contient_pas():
    assert apply_operator("hello", "ne_contient_pas", "world", "text") is True
    assert apply_operator("hello world", "ne_contient_pas", "world", "text") is False


def test_apply_number_lt():
    assert apply_operator("5", "<", "10", "number") is True
    assert apply_operator("10", "<", "5", "number") is False


def test_apply_number_gt():
    assert apply_operator("10", ">", "5", "number") is True


def test_apply_number_lte():
    assert apply_operator("5", "<=", "5", "number") is True
    assert apply_operator("6", "<=", "5", "number") is False


def test_apply_number_gte():
    assert apply_operator("5", ">=", "5", "number") is True


def test_apply_number_eq():
    assert apply_operator("3.14", "=", "3.14", "number") is True


def test_apply_number_non_numeric_raises():
    with pytest.raises(ValueError):
        apply_operator("abc", "<", "10", "number")


def test_apply_unknown_operator_raises():
    with pytest.raises(ValueError):
        apply_operator("x", "LIKE", "x", "text")


# --- evaluate_qualification ---

def _rule(question_id, operator, threshold, field_type, is_optional=False):
    return {
        "question_id": question_id,
        "operator": operator,
        "threshold_value": threshold,
        "field_type": field_type,
        "is_optional": is_optional,
    }


def test_evaluate_empty_rules():
    assert evaluate_qualification([], {}) is True


def test_evaluate_all_pass():
    rules = [_rule(1, "=", "Paris", "text")]
    assert evaluate_qualification(rules, {1: "Paris"}) is True


def test_evaluate_one_fails():
    rules = [
        _rule(1, "=", "Paris", "text"),
        _rule(2, ">", "18", "number"),
    ]
    assert evaluate_qualification(rules, {1: "Paris", 2: "16"}) is False


def test_evaluate_and_mode_first_fail_stops():
    rules = [
        _rule(1, "=", "Paris", "text"),
        _rule(2, "=", "yes", "text"),
    ]
    assert evaluate_qualification(rules, {1: "Lyon", 2: "yes"}) is False


def test_evaluate_optional_missing_skipped():
    rules = [
        _rule(1, "=", "yes", "text", is_optional=True),
        _rule(2, "=", "Paris", "text"),
    ]
    # question 1 is optional and absent → skipped, question 2 passes
    assert evaluate_qualification(rules, {2: "Paris"}) is True


def test_evaluate_optional_present_evaluated():
    rules = [_rule(1, "=", "yes", "text", is_optional=True)]
    # Optional but present → must pass
    assert evaluate_qualification(rules, {1: "no"}) is False


def test_evaluate_required_missing_fails():
    rules = [_rule(1, "=", "yes", "text", is_optional=False)]
    # Required but absent → answer is "" → fails
    assert evaluate_qualification(rules, {}) is False
