# Model changelog

## Combined 1.0.0 / Router 1.0.0 (23 Aug 2026)

- Dual-engine router only; IT and OT math not hybridised.
- Output Bridge last-run metrics ENGINE_WRITTEN (B/C and H–J); sheet `00 Engine Results` including Control What-If table.
- Dashboard **Basis** control (default Prudent). Metric labels are not prefixed with the basis name.
- Control What-If production-N goldens for FS/PG/EA/MF.
- Outside-In schema 1.0.0: facility/organisation/route exposure vs `ttp_prevent_barrier` overlay; rationale sheet required.

## IT engine 1.1.1

Unchanged methodology. Return dict expanded with best/prudent tails and frequencies for the Bridge.

## OT engine 1.7.1

**Patch** over 1.7: optional Prevent-barrier multipliers from `00 OI Engine Overlay`. Empty overlay ⇒ same stochastic model as 1.7. Production goldens (no overlay) reproduced 1.7 AAL.

Packs: PG-v1.6, EA-v1.0, MF-v1.0 (working calibration caveats unchanged).

## Anti-double-counting

One approved finding may change **either** opportunity/feasibility **or** a stage/TTP prevent barrier, not both, unless the rationale explicitly records `exposure vs exploitability`. Attempt frequency is not increased by CVE/KEV/EPSS evidence alone.
