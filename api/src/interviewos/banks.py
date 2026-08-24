from __future__ import annotations

from copy import deepcopy

from interviewos.constants import DIFFICULTY_LADDER, STEM_TYPES

# Each technical item: difficulty, format, stem, optional latex/snippet,
# choices, correct_label, correct_explanation, interviewer_note.


def _mcq(
    difficulty: str,
    stem: str,
    choices: dict[str, str],
    correct: str,
    explanation: str,
    *,
    latex: str | None = None,
    note: str = "",
) -> dict:
    return {
        "question_text": stem,
        "question_type": "technical",
        "answer_format": "multiple_choice_with_explanation",
        "difficulty": difficulty,
        "latex": latex,
        "snippet": None,
        "choices": [{"label": k, "text": v} for k, v in choices.items()],
        "correct_label": correct,
        "correct_explanation": explanation,
        "interviewer_note": note or "Checking technical reasoning.",
    }


def _explain(
    difficulty: str,
    stem: str,
    snippet: str,
    explanation: str,
    *,
    note: str = "",
) -> dict:
    return {
        "question_text": stem,
        "question_type": "technical",
        "answer_format": "explain_snippet",
        "difficulty": difficulty,
        "latex": None,
        "snippet": snippet,
        "choices": [],
        "correct_label": None,
        "correct_explanation": explanation,
        "interviewer_note": note or "Walk me through this like you would on a whiteboard.",
    }


SWE_BANK: list[dict] = [
    _mcq(
        "Beginner",
        "What is the average-case time complexity of binary search on a sorted array of length n?",
        {
            "A": "O(1)",
            "B": "O(log n)",
            "C": "O(n)",
            "D": "O(n log n)",
        },
        "B",
        "Each step halves the search space, so steps grow as log2(n). Worst case is also O(log n).",
        latex=r"O(\log n)",
        note="Classic complexity warmup.",
    ),
    _mcq(
        "Beginner",
        "You need last-in, first-out semantics for a stream of items. Which structure fits?",
        {"A": "Queue", "B": "Stack", "C": "Priority queue", "D": "Hash set"},
        "B",
        "LIFO is a stack. A queue is FIFO.",
        note="LIFO vs FIFO recall.",
    ),
    _explain(
        "Beginner",
        "Walk me through this function. What does it return for nums = [1, 2, 3]?",
        "def total(nums):\n    s = 0\n    for n in nums:\n        s += n\n    return s",
        "It sums the list and returns 6. There is no bug; it is a linear scan accumulating a running total.",
        note="Can they narrate a simple loop out loud?",
    ),
    _mcq(
        "Intermediate",
        "You need the shortest path (fewest edges) from a node in an unweighted graph. Which traversal is best?",
        {
            "A": "DFS, because it explores deep first.",
            "B": "BFS, because it visits nodes in order of distance.",
            "C": "Either — they give the same path on unweighted graphs.",
            "D": "Dijkstra is required for shortest paths.",
        },
        "B",
        "BFS visits nodes in increasing distance from the start. Dijkstra is for weighted graphs.",
        note="Graph traversal selection.",
    ),
    _mcq(
        "Intermediate",
        "What is the average-case lookup time of a well-implemented hash map?",
        {"A": "O(1) on average.", "B": "O(log n).", "C": "O(n).", "D": "O(n log n)."},
        "A",
        "With a good hash and load factor, lookup is amortized O(1). Worst case can degrade to O(n).",
        note="Hash map basics.",
    ),
    _explain(
        "Intermediate",
        "This function is supposed to reverse a list in place. What is wrong, and how would you fix it?",
        "def reverse(items):\n    for i in range(len(items)):\n        items[i] = items[len(items) - 1 - i]\n    return items",
        "The loop overwrites the first half before it is swapped, so values are lost. Swap i with n-1-i only while i < n/2, or use two pointers.",
        note="Debug a classic off-by-structure bug.",
    ),
    _mcq(
        "Advanced",
        "A recursive tree algorithm does O(1) work per node and visits each node once. What is its time complexity on a tree with n nodes?",
        {"A": "O(1)", "B": "O(log n)", "C": "O(n)", "D": "O(n^2)"},
        "C",
        "If every node is visited a constant number of times, total work is linear in n regardless of height.",
        note="Connecting traversal to complexity.",
    ),
    _explain(
        "Advanced",
        "This Python snippet is meant to count unique words. Why can it be wrong, and what would you change?",
        "def unique_count(words):\n    seen = []\n    for w in words:\n        if w not in seen:\n            seen.append(w)\n    return len(seen)",
        "Membership in a list is O(n), so the whole function is O(n^2). Use a set for O(n). Also decide whether case and punctuation should be normalized.",
        note="Complexity plus correctness of uniqueness.",
    ),
    _mcq(
        "Intense",
        "You have a stream of integers and must report the median after every insertion. Which structure is the usual interview solution?",
        {
            "A": "A sorted array rebuilt each time.",
            "B": "Two heaps: a max-heap of the lower half and a min-heap of the upper half.",
            "C": "A single FIFO queue.",
            "D": "DFS over a BST of the entire history each query.",
        },
        "B",
        "Two heaps keep the two halves balanced so the median is at the heap roots in O(log n) per insert.",
        note="Harder data-structure design.",
    ),
    _explain(
        "Intense",
        "This concurrent counter is incremented from many threads. What can go wrong, and how would you make it safe?",
        "count = 0\n\ndef bump():\n    global count\n    count = count + 1",
        "Read-modify-write on count is not atomic, so increments can be lost. Use a lock, an atomic integer, or a queue of events reduced by one owner.",
        note="Concurrency without requiring a full systems interview.",
    ),
]

QUANT_BANK: list[dict] = [
    _mcq(
        "Beginner",
        "You roll a fair six-sided die once and win the dollar amount shown. What is the expected value?",
        {"A": "$3.00", "B": "$3.50", "C": "$4.00", "D": "$6.00"},
        "B",
        "(1+2+3+4+5+6)/6 = 21/6 = 3.50.",
        latex=r"E[X] = \sum_{k=1}^{6} k \cdot \tfrac{1}{6}",
    ),
    _mcq(
        "Beginner",
        "A fair coin is flipped. What is P(heads)?",
        {"A": "0", "B": "1/4", "C": "1/2", "D": "1"},
        "C",
        "Two equally likely outcomes; heads is one of them.",
    ),
    _explain(
        "Beginner",
        "A game pays $10 with probability 1/2 and $0 otherwise. Talk me through the expected payout.",
        "payoff = 10 with p = 1/2 else 0",
        "E = 10 * 1/2 + 0 * 1/2 = 5. Expected value is a probability-weighted average, not a typical outcome.",
    ),
    _mcq(
        "Intermediate",
        "X and Y are independent, each with variance sigma^2. What is Var(X + Y)?",
        {"A": "sigma^2", "B": "2 * sigma", "C": "2 * sigma^2", "D": "4 * sigma^2"},
        "C",
        "Independence implies Cov=0 so Var(X+Y)=Var(X)+Var(Y)=2 sigma^2.",
        latex=r"\mathrm{Var}(X+Y)=\mathrm{Var}(X)+\mathrm{Var}(Y)+2\mathrm{Cov}(X,Y)",
    ),
    _mcq(
        "Intermediate",
        "You flip a fair coin until heads. Expected number of flips including the heads?",
        {"A": "1", "B": "1.5", "C": "2", "D": "Infinity"},
        "C",
        "Geometric with p=1/2 has mean 1/p=2.",
        latex=r"E[N]=\sum_{k=1}^{\infty} k (1/2)^k",
    ),
    _explain(
        "Intermediate",
        "Two strategies have the same expected return. A has half the volatility of B. Which has the better Sharpe, and why?",
        "Sharpe = (E[R] - Rf) / sigma",
        "Sharpe is return per unit risk. Halving sigma at the same mean roughly doubles Sharpe (Rf small). A is better.",
    ),
    _mcq(
        "Advanced",
        "For i.i.d. samples, how does the standard error of the mean scale with sample size N?",
        {
            "A": "Proportional to 1/N",
            "B": "Proportional to 1/sqrt(N)",
            "C": "Proportional to sqrt(N)",
            "D": "Independent of N",
        },
        "B",
        "SE of the sample mean is sigma/sqrt(N).",
        latex=r"SE \propto 1/\sqrt{N}",
    ),
    _explain(
        "Advanced",
        "You observe a strategy with a high Sharpe on one year of daily data. What should you worry about before trusting it?",
        "sharpe_hat from 252 daily points",
        "Estimation error, multiple testing, non-stationarity, and overfitting. One year can look great by chance; ask for out-of-sample and a simple baseline.",
    ),
    _mcq(
        "Intense",
        "A European call and put on the same strike and expiry satisfy which no-arbitrage relation (rates aside, conceptual form)?",
        {
            "A": "Call price equals put price always.",
            "B": "Call − put equals a forward on the strike (put-call parity).",
            "C": "Call + put equals zero.",
            "D": "Puts cannot exist if calls exist.",
        },
        "B",
        "Put-call parity ties call and put prices to the forward. Exact formula includes discounting; the idea is a no-arbitrage identity.",
    ),
    _explain(
        "Intense",
        "A Monte Carlo estimator of an option price has huge variance. Talk through one control you would try first.",
        "price ≈ mean of discounted payoffs over N paths",
        "Antithetic variates, control variates (e.g. the Black-Scholes closed form as control), or importance sampling. Also check you are discounting and using the right measure.",
    ),
]

SCICOMP_BANK: list[dict] = [
    _mcq(
        "Beginner",
        "You have a 1000x500 matrix A and a length-500 vector x. What is the shape of A @ x?",
        {"A": "Length 1000.", "B": "Length 500.", "C": "1000 x 500.", "D": "Scalar."},
        "A",
        "Matrix-vector (m x n) @ (n,) -> (m,).",
        latex=r"A \in \mathbb{R}^{1000 \times 500},\; x \in \mathbb{R}^{500}",
    ),
    _mcq(
        "Beginner",
        "Which statement about floating-point addition is most accurate?",
        {
            "A": "All decimals are stored exactly.",
            "B": "Many decimals such as 0.1 are not exact in binary, so == can fail.",
            "C": "float64 never rounds.",
            "D": "Addition is always associative.",
        },
        "B",
        "0.1 and 0.2 are not exact in binary IEEE floats; compare with a tolerance.",
    ),
    _explain(
        "Beginner",
        "This comparison is failing in tests. Why, and what should you do instead?",
        "assert (0.1 + 0.2) == 0.3",
        "Rounding error. Use math.isclose or a tolerance. Do not teach students that floats are broken; teach representation.",
    ),
    _mcq(
        "Intermediate",
        "In a Monte Carlo estimate, what generally happens to standard error as independent paths N increase?",
        {
            "A": "Decreases proportional to 1/sqrt(N).",
            "B": "Decreases proportional to 1/N^2.",
            "C": "Increases proportional to sqrt(N).",
            "D": "Does not depend on N.",
        },
        "A",
        "SE of a sample mean scales as sigma/sqrt(N).",
        latex=r"SE \propto 1/\sqrt{N}",
    ),
    _mcq(
        "Intermediate",
        "Forward Euler on an ODE blows up. What is the first practical change to try?",
        {
            "A": "Use a larger time step.",
            "B": "Reduce the time step until the scheme is stable.",
            "C": "Switch to float32.",
            "D": "Add random noise.",
        },
        "B",
        "Forward Euler is conditionally stable. Shrink dt; longer term, consider an implicit method.",
    ),
    _explain(
        "Intermediate",
        "This loop builds a matrix one row at a time by concatenating. What is the performance issue?",
        "A = np.zeros((0, 3))\nfor row in rows:\n    A = np.vstack([A, row])",
        "Repeated vstack copies the growing array, O(n^2). Preallocate or collect rows and stack once.",
    ),
    _mcq(
        "Advanced",
        "You are solving Ax=b with a dense n x n matrix using a naive cubic solver. How does runtime scale?",
        {"A": "O(n)", "B": "O(n log n)", "C": "O(n^2)", "D": "O(n^3)"},
        "D",
        "Dense Gaussian elimination / LU is cubic in n.",
    ),
    _explain(
        "Advanced",
        "A simulation is stable in double precision and blows up in single precision. What hypotheses would you test?",
        "same scheme, float32 vs float64",
        "Rounding accumulation, a stability threshold near machine epsilon, cancellation in a residual. Check condition number and whether a quantity that should be ~1e-8 is being treated as zero.",
    ),
    _mcq(
        "Intense",
        "Which statement about stiffness in ODEs is most accurate?",
        {
            "A": "Stiff problems are always nonlinear.",
            "B": "Explicit methods may need tiny steps; implicit methods are often preferred.",
            "C": "Stiffness means the solution is chaotic.",
            "D": "You fix stiffness by using bigger steps.",
        },
        "B",
        "Stiffness is a stability/step-size issue. Implicit (or specially designed) methods handle separated timescales better.",
    ),
    _explain(
        "Intense",
        "You need to integrate a conservation law and your scheme slowly gains mass. What would you look at first?",
        "update: u^{n+1} = u^n + dt * flux_difference",
        "Check discrete conservation (telescoping fluxes), boundary fluxes, and whether the flux is evaluated consistently (e.g. conservative form). Also check dt vs CFL.",
    ),
]

DS_BANK: list[dict] = [
    _mcq(
        "Beginner",
        "Why hold out a test set instead of evaluating only on training data?",
        {
            "A": "Training data is too large to evaluate.",
            "B": "To estimate performance on data the model has not fitted.",
            "C": "Test data is more accurate.",
            "D": "It is required by law.",
        },
        "B",
        "The point is generalization. Training accuracy alone does not tell you real-world behavior.",
    ),
    _mcq(
        "Beginner",
        "A model that always predicts 'not fraud' on a dataset with 1% fraud has about what accuracy?",
        {"A": "1%", "B": "50%", "C": "99%", "D": "Cannot tell."},
        "C",
        "99% of rows are not fraud. Accuracy is the wrong metric; use precision/recall.",
    ),
    _explain(
        "Beginner",
        "Train accuracy is 99% and test accuracy is 60%. What is the most likely diagnosis, and what would you try?",
        "train_acc=0.99  test_acc=0.60",
        "Overfitting. Regularize, simplify, get more data, or stop earlier. Do not add more capacity first.",
    ),
    _mcq(
        "Intermediate",
        "Which statement best captures the bias-variance tradeoff?",
        {
            "A": "Lower bias always means lower test error.",
            "B": "Reducing complexity usually lowers variance but can raise bias.",
            "C": "Variance is irreducible.",
            "D": "Bias and variance ignore model choice.",
        },
        "B",
        "Simpler models tend to be more stable (lower variance) and less flexible (higher bias).",
        latex=r"Error \approx Bias^2 + Variance + Noise",
    ),
    _mcq(
        "Intermediate",
        "You one-hot encode a high-cardinality ID column before a linear model. What is the main risk?",
        {
            "A": "The model becomes too slow to start.",
            "B": "Huge sparse feature space and overfitting rare IDs.",
            "C": "One-hot encoding is lossless so there is no risk.",
            "D": "Linear models cannot read numbers.",
        },
        "B",
        "Rare levels get their own weights with little data. Target encoding or grouping rares is safer.",
    ),
    _explain(
        "Intermediate",
        "This train/test split leaked the future. Point at the bug.",
        "scaler.fit(all_data)\nX_train, X_test = split(scaler.transform(all_data))",
        "The scaler saw the test distribution. Fit on train only, then transform both. Same for any target-derived feature.",
    ),
    _mcq(
        "Advanced",
        "For a ranking model, which metric is more aligned with 'put relevant items near the top' than raw accuracy?",
        {"A": "Training loss only", "B": "NDCG or MAP", "C": "Number of parameters", "D": "File size"},
        "B",
        "Ranking metrics care about order. Accuracy treats every position the same.",
    ),
    _explain(
        "Advanced",
        "A classifier looks strong on a random split but fails in production a month later. What evaluations would you add?",
        "offline random split AUC = 0.94",
        "Time-based split, slice metrics by segment, calibration, and a simple baseline. Check distribution shift and label delay.",
    ),
    _mcq(
        "Intense",
        "You must choose between a more accurate black-box model and a slightly worse linear model for a high-stakes decision. Which consideration is most interview-relevant?",
        {
            "A": "Always pick the higher AUC.",
            "B": "Interpretability, monitoring, and error costs may outweigh a small AUC gap.",
            "C": "Linear models cannot be used in production.",
            "D": "Black-box models never miscalibrate.",
        },
        "B",
        "Accuracy is not the only production constraint. Be able to explain tradeoffs without dogma.",
    ),
    _explain(
        "Intense",
        "You A/B test a new model and the treatment looks better on clicks but revenue is flat. How do you talk about next steps?",
        "lift in CTR, no lift in revenue",
        "Metric mismatch, position bias, novelty, and delayed conversions. Do not ship on a proxy that the business does not value. Pre-register the decision metric.",
    ),
]

# Workplace / scholarship reasoning — NOT SWE trivia.
WORKPLACE_BANK: list[dict] = [
    _mcq(
        "Beginner",
        "A teammate asks you to do something you do not know how to do yet. What is the strongest first move in an internship?",
        {
            "A": "Say yes and stay silent so you do not look inexperienced.",
            "B": "Clarify the goal, then ask a specific question after you have tried once.",
            "C": "Refuse any task that is not already on your resume.",
            "D": "Wait until the deadline and then explain you were stuck.",
        },
        "B",
        "Interviewers want initiative plus communication. Trying first and asking a sharp question beats hiding or blocking.",
        note="Help-seeking without performing fake expertise.",
    ),
    _mcq(
        "Beginner",
        "You have two small tasks due today and one is blocked on a reply. What should you do?",
        {
            "A": "Idle until the reply arrives.",
            "B": "Work the unblocked task and send a short status on the blocked one.",
            "C": "Mark both complete.",
            "D": "Only work on whichever feels more interesting.",
        },
        "B",
        "Unblock yourself with parallel work and make the dependency visible. That is intern-level professionalism.",
    ),
    _explain(
        "Beginner",
        "Read this Slack message. What would you change before sending it to a manager?",
        "hey so like the thing is broken i guess maybe we should fix it sometime",
        "State the problem, impact, what you tried, and a clear ask. Keep the voice; drop hedges and vagueness.",
    ),
    _mcq(
        "Intermediate",
        "You notice a process that wastes an hour a week. How do you raise it?",
        {
            "A": "Complain in a group chat with no proposal.",
            "B": "Describe the current cost, a possible fix, and ask who owns the decision.",
            "C": "Change production without telling anyone.",
            "D": "Ignore it; interns should not comment on process.",
        },
        "B",
        "Good judgment: quantify, propose, respect ownership. Do not silently change shared systems.",
    ),
    _mcq(
        "Intermediate",
        "A scholarship interviewer asks what the funding would change. Which answer is strongest?",
        {
            "A": "It would look good on my resume.",
            "B": "A concrete constraint it removes (hours of work, unpaid summer, travel) and what you would do with that time.",
            "C": "I deserve it more than other people.",
            "D": "I have not thought about it.",
        },
        "B",
        "Committees fund a specific unlock, not a vibe. Specifics beat comparison and status.",
    ),
    _explain(
        "Intermediate",
        "You promised a draft Friday and it will slip to Monday. Draft the update you would send Thursday afternoon.",
        "original: 'draft Friday'",
        "Say the new time, the reason without drama, what is already done, and what you need. Early notice beats a silent miss.",
    ),
    _mcq(
        "Advanced",
        "A teammate takes credit for work you did in a meeting. What is the most professional next step?",
        {
            "A": "Shame them publicly in the same meeting.",
            "B": "Follow up with facts in writing and, if needed, a private conversation with your manager.",
            "C": "Quit the same day.",
            "D": "Do worse work so they cannot use it.",
        },
        "B",
        "Protect the record without escalating to theater. Evidence and the right audience matter.",
    ),
    _explain(
        "Advanced",
        "You are transferring schools. How would you explain a C in a required course without sounding like you are making excuses?",
        "transcript: C in Calculus I, A in later proof-based course",
        "Own the result, name what changed (hours, tutoring, approach), and point to later evidence. Do not attack the professor or hide the grade.",
    ),
    _mcq(
        "Intense",
        "You discover a teammate copied text from the internet into a shared application essay you both must submit. What do you do?",
        {
            "A": "Submit it; everyone does this.",
            "B": "Stop the submission, tell them it cannot go out, and escalate if they refuse.",
            "C": "Rewrite only your half and hope.",
            "D": "Post about it on social media.",
        },
        "B",
        "Integrity first. Do not submit, do not pile on publicly, do not split the difference.",
    ),
    _explain(
        "Intense",
        "An interviewer pushes you to exaggerate a leadership title. How do you refuse while staying in the conversation?",
        "prompt: 'Just say you led the team'",
        "Correct the title, describe the actual scope, and keep offering evidence. Refusing to lie is compatible with staying warm and specific.",
    ),
]

TECHNICAL_BANKS: dict[str, list[dict]] = {
    "Technical SWE": SWE_BANK,
    "Quant / Trading": QUANT_BANK,
    "Scientific Computing": SCICOMP_BANK,
    "Data Science": DS_BANK,
    "Research Program": SCICOMP_BANK,
    "Internship": WORKPLACE_BANK,
    "Scholarship": WORKPLACE_BANK,
    "College / Transfer": WORKPLACE_BANK,
    "First Job": WORKPLACE_BANK,
    "Custom": WORKPLACE_BANK,
}

QUALITATIVE_STARTERS: dict[str, dict[str, str]] = {
    "Internship": {
        "Beginner": "Walk me through what drew you to this internship and what you hope to learn.",
        "Intermediate": "Walk me through a project or class that made you want this internship, and what you would want to get better at this summer.",
        "Advanced": "What is the highest-leverage thing you have already done that you would want this internship to build on?",
        "Intense": "If I only remember one thing about you after this interview, what should it be — and what evidence should I attach to it?",
    },
    "Scholarship": {
        "Beginner": "Tell me about yourself and what this scholarship would make possible.",
        "Intermediate": "What would actually change in your week if you received this scholarship?",
        "Advanced": "Tell me about a time you kept going when the resources around you were thin.",
        "Intense": "Why this scholarship, and why should a committee trust you with scarce funds?",
    },
    "Research Program": {
        "Beginner": "Tell me about your background and a project or idea that genuinely excites you.",
        "Intermediate": "Walk me through a computational or research project you actually finished. What surprised you?",
        "Advanced": "What question would you want to spend a summer trying to answer, and why are you a good person to try?",
        "Intense": "Describe a result you got that was plausible but wrong. How did you catch it?",
    },
    "College / Transfer": {
        "Beginner": "Why this school, and what do you hope the next two years look like academically?",
        "Intermediate": "What have you already done to prepare for this campus, and what will be new for you?",
        "Advanced": "Which academic community do you want to join here, and what would you contribute on day one?",
        "Intense": "Transfer stories can sound generic. Give me the version that could only be yours.",
    },
    "First Job": {
        "Beginner": "Walk me through your background and why this role caught your attention.",
        "Intermediate": "What have you actually shipped or finished that is closest to this job?",
        "Advanced": "Where have you already operated without a lot of supervision, and what broke?",
        "Intense": "Why this role instead of the obvious alternatives, with evidence rather than adjectives?",
    },
    "Technical SWE": {
        "Beginner": "Walk me through a project you actually built and why you chose that design.",
        "Intermediate": "Tell me about a bug or design choice that taught you something you still use.",
        "Advanced": "Walk me through a tradeoff you made in a project — what you optimized for, and what you gave up.",
        "Intense": "Describe a system you would redesign now. What was wrong, and what would you change first?",
    },
    "Quant / Trading": {
        "Beginner": "Tell me about a problem where you had to reason from first principles, not a memorized formula.",
        "Intermediate": "Walk me through a quantitative project and one assumption you would now challenge.",
        "Advanced": "When did a model or backtest lie to you, and how did you find out?",
        "Intense": "Give me a market or probability idea you understand well enough to teach in three minutes.",
    },
    "Scientific Computing": {
        "Beginner": "Tell me about a computational project and one thing about it that surprised you.",
        "Intermediate": "Walk me through how you knew a simulation or numerical result was trustworthy.",
        "Advanced": "Describe a numerical issue (stability, precision, cost) you actually had to manage.",
        "Intense": "If I gave you a code that 'mostly works,' how would you decide whether to trust it?",
    },
    "Data Science": {
        "Beginner": "Walk me through a data project you finished and what you would do differently.",
        "Intermediate": "Tell me about a time a metric or dashboard misled you.",
        "Advanced": "How do you decide a model is good enough to act on, not just good on a notebook score?",
        "Intense": "Describe a messy data decision where two reasonable people could disagree. What did you choose?",
    },
    "Custom": {
        "Beginner": "Tell me about yourself and why this opportunity caught your attention.",
        "Intermediate": "What have you already done that is closest to this opportunity?",
        "Advanced": "What would success in this role look like after 90 days for you personally?",
        "Intense": "Why you, why this, why now — with evidence, not slogans.",
    },
}

PROBE_TEMPLATES = {
    "vague": (
        "I heard a short answer. Give me one concrete moment — a project, class, or conversation — and walk me through what you actually did.",
        "Pushing for a concrete example.",
    ),
    "no_evidence": (
        "I want evidence behind that. What is one thing you have actually built, written, or led that shows it?",
        "Asking for evidence.",
    ),
    "no_motivation": (
        "Why does this specific opportunity matter to you? What would change if you got it?",
        "Probing motivation.",
    ),
    "technical_miss": (
        "That choice is not what I was looking for. Walk me through how you would re-derive it from first principles, without defending the original pick.",
        "Technical follow-up after a miss.",
    ),
    "strong": (
        "That is a strong start. What was the hardest part of that work, and what did you change because of it?",
        "Going deeper on a strong answer.",
    ),
}


def bank_for(interview_type: str) -> list[dict]:
    if interview_type in TECHNICAL_BANKS:
        return TECHNICAL_BANKS[interview_type]
    return TECHNICAL_BANKS["Custom"]


def qualitative_starter(interview_type: str, difficulty: str) -> str:
    table = QUALITATIVE_STARTERS.get(interview_type) or QUALITATIVE_STARTERS["Custom"]
    if difficulty in table:
        return table[difficulty]
    return table["Intermediate"]


def _difficulty_rank(name: str) -> int:
    try:
        return DIFFICULTY_LADDER.index(name)
    except ValueError:
        return 1


def select_technical_item(
    interview_type: str,
    difficulty: str,
    used_stems: set[str],
    *,
    prefer_format: str | None = None,
) -> dict:
    """Pick a technical item matching difficulty; never repeats a used stem."""
    bank = [deepcopy(item) for item in bank_for(interview_type)]
    unused = [item for item in bank if item["question_text"] not in used_stems]
    if not unused:
        raise RuntimeError("technical bank exhausted for this session")

    def rank_gap(item: dict) -> tuple[int, int]:
        gap = abs(_difficulty_rank(item["difficulty"]) - _difficulty_rank(difficulty))
        format_penalty = 0
        if prefer_format and item["answer_format"] != prefer_format:
            format_penalty = 1
        same_diff = 0 if item["difficulty"] == difficulty else 1
        return (same_diff, gap, format_penalty)

    unused.sort(key=rank_gap)
    # Prefer exact difficulty when available.
    exact = [i for i in unused if i["difficulty"] == difficulty]
    pool = exact or unused
    if prefer_format:
        formatted = [i for i in pool if i["answer_format"] == prefer_format]
        if formatted:
            pool = formatted
    return deepcopy(pool[0])


def is_stem_type(interview_type: str) -> bool:
    return interview_type in STEM_TYPES
