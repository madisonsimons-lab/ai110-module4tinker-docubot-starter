# DocuBot Model Card

This model card is a short reflection on your DocuBot system. Fill it out after you have implemented retrieval and experimented with all three modes:

1. Naive LLM over full docs  
2. Retrieval only  
3. RAG (retrieval plus LLM)

Use clear, honest descriptions. It is fine if your system is imperfect.

---

## 1. System Overview

**What is DocuBot trying to do?**  
Describe the overall goal in 2 to 3 sentences.

> DocuBot is a small documentation assistant for answering developer questions from a local docs folder. It supports a naive LLM mode, a retrieval-only mode, and a retrieval-augmented generation mode so the system can be compared under different grounding strategies.

**What inputs does DocuBot take?**  
For example: user question, docs in folder, environment variables.

> DocuBot takes a user question, the markdown or text files in the docs folder, and optionally a GEMINI_API_KEY environment variable for LLM-backed modes. The retrieval system also depends on the content and structure of the docs because it indexes heading-based sections rather than raw files.

**What outputs does DocuBot produce?**

> In retrieval-only mode it returns ranked text snippets with filenames. In naive LLM mode and RAG mode it attempts to return natural-language answers, with RAG intended to ground those answers in retrieved snippets.

---

## 2. Retrieval Design

**How does your retrieval system work?**  
Describe your choices for indexing and scoring.

- How do you turn documents into an index?
- How do you score relevance for a query?
- How do you choose top snippets?

> The system first loads each document and splits it into smaller heading-based sections. It builds a simple inverted index from normalized content tokens to filenames, then scores each section by token overlap, short query phrase matches, and small structural bonuses for route-shaped sections, matching headings, and table-like content. The top scoring sections that pass an evidence threshold are returned as snippets.

**What tradeoffs did you make?**  
For example: speed vs precision, simplicity vs accuracy.

> I chose a Python-only bag-of-words style retriever because it is easy to inspect and debug. That makes the system simple and fast on a small corpus, but it still uses brittle lexical matching, so generic headings and repeated terms can sometimes outrank the best snippet.

---

## 3. Use of the LLM (Gemini)

**When does DocuBot call the LLM and when does it not?**  
Briefly describe how each mode behaves.

- Naive LLM mode:
- Retrieval only mode:
- RAG mode:

> Naive LLM mode calls Gemini directly for the question. Retrieval only mode never calls the LLM and only returns snippets from the docs. RAG mode retrieves snippets first and then sends only those snippets plus the question to Gemini.

**What instructions do you give the LLM to keep it grounded?**  
Summarize the rules from your prompt. For example: only use snippets, say "I do not know" when needed, cite files.

> The RAG prompt tells the model to answer using only the provided snippets, not invent endpoints or configuration values, refuse with the exact sentence "I do not know based on the docs I have." when evidence is insufficient, and briefly mention which files it relied on. One important limitation is that naive mode does not currently follow those grounding rules because the implementation ignores the full docs text and sends only the question.

---

## 4. Experiments and Comparisons

Run the **same set of queries** in all three modes. Fill in the table with short notes.

You can reuse or adapt the queries from `dataset.py`.

| Query | Naive LLM: helpful or harmful? | Retrieval only: helpful or harmful? | RAG: helpful or harmful? | Notes |
|------|---------------------------------|--------------------------------------|---------------------------|-------|
| Where is the auth token generated? | Not run on this machine; design is weakly grounded because naive mode ignores the docs text | Helpful but verbose; it returns the correct Token Generation section plus extra AUTH sections | Not run on this machine; intended to be helpful because retrieval finds the right evidence first | Retrieval surfaces AUTH.md sections headed Token Generation, Authentication Guide, and Environment Variables. |
| How do I connect to the database? | Not run on this machine; if enabled it would answer without explicit grounding to docs | Helpful but somewhat noisy; it returns the correct Connection Configuration section plus broad database context | Not run on this machine; intended to summarize the DATABASE.md sections more clearly than retrieval only | Retrieval returns the DATABASE.md title section, Connection Configuration, and Overview. |
| Which endpoint lists all users? | Not run on this machine; if enabled it could sound confident without citing the exact endpoint | Mostly helpful; the top result is correct but lower ranked snippets still include unrelated database helper text | Not run on this machine; intended to answer from the GET /api/users snippet only | Retrieval uses the GET /api/users section first, but also includes DATABASE.md Query Helpers. |
| How does a client refresh an access token? | Not run on this machine; if enabled it could blend login and refresh details | Accurate but harder to interpret because the top snippet is good while later snippets are mixed | Not run on this machine; intended to convert the best snippets into a clearer answer | Retrieval returns AUTH.md Client Workflow first, then API reference context. |

**What patterns did you notice?**  

- When does naive LLM look impressive but untrustworthy?  
- When is retrieval only clearly better?  
- When is RAG clearly better than both?

> The strongest pattern is that system design matters more than model fluency. Retrieval only is often accurate because it exposes raw evidence, but the output can still be hard to read when multiple snippets are returned. Naive mode is currently the least trustworthy design because even if Gemini were available, the code ignores the docs and asks the model the question directly. RAG is the most promising design because it combines retrieval evidence with an explicit refusal rule, but I could not verify its live behavior on this machine because GEMINI_API_KEY was missing during testing.

---

## 5. Failure Cases and Guardrails

**Describe at least two concrete failure cases you observed.**  
For each one, say:

- What was the question?  
- What did the system do?  
- What should have happened instead?

> Failure case 1: The question "Which endpoint lists all users?" returned the correct API snippet in retrieval-only mode, but it also returned a DATABASE.md Query Helpers section. The system should still prefer the API snippet, but the extra database helper text makes the answer harder to interpret.

> Failure case 2: I could not run naive mode or RAG mode during this session because GEMINI_API_KEY was missing. In addition, code inspection showed that naive mode ignores the full docs text entirely, so even with a valid key it would produce answers that sound authoritative but are weakly grounded.

**When should DocuBot say “I do not know based on the docs I have”?**  
Give at least two specific situations.

> DocuBot should refuse when no retrieved section has enough overlapping evidence for the query, such as questions about payment processing that are not covered in the docs. It should also refuse when the retrieved snippets are only loosely related and do not directly answer the question, for example if a route question only matches generic setup or overview text.

**What guardrails did you implement?**  
Examples: refusal rules, thresholds, limits on snippets, safe defaults.

> The retriever now works on smaller heading-based sections instead of whole files, which reduces irrelevant context. It also filters weak matches with an explicit evidence check before returning a snippet. On the LLM side, the RAG prompt tells Gemini to use only the retrieved snippets, avoid invention, and refuse explicitly when evidence is missing.

---

## 6. Limitations and Future Improvements

**Current limitations**  
List at least three limitations of your DocuBot system.

1. The current environment does not have a working Gemini key, so live comparison of Mode 1 and Mode 3 was blocked.
2. Naive mode is not actually grounded because the implementation ignores the full docs text.
3. Retrieval still relies on brittle lexical matching, so extra sections from the same or related files can appear in the results.

**Future improvements**  
List two or three changes that would most improve reliability or usefulness.

1. Fix naive mode so it actually includes the full document corpus in the prompt.
2. Deduplicate or compress overlapping snippets so retrieval-only output is easier to read.
3. Improve scoring with better normalization or lightweight semantic matching so related words do not depend on exact token forms.

---

## 7. Responsible Use

**Where could this system cause real world harm if used carelessly?**  
Think about wrong answers, missing information, or over trusting the LLM.

> This system could cause harm if developers trust fluent answers about authentication, permissions, or database behavior without checking the docs or code. A weakly grounded LLM answer could invent an endpoint or omit a security constraint, and even retrieval-only mode can still bury the relevant evidence under extra snippets if used carelessly.

**What instructions would you give real developers who want to use DocuBot safely?**  
Write 2 to 4 short bullet points.

- Treat every answer as a starting point and verify the cited docs section before changing code.
- Prefer retrieval or RAG over naive generation when correctness matters.
- If the system cannot show a clearly relevant snippet, treat the result as unsupported.
- Re-test the same question across modes when an answer seems surprisingly confident.

---
