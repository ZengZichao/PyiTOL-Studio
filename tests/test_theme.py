"""Theme rendering: selector hygiene and token completeness.

The two bugs these cover were both invisible in code review and obvious on
screen, so they are worth locking down:

* a comma-separated selector list where the pseudo-state lands on the last
  branch only — ``A, B, C:focus`` styles A and B with the plain rule, so every
  input in the app wore the 2px brand focus ring permanently;
* a descendant selected through an ancestor's pseudo-state, which Qt does not
  support — the rule then matches *every* descendant, so all wizard cards drew
  their icon on solid brand green whether selected or not.
"""

from __future__ import annotations

import re

from pyitolstudio.theme import _INPUT_WIDGETS, build_stylesheet, palette


def _rules(qss: str):
    """Yield (selector, body) for every rule, skipping comments."""
    stripped = re.sub(r"/\*.*?\*/", "", qss, flags=re.S)
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", stripped):
        selector = match.group(1).strip()
        if selector:
            yield selector, match.group(2)


def test_input_widgets_are_stamped_one_by_one():
    qss = build_stylesheet(True)
    for widget in _INPUT_WIDGETS:
        for pseudo in (":focus", ":hover", ":disabled"):
            assert f"{widget}{pseudo}" in qss, f"{widget}{pseudo} missing from QSS"


def test_no_pseudo_state_is_appended_to_a_selector_list():
    """Every branch of a comma list must carry its own pseudo-state.

    ``QToolButton:pressed, QToolButton:checked`` is fine — both branches are
    stated.  ``A, B, C:focus`` is the bug: A and B silently take the plain
    rule, so they render as if permanently focused.
    """
    for dark in (True, False):
        for selector, _body in _rules(build_stylesheet(dark)):
            branches = [b.strip() for b in selector.split(",")]
            if len(branches) < 2:
                continue
            stated = [b for b in branches if re.search(r":[a-z-]+$", b)]
            if stated and len(stated) != len(branches):
                raise AssertionError(f"combined pseudo-state selector: {selector!r}")


def test_no_descendant_selected_by_ancestor_pseudo_state():
    for dark in (True, False):
        for selector, _body in _rules(build_stylesheet(dark)):
            assert not re.search(r":[a-z]+\s+Q[A-Za-z]", selector), (
                f"unreachable descendant selector: {selector!r}"
            )


def test_both_modes_expose_the_same_tokens():
    assert set(palette(True)) == set(palette(False))


def test_stylesheet_differs_between_modes():
    assert build_stylesheet(True) != build_stylesheet(False)
