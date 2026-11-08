"""A dependency-free adapter around an already loaded VoxCPM/VoxCPM2 model."""

from .normalizer import NorwegianNormalizer


def generate_norwegian(model, text, *, normalizer=None, strict=True, **kwargs):
    """Return (audio, normalization_report); no model loading or GPU allocation.

    Strict mode refuses flagged text before invoking the model. Callers can
    explicitly use strict=False to retain and synthesize unresolved spans.
    Prompt transcripts and voice controls are not rewritten by this adapter.
    """
    if "normalize" in kwargs:
        raise TypeError("adapter manages normalize=False to avoid English normalization")
    report = (normalizer or NorwegianNormalizer()).analyze(text)
    if strict and report.needs_review:
        details = "; ".join(f"{i.original!r}: {i.reason}" for i in report.issues)
        raise ValueError("Text requires normalization review: " + details)
    return model.generate(text=report.text, normalize=False, **kwargs), report
