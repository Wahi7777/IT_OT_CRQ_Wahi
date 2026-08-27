"""Driver dependency treatment within a successful IT loss event.

Working approach (not a Balbix-specified copula)
================================================

Balbix Breach Impact Model equations are deterministic driver formulas. They do
not define a Monte Carlo dependence structure among drivers. This package uses
the following documented default:

1. Control channels remain Duration / Exposure / Direct (path-factor channels).
2. For each successful event, draw one shared standard normal per channel:
   Z_c = √ρ · Z_common + √(1−ρ) · Z_c_idiosyncratic, with ρ = LOSS_BLOCK_RHO.
3. Every applicable driver in channel c uses the **same** Z_c:
   L_d = exp(μ_d + σ_d · Z_c).
4. Event loss = Σ_d L_d.

Implications
------------
* Drivers in the same channel are **comonotonic in Gaussian latent space**
  (perfect positive dependence of the underlying normals). They do not
  diversify merely because they are reported separately.
* Channels are **equicorrelated** at pack ρ (FS pack: 0.5), matching the
  pre-unified three-block Monte Carlo dependence across Duration/Exposure/Direct.
* This is **not** independent sampling, not a full correlation matrix, and not
  a structural factor model on duration / records / payment flow (those inputs
  remain scenario P50/P99 point values that set μ_d, σ_d before the draw).

Limitations
-----------
* Shared operational factors (same affected-record count, same outage days) are
  embedded in calibrated P50/P99 parameters, then applied through channel
  comonotonicity — they are not re-sampled as separate random variables.
* Pairwise dependence between channels is a single ρ, not empirically calibrated
  per sector.
* Sum of comonotonic driver lognormals ≠ lognormal fitted to (Σ P50, Σ P99);
  scenario severity therefore differs from the former block-level fit by design.

Sensitivity
-----------
ρ → 1: channels become comonotonic with each other (stronger tails).
ρ → 0: channels independent (more diversification across Duration/Exposure/Direct).
Within-channel dependence remains comonotonic regardless of ρ.
"""

DEPENDENCY_MODEL = {
    "id": "channel_comonotonic_gaussian",
    "within_channel": "comonotonic",
    "across_channel": "equicorrelated_gaussian",
    "rho_parameter": "LOSS_BLOCK_RHO",
}
