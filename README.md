# InterviewOS

**Practice high-stakes interviews when you do not have insider access.**

Built for the Spring Sprint Hackathon &mdash; *Economic Empowerment & Education* track.

---

## What it does

InterviewOS is a structured AI mock-interview *environment* — not a chat
window. It plans an interview, asks adaptive questions through an animated
interviewer, supports both qualitative *and* technical multiple-choice
questions (with rendered LaTeX for math), runs a per-question timer, scores
the whole transcript on a 10-dimension rubric, and gives a question-by-question
review plus targeted drills the user can take home.

It is a single Streamlit app. No database, no auth, no file upload.

## Who it helps

Students who have talent but not always access to realistic interview
practice:

- First-generation college students
- Low-income students
- Rural and small-town students
- Community college students preparing to transfer
- Immigrant students
- Anyone applying to internships, scholarships, research programs, transfer
  admissions, first jobs, technical SWE roles, quant roles, scientific
  computing roles, or data science roles without an alumni network or family
  Rolodex

## Why it matters

Many students do not lose opportunities because they lack ability. They
lose them because their **first real interview is also their first serious
practice**. Wealthier and better-networked students get to rehearse with
parents, family friends, alumni, recruiters, or paid coaches. InterviewOS
gives every student a realistic, low-stakes place to practice, get
feedback, and try again.

## Features

- **Animated interviewer avatar** with floating + blinking animations and a
  speech bubble — the question feels asked, not pasted.
- **Auto, Qualitative, Technical, and Mixed** interview modes. In Mixed
  mode, qualitative and technical questions alternate.
- **Auto mode** plans the interview for the user: it picks the mode,
  difficulty, question count, and timer based on the opportunity description
  and the applicant's background. The plan is shown back to the user in an
  "AI Interview Plan" card.
- **Configurable interview length** (3, 5, 7, or 10 questions; capped at 10
  for hackathon demos).
- **Difficulty levels:** Beginner / Intermediate / Advanced / Intense (or
  Auto).
- **Per-question timer** (off / 30s / 60s / 90s / 120s) with a smoothly-
  animated CSS countdown bar that does not depend on Streamlit reruns.
  Submission is *not* force-killed on expiry — the user can still finish.
- **Technical multiple-choice questions** with 4 labeled options and a
  required written reasoning prompt. The correct answer is hidden during
  the interview and revealed only at scoring.
- **LaTeX rendering** for math via `st.latex`, with a graceful `st.code`
  fallback if the LaTeX is malformed.
- **Adaptive follow-up questions** that respond to vagueness, missing
  evidence, missing motivation, or strong answers.
- **10-dimension rubric** (clarity, specificity, confidence, relevance,
  authenticity, structure, evidence & examples, growth mindset,
  technical reasoning, technical correctness).
- **Question-by-question review** with the correct answer + explanation
  for each technical question.
- **Improved-answer rewrite** that strips the user's hedges and front-loads
  a one-sentence point — *while preserving their actual facts*.
- **Targeted drills** that quote the user's own content.
- **Download report (Markdown)** so the user can take everything home.
- **"Try again at higher difficulty"** button that re-runs the same
  opportunity at the next rung of the difficulty ladder.
- **"See sample feedback report"** button on setup that opens a fully
  populated dashboard for a 30-second judge.
- **Demo Mode badge** when no `ANTHROPIC_API_KEY` is set — every feature
  still works, deterministically, with zero cost or network calls.

## Why this is not just ChatGPT

This is a practice **environment**, not a chat window. It includes:

- A structured interview loop (setup &rarr; AI plan &rarr; N adaptive
  questions &rarr; scoring &rarr; question reviews &rarr; drills)
- An animated interviewer that simulates pacing
- Adaptive follow-up questions
- Technical multiple-choice questions with required written reasoning
- Rendered math (LaTeX) for technical questions
- Rubric-based scoring across 10 dimensions
- Question-by-question review with correct answers + explanations
- An improved-answer rewrite that **preserves the user's actual facts**
- Targeted drills tied to the user's specific content
- Visible coaching safeguards on every screen

## How it uses AI

- If `ANTHROPIC_API_KEY` is set, the app uses Anthropic's Claude to plan
  the interview, generate the opening question, generate adaptive
  follow-ups (qualitative *and* technical), and score the rubric +
  question reviews.
- Every Claude call is constrained to **return JSON only**, validated with
  Pydantic, and falls back to deterministic mock data on any failure
  (invalid JSON, schema mismatch, network error). The app never crashes
  mid-demo.
- If no API key is present, the app runs in **Demo Mode** with a visible
  yellow badge. A deterministic mock planner, mock qualitative interviewer,
  and a small bank of mock technical questions per interview type take
  over. Reviewers can experience the full flow with zero setup or cost.

## Ethical risks and safeguards

AI coaching for interviews can do real harm if it is built carelessly.
InterviewOS is opinionated about this:

**Risks we take seriously**

- AI can reflect biases about "professional" speech, accent, or style.
- AI can pressure users to flatten their identity or culture.
- AI can hallucinate achievements that the user never actually had.
- AI can make math or correctness mistakes on technical questions.
- AI feedback can be mistaken for an actual hiring/admissions verdict.

**Built-in safeguards**

- The system prompt forbids judging accent, dialect, identity,
  personality, socioeconomic background, or cultural style.
- The improved-answer rewrite is explicitly told to **preserve the user's
  actual facts** and not invent achievements.
- The model is told to never predict whether the user will or will not
  get the role, and never encourage lying or exaggeration.
- The technical scoring prompt is told to be honest about uncertainty
  rather than guess at correctness.
- A persistent **Ethical safeguards** card is shown near the bottom of
  every screen reminding users that this is coaching, not a verdict, that
  technical answers may have mistakes, and that humans remain in control.
- An **ethical reminder** is included in every feedback dashboard.

## Local setup

Requires Python 3.10+.

```bash
# 1. Clone and enter the project
cd "Spring Sprint Hackathon"

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Set up your Anthropic key for Live mode
cp .env.example .env
# then edit .env and paste your ANTHROPIC_API_KEY

# 5. Run the app
streamlit run app.py
```

The app opens at <http://localhost:8501>.

If `.env` is missing or empty, the app runs in **Demo Mode** automatically
and displays a yellow badge at the top. Demo Mode is fully functional and
deterministic &mdash; great for reviewers without an API key.

## Environment variables

| Variable            | Required | Purpose                                                                 |
| ------------------- | -------- | ----------------------------------------------------------------------- |
| `ANTHROPIC_API_KEY` | optional | Enables Live mode. If missing, the app uses deterministic mock data.    |
| `ANTHROPIC_MODEL`   | optional | Override the default Claude model. Defaults to the constant in `app.py`.|

## 2-minute demo script

1. **(0:00) Open the app.** Point out the **Demo Mode** badge if you have
   no API key, or the **Live mode** badge if you do. Read the hero
   tagline: *"Practice high-stakes interviews when you do not have
   insider access."*
2. **(0:10) Read the two intro cards** &mdash; *Why this matters* and
   *Why this is not just ChatGPT*.
3. **(0:25) Choose Auto mode.** In the setup card, set **Interview mode**
   to *Auto*, **Difficulty** to *Auto*, **Number of questions** to *Auto*,
   and **Timer** to *60 seconds / question*. Pick **Interview type:
   Research Program** (or paste a research/technical opportunity into the
   description box). Click **Start interview**.
4. **(0:45) Show the AI Interview Plan card.** It explains in plain
   English why the AI picked Mixed mode, Intermediate difficulty, and
   3 questions for this profile.
5. **(0:55) The animated interviewer avatar** asks the first
   (qualitative) question. The italic *Coach:* line shows what the
   interviewer is probing for. Type a short answer and submit.
6. **(1:15) The next question is technical and rendered with LaTeX**
   (e.g. Monte Carlo standard error). Pick one of A/B/C/D, write a
   one-sentence reason, submit. The countdown bar shrinks smoothly the
   whole time.
7. **(1:30) Answer the third question.** Click **End interview and score
   me**.
8. **(1:40) The feedback dashboard** shows: overall score, the 10-item
   rubric grid (qualitative + technical scores split out), the
   question-by-question review (with the correct answer + explanation
   revealed for the technical item), the improved-answer rewrite, three
   targeted drills, and a download button.
9. **(1:55) Scroll to the Ethical safeguards card.** Call out: this is
   coaching, not a verdict; the rewrite preserves the user's real facts;
   technical answers may have mistakes, verify yourself; humans remain in
   control.

## Future improvements

- More interview types (graduate school, technical phone screens,
  behavioral case interviews)
- Voice-mode practice with speech-to-text answers
- Save transcripts locally so users can compare attempts over time
- A community-sourced library of real opportunity descriptions to
  practice against
- Localization for non-English-dominant students
- Optional human-in-the-loop review for users who want a real coach to
  read the AI feedback before they trust it
