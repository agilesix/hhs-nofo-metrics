"""Source-neutral grammatical classification for accepted sentence spans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Iterable

POLICY_DECISIONS: Final = frozenset({"included", "excluded", "unresolved"})
POLICY_REASON_CODES_BY_DECISION: Final = {
    "included": frozenset({"included_complete_sentence"}),
    "excluded": frozenset(
        {
            "excluded_heading_or_label",
            "excluded_citation_or_reference",
            "excluded_incomplete_clause",
            "excluded_navigation_or_page_furniture",
            "excluded_standalone_outline_marker",
        }
    ),
    "unresolved": frozenset(
        {
            "unresolved_grammatical_completeness",
            "unresolved_candidate_text_malformed",
            "unresolved_structural_role",
        }
    ),
}
POLICY_REASON_CODES: Final = frozenset().union(
    *POLICY_REASON_CODES_BY_DECISION.values()
)
POLICY_BASIS_CODES: Final = frozenset(
    {
        "authoritative_citation_region",
        "authoritative_heading_region",
        "balanced_terminal_punctuation",
        "candidate_text_unbalanced_delimiters",
        "explicit_subject_predicate",
        "fragment_form",
        "imperative_directive",
        "non_authoritative_citation_signal",
        "non_authoritative_heading_signal",
        "no_determinate_grammar_signal",
        "nominal_list_or_table_item",
        "page_furniture_region",
        "standalone_outline_marker",
        "terminal_question",
    }
)

_SPACE_RE = re.compile(r"\s+")
_TERMINAL_RE = re.compile(r"[.!?][\"'”’)]*$")
_QUESTION_RE = re.compile(r"\?[\"'”’)]*$")
_SCORING_PREFIX_RE = re.compile(r"^\(\s*\d+\s+to\s+\d+\s+points?\s*\)\s*", re.I)
_PAREN_PREFIX_RE = re.compile(r"^\([^)]{1,80}\)\s+")
_QUALIFIER_RE = re.compile(
    r"^(?:also|briefly|carefully|clearly|explicitly|generally|please|typically)\s+",
    re.I,
)
_LABEL_PREFIX_RE = re.compile(r"^[^:]{1,120}:\s+(?=[A-Za-z])")
_DEPENDENT_PREFIX_RE = re.compile(
    r"^(?:although|because|if|unless|when|where|while)\b", re.I
)
_INTRODUCTORY_MAIN_CLAUSE_RE = re.compile(
    r"^(?:after|as|before|by|for|following|in|starting|to)\b"
    r".{1,240}?,\s*(?P<main>.+)$",
    re.I,
)
_FOLLOWING_THERE_RE = re.compile(
    r"^following\b.{1,240}?\b(?P<main>there\s+(?:is|are|was|were)\b.+)$",
    re.I,
)
_OUTLINE_MARKER_RE = re.compile(
    r"^(?:\(?\d{1,3}[.)]|\(?[A-Za-z][.)]|[ivxlcdm]+[.)])$", re.I
)
_INFINITIVE_PREFIX_RE = re.compile(r"^to\s+(?!the\s+extent\b)", re.I)
_GERUND_PREFIX_RE = re.compile(r"^[A-Za-z]{3,}ing\b", re.I)
_PARTICIPLE_OR_THIRD_PERSON_PREFIX_RE = re.compile(
    r"^(?:allows|describes|enables|ensures|gained|includes|operating|participating|"
    r"requests|resulting)\b",
    re.I,
)
_THERE_PREDICATE_RE = re.compile(r"^there\s+(?:is|are|was|were|has|have)\b", re.I)
_CONTRACTED_PREDICATE_RE = re.compile(r"^(?:it|there|that|this)[’']s\s+[A-Za-z]", re.I)
_PRONOUN_LEXICAL_PREDICATE_RE = re.compile(
    r"^(?:i|you|we|they)\s+(?:(?:also|generally|typically)\s+)?[A-Za-z]+\b",
    re.I,
)
_PRONOUN_CONTRACTED_PREDICATE_RE = re.compile(
    r"^(?:i|you|we|they)[’'](?:d|ll|m|re|ve)\s+[A-Za-z]", re.I
)
_EXPLICIT_SUBJECT_RE = re.compile(
    r"^(?:"
    r"i|you|we|they|it|this|that|these|those|"
    r"applicants?|recipients?|reviewers?|awardees?|projects?|programs?|"
    r"hhs|hrsa|acf|cms|cdc|nih|samhsa|acl|ihs|grants\.gov|sam\.gov|"
    r"an?\s+[A-Za-z][A-Za-z'’-]*|the\s+[A-Za-z][A-Za-z'’-]*|"
    r"any\s+[A-Za-z][A-Za-z'’-]*|"
    r"(?:my|our|their|your)\s+[A-Za-z][A-Za-z'’-]*"
    r")\b(?P<middle>.{0,320}?)\b"
    r"(?:am|is|are|was|were|has|have|had|do|does|did|can|could|may|might|"
    r"must|shall|should|will|would)\b",
    re.I,
)
_EXPLICIT_LEXICAL_PREDICATE_RE = re.compile(
    r"^(?:"
    r"examples?\b.{0,180}\binclude|"
    r"such\s+involvement\b.{0,120}\bimplicates|"
    r"these\b.{0,120}\breplace|"
    r"[A-Z][A-Za-z0-9 /&()'’.,-]{2,200}\b"
    r"(?:applies|creates|expects|gives|includes|implicates|occurs|provides|"
    r"remains|replaces|requires|shows?|tells)"
    r")\b",
    re.I,
)
_GENERIC_AUXILIARY_PREDICATE_RE = re.compile(
    r"^(?P<middle>[A-Z][^.!?]{0,320}?)\b"
    r"(?i:am|is|are|was|were|has|have|had|do|does|did|can|could|may|might|"
    r"must|shall|should|will|would)\b"
)
_DIRECTIVE_VERBS: Final = frozenset(
    {
        "account",
        "administer",
        "agree",
        "align",
        "answer",
        "apply",
        "assess",
        "attach",
        "begin",
        "budget",
        "check",
        "choose",
        "collect",
        "complete",
        "comply",
        "conduct",
        "contact",
        "convene",
        "coordinate",
        "cover",
        "create",
        "decide",
        "define",
        "deliver",
        "demonstrate",
        "describe",
        "design",
        "develop",
        "double-space",
        "educate",
        "ensure",
        "enter",
        "explain",
        "finalize",
        "follow",
        "fund",
        "hold",
        "identify",
        "implement",
        "include",
        "indicate",
        "invest",
        "label",
        "leave",
        "list",
        "maintain",
        "make",
        "meet",
        "monitor",
        "operationalize",
        "organize",
        "participate",
        "print",
        "promote",
        "provide",
        "reach",
        "recruit",
        "replicate",
        "report",
        "review",
        "save",
        "see",
        "select",
        "state",
        "stabilize",
        "strengthen",
        "submit",
        "support",
        "update",
        "upload",
        "use",
        "work",
    }
)


@dataclass(frozen=True, slots=True)
class SentencePolicyClassification:
    decision: str
    reason_code: str
    basis_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.decision not in POLICY_DECISIONS:
            raise ValueError(f"unsupported policy decision: {self.decision}")
        if self.reason_code not in POLICY_REASON_CODES_BY_DECISION[self.decision]:
            raise ValueError("reason_code is incompatible with policy decision")
        if self.basis_codes != tuple(sorted(set(self.basis_codes))):
            raise ValueError("basis_codes must be unique and canonical")
        if not self.basis_codes or set(self.basis_codes) - POLICY_BASIS_CODES:
            raise ValueError("basis_codes contain an unsupported value")


def _classification(
    decision: str, reason_code: str, *basis_codes: str
) -> SentencePolicyClassification:
    return SentencePolicyClassification(
        decision=decision,
        reason_code=reason_code,
        basis_codes=tuple(sorted(set(basis_codes))),
    )


def _balanced_delimiters(text: str) -> bool:
    pairs = (("(", ")"), ("[", "]"), ("{", "}"))
    return all(text.count(left) == text.count(right) for left, right in pairs)


def _directive_stem(text: str) -> str:
    value = _SCORING_PREFIX_RE.sub("", text, count=1)
    value = _PAREN_PREFIX_RE.sub("", value, count=1)
    label = _LABEL_PREFIX_RE.match(value)
    if label is not None:
        value = value[label.end() :]
    while True:
        updated = _QUALIFIER_RE.sub("", value, count=1)
        if updated == value:
            break
        value = updated
    return value.lstrip()


def _starts_with_directive(text: str) -> bool:
    stem = _directive_stem(text)
    match = re.match(r"([A-Za-z]+(?:-[A-Za-z]+)?)\b", stem)
    return match is not None and match.group(1).casefold() in _DIRECTIVE_VERBS


def _has_explicit_subject_predicate(text: str) -> bool:
    if (
        _THERE_PREDICATE_RE.match(text)
        or _CONTRACTED_PREDICATE_RE.match(text)
        or _PRONOUN_LEXICAL_PREDICATE_RE.match(text)
        or _PRONOUN_CONTRACTED_PREDICATE_RE.match(text)
        or _EXPLICIT_LEXICAL_PREDICATE_RE.match(text)
    ):
        return True
    match = _EXPLICIT_SUBJECT_RE.match(text)
    if match is None:
        match = _GENERIC_AUXILIARY_PREDICATE_RE.match(text)
    if match is None:
        return False
    middle = match.group("middle").casefold()
    # A pronoun inside a determiner-led subject often indicates an embedded
    # relative clause rather than a matrix predicate (for example, "The type
    # of evaluations your organization will use ..."). Abstain in that case.
    return re.search(r"\b(?:my|our|their|your)\b", middle) is None


def _policy_clause(text: str) -> str:
    value = text
    label = _LABEL_PREFIX_RE.match(value)
    if label is not None:
        value = value[label.end() :]
    introductory = _INTRODUCTORY_MAIN_CLAUSE_RE.match(value)
    if introductory is not None:
        comma_suffixes = (
            value[match.end() :].lstrip() for match in re.finditer(r",\s*", value[:320])
        )
        value = next(
            (
                candidate
                for candidate in comma_suffixes
                if _has_explicit_subject_predicate(candidate)
            ),
            introductory.group("main"),
        )
    else:
        following = _FOLLOWING_THERE_RE.match(value)
        if following is not None:
            value = following.group("main")
    if value.casefold().startswith("as noted"):
        candidates = tuple(
            value[match.start() :]
            for match in re.finditer(
                r"\b(?:applicants?|recipients?|the|these|those|we|you)\b",
                value,
                re.I,
            )
        )
        value = next(
            (
                candidate
                for candidate in reversed(candidates)
                if _has_explicit_subject_predicate(candidate)
            ),
            value,
        )
    return value.lstrip()


def classify_sentence_candidate(
    text: str,
    *,
    structural_kinds: Iterable[str] = (),
    authoritative_structural_kinds: Iterable[str] = (),
) -> SentencePolicyClassification:
    """Classify one accepted span without changing its boundary or source text."""

    value = _SPACE_RE.sub(" ", text).strip()
    kinds = frozenset(structural_kinds)
    authoritative = frozenset(authoritative_structural_kinds)
    if "heading" in authoritative:
        return _classification(
            "excluded", "excluded_heading_or_label", "authoritative_heading_region"
        )
    if "citation" in authoritative:
        return _classification(
            "excluded",
            "excluded_citation_or_reference",
            "authoritative_citation_region",
        )
    if kinds & {"header", "footer"}:
        return _classification(
            "excluded",
            "excluded_navigation_or_page_furniture",
            "page_furniture_region",
        )
    if "heading" in kinds:
        return _classification(
            "unresolved",
            "unresolved_structural_role",
            "non_authoritative_heading_signal",
        )
    if "citation" in kinds:
        return _classification(
            "unresolved",
            "unresolved_structural_role",
            "non_authoritative_citation_signal",
        )
    if not value or not _balanced_delimiters(value):
        return _classification(
            "unresolved",
            "unresolved_candidate_text_malformed",
            "candidate_text_unbalanced_delimiters",
        )
    terminal = _TERMINAL_RE.search(value) is not None
    if not terminal:
        return _classification(
            "excluded", "excluded_incomplete_clause", "fragment_form"
        )
    if _OUTLINE_MARKER_RE.fullmatch(value):
        return _classification(
            "excluded",
            "excluded_standalone_outline_marker",
            "standalone_outline_marker",
        )
    if _QUESTION_RE.search(value):
        words = re.findall(r"[A-Za-z]+", value)
        pronouns = {"i", "it", "they", "we", "you"}
        if len(words) <= 3 and not pronouns & {word.casefold() for word in words}:
            return _classification(
                "unresolved",
                "unresolved_structural_role",
                "non_authoritative_heading_signal",
            )
        return _classification(
            "included",
            "included_complete_sentence",
            "balanced_terminal_punctuation",
            "terminal_question",
        )
    if _starts_with_directive(value):
        return _classification(
            "included",
            "included_complete_sentence",
            "balanced_terminal_punctuation",
            "imperative_directive",
        )
    if _DEPENDENT_PREFIX_RE.match(value):
        comma = value.find(",")
        if comma > 0 and (
            _starts_with_directive(value[comma + 1 :])
            or _has_explicit_subject_predicate(value[comma + 1 :].lstrip())
        ):
            return _classification(
                "included",
                "included_complete_sentence",
                "balanced_terminal_punctuation",
                "explicit_subject_predicate",
            )
        return _classification(
            "unresolved",
            "unresolved_grammatical_completeness",
            "no_determinate_grammar_signal",
        )
    policy_clause = _policy_clause(value)
    if policy_clause != value and _has_explicit_subject_predicate(policy_clause):
        return _classification(
            "included",
            "included_complete_sentence",
            "balanced_terminal_punctuation",
            "explicit_subject_predicate",
        )
    if (
        _INFINITIVE_PREFIX_RE.match(value)
        or _GERUND_PREFIX_RE.match(value)
        or _PARTICIPLE_OR_THIRD_PERSON_PREFIX_RE.match(value)
    ):
        return _classification(
            "excluded", "excluded_incomplete_clause", "fragment_form"
        )
    if _has_explicit_subject_predicate(value):
        return _classification(
            "included",
            "included_complete_sentence",
            "balanced_terminal_punctuation",
            "explicit_subject_predicate",
        )
    if kinds & {"list_item", "table_cell", "table_row"}:
        return _classification(
            "excluded",
            "excluded_incomplete_clause",
            "nominal_list_or_table_item",
        )
    return _classification(
        "unresolved",
        "unresolved_grammatical_completeness",
        "no_determinate_grammar_signal",
    )
