"""
Core DocuBot class responsible for:
- Loading documents from the docs/ folder
- Building a simple retrieval index (Phase 1)
- Retrieving relevant snippets (Phase 1)
- Supporting retrieval only answers
- Supporting RAG answers when paired with Gemini (Phase 2)
"""

import os
import glob
import re


STOPWORDS = {
    "a",
    "an",
    "any",
    "and",
    "are",
    "by",
    "do",
    "does",
    "for",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "mention",
    "of",
    "or",
    "that",
    "the",
    "there",
    "these",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "docs",
}

class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None):
        """
        docs_folder: directory containing project documentation files
        llm_client: optional Gemini client for LLM based answers
        """
        self.docs_folder = docs_folder
        self.llm_client = llm_client

        # Load documents into memory
        self.documents = self.load_documents()  # List of (filename, text)

        # Break documents into smaller retrieval units.
        self.sections = self.build_sections(self.documents)

        # Build a retrieval index (implemented in Phase 1)
        self.index = self.build_index(self.sections)

    # -----------------------------------------------------------
    # Document Loading
    # -----------------------------------------------------------

    def load_documents(self):
        """
        Loads all .md and .txt files inside docs_folder.
        Returns a list of tuples: (filename, text)
        """
        docs = []
        pattern = os.path.join(self.docs_folder, "*.*")
        for path in glob.glob(pattern):
            if path.endswith(".md") or path.endswith(".txt"):
                with open(path, "r", encoding="utf8") as f:
                    text = f.read()
                filename = os.path.basename(path)
                docs.append((filename, text))
        return docs

    def build_sections(self, documents):
        """
        Split each document into heading-based sections.
        """
        sections = []

        for filename, text in documents:
            blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
            current_section = []

            for block in blocks:
                if block.startswith("#") and current_section:
                    sections.append((filename, "\n\n".join(current_section)))
                    current_section = [block]
                else:
                    current_section.append(block)

            if current_section:
                sections.append((filename, "\n\n".join(current_section)))

        return sections

    # -----------------------------------------------------------
    # Index Construction (Phase 1)
    # -----------------------------------------------------------

    def _tokenize(self, text):
        """
        Lowercase text and extract simple word tokens.
        """
        return re.findall(r"\b\w+\b", text.lower())

    def _normalize_token(self, token):
        """
        Collapse a few common suffix variations to a shared base form.
        """
        for suffix in ("ing", "ed", "es", "s", "ion"):
            if token.endswith(suffix) and len(token) > len(suffix) + 2:
                return token[: -len(suffix)]
        return token

    def _content_tokens(self, text):
        """
        Return tokens with common question words removed.
        """
        tokens = []
        for token in self._tokenize(text):
            if token in STOPWORDS:
                continue
            tokens.append(self._normalize_token(token))
        return tokens

    def _query_phrases(self, query):
        """
        Build simple two-word phrases from the query tokens.
        """
        tokens = self._content_tokens(query)
        return [f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)]

    def _route_bonus(self, query, text):
        """
        Prefer route-shaped sections for endpoint-style questions.
        """
        query_tokens = set(self._content_tokens(query))
        text_lower = text.lower()

        if ("endpoint" in query_tokens or "route" in query_tokens) and "/api/" in text_lower:
            return 3

        return 0

    def _heading_bonus(self, query, text):
        """
        Prefer sections whose heading matches the query terms.
        """
        query_tokens = set(self._content_tokens(query))
        heading = text.splitlines()[0] if text else ""
        heading_tokens = set(self._content_tokens(heading))

        bonus = 2 * len(query_tokens.intersection(heading_tokens))

        if "table" in query_tokens and "|" in text:
            bonus += 2

        return bonus

    def has_meaningful_evidence(self, query, text, score):
        """
        Decide whether a chunk contains enough signal to return.
        """
        query_tokens = set(self._content_tokens(query))
        text_tokens = set(self._content_tokens(text))
        matched_tokens = query_tokens.intersection(text_tokens)

        if not matched_tokens:
            return False

        if len(query_tokens) >= 3 and len(matched_tokens) < 2:
            return False

        return score >= 2

    def build_index(self, documents):
        """
        TODO (Phase 1):
        Build a tiny inverted index mapping lowercase words to the documents
        they appear in.

        Example structure:
        {
            "token": ["AUTH.md", "API_REFERENCE.md"],
            "database": ["DATABASE.md"]
        }

        Keep this simple: split on whitespace, lowercase tokens,
        ignore punctuation if needed.
        """
        index = {}

        for filename, text in documents:
            unique_tokens = set(self._content_tokens(text))
            for token in unique_tokens:
                if token not in index:
                    index[token] = []
                index[token].append(filename)

        return index

    # -----------------------------------------------------------
    # Scoring and Retrieval (Phase 1)
    # -----------------------------------------------------------

    def score_document(self, query, text):
        """
        TODO (Phase 1):
        Return a simple relevance score for how well the text matches the query.

        Suggested baseline:
        - Convert query into lowercase words
        - Count how many appear in the text
        - Return the count as the score
        """
        query_tokens = self._content_tokens(query)
        text_tokens = self._content_tokens(text)
        matched_tokens = set(query_tokens).intersection(text_tokens)
        text_phrases = [
            f"{text_tokens[i]} {text_tokens[i + 1]}"
            for i in range(len(text_tokens) - 1)
        ]

        score = 3 * len(matched_tokens)

        for phrase in self._query_phrases(query):
            score += 3 * text_phrases.count(phrase)

        score += self._route_bonus(query, text)
        score += self._heading_bonus(query, text)

        return score

    def retrieve(self, query, top_k=3):
        """
        TODO (Phase 1):
        Use the index and scoring function to select top_k relevant document snippets.

        Return a list of (filename, text) sorted by score descending.
        """
        candidate_filenames = set()
        for token in self._content_tokens(query):
            for filename in self.index.get(token, []):
                candidate_filenames.add(filename)

        if not candidate_filenames:
            return []

        scored_results = []
        for filename, text in self.sections:
            if filename not in candidate_filenames:
                continue

            score = self.score_document(query, text)
            if self.has_meaningful_evidence(query, text, score):
                scored_results.append((score, filename, text))

        scored_results.sort(key=lambda item: (-item[0], item[1]))

        return [(filename, text) for _, filename, text in scored_results[:top_k]]

    # -----------------------------------------------------------
    # Answering Modes
    # -----------------------------------------------------------

    def answer_retrieval_only(self, query, top_k=3):
        """
        Phase 1 retrieval only mode.
        Returns raw snippets and filenames with no LLM involved.
        """
        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        formatted = []
        for filename, text in snippets:
            formatted.append(f"[{filename}]\n{text}\n")

        return "\n---\n".join(formatted)

    def answer_rag(self, query, top_k=3):
        """
        Phase 2 RAG mode.
        Uses student retrieval to select snippets, then asks Gemini
        to generate an answer using only those snippets.
        """
        if self.llm_client is None:
            raise RuntimeError(
                "RAG mode requires an LLM client. Provide a GeminiClient instance."
            )

        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        return self.llm_client.answer_from_snippets(query, snippets)

    # -----------------------------------------------------------
    # Bonus Helper: concatenated docs for naive generation mode
    # -----------------------------------------------------------

    def full_corpus_text(self):
        """
        Returns all documents concatenated into a single string.
        This is used in Phase 0 for naive 'generation only' baselines.
        """
        return "\n\n".join(text for _, text in self.documents)
