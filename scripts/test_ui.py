"""Smoke-test the Streamlit UI headlessly (streamlit.testing.AppTest).

Verifies the full UI flow: type a question + submit -> answer card with one
citation link and the last-updated note; click an example button -> auto-asked;
guardrail input -> blocked message instead of an answer.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from streamlit.testing.v1 import AppTest

Q1 = "What is the expense ratio of HDFC Large Cap Fund?"
Q2 = "What is the lock-in period of the ELSS fund?"
GUARD = "Should I buy HDFC Small Cap Fund?"


def _texts(app):
    return "\n".join(str(el.value) for el in app.markdown) + "\n" + "\n".join(
        str(el.value) for el in app.caption
    )


def check(name, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {name}{(' -> ' + detail) if detail and not condition else ''}")
    return condition


def _submit_button(app):
    for b in app.button:
        if str(getattr(b, "key", "") or "").startswith("FormSubmitter:"):
            return b
    return None


def main():
    results = []

    at = AppTest.from_file(str(config.PROJECT_ROOT / "app.py"), default_timeout=300).run()
    results.append(check("app renders welcome + disclaimer", "Welcome" in _texts(at)))
    results.append(check("3 example buttons present", len(at.button) >= 4, f"{len(at.button)} buttons"))

    submit = _submit_button(at)
    at.text_input[0].set_value(Q1)
    submit.click().run()
    results.append(check("submitting a typed question returns an answer card", "Assistant:" in _texts(at)))
    body = _texts(at)
    results.append(
        check("answer card carries one corpus citation link", any("groww.in" in str(m.value) for m in at.markdown))
    )
    results.append(
        check("last-updated note present", config.LAST_UPDATED_LABEL in body, body[-200:])
    )

    at2 = AppTest.from_file(str(config.PROJECT_ROOT / "app.py"), default_timeout=300).run()
    at2.button[0].click().run()
    results.append(check("clicking an example auto-asks it", "Assistant:" in _texts(at2), _texts(at2)[-200:]))

    at3 = AppTest.from_file(str(config.PROJECT_ROOT / "app.py"), default_timeout=300).run()
    at3.text_input[0].set_value(GUARD).run()
    blocked = "Assistant:" not in _texts(at3)
    results.append(
        check("advice question is refused in the UI", blocked and "advice" in _texts(at3).lower(), _texts(at3)[-200:])
    )

    print(f"\n{sum(results)}/{len(results)} UI checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
