using AbFramework.Results;
using AbFramework.Stats;
using MathNet.Numerics.Distributions;

namespace AbFramework.Backends;

public sealed class DefaultBackend : IStatisticalBackend
{
    public MetricResult TestProportion(
        string metricName,
        string controlVariant,
        string treatmentVariant,
        ProportionStats stats,
        double alpha)
    {
        if (stats.ControlN <= 0 || stats.TreatmentN <= 0)
            throw new ArgumentOutOfRangeException(nameof(stats), "Sample sizes must be > 0");
        if (stats.ControlSuccesses < 0 || stats.TreatmentSuccesses < 0)
            throw new ArgumentOutOfRangeException(nameof(stats), "Successes must be >= 0");
        if (stats.ControlSuccesses > stats.ControlN || stats.TreatmentSuccesses > stats.TreatmentN)
            throw new ArgumentOutOfRangeException(nameof(stats), "Successes cannot exceed N");

        var pC = (double)stats.ControlSuccesses / stats.ControlN;
        var pT = (double)stats.TreatmentSuccesses / stats.TreatmentN;

        // Match Python (ab_framework/backends/scipy_backend.py):
        // - z-stat + p-value use pooled SE
        // - CI uses Wald SE with unpooled per-group variances
        var pooled = (double)(stats.ControlSuccesses + stats.TreatmentSuccesses) / (stats.ControlN + stats.TreatmentN);
        var sePooled = Math.Sqrt(Math.Max(pooled * (1.0 - pooled), 0.0) * (1.0 / stats.ControlN + 1.0 / stats.TreatmentN));

        var diff = pT - pC;
        double z = sePooled > 0 ? diff / sePooled : 0.0;
        var pValue = 2.0 * (1.0 - Normal.CDF(0.0, 1.0, Math.Abs(z)));

        var zCrit = Normal.InvCDF(0.0, 1.0, 1.0 - alpha / 2.0);
        var seDiff = Math.Sqrt(
            Math.Max(pC * (1.0 - pC), 0.0) / stats.ControlN
            + Math.Max(pT * (1.0 - pT), 0.0) / stats.TreatmentN);
        var ciLower = diff - zCrit * seDiff;
        var ciUpper = diff + zCrit * seDiff;

        var lift = pC > 0.0 ? diff / pC : 0.0;
        var significant = pValue < alpha;

        var seControl = Math.Sqrt(Math.Max(pC * (1.0 - pC), 0.0) / stats.ControlN);
        var seTreatment = Math.Sqrt(Math.Max(pT * (1.0 - pT), 0.0) / stats.TreatmentN);

        return new MetricResult(
            MetricName: metricName,
            MetricType: MetricType.Proportion,
            ControlVariant: controlVariant,
            TreatmentVariant: treatmentVariant,
            ControlValue: pC,
            TreatmentValue: pT,
            SampleSizeControl: stats.ControlN,
            SampleSizeTreatment: stats.TreatmentN,
            Lift: lift,
            PValue: pValue,
            CiLower: ciLower,
            CiUpper: ciUpper,
            Significant: significant,
            StandardErrorControl: seControl,
            StandardErrorTreatment: seTreatment);
    }

    public MetricResult TestMean(
        string metricName,
        string controlVariant,
        string treatmentVariant,
        MeanStats stats,
        double alpha)
    {
        if (stats.ControlN <= 1 || stats.TreatmentN <= 1)
            throw new ArgumentOutOfRangeException(nameof(stats), "Sample sizes must be > 1 for t-test");
        if (stats.ControlStdDev < 0 || stats.TreatmentStdDev < 0)
            throw new ArgumentOutOfRangeException(nameof(stats), "StdDev must be >= 0");

        var diff = stats.TreatmentMean - stats.ControlMean;

        // Welch's t-test
        var varC = stats.ControlStdDev * stats.ControlStdDev;
        var varT = stats.TreatmentStdDev * stats.TreatmentStdDev;
        var se = Math.Sqrt(varC / stats.ControlN + varT / stats.TreatmentN);

        double t = se > 0 ? diff / se : 0.0;

        var dfNumerator = Math.Pow(varC / stats.ControlN + varT / stats.TreatmentN, 2.0);
        var dfDenominator = Math.Pow(varC / stats.ControlN, 2.0) / (stats.ControlN - 1)
                            + Math.Pow(varT / stats.TreatmentN, 2.0) / (stats.TreatmentN - 1);
        var df = dfDenominator > 0 ? dfNumerator / dfDenominator : (stats.ControlN + stats.TreatmentN - 2);

        var pValue = 2.0 * (1.0 - StudentT.CDF(0.0, 1.0, df, Math.Abs(t)));

        var tCrit = StudentT.InvCDF(0.0, 1.0, df, 1.0 - alpha / 2.0);
        var ciLower = diff - tCrit * se;
        var ciUpper = diff + tCrit * se;

        var lift = stats.ControlMean != 0.0 ? diff / stats.ControlMean : 0.0;
        var significant = pValue < alpha;

        return new MetricResult(
            MetricName: metricName,
            MetricType: MetricType.Mean,
            ControlVariant: controlVariant,
            TreatmentVariant: treatmentVariant,
            ControlValue: stats.ControlMean,
            TreatmentValue: stats.TreatmentMean,
            SampleSizeControl: stats.ControlN,
            SampleSizeTreatment: stats.TreatmentN,
            Lift: lift,
            PValue: pValue,
            CiLower: ciLower,
            CiUpper: ciUpper,
            Significant: significant,
            StdDevControl: stats.ControlStdDev,
            StdDevTreatment: stats.TreatmentStdDev);
    }

    public SrmCheckResult CheckSrm(
        string controlVariant,
        string treatmentVariant,
        int observedControl,
        int observedTreatment,
        double expectedControlFraction,
        double expectedTreatmentFraction,
        double alpha)
    {
        if (observedControl < 0 || observedTreatment < 0)
            throw new ArgumentOutOfRangeException(nameof(observedControl), "Observed counts must be >= 0");

        var total = observedControl + observedTreatment;
        if (total <= 0)
            throw new ArgumentOutOfRangeException(nameof(observedControl), "Total observed must be > 0");

        if (expectedControlFraction <= 0 || expectedTreatmentFraction <= 0)
            throw new ArgumentOutOfRangeException(nameof(expectedControlFraction), "Expected fractions must be > 0");

        // Normalize expected fractions
        var sum = expectedControlFraction + expectedTreatmentFraction;
        expectedControlFraction /= sum;
        expectedTreatmentFraction /= sum;

        var expectedControl = total * expectedControlFraction;
        var expectedTreatment = total * expectedTreatmentFraction;

        // Chi-square with 1 degree of freedom
        var chi2 = Math.Pow(observedControl - expectedControl, 2.0) / expectedControl
                   + Math.Pow(observedTreatment - expectedTreatment, 2.0) / expectedTreatment;

        var p = 1.0 - ChiSquared.CDF(1, chi2);
        var pass = p >= alpha;

        var rec = pass
            ? "[OK] No SRM detected - randomization looks good"
            : $"[WARNING] SRM detected (p={p:F4}). Investigate assignment / logging before trusting results.";

        return new SrmCheckResult(
            ControlVariant: controlVariant,
            TreatmentVariant: treatmentVariant,
            ObservedControl: observedControl,
            ObservedTreatment: observedTreatment,
            ExpectedControlFraction: expectedControlFraction,
            ExpectedTreatmentFraction: expectedTreatmentFraction,
            PValue: p,
            Pass: pass,
            Recommendation: rec);
    }
}
