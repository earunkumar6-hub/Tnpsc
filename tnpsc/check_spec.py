"""Consistency checks for the prompt spec.

Run: python -m tnpsc.check_spec      (exit code 1 if any error)
"""
import inspect
import sys
import typing
from dataclasses import dataclass

from pydantic import BaseModel

from tnpsc.schemas import MODE_SCHEMAS, VerifierCheck
from tnpsc.spec import PARTS, load_spec, units


@dataclass
class Issue:
    level: str  # "error" | "warning"
    check: str
    message: str


def check_exam_totals(spec: dict) -> list[Issue]:
    ex = spec["exam_context"]
    per_q = ex["marks_per_question"]
    issues = []
    if sum(p["questions"] for p in ex["parts"]) != ex["total_questions"]:
        issues.append(Issue("error", "exam_totals", "Part question counts do not add up to total_questions"))
    for p in ex["parts"]:
        if p["questions"] * per_q != p["marks"]:
            issues.append(Issue("error", "exam_totals", f"Part {p['part']}: {p['questions']} x {per_q} != {p['marks']} marks"))
    if ex["total_questions"] * per_q != ex["total_marks"]:
        issues.append(Issue("error", "exam_totals", "total_questions x marks_per_question != total_marks"))
    return issues


def check_unit_counts(spec: dict) -> list[Issue]:
    part_q = {p["part"]: p["questions"] for p in spec["exam_context"]["parts"]}
    issues = []
    for part in PARTS:
        unit_list = spec["syllabus_tree"][part]
        known = sum(u["exam_questions"] for u in unit_list if isinstance(u["exam_questions"], int))
        pending = [u["unit_id"] for u in unit_list if not isinstance(u["exam_questions"], int)]
        if known > part_q[part]:
            issues.append(Issue("error", "unit_counts", f"Part {part}: unit counts sum to {known}, above {part_q[part]}"))
        elif pending:
            issues.append(Issue("warning", "unit_counts",
                                f"Part {part}: {', '.join(pending)} have no count yet; "
                                f"{part_q[part] - known} questions left to allocate from PYQ weightage"))
        elif known != part_q[part]:
            issues.append(Issue("error", "unit_counts", f"Part {part}: unit counts sum to {known}, expected {part_q[part]}"))
    return issues


def check_unit_tests(spec: dict) -> list[Issue]:
    ut = spec["test_series"]["unit_tests"]
    unit_map = {u["unit_id"]: u for u in units(spec)}
    tested = [t["unit_id"] for t in ut["tests"]]
    issues = []
    if ut["count"] != len(ut["tests"]):
        issues.append(Issue("error", "unit_tests", f"count is {ut['count']} but {len(ut['tests'])} tests are listed"))
    missing = sorted(set(unit_map) - set(tested))
    if missing:
        issues.append(Issue("error", "unit_tests", f"No unit test for {', '.join(missing)}"))
    dupes = sorted({u for u in tested if tested.count(u) > 1})
    if dupes:
        issues.append(Issue("error", "unit_tests", f"More than one unit test for {', '.join(dupes)}"))
    for t in ut["tests"]:
        unit = unit_map.get(t["unit_id"])
        if unit is None:
            issues.append(Issue("error", "unit_tests", f"{t['test_id']}: unknown unit_id {t['unit_id']}"))
            continue
        q = unit["exam_questions"]
        expected = 50 if isinstance(q, int) and q >= 15 else 25
        if t["questions"] != expected:
            issues.append(Issue("error", "unit_tests",
                                f"{t['test_id']}: lists {t['questions']} questions, sizing_rule gives {expected} "
                                f"(unit carries {q} exam questions)"))
    return issues


def check_modes(spec: dict) -> list[Issue]:
    modes = set(spec["modes"])
    declared = set(spec["runtime_variables"]["{{mode}}"].split(" | "))
    tiered = [m for tier in spec["tech_stack"]["llm"]["tiers"].values() for m in tier]
    issues = []
    if declared != modes:
        issues.append(Issue("error", "modes", f"runtime_variables {{{{mode}}}} differs from modes: {sorted(declared ^ modes)}"))
    if set(MODE_SCHEMAS) != modes:
        issues.append(Issue("error", "modes", f"Pydantic models differ from modes: {sorted(set(MODE_SCHEMAS) ^ modes)}"))
    if sorted(tiered) != sorted(modes):
        issues.append(Issue("error", "modes", "LLM tiers must list every mode exactly once"))
    return issues


def check_runtime_variables(spec: dict) -> list[Issue]:
    defined = set(spec["runtime_variables"])
    return [
        Issue("warning", "runtime_variables", f"{name}: input {var} is not described in runtime_variables")
        for name, mode in spec["modes"].items()
        for var in mode.get("inputs", [])
        if var not in defined
    ]


def _model_in(annotation) -> type[BaseModel] | None:
    """The BaseModel class inside an annotation like Model, list[Model] or Model | None."""
    if typing.get_origin(annotation) is None and inspect.isclass(annotation) and issubclass(annotation, BaseModel):
        return annotation
    for arg in typing.get_args(annotation):
        if model := _model_in(arg):
            return model
    return None


def _compare(spec_obj: dict, model: type[BaseModel], path: str, issues: list[Issue]) -> None:
    spec_keys, model_keys = set(spec_obj), set(model.model_fields)
    if spec_keys != model_keys:
        issues.append(Issue("error", "schema_drift",
                            f"{path}: only in spec {sorted(spec_keys - model_keys)}, "
                            f"only in model {sorted(model_keys - spec_keys)}"))
    for key in spec_keys & model_keys:
        value = spec_obj[key]
        if isinstance(value, list) and value and isinstance(value[0], dict):
            value = value[0]
        if isinstance(value, dict):
            sub = _model_in(model.model_fields[key].annotation)
            if sub is None:
                issues.append(Issue("error", "schema_drift", f"{path}.{key}: spec has an object, model field is not a model"))
            else:
                _compare(value, sub, f"{path}.{key}", issues)


def check_schema_drift(spec: dict) -> list[Issue]:
    issues: list[Issue] = []
    for name, model in MODE_SCHEMAS.items():
        if name in spec["modes"]:
            _compare(spec["modes"][name]["output_schema"], model, name, issues)
    return issues


def check_verifier_checks(spec: dict) -> list[Issue]:
    in_spec = {c.split(":")[0].strip() for c in spec["modes"]["question_verifier"]["checks"]}
    in_model = set(typing.get_args(VerifierCheck))
    if in_spec != in_model:
        return [Issue("error", "verifier_checks", f"Check names differ between spec and model: {sorted(in_spec ^ in_model)}")]
    return []


CHECKS = [
    check_exam_totals,
    check_unit_counts,
    check_unit_tests,
    check_modes,
    check_runtime_variables,
    check_schema_drift,
    check_verifier_checks,
]


def run(spec: dict) -> list[Issue]:
    return [issue for check in CHECKS for issue in check(spec)]


def main() -> int:
    issues = run(load_spec())
    for i in issues:
        print(f"{i.level.upper():7} [{i.check}] {i.message}")
    errors = sum(i.level == "error" for i in issues)
    print(f"\n{errors} error(s), {len(issues) - errors} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
