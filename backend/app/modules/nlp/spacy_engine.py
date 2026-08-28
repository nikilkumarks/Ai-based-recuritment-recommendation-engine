"""Process-wide spaCy blank English pipeline + PhraseMatcher.

No transformer weights are loaded. PhraseMatcher is a gazetteer, not NER training.
"""

from __future__ import annotations

from functools import lru_cache

import spacy
from spacy.language import Language
from spacy.matcher import PhraseMatcher

from app.modules.nlp.lexicon import SKILL_LEXICON


@lru_cache(maxsize=1)
def get_nlp() -> tuple[Language, PhraseMatcher]:
    nlp = spacy.blank("en")
    if "sentencizer" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(term) for term in SKILL_LEXICON]
    matcher.add("SKILL", patterns)
    return nlp, matcher


def warm_nlp() -> None:
    get_nlp()
