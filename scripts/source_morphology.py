"""Decode source MorphGNT CCAT-style morphological codes, without guessing.

The documented parsing code comprises 8 *independent* columns:
person, tense, voice, mood, case, number, gender, degree.
An ASCII '-' means 'not annotated / not applicable': it is NOT a value.
The actual MorphGNT 2024 source also uses V (vocative) in its case column,
in addition to the four cases listed in its README.

These are derived annotations. The raw source_pos and source_parsing features
remain authoritative and unchanged; future source versions may require a
separate decoder version, not silently changing the meaning of existing tags.
"""
from __future__ import annotations

MORPH_FEATURES = (
    "morph_pos",
    "morph_person",
    "morph_tense",
    "morph_voice",
    "morph_mood",
    "morph_case",
    "morph_number",
    "morph_gender",
    "morph_degree",
)

POS = {
    "A-": "adjective",
    "C-": "conjunction",
    "D-": "adverb",
    "I-": "interjection",
    "N-": "noun",
    "P-": "preposition",
    "RA": "definite_article",
    "RD": "demonstrative_pronoun",
    "RI": "interrogative_indefinite_pronoun",
    "RP": "personal_pronoun",
    "RR": "relative_pronoun",
    "V-": "verb",
    "X-": "particle",
}
COLUMNS = (
    {"1": "first", "2": "second", "3": "third"},
    {"P": "present", "I": "imperfect", "F": "future",
     "A": "aorist", "X": "perfect", "Y": "pluperfect"},
    {"A": "active", "M": "middle", "P": "passive"},
    {"I": "indicative", "D": "imperative", "S": "subjunctive",
     "O": "optative", "N": "infinitive", "P": "participle"},
    {"N": "nominative", "G": "genitive", "D": "dative",
     "A": "accusative", "V": "vocative"},
    {"S": "singular", "P": "plural"},
    {"M": "masculine", "F": "feminine", "N": "neuter"},
    {"C": "comparative", "S": "superlative"},
)
assert len(COLUMNS) == len(MORPH_FEATURES) - 1


def decode_source_morphology(pos: str, parsing: str) -> dict[str, str]:
    """Return only positive, source-supported morphological information.

    Any unexpected input fails instead of forging an approximate annotation.
    The input is a POS code (2 characters) and parsing code (8 characters).
    """
    if pos not in POS:
        raise ValueError(f"unknown MorphGNT POS code {pos!r}")
    if len(parsing) != 8:
        raise ValueError("MorphGNT parsing code must have eight positions")
    result = {"morph_pos": POS[pos]}
    for index, (feature, table) in enumerate(zip(MORPH_FEATURES[1:], COLUMNS)):
        char = parsing[index]
        if char == "-":
            continue
        if char not in table:
            raise ValueError(f"unknown MorphGNT code at position {index+1}: {char!r}")
        result[feature] = table[char]
    return result
