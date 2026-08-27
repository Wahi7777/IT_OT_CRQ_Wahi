# Security review

Date: 23 August 2026  
Scope: `src/crq`, `src/it_ot_crq`, `src/it_crq`, `src/ot_crq`, tests, combined workbook inputs.

## Static analysis

| Tool | Result |
| --- | --- |
| ruff `src` `tests` | PASS |
| bandit `-ll` `-r src` | PASS (0 medium/high). Geography `ValueError` annotated `# nosec B608` — not SQL. |
| pip-audit `-r requirements.txt` | PASS — no known vulnerabilities |
| Secret patterns (AKIA / PEM / Stripe live) | PASS — `tests/security/test_secrets_scan.py` |

## Runtime protections (retested)

- CSV/Excel formula injection prefix (`sanitize_untrusted_text`)
- Path traversal (`..`) rejected
- Canonical `model/Guided_IT_OT_CRQ_Model_v1_0.xlsx` and v0.3 names cannot be overwrite targets
- Unknown sector fail-closed
- Unknown TTP / blank geography fail-closed (OT)
- Untrusted OI CSV row limits and sanitisation
- Attribution below High/Medium does not change parameters
- Same finding cannot change exposure and TTP barrier unless `double_counting_assessment` contains `exposure vs exploitability`
- No AAL multiplier / no direct P(success) overwrite

## Residual

Bandit low findings on the legacy engines were not treated as release blockers. Do not suppress new High findings to greenwash a release.
