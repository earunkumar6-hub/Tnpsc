"""Loads the prompt spec (tnpsc_group4_rag_prompt.json)."""
import json
from pathlib import Path

SPEC_PATH = Path(__file__).resolve().parent.parent / "tnpsc_group4_rag_prompt.json"
PARTS = ("A", "B", "C")


def load_spec(path: Path = SPEC_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def units(spec: dict) -> list[dict]:
    """All syllabus units across parts A, B and C, each with its 'part' added."""
    tree = spec["syllabus_tree"]
    return [{**unit, "part": part} for part in PARTS for unit in tree[part]]
