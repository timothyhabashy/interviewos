from interviewos.banks import bank_for, select_technical_item, qualitative_starter
from interviewos.constants import DIFFICULTY_LADDER


def test_difficulty_changes_bank_selection():
    used: set[str] = set()
    beginner = select_technical_item("Technical SWE", "Beginner", used)
    used.add(beginner["question_text"])
    intense = select_technical_item("Technical SWE", "Intense", used)
    assert beginner["difficulty"] == "Beginner"
    assert intense["difficulty"] == "Intense"
    assert beginner["question_text"] != intense["question_text"]


def test_non_stem_mixed_does_not_use_swe_trivia():
    item = select_technical_item("Scholarship", "Beginner", set())
    stem = item["question_text"].lower()
    assert "binary search" not in stem
    assert item in bank_for("Scholarship") or item["question_text"] in {
        q["question_text"] for q in bank_for("Scholarship")
    }


def test_never_repeats_stem():
    used: set[str] = set()
    seen: list[str] = []
    for _ in range(6):
        item = select_technical_item("Data Science", "Intermediate", used)
        assert item["question_text"] not in seen
        seen.append(item["question_text"])
        used.add(item["question_text"])


def test_qualitative_starter_changes_with_difficulty():
    easy = qualitative_starter("Internship", "Beginner")
    hard = qualitative_starter("Internship", "Intense")
    assert easy != hard
    for level in DIFFICULTY_LADDER:
        assert qualitative_starter("Custom", level)


def test_technical_items_have_answer_keys_when_mcq():
    for item in bank_for("Technical SWE"):
        if item["answer_format"] == "multiple_choice_with_explanation":
            assert item["correct_label"] in {"A", "B", "C", "D"}
            assert item["correct_explanation"]
            assert len(item["choices"]) == 4
