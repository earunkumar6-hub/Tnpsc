import copy

import pytest
from pydantic import ValidationError

from tnpsc.check_spec import check_modes, check_schema_drift, check_verifier_checks
from tnpsc.schemas import MODE_SCHEMAS
from tnpsc.spec import load_spec

QUESTION = {
    "question_id": "Q1",
    "part": "A",
    "unit": "A4",
    "topic": "Fundamental Rights",
    "type": "direct",
    "difficulty": "easy",
    "question": {"en": "Which Article abolishes untouchability?", "ta": "தீண்டாமையை ஒழிக்கும் சட்டப்பிரிவு எது?"},
    "options": {k: {"en": f"Article {n}", "ta": f"சட்டப்பிரிவு {n}"} for k, n in zip("ABCD", (14, 17, 19, 21))},
    "answer": "B",
    "explanation": {"en": "Article 17 [C1]", "ta": "சட்டப்பிரிவு 17 [C1]"},
    "citation": "C1",
    "origin": "generated",
    "pyq_ref": {"year": None, "question_no": None},
}

SAMPLES = {
    "doubt_chat": {
        "status": "ok", "answer": "...", "exam_tip": None, "citations": ["C1"], "related_topics": [],
    },
    "topic_notes": {
        "part": "A", "unit": "A4", "topic": "Fundamental Rights", "language": "en",
        "summary": {"en": "...", "ta": None},
        "key_points": [{"en": "...", "ta": None, "citation": "C1", "asked_in_pyq": [2022]}],
        "quick_facts_table": [{"item": "Article 17", "value": "Abolition of untouchability", "citation": "C1"}],
        "pyq_patterns": [], "likely_questions": [{"en": "...", "ta": None}], "gaps": [],
    },
    "mock_exam": {"exam_id": "FM-SYL-1", "questions": [QUESTION]},
    "syllabus_mock_test": {
        "test_id": "UT-A4", "scope": "unit",
        "syllabus_node": {"part": "A", "unit_id": "A4", "topic": None},
        "time_limit_minutes": 45,
        "coverage": [{"topic": "Fundamental Rights", "planned": 5, "generated": 1}],
        "uncovered_topics": [{"topic": "Fundamental Rights", "shortfall": 4, "reason": "too few chunks"}],
        "questions": [QUESTION],
    },
    "pyq_tagger": {
        "question_id": "PYQ-2022-14", "unit_id": "A4", "topic": "Fundamental Rights", "status": "ok",
        "outdated_reason": None, "key_conflict": False, "supporting_citation": "C1",
    },
    "pyq_explainer": {
        "question_id": "PYQ-2022-14", "status": "ok", "explanation": {"en": "...", "ta": "..."},
        "why_others_wrong": [{"option": "A", "reason": "..."}], "citations": ["C1"],
    },
    "question_verifier": {
        "question_id": "Q1", "verdict": "reject", "failed_checks": ["single_correct"], "fix_suggestion": "...",
    },
    "result_analysis": {
        "score": {"part_a": 90.0, "part_b": 30.0, "part_c": 120.0, "total": 240.0},
        "unit_accuracy": [{"unit": "A4", "correct": 12, "total": 15}],
        "weak_topics": ["Fundamental Rights"],
        "revision_plan": [{"topic": "Fundamental Rights", "action": "..."}],
        "topic_accuracy": [{"topic": "Fundamental Rights", "correct": 3, "total": 5}],
        "part_c_qualified": True, "mock_type": "syllabus_based",
    },
}


def test_every_mode_has_a_sample():
    assert set(SAMPLES) == set(MODE_SCHEMAS)


@pytest.mark.parametrize("mode", SAMPLES)
def test_valid_sample_parses(mode):
    MODE_SCHEMAS[mode].model_validate(SAMPLES[mode])


@pytest.mark.parametrize("mode", SAMPLES)
def test_missing_field_rejected(mode):
    data = copy.deepcopy(SAMPLES[mode])
    data.pop(next(iter(data)))
    with pytest.raises(ValidationError):
        MODE_SCHEMAS[mode].model_validate(data)


@pytest.mark.parametrize("mode", SAMPLES)
def test_extra_field_rejected(mode):
    with pytest.raises(ValidationError):
        MODE_SCHEMAS[mode].model_validate({**SAMPLES[mode], "extra": 1})


def test_question_requires_tamil():
    q = copy.deepcopy(QUESTION)
    q["question"] = {"en": "only English", "ta": None}
    with pytest.raises(ValidationError):
        MODE_SCHEMAS["mock_exam"].model_validate({"exam_id": "X", "questions": [q]})


def test_invalid_answer_letter_rejected():
    with pytest.raises(ValidationError):
        MODE_SCHEMAS["mock_exam"].model_validate({"exam_id": "X", "questions": [{**QUESTION, "answer": "E"}]})


def test_models_match_spec():
    spec = load_spec()
    issues = check_schema_drift(spec) + check_modes(spec) + check_verifier_checks(spec)
    assert issues == [], issues
