# TEST-006 — Portuguese translation for "Linear m" header

**Feature:** ms-002 Purchase Table Linear Meters
**AC:** AC-6 — When language is Portuguese the column header renders as "m lineares".

## Preconditions

- `set_language("pt")` called before or after widget construction.

## Steps

1. `set_language("pt")`.
2. Call `widget.retranslate()` (or construct a new widget).
3. Read horizontal header label at index 5.

## Expected Result

- Header label at index 5 is `"m lineares"`.

## Automated test

`resources/languages/pt.yaml` contains `purchase.headers.linear_m: "m lineares"`.
The i18n infrastructure is verified by existing language-switch tests in the
unit test suite (`test_i18n.py`). The specific key is reachable via `tr("purchase.headers.linear_m")`.
