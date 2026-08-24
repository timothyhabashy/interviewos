from __future__ import annotations

import re

from interviewos.constants import (
    EVIDENCE_PATTERN,
    ETHICAL_GUARDRAILS,
    HEDGE_PATTERN,
    LEARNING_PATTERN,
    MOTIVATION_PATTERN,
    PROJECT_VERB_PATTERN,
    QUALITATIVE_RUBRIC_KEYS,
    RUBRIC_CATEGORIES,
    STRUCTURE_PATTERN,
    TECHNICAL_RUBRIC_KEYS,
)
from interviewos.models import (
    Feedback,
    ImprovedAnswer,
    InterviewConfig,
    InterviewPlan,
    QuestionReview,
    RubricItem,
    TargetedDrill,
    Turn,
)


def _answer_text(turn: Turn) -> str:
    return turn.answer.written_response or ""


def _strip_hedges(text: str) -> str:
    out = text
    prev = None
    while out != prev:
        prev = out
        out = HEDGE_PATTERN.sub("", out)
        out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([,.!?;:])", r"\1", out)
    out = re.sub(r"^\s*[,.;:]\s*", "", out)
    out = re.sub(r",\s*,", ",", out)
    out = re.sub(r",(\s*[.!?])", r"\1", out)
    return out.strip()


def _capitalize_first(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]


def _avg_sentence_length(text: str) -> float:
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return 0.0
    return sum(len(s.split()) for s in sentences) / len(sentences)


def _count_specifics(text: str) -> int:
    return len(EVIDENCE_PATTERN.findall(text))


def _short_phrase(text: str) -> str:
    m = PROJECT_VERB_PATTERN.search(text)
    if m:
        return m.group(2).strip().rstrip(".,!?;:'\"")
    words = text.split()
    snippet = " ".join(words[:6]).strip(".,!?;:'\"")
    return snippet or "your answer"


def _build_headline_from_answer(answer: str, config: InterviewConfig) -> str:
    interview_type = config.interview_type.lower()
    m = PROJECT_VERB_PATTERN.search(answer)
    if m:
        verb = m.group(1).lower()
        thing = m.group(2).strip().rstrip(".,!?;:'\"")
        return (
            f"Here is the short version: I {verb} {thing}, and that is "
            "the experience I want to build on here."
        )
    return (
        f"Here is the short version: this {interview_type} matters to me, "
        "and here is the most honest version of what I would say with "
        "another minute to think."
    )


def _build_bridge(config: InterviewConfig) -> str:
    opp = (config.opportunity_description or "").strip()
    interview_type = config.interview_type.lower()
    if not opp:
        return (
            f"That matters here because this {interview_type} is exactly "
            "the kind of role where I want to keep getting better."
        )
    sentence = re.split(r"[.!?]", opp)[0].strip().rstrip(",")
    if len(sentence) > 110:
        sentence = sentence[:107].rsplit(" ", 1)[0] + "..."
    return (
        f"That matters for this role because it is about {sentence.lower()} "
        "— and that is exactly the kind of work I want to keep getting better at."
    )


def _build_improved_answer(weakest: Turn, config: InterviewConfig) -> ImprovedAnswer:
    original = _answer_text(weakest) or "(no written explanation provided)"
    cleaned = _capitalize_first(_strip_hedges(original))
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    rewrite = f"{_build_headline_from_answer(original, config)} {cleaned} {_build_bridge(config)}"
    return ImprovedAnswer(
        original_question=weakest.question.question_text,
        rewrite=rewrite,
        what_changed=(
            "Added a one-sentence headline, stripped hedging words without "
            "changing your facts, and closed with a bridge to the opportunity. "
            "No new achievements were invented."
        ),
    )


def _personalized_drills(config: InterviewConfig, transcript: list[Turn]) -> list[TargetedDrill]:
    if not transcript:
        return []
    longest = max(transcript, key=lambda t: len(_answer_text(t)))
    weakest = min(transcript, key=lambda t: len(_answer_text(t)))
    snippet = _short_phrase(_answer_text(longest))
    weakest_q = weakest.question.question_text
    short_q = (weakest_q[:65] + "...") if len(weakest_q) > 65 else weakest_q
    return [
        TargetedDrill(
            drill=(
                f"Re-record your answer about {snippet} in 90 seconds, "
                "using the structure: point, example, takeaway."
            ),
            why_this_helps=(
                "You already have the material — this makes the strongest part land first."
            ),
        ),
        TargetedDrill(
            drill=(
                f"Take your shortest answer (to '{short_q}') and rewrite it "
                "with one concrete detail. Practice it out loud."
            ),
            why_this_helps="Short answers are usually missing one specific that would make them memorable.",
        ),
        TargetedDrill(
            drill="Delete every hedging word ('maybe', 'just', 'kind of', 'I guess') from your answers.",
            why_this_helps="Removes verbal shrinking so your real point lands.",
        ),
    ]


def _unassessed(kind: str) -> RubricItem:
    if kind == "qualitative":
        return RubricItem(
            score=None,
            assessed=False,
            feedback="No qualitative answers in this interview, so this dimension was not assessed.",
        )
    return RubricItem(
        score=None,
        assessed=False,
        feedback="No technical questions in this interview, so this dimension was not assessed.",
    )


def _score_qualitative_rubric(
    config: InterviewConfig, qual_turns: list[Turn]
) -> dict[str, RubricItem]:
    full_text = " ".join(_answer_text(t) for t in qual_turns)
    word_counts = [len(_answer_text(t).split()) for t in qual_turns]
    total_words = sum(word_counts)
    avg_words = total_words / max(len(qual_turns), 1)
    avg_sentence = sum(_avg_sentence_length(_answer_text(t)) for t in qual_turns) / max(
        len(qual_turns), 1
    )
    specifics = _count_specifics(full_text)
    hedges = len(HEDGE_PATTERN.findall(full_text))
    hedge_density = hedges / max(total_words, 1) * 100
    has_motivation = bool(MOTIVATION_PATTERN.search(full_text))
    has_learning = bool(LEARNING_PATTERN.search(full_text))
    structure_hits = len(STRUCTURE_PATTERN.findall(full_text))
    has_structure = structure_hits >= 2
    opp_words = {
        w
        for w in re.findall(r"[a-z]{4,}", (config.opportunity_description or "").lower())
        if w
        not in {
            "this",
            "that",
            "with",
            "from",
            "have",
            "your",
            "about",
            "they",
            "their",
            "should",
            "would",
            "could",
            "while",
            "where",
            "which",
            "applicants",
            "summer",
            "early",
            "looking",
            "interested",
            "role",
            "able",
            "into",
        }
    }
    has_opp_overlap = (
        any(w in full_text.lower() for w in opp_words) if opp_words else has_motivation
    )

    if 12 <= avg_sentence <= 22 and total_words >= 80:
        clarity = (5, "Sentences are easy to follow with a steady rhythm.")
    elif avg_sentence > 30:
        clarity = (2, "Sentences run long; break them into 12-20 word units.")
    elif total_words < 30:
        clarity = (1, "Answers are too short to land a clear point.")
    elif 8 <= avg_sentence < 12 or 22 < avg_sentence <= 30:
        clarity = (4, "Mostly clear. Open each answer with one short point sentence.")
    else:
        clarity = (3, "Clear enough, but uneven.")

    if specifics >= 6:
        specificity = (5, "You backed claims with concrete artifacts.")
    elif specifics >= 3:
        specificity = (4, "Decent specifics. Aim for one concrete artifact per answer.")
    elif specifics >= 1:
        specificity = (3, "You have one or two specifics. Spread them across every answer.")
    else:
        specificity = (1, "Answers stayed abstract. Lead with what you actually did.")

    if hedge_density < 1.5 and total_words >= 60:
        confidence = (5, "Almost no hedging — your point lands.")
    elif hedge_density < 3:
        confidence = (4, "Mostly confident. Trim a few more hedges.")
    elif hedge_density < 5:
        confidence = (3, "Several hedges per answer. Cut them on the next pass.")
    elif hedge_density < 8:
        confidence = (2, "Frequent hedging shrinks your point.")
    else:
        confidence = (1, "Heavy hedging. Rewrite one answer with zero hedge words.")

    if has_opp_overlap and has_motivation:
        relevance = (5, "You connected stories to what the opportunity is about.")
    elif has_opp_overlap or has_motivation:
        relevance = (4, "Tie each story back to a specific phrase from the description.")
    elif total_words >= 60:
        relevance = (3, "You said real things, but the listener has to connect them to the role.")
    else:
        relevance = (2, "Add a one-line bridge to the role at the end of each answer.")

    # Authenticity can go below 4 — unlike the hackathon scorer.
    if total_words >= 100 and has_learning:
        authenticity = (5, "Your voice comes through with real reflection.")
    elif total_words >= 40:
        authenticity = (3, "Honest, but still a bit generic. Keep your own details; drop template language.")
    elif total_words >= 15:
        authenticity = (2, "Too little of you is on the page yet to judge a real voice.")
    else:
        authenticity = (1, "Almost no personal content. Interviewers cannot hear you from this.")

    if has_structure and avg_words >= 60:
        structure = (5, "Strong structural markers — listeners can follow you.")
    elif has_structure or avg_words >= 50:
        structure = (4, "Some structure. Try: situation, what I did, what I learned.")
    elif avg_words >= 25:
        structure = (3, "Use a simple frame so answers do not drift.")
    else:
        structure = (2, "Answers are too short to need much structure yet.")

    if specifics >= 5 and has_learning:
        evidence = (5, "Real examples plus reflection.")
    elif specifics >= 3:
        evidence = (4, "Good evidence. Pair each example with one takeaway sentence.")
    elif specifics >= 1:
        evidence = (3, "You have an example. Use it earlier in the answer.")
    else:
        evidence = (1, "No concrete examples yet.")

    if has_learning and total_words >= 80:
        growth = (5, "You named what you learned and what you would do differently.")
    elif has_learning:
        growth = (4, "Some reflection. Make the mistake and the change more concrete.")
    elif total_words >= 60:
        growth = (3, "Add one moment where you got something wrong.")
    else:
        growth = (2, "No reflection visible yet.")

    mapping = {
        "clarity": clarity,
        "specificity": specificity,
        "confidence": confidence,
        "relevance": relevance,
        "authenticity": authenticity,
        "structure": structure,
        "evidence_examples": evidence,
        "growth_mindset": growth,
    }
    return {
        key: RubricItem(score=score, feedback=fb, assessed=True)
        for key, (score, fb) in mapping.items()
    }


def _score_technical_rubric(tech_turns: list[Turn]) -> dict[str, RubricItem]:
    correct_count = 0
    answered_count = 0
    reasoning_lengths: list[int] = []
    explain_hits = 0
    explain_total = 0
    for turn in tech_turns:
        sel = turn.answer.selected_choice
        if turn.question.answer_format == "multiple_choice_with_explanation":
            if sel is not None:
                answered_count += 1
                if turn.question.correct_label and sel == turn.question.correct_label:
                    correct_count += 1
        else:
            explain_total += 1
            explanation = (turn.question.correct_explanation or "").lower()
            written = _answer_text(turn).lower()
            tokens = [w for w in re.findall(r"[a-z]{4,}", explanation) if w not in {"this", "that", "with"}]
            overlap = sum(1 for w in set(tokens) if w in written)
            if overlap >= 2 or len(written.split()) >= 40:
                explain_hits += 1
        reasoning_lengths.append(len(_answer_text(turn).split()))

    graded = answered_count + explain_total
    accuracy = (correct_count + explain_hits) / max(graded, 1)
    avg_reasoning = sum(reasoning_lengths) / max(len(reasoning_lengths), 1)

    if accuracy >= 0.9:
        tc = (5, "Strong correctness across the technical questions.")
    elif accuracy >= 0.6:
        tc = (4, "Solid majority correct. Re-derive the misses from first principles.")
    elif accuracy >= 0.4:
        tc = (3, "Mixed results. Use the question reviews to study the misses.")
    elif answered_count == 0 and explain_total == 0:
        tc = (2, "No technical answers selected.")
    else:
        tc = (2, "Most technical questions were missed. Slow down and write the steps first.")

    if avg_reasoning >= 35:
        tr = (5, "You wrote real reasoning, not just a one-line guess.")
    elif avg_reasoning >= 18:
        tr = (4, "Decent reasoning. State assumption, step, conclusion.")
    elif avg_reasoning >= 8:
        tr = (3, "Reasoning is too brief to evaluate.")
    else:
        tr = (2, "Almost no written reasoning.")

    return {
        "technical_reasoning": RubricItem(score=tr[0], feedback=tr[1], assessed=True),
        "technical_correctness": RubricItem(score=tc[0], feedback=tc[1], assessed=True),
    }


def _build_question_reviews(transcript: list[Turn]) -> list[QuestionReview]:
    reviews: list[QuestionReview] = []
    for i, turn in enumerate(transcript):
        q = turn.question
        ans_text = _answer_text(turn)
        words = len(ans_text.split())
        expired_note = (
            " You ran out of time — next pass, start with the headline even if the rest is rough."
            if turn.answer.time_expired
            else ""
        )
        if q.question_type == "technical":
            sel = turn.answer.selected_choice
            correct_label = q.correct_label
            correct_text = None
            if correct_label and q.choices:
                for c in q.choices:
                    if c.label == correct_label:
                        correct_text = f"{correct_label}. {c.text}"
                        break
            if q.answer_format == "explain_snippet":
                what_well = (
                    "You tried to reason in words, which is what a real interviewer can evaluate."
                    if words >= 8
                    else "You engaged the prompt; next time narrate the steps out loud."
                )
                what_to = (
                    (q.correct_explanation or "Re-derive the intended explanation on paper.")
                    + expired_note
                )
                reviews.append(
                    QuestionReview(
                        question_index=i,
                        question_id=q.id,
                        question_type="technical",
                        what_went_well=what_well,
                        what_to_improve=what_to,
                        correct_answer_if_applicable=None,
                        explanation_if_applicable=q.correct_explanation,
                        time_expired=turn.answer.time_expired,
                        source=turn.answer.source,
                    )
                )
                continue
            if correct_label is None:
                reviews.append(
                    QuestionReview(
                        question_index=i,
                        question_id=q.id,
                        question_type="technical",
                        what_went_well="You committed to an answer.",
                        what_to_improve="No stored answer key for this item; re-derive it yourself."
                        + expired_note,
                        correct_answer_if_applicable=None,
                        explanation_if_applicable=None,
                        time_expired=turn.answer.time_expired,
                        source=turn.answer.source,
                    )
                )
                continue
            correct = sel is not None and sel == correct_label
            if correct:
                what_well = f"You picked {sel} and that is the right answer."
                what_to = "Tighten reasoning to one or two sentences." + expired_note
            else:
                what_well = "You committed to a choice and wrote an explanation."
                what_to = (
                    f"You picked {sel or '(none)'}, but the correct answer is {correct_label}. "
                    "Re-derive it from the explanation."
                    + expired_note
                )
            reviews.append(
                QuestionReview(
                    question_index=i,
                    question_id=q.id,
                    question_type="technical",
                    what_went_well=what_well,
                    what_to_improve=what_to,
                    correct_answer_if_applicable=correct_text,
                    explanation_if_applicable=q.correct_explanation,
                    time_expired=turn.answer.time_expired,
                    source=turn.answer.source,
                )
            )
        else:
            specifics = _count_specifics(ans_text)
            hedges = len(HEDGE_PATTERN.findall(ans_text))
            if words >= 60 and specifics >= 2:
                what_well = "Real length, real examples — this would land."
            elif words >= 30:
                what_well = "You said something concrete."
            else:
                what_well = "You answered honestly; now we add specifics."
            issue_bits = []
            if words < 30:
                issue_bits.append("add 2-3 more sentences with one specific example")
            if hedges >= 3:
                issue_bits.append("trim hedges like 'just', 'maybe', 'kind of'")
            if specifics == 0:
                issue_bits.append("name a real project, class, or moment")
            what_to = (
                "; ".join(issue_bits)
                if issue_bits
                else "tie the last sentence back to what this opportunity is asking for"
            )
            reviews.append(
                QuestionReview(
                    question_index=i,
                    question_id=q.id,
                    question_type="qualitative",
                    what_went_well=what_well,
                    what_to_improve=what_to[:1].upper() + what_to[1:] + "." + expired_note,
                    time_expired=turn.answer.time_expired,
                    source=turn.answer.source,
                )
            )
    return reviews


def overall_score(rubric: dict[str, RubricItem]) -> tuple[int, int]:
    assessed = [item for item in rubric.values() if item.assessed and item.score is not None]
    if not assessed:
        return 0, 0
    total = sum(item.score or 0 for item in assessed)
    return int(round(total / (len(assessed) * 5) * 100)), len(assessed)


def mock_feedback(
    config: InterviewConfig, plan: InterviewPlan, transcript: list[Turn]
) -> Feedback:
    qual_turns = [t for t in transcript if t.question.question_type == "qualitative"]
    tech_turns = [t for t in transcript if t.question.question_type == "technical"]

    rubric: dict[str, RubricItem] = {}
    if qual_turns:
        rubric.update(_score_qualitative_rubric(config, qual_turns))
    if tech_turns:
        rubric.update(_score_technical_rubric(tech_turns))
    for key, _label in RUBRIC_CATEGORIES:
        if key not in rubric:
            kind = "technical" if key in TECHNICAL_RUBRIC_KEYS else "qualitative"
            rubric[key] = _unassessed(kind)

    score, assessed_n = overall_score(rubric)
    weakest_pool = qual_turns or transcript
    weakest = min(weakest_pool, key=lambda t: len(_answer_text(t)))
    longest = max(transcript, key=lambda t: len(_answer_text(t))) if transcript else weakest

    notes: list[str] = []
    expired = sum(1 for t in transcript if t.answer.time_expired)
    if expired:
        notes.append(
            f"{expired} answer(s) were submitted after the timer. "
            "Start with the headline next time; finishing late is coaching, not a hidden penalty."
        )
    voice = sum(1 for t in transcript if t.answer.source == "voice")
    if voice:
        notes.append(
            f"{voice} answer(s) were captured by voice. Edit the transcript before you treat it as gospel."
        )
    if plan.resolved_difficulty:
        notes.append(
            f"Difficulty was {plan.resolved_difficulty}; questions were drawn from that band when possible."
        )

    summary_bits = []
    if qual_turns:
        summary_bits.append("front-load specifics and tie each story to the opportunity")
    if tech_turns:
        summary_bits.append("write one or two sentences of reasoning before picking")
    summary = (
        "You have real substance to work with. The biggest unlocks are: "
        + ("; ".join(summary_bits) or "keep practicing with more complete answers")
        + ". Keep your voice. Tighten the structure."
    )

    weakest_key = None
    weakest_item = None
    for key, item in rubric.items():
        if not item.assessed or item.score is None:
            continue
        if weakest_item is None or (item.score < weakest_item.score):  # type: ignore[operator]
            weakest_key, weakest_item = key, item
    if weakest_item and weakest_key:
        label = dict(RUBRIC_CATEGORIES).get(weakest_key, weakest_key)
        biggest = f"Your weakest assessed dimension is {label} ({weakest_item.score}/5). {weakest_item.feedback}"
    else:
        biggest = "No assessed rubric data yet."

    if transcript:
        scored = [
            (i, _count_specifics(_answer_text(t)) * 2 + len(_answer_text(t).split()))
            for i, t in enumerate(transcript)
        ]
        best_idx = max(scored, key=lambda x: x[1])[0]
        q = transcript[best_idx].question.question_text
        short_q = (q[:80] + "...") if len(q) > 80 else q
        strongest = (
            f"Your answer to '{short_q}' showed the most depth. Build other answers to match it."
        )
    else:
        strongest = "No answers yet."

    return Feedback(
        overall_score=score,
        overall_summary=summary,
        rubric=rubric,
        question_reviews=_build_question_reviews(transcript),
        strongest_moment=strongest,
        biggest_issue=biggest,
        improved_answer=_build_improved_answer(weakest, config),
        targeted_drills=_personalized_drills(config, transcript),
        next_practice_question=(
            f"Building on your answer about {_short_phrase(_answer_text(longest))}: "
            "tell me about a time you kept going on something hard when you "
            "did not have anyone around to help you figure it out."
        ),
        ethical_reminder=(
            "This is coaching, not a hiring decision. You do not need to "
            "change your voice, identity, or background to be taken seriously. "
            "For technical questions, double-check correctness yourself."
        ),
        coaching_notes=notes,
        assessed_dimension_count=assessed_n,
    )


def score_interview(
    config: InterviewConfig,
    plan: InterviewPlan,
    transcript: list[Turn],
    *,
    live: bool = False,
) -> Feedback:
    if live:
        try:
            from interviewos.claude import score_interview_live
            from interviewos.public import public_question_dict

            payload = {
                "config": config.model_dump(),
                "plan": plan.model_dump(),
                "turns": [
                    {
                        "question": public_question_dict(t.question)
                        | {
                            "correct_label": t.question.correct_label,
                            "correct_explanation": t.question.correct_explanation,
                        },
                        "answer": t.answer.model_dump(),
                    }
                    for t in transcript
                ],
                "guardrails": ETHICAL_GUARDRAILS,
            }
            data = score_interview_live(
                "Score this interview JSON.\n" + str(payload)
            )
            return Feedback(**data)
        except Exception:
            return mock_feedback(config, plan, transcript)
    return mock_feedback(config, plan, transcript)
