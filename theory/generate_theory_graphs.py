"""Generate all illustrative figures used in AB_TESTING_THEORY.md.

Each function below produces a single PNG file that is embedded in the
theory document. The goal is to turn the abstract formulas and
definitions (MDE, power, α, SRM, Type I/II errors) into concrete,
visual examples with fixed numerical assumptions that match the text.

Run this module as a script from the repository root:

    python theory/generate_theory_graphs.py

"""

import pathlib

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm


def generate_routing_bug_plot(output_path: pathlib.Path) -> None:
    """Simulate a routing bug / SRM for a 70/30 traffic split.

    This plot corresponds to the SRM example in the "Traffic and Data
    Quality Monitoring" section. It constructs a *toy* experiment where:

    * The intended allocation to variant A is 70% (target_ratio = 0.7).
    * For the first ~20 days, the realized cumulative ratio fluctuates
        randomly around 0.7.
    * Starting at day 21, a synthetic "bug" gradually pushes more
        traffic into A, so the cumulative ratio drifts upward.

    The gray band is an approximate ±3σ confidence band around 0.7
    under a healthy system with steadily increasing cumulative user
    counts. When the blue line exits this band and keeps drifting, it
    visually indicates a sample-ratio mismatch that would be picked up
    by SRM checks.
    """

    rng = np.random.default_rng(42)

    days = np.arange(1, 41)  # 40 days

    target_ratio = 0.7

    # Start around the target split (70/30) with small random noise
    base_ratio = target_ratio + rng.normal(0.0, 0.01, size=days.size)

    # Introduce a gradual drift starting at day 21
    bug_start_day = 21
    drift_length = days.size - (bug_start_day - 1)
    drift = np.linspace(0.0, 0.12, drift_length)  # up to ~0.82

    ratio = base_ratio.copy()
    ratio[bug_start_day - 1 :] += drift

    fig, ax = plt.subplots(figsize=(8, 4.5))

    ax.plot(days, ratio, marker="o", linestyle="-", color="#1f77b4", label="Observed allocation ratio")
    ax.axhline(target_ratio, color="gray", linestyle="--", linewidth=1.2, label="Target 70/30 split")

    # Approximate 99.7% confidence band (±3σ) around the target split under a
    # hypothetical "no bug" scenario with steadily growing cumulative
    # traffic. This helps visualize when the observed ratio meaningfully
    # departs from what random noise alone would explain.
    p0 = target_ratio
    daily_users = 4000  # illustrative; not tied to any real system
    n_cum = daily_users * days
    se = np.sqrt(p0 * (1 - p0) / n_cum)
    band = 3 * se
    lower = p0 - band
    upper = p0 + band
    ax.fill_between(
            days,
            lower,
            upper,
            color="gray",
            alpha=0.12,
            label="Approx. ±3σ band (no bug)",
    )

    ax.axvspan(bug_start_day, days[-1], color="red", alpha=0.05)

    ax.set_xlabel("Day")
    ax.set_ylabel("Cumulative allocation ratio to variant A")
    ax.set_title("Example of routing bug / Sample Ratio Mismatch (SRM) over time")
    ax.set_ylim(0.45, 0.9)

    ax.legend(loc="best")
    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.7)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_sample_size_vs_mde_plot(output_path: pathlib.Path) -> None:
    """Sample size per variant as a function of MDE (proportion metric).

    This implements the planning formula from Section 3.C for a
    two-variant proportion test with:

    * Baseline rate p = 3.2%.
    * Significance level α = 0.05.
    * Power = 0.80.

    The x-axis varies the *relative* MDE (from 2% to 30% lift over the
    baseline), which we convert into an absolute difference. The
    y-axis is the required sample size per variant. The red annotated
    point shows a typical configuration used in the docs: detecting a
    10% relative lift and the corresponding users per variant.
    """

    # Parameters chosen to match the narrative in the doc
    alpha = 0.05
    power = 0.80
    z_alpha_over_2 = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)

    p = 0.032  # 3.2% baseline conversion rate

    # Relative MDE from 2% to 30% lift, converted to absolute delta
    relative_mde = np.linspace(0.02, 0.30, 80)
    mde_abs = p * relative_mde

    n_per_group = 2 * (z_alpha_over_2 + z_beta) ** 2 * (p * (1 - p)) / (mde_abs**2)

    fig, ax = plt.subplots(figsize=(8, 4.5))

    ax.plot(relative_mde * 100, n_per_group, color="#1f77b4")
    ax.set_xlabel("Relative MDE (% lift over baseline)")
    ax.set_ylabel("Required sample size per variant")
    ax.set_title("Sample size per variant vs. Minimum Detectable Effect (MDE)")

    # Annotate a "typical" planning point for intuition: a 10% lift.
    ref_rel_mde = 0.10  # 10% relative improvement
    ref_mde_abs = p * ref_rel_mde
    ref_n = 2 * (z_alpha_over_2 + z_beta) ** 2 * (p * (1 - p)) / (ref_mde_abs**2)

    ax.scatter(ref_rel_mde * 100, ref_n, color="#d62728", zorder=3)
    ax.axvline(ref_rel_mde * 100, color="#d62728", linestyle="--", linewidth=1.0)
    ax.annotate(
        f"10% lift → ~{int(ref_n):,} users / variant",
        xy=(ref_rel_mde * 100, ref_n),
        xytext=(ref_rel_mde * 100 + 1.5, ref_n * 0.6),
        arrowprops={"arrowstyle": "->", "color": "#d62728"},
        fontsize=8,
        color="#d62728",
    )

    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.7)
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_power_vs_sample_size_plot(output_path: pathlib.Path) -> None:
    """Power curve as a function of sample size for a fixed lift.

    This uses the normal approximation for a two-sided z-test on
    proportions, with:

    * Baseline rate p = 3.2%.
    * Relative lift = 10%.
    * Significance level α = 0.05.

    The x-axis is the per-variant sample size, and the y-axis is the
    resulting power (1 - β). The curve illustrates the "S-shape":
    power grows quickly at small n, then exhibits diminishing returns
    once you approach high power (e.g. 0.8–0.9).
    """

    alpha = 0.05
    z_alpha_over_2 = norm.ppf(1 - alpha / 2)

    p = 0.032  # baseline
    rel_mde = 0.10  # 10% relative lift
    mde_abs = p * rel_mde

    # Range of per-variant sample sizes
    n_values = np.linspace(5_000, 80_000, 80)

    # Standard error for difference in proportions with equal sizes
    se_diff = np.sqrt(2 * p * (1 - p) / n_values)
    # Non-centrality parameter under alternative
    lambd = mde_abs / se_diff

    # Power for two-sided test under normal approximation
    # P(|Z| > z_alpha/2 | Z ~ N(lambda, 1))
    power = norm.cdf(-z_alpha_over_2 - lambd) + 1 - norm.cdf(z_alpha_over_2 - lambd)

    fig, ax = plt.subplots(figsize=(8, 4.5))

    ax.plot(n_values, power, color="#d62728")
    ax.set_xlabel("Sample size per variant")
    ax.set_ylabel("Power (1 - β)")
    ax.set_title("Power vs. sample size for a 10% relative lift (proportion metric)")
    ax.set_ylim(0.0, 1.05)

    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.7)
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_type1_type2_plot(output_path: pathlib.Path) -> None:
    """Visualize Type I (α) and Type II (β) errors on z-scales.

    This figure draws two normal curves over the same standardized
    x-axis (the test statistic / z-score):

    * Blue: the null distribution, centered at 0 (no effect).
    * Orange: an alternative distribution, centered at delta = 2
      standard deviations to the right (a true positive lift).

    For a two-sided test with α = 0.05, we place critical values at
    ±z_{α/2}. Under the null (blue), the tails beyond these cutoffs
    are the Type I error regions (false positives). Under the
    alternative (orange), the central area between the cutoffs is the
    Type II error region (false negatives). This visually connects the
    abstract definitions of α and β to concrete areas under the two
    curves.
    """

    alpha = 0.05
    z_alpha_over_2 = norm.ppf(1 - alpha / 2)

    # Effect size under alternative in SD units
    delta = 2.0

    x = np.linspace(-5, 7, 800)
    null_pdf = norm.pdf(x, loc=0.0, scale=1.0)
    alt_pdf = norm.pdf(x, loc=delta, scale=1.0)

    fig, ax = plt.subplots(figsize=(8, 4.5))

    ax.plot(x, null_pdf, label="Null distribution (no effect)", color="#1f77b4")
    ax.plot(x, alt_pdf, label="Alternative distribution (true effect)", color="#ff7f0e")

    # Shade Type I error regions under null beyond critical values
    ax.fill_between(x, 0, null_pdf, where=(x <= -z_alpha_over_2), color="#1f77b4", alpha=0.15)
    ax.fill_between(x, 0, null_pdf, where=(x >= z_alpha_over_2), color="#1f77b4", alpha=0.15, label="Type I error (α)")

    # Mark the β region: where the alternative still falls inside the
    # acceptance region defined by the same cutoffs.
    z_beta = norm.ppf(0.8)
    ax.fill_between(
        x,
        0,
        alt_pdf,
        where=(x > -z_alpha_over_2) & (x < z_alpha_over_2),
        color="#ff7f0e",
        alpha=0.15,
        label="Type II error (β)",
    )

    ax.axvline(-z_alpha_over_2, color="gray", linestyle="--", linewidth=1.0)
    ax.axvline(z_alpha_over_2, color="gray", linestyle="--", linewidth=1.0)

    ax.set_xlabel("Test statistic (standardized)")
    ax.set_ylabel("Density")
    ax.set_title("Type I (α) and Type II (β) error regions")

    ax.legend(loc="upper right")
    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.7)
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_sample_size_vs_power_alpha_plot(output_path: pathlib.Path) -> None:
    """Required sample size vs. power for several α choices.

    This plot keeps the baseline rate and effect size fixed:

    * Baseline p = 3.2%.
    * Relative MDE = 10%.

    For each α in {0.10, 0.05, 0.01} and power ∈ [0.6, 0.95], we use
    the same two-proportion sample-size formula as in
    generate_sample_size_vs_mde_plot to compute the required sample
    size per variant. Each curve therefore answers:

    "If I want this power and this α for a 10% lift over 3.2%, how
    many users per variant do I need?"

    The figure makes it explicit that stricter α (smaller values) and
    higher power always increase the required sample size.
    """

    p = 0.032  # 3.2% baseline conversion rate
    rel_mde = 0.10  # 10% relative lift
    mde_abs = p * rel_mde

    power_values = np.linspace(0.6, 0.95, 71)
    alphas = [0.10, 0.05, 0.01]

    fig, ax = plt.subplots(figsize=(8, 4.5))

    for alpha in alphas:
        z_alpha_over_2 = norm.ppf(1 - alpha / 2)
        z_beta = norm.ppf(power_values)
        n_per_group = 2 * (z_alpha_over_2 + z_beta) ** 2 * (p * (1 - p)) / (mde_abs**2)
        ax.plot(power_values, n_per_group, label=f"α = {alpha:0.02f}")

    ax.set_xlabel("Power (1 - β)")
    ax.set_ylabel("Required sample size per variant")
    ax.set_title("Sample size per variant vs. power for different α (10% lift, p = 3.2%)")
    ax.set_ylim(bottom=0)

    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.7)
    ax.legend(loc="upper left")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent
    generate_routing_bug_plot(root / "routing_bug.png")
    generate_sample_size_vs_mde_plot(root / "sample_size_vs_mde.png")
    generate_power_vs_sample_size_plot(root / "power_vs_sample_size.png")
    generate_type1_type2_plot(root / "type1_type2_errors.png")
    generate_sample_size_vs_power_alpha_plot(root / "sample_size_vs_power_alpha.png")


if __name__ == "__main__":
    main()
