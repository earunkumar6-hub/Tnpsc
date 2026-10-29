"""Pydantic models mirroring each mode's output_schema in the spec.

Every field is required (the spec says "never omit a field"); fields that may not
apply are nullable. Extra fields are rejected so outputs match the schema exactly.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict

Part = Literal["A", "B", "C"]
Language = Literal["en", "ta", "en+ta"]
OptionLetter = Literal["A", "B", "C", "D"]
VerifierCheck = Literal[
    "answer_supported",
    "single_correct",
    "bilingual_match",
    "no_pyq_duplicate",
    "syllabus_fit",
    "level",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BiText(Strict):
    """English/Tamil pair where either side may be null."""
    en: str | None
    ta: str | None


class QText(Strict):
    """Question text: Tamil always present, English may be null (Part C is Tamil only; not enforced here)."""
    en: str | None
    ta: str


# --- doubt_chat ---------------------------------------------------------------

class DoubtChat(Strict):
    status: Literal["ok", "insufficient_context"]
    answer: str
    exam_tip: str | None
    citations: list[str]
    related_topics: list[str]


# --- topic_notes --------------------------------------------------------------

class KeyPoint(Strict):
    en: str | None
    ta: str | None
    citation: str
    asked_in_pyq: list[int]


class QuickFact(Strict):
    item: str
    value: str
    citation: str


class TopicNotes(Strict):
    part: Part
    unit: str
    topic: str
    language: Language
    summary: BiText
    key_points: list[KeyPoint]
    quick_facts_table: list[QuickFact]
    pyq_patterns: list[str]
    likely_questions: list[BiText]
    gaps: list[str]


# --- mock_exam / syllabus_mock_test --------------------------------------------

class Options(Strict):
    A: QText
    B: QText
    C: QText
    D: QText


class PyqRef(Strict):
    year: int | None
    question_no: int | None


class Question(Strict):
    question_id: str
    part: Part
    unit: str
    topic: str
    type: str
    difficulty: Literal["easy", "medium", "hard"]
    question: QText
    options: Options
    answer: OptionLetter
    explanation: QText
    citation: str
    origin: Literal["generated", "pyq"]
    pyq_ref: PyqRef


class MockExam(Strict):
    exam_id: str
    questions: list[Question]


class SyllabusNode(Strict):
    part: Part
    unit_id: str | None
    topic: str | None


class Coverage(Strict):
    topic: str
    planned: int
    generated: int


class UncoveredTopic(Strict):
    topic: str
    shortfall: int
    reason: str


class SyllabusMockTest(Strict):
    test_id: str
    scope: Literal["topic", "unit", "part"]
    syllabus_node: SyllabusNode
    time_limit_minutes: int
    coverage: list[Coverage]
    uncovered_topics: list[UncoveredTopic]
    questions: list[Question]


# --- pyq_tagger / pyq_explainer ----------------------------------------------

class PyqTag(Strict):
    question_id: str
    unit_id: str | None
    topic: str | None
    status: Literal["ok", "out_of_syllabus", "outdated"]
    outdated_reason: str | None
    key_conflict: bool
    supporting_citation: str | None


class WrongOption(Strict):
    option: OptionLetter
    reason: str


class PyqExplanation(Strict):
    question_id: str
    status: Literal["ok", "unsupported"]
    explanation: BiText
    why_others_wrong: list[WrongOption]
    citations: list[str]


# --- question_verifier --------------------------------------------------------

class VerifierResult(Strict):
    question_id: str
    verdict: Literal["accept", "reject"]
    failed_checks: list[VerifierCheck]
    fix_suggestion: str | None


# --- result_analysis ----------------------------------------------------------

class Score(Strict):
    part_a: float
    part_b: float
    part_c: float
    total: float


class UnitAccuracy(Strict):
    unit: str
    correct: int
    total: int


class TopicAccuracy(Strict):
    topic: str
    correct: int
    total: int


class RevisionItem(Strict):
    topic: str
    action: str


class ResultAnalysis(Strict):
    score: Score
    unit_accuracy: list[UnitAccuracy]
    weak_topics: list[str]
    revision_plan: list[RevisionItem]
    topic_accuracy: list[TopicAccuracy]
    part_c_qualified: bool
    mock_type: Literal["unit_test", "pyq_based", "syllabus_based"]


MODE_SCHEMAS: dict[str, type[Strict]] = {
    "doubt_chat": DoubtChat,
    "topic_notes": TopicNotes,
    "mock_exam": MockExam,
    "syllabus_mock_test": SyllabusMockTest,
    "pyq_tagger": PyqTag,
    "pyq_explainer": PyqExplanation,
    "question_verifier": VerifierResult,
    "result_analysis": ResultAnalysis,
}
