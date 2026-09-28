"""Versioned PC-v1 aggregation; uncertain/missing judgments stay unscored."""

DIMENSIONS = (
    ('fidelity', 'premise_fidelity'),
    ('fidelity', 'target_fidelity'),
    ('validity', 'evidence_integration'),
    ('validity', 'mathematical_validity'),
)

RELAXED_RATING_VERSION = 'RECONSTRUCT-RATING-v2'
RELAXED_RATING_BOUNDARIES = (20, 40, 50, 70)
BALANCED_RATING_VERSION = 'RECONSTRUCT-RATING-v3'
BALANCED_RATING_BOUNDARIES = (18.75, 37.5, 56.25, 75)
BALANCED_V4_VERSION = 'RECONSTRUCT-RATING-v4'
BALANCED_V4_BOUNDARIES = (18.75, 43.75, 56.25, 75)


def relaxed_rating(score):
    """Prospective display policy; never changes the underlying quality score."""
    if score is None:
        return None
    if type(score) not in (int, float) or not 0 <= score <= 100:
        raise ValueError('Expected a finite score from 0 to 100, or None')
    return 1 + sum(score >= boundary for boundary in RELAXED_RATING_BOUNDARIES)


def balanced_rating(score):
    """Frozen development-calibrated bands; no cohort ranks or forced counts."""
    if score is None:
        return None
    if type(score) not in (int, float) or not 0 <= score <= 100:
        raise ValueError('Expected a finite score from 0 to 100, or None')
    return 1 + sum(score >= boundary for boundary in BALANCED_RATING_BOUNDARIES)


def balanced_rating_v4(score):
    """Raise only the v3 boundary between ratings 2 and 3 by one raw point."""
    if score is None:
        return None
    if type(score) not in (int, float) or not 0 <= score <= 100:
        raise ValueError('Expected a finite score from 0 to 100, or None')
    return 1 + sum(score >= boundary for boundary in BALANCED_V4_BOUNDARIES)


def aggregate(fidelity=None, validity=None):
    judgments = {'fidelity': fidelity or {}, 'validity': validity or {}}
    dimensions = {}
    for role, name in DIMENSIONS:
        value = judgments[role].get(name, {}).get('score')
        if value is not None and (type(value) is not int or not 0 <= value <= 4):
            raise ValueError('Invalid dimension score: ' + name)
        dimensions[name] = value
    known = [v for v in dimensions.values() if v is not None]
    lower = 6.25 * sum(known)
    upper = lower + 25 * (4 - len(known))
    shortcut = judgments['validity'].get('shortcut', {}).get('present')
    if shortcut is not None and type(shortcut) is not bool:
        raise ValueError('Shortcut status must be Boolean or unresolved')
    raw = lower if len(known) == 4 else None
    resolved = (len(known) == 4 and shortcut is False
                and all(judgments[role].get('status') == 'scored' for role in judgments))
    if shortcut is True:
        score, bounds, reason = 0.0, [0.0, 0.0], 'known_shortcut'
    elif resolved:
        score, bounds, reason = raw, [raw, raw], None
    else:
        score, bounds, reason = None, [0.0 if shortcut is None else lower, upper], 'unresolved_judgment'
    return {
        'version': 'RECONSTRUCT-PC-v1', 'dimensions': dimensions,
        'raw_dimension_total': raw, 'shortcut': shortcut,
        'score_100': score, 'score_bounds': bounds, 'reason': reason,
        'rating_1_to_5': min(5, int(score // 20) + 1) if score is not None else None,
    }
