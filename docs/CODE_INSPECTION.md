# Deep Code Inspection – Findings (appended pass)

## 1. Potential errors and security risks (suspicious areas)

| # | Location | Issue | Why suspicious |
|---|----------|--------|----------------|
| 1 | `spec.from_toml` | **TOMLDecodeError not caught** | `tomllib.loads(raw)` raises `tomllib.TOMLDecodeError` on invalid TOML. The exception propagates with a generic traceback; users get a clearer message if we catch it and raise `ValueError` with the spec path. |
| 2 | `driver.create_driver` | **FileExistsError re-raised without chaining** | `except FileExistsError:` then `raise ValueError(...)` without `from exc`. Exception chaining (PEP 3134) preserves cause and improves debugging; lint (B904) flags this. |
| 3 | `scraper.search_subpages` | **SkipEntryError raised without chaining** | Inside `except StaleElementReferenceException:` we `raise SkipEntryError(...)` without capturing the exception or using `from exc`. Same B904 concern. |
| 4 | `driver` | **Unused import and f-strings** | `import logging` is unused (F401). In `_validate_path_safe`, two f-strings have no placeholders (F541); use plain strings. |
| 5 | `config.from_mapping` | **Timeout ints unbounded** | `_int()` returns whatever is in the mapping; negative or very large timeouts (e.g. `page_load_timeout_s`) could be passed to Selenium. Low probability (TOML/API controlled). |

## 2. Prioritisation by probability and impact

- **Medium probability, medium impact:** (1) Invalid TOML is plausible; (2)(3) exception chaining is best practice and helps debugging.
- **Low probability:** (4) lint/cleanup; (5) only if spec or caller supplies bad values.

## 3. Why each problem could occur

- **TOMLDecodeError:** Code assumes valid TOML after size/encoding checks; malformed syntax still raises.
- **Exception chaining:** Original code replaced the exception with a user-facing one but did not use `raise ... from exc`.
- **Unused/f-strings:** Leftover or style; no runtime bug.
- **Timeout bounds:** No validation on ints from mapping; defensive clamping improves robustness.

## 4. Priority classification

| Priority | Description | Items |
|----------|-------------|--------|
| **P2** | Important robustness / best practice | (1) Wrap TOMLDecodeError; (2)(3) exception chaining; (4) lint fixes |
| **P3** | Nice-to-have | (5) Clamp timeout ints to a reasonable range in config |

## 5. Fixes applied (iterative)

- **P2:** In `spec.from_toml`, wrap `tomllib.loads(raw)` in try/except; on `tomllib.TOMLDecodeError`, raise `ValueError` with path and message.
- **P2:** In `driver.create_driver`, use `except FileExistsError as exc:` and `raise ValueError(...) from exc`.
- **P2:** In `scraper.search_subpages`, use `except StaleElementReferenceException as exc:` and `raise SkipEntryError(...) from exc`.
- **P2:** In `driver`, remove unused `logging` import; in `_validate_path_safe`, use normal strings instead of f-strings without placeholders.
- **P3:** In `config.from_mapping`, added `_clamp_int` and `_int(..., min_val, max_val)`; timeouts clamped to 1–3600, retries to 1–100, restart_threshold to 0–1000.

---

## 6. Fourth pass – re-inspection (appended)

Full re-examination of the codebase after the above fixes:

- **spec:** TOMLDecodeError is caught and re-raised as ValueError with path. render_template KeyError is chained with `from exc`. No issues.
- **driver:** FileExistsError chained with `from exc`; no unused imports; no f-strings without placeholders. Path and user-agent validation in place. No issues.
- **scraper:** StaleElementReferenceException and other exception paths use `from exc` where a new exception is raised. No issues.
- **config:** Timeout and retry ints are clamped via _int(..., min_val, max_val). restart_threshold allows 0 (disable restart). No issues.
- **cli:** CSV formula escaping, header-only output, apply_cli_args and clamp_navigation in use. No issues.
- **selenium_ops, url_filter, io, extract_*, relevance, logging_utils:** No new errors or security risks identified.

**Result:** No new P0–P3 issues found. All previously applied fixes are present and verified. No further code changes required for this pass.

---

## 7. Fifth pass – re-inspection (appended)

Full re-examination of the codebase with focus on config construction and exception paths.

### 7.1 New findings

| # | Location | Issue | Why suspicious |
|---|----------|--------|----------------|
| 6 | `cli.main` | **google_domain validation bypass** | When a spec file is used, `config = replace(config_from_spec, google_domain=...)` builds a new `ScraperConfig` via `dataclasses.replace()`. `replace()` does not run `__post_init__`, so `_validate_google_domain()` is never called for the final domain. A user can pass `--google-domain evil.com` (or a spec with invalid domain) and the process would use it, bypassing the allowlist. |
| 7 | `scraper.link_priority` | **Bare `except Exception` with no log** | `except Exception: return 1` swallows any exception (e.g. from `element.text` or `get_attribute`) without logging. Rest of codebase uses `logging.debug` for non-fatal failures; this makes debugging harder. |

### 7.2 Prioritisation and classification

- **P1 (breaking / security):** (6) – Validation bypass allows an invalid or malicious Google domain to be used.
- **P3 (nice-to-have):** (7) – Consistency and debuggability; no functional bug.

### 7.3 Why each problem could occur

- **Validation bypass:** `dataclasses.replace()` creates a new instance by copying fields and does not invoke `__init__` or `__post_init__`. The original design assumed all configs were created via `ScraperConfig(...)` or `from_mapping()`, both of which run `__post_init__`.
- **Silent exception:** Defensive coding to avoid breaking the sort key, but without a log it hides transient Selenium/DOM issues.

### 7.4 Fixes applied

- **P1:** In `config.py`, add `ScraperConfig.validate(self)` that calls `_validate_google_domain(self.google_domain)`. In `cli.main`, after building the final `spec, config` (including after `replace(config_from_spec, ...)`), call `config.validate()` so the domain is always validated regardless of construction path.
- **P3:** In `scraper.link_priority`, replace `except Exception: return 1` with `except Exception as exc: logging.debug("link_priority failed: %s", exc); return 1`.

**Note:** On CPython 3.13, `dataclasses.replace()` does invoke the class constructor and thus `__post_init__`, so the bypass may not occur on all versions. The explicit `config.validate()` after building the final config remains defensive and ensures the domain is always validated regardless of implementation.

**Result:** P1 and P3 fixes applied. Tests added for `config.validate()` and replace-with-invalid-domain behavior. All 35 tests pass.

---

## 8. Sixth pass – deep inspection (appended)

**Date:** 2026-03-02

### 1a. Potential errors

| # | Location | Issue | Why suspicious |
|---|----------|-------|----------------|
| 8 | `Makefile` test target | `pytest -q` depended on environment import path setup | In some environments, package import failed during collection (`ModuleNotFoundError`) even though source code was present. |
| 10 | `pyproject.toml` pytest config | `pytest-asyncio` deprecation warning (`asyncio_default_fixture_loop_scope` unset) | Warning noise can hide real failures and will change default behavior in future plugin versions. |

### 1b. Security risks

| # | Location | Issue | Why suspicious |
|---|----------|-------|----------------|
| 9 | `driver.py`, `human.py` randomization calls | `random.choice/random.uniform/random.random` flagged by Bandit B311 | Standard PRNG is predictable; security scanners classify this as weak randomness when used in behavior-affecting paths. |

### 2. Prioritisation by probability

- **P1:** Makefile test invocation path sensitivity (high probability in CI/dev env variance).
- **P3:** predictable PRNG usage in automation jitter/user-agent selection (low direct exploitability here, but recurrent security lint finding).
- **P3:** unset pytest-asyncio fixture loop scope warning (high probability noise in every test run).

### 3. Why each problem could occur

- `pytest -q` executes binary entrypoint directly; depending on shell/venv/path resolution, package root may not be on import path during test collection.
- `random` module is Mersenne Twister; Bandit flags it whenever cryptographically stronger randomness is preferred.
- pytest-asyncio warns when loop scope default is implicit; future plugin defaults may shift behavior unexpectedly.

### 4. Fixes applied

- **P1:** `Makefile` test target changed to `python -m pytest -q` for stable import/module resolution.
- **P3:** switched to `random.SystemRandom()` for:
  - user-agent/window-size selection in `driver.py`
  - typing delay and pause jitter in `human.py`
- **P3:** set `asyncio_default_fixture_loop_scope = "function"` in `pyproject.toml` under `[tool.pytest.ini_options]`.

### 5. Verification

- `make ci security dependency-audit`: pass.
- `bandit -r humanized_selenium_scraper -x tests --severity-level low`: no issues.
- `pytest -q`: 35 passed.

### 6. Classification (sixth pass)

- **P0:** none
- **P1:** resolved
- **P2:** none
- **P3:** resolved

---

## 9. Seventh pass – deep inspection (appended)

**Date:** 2026-03-02

### 1a. Potential errors

| # | Location | Issue | Why suspicious |
|---|----------|-------|----------------|
| 11 | `driver.py` path validator | `_validate_path_safe` used regex that rejected backslash (`\\`) | Windows profile paths typically include backslashes (e.g. `C:\Users\...`). This can wrongly reject valid paths and break driver startup on Windows. |

### 1b. Security risks

- No new high/critical security vulnerabilities identified in this pass.

### 2. Prioritisation by probability

- **P1 (high probability on Windows):** valid Windows profile paths can be rejected by path sanitization.

### 3. Why it could occur

- A single regex (`_DANGEROUS_CHARS`) was shared between CLI-argument validation and path validation.
- Blocking backslash is useful for shell-like arg hardening but invalid for Windows path semantics.

### 4. Fixes applied

- Split validators:
  - `_DANGEROUS_ARG_CHARS` keeps backslash blocked for Chrome arg strings.
  - `_DANGEROUS_PATH_CHARS` allows backslash for filesystem paths.
- Added regression test to verify Windows-style path acceptance in `_validate_path_safe`.

### 5. Verification

- `make ci security dependency-audit`: pass (`36 passed`, bandit clean, pip-audit clean).
- `bandit -r humanized_selenium_scraper -x tests --severity-level low`: no issues.

### 6. Classification (seventh pass)

- **P0:** none
- **P1:** resolved
- **P2:** none
- **P3:** none new

---

## 10. Eighth pass – deep inspection (appended)

**Date:** 2026-03-02

### 1a. Potential errors

- Re-checked driver/path sanitization and Selenium startup flow.
- No new runtime defects identified beyond previously fixed items.

### 1b. Security risks

- No new high/critical security vulnerabilities identified in this pass.

### 2. Suspicious areas reviewed

| Area | Why suspicious | Result |
|------|----------------|--------|
| Chrome profile path sanitization | Platform-specific path chars (Windows `\`) can conflict with generic security filters | Prior fix verified: Windows-style paths now accepted while dangerous chars remain blocked. |
| Driver arg sanitization | Shared validators can accidentally relax arg hardening | Arg validator remains strict (`_DANGEROUS_ARG_CHARS`), separate from path validator. |

### 3. Verification

- `make ci security dependency-audit`: pass (`36 passed`, bandit clean, pip-audit clean).
- `bandit -r humanized_selenium_scraper -x tests --severity-level low`: no issues.

### 4. Classification (eighth pass)

- **P0:** none
- **P1:** none new
- **P2:** none
- **P3:** none new

---

## 11. Ninth pass – release-prep verification (appended)

**Date:** 2026-03-02

### 1a. Potential errors

- Re-ran full static/type/runtime checks after README and CI standardization.
- No new runtime defects identified.

### 1b. Security risks

- Re-ran Bandit and dependency audit from canonical local gate.
- No new security issues identified.

### 2. Suspicious areas reviewed

| Area | Why suspicious | Result |
|------|----------------|--------|
| README lifecycle documentation | Diagram updates can diverge from actual retry/skip flow | Updated diagrams now show explicit retry/skip failure branches consistent with `Session.search` and row loop behavior. |
| CI parity with release gate | Previous workflow covered only lint/tests | Workflow now runs `make ci security dependency-audit` to match the canonical local gate. |

### 3. Verification

- `make ci security dependency-audit`: pass (`36 passed`, mypy clean, bandit clean, pip-audit clean).
- `bandit -r humanized_selenium_scraper -x tests --severity-level low`: no issues.

### 4. Classification (ninth pass)

- **P0:** none
- **P1:** none
- **P2:** none
- **P3:** none new

### 5. Closure

- Final iteration result: **no new P3 findings**.
