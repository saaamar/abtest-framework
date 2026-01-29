using System.Data;
using AbFramework;
using AbFramework.Stats;
using Xunit;

namespace AbFramework.Tests;

public sealed class ParityRegressionTests
{
    private static void AssertClose(double expected, double actual, double tol, string? message = null)
    {
        if (double.IsNaN(expected) || double.IsNaN(actual))
            Assert.Fail(message ?? $"NaN encountered (expected={expected}, actual={actual})");

        var diff = Math.Abs(expected - actual);
        Assert.True(diff <= tol, message ?? $"Expected {expected} but got {actual} (diff={diff}, tol={tol})");
    }

    private static int SumInt(DataTable table, string columnName)
    {
        var sum = 0;
        foreach (DataRow row in table.Rows)
            sum += Convert.ToInt32(row[columnName]);
        return sum;
    }

    private static DataTable BuildProportionInput()
    {
        var t = new DataTable();
        t.Columns.Add("day", typeof(string));
        t.Columns.Add("successes_control", typeof(int));
        t.Columns.Add("n_control", typeof(int));
        t.Columns.Add("successes_treatment", typeof(int));
        t.Columns.Add("n_treatment", typeof(int));

        // Matches examples/ParityCheck and verification/cs_python_parity/cs_python_parity_check.py
        t.Rows.Add("2026-01-01", 1197, 12000, 1302, 12000);
        t.Rows.Add("2026-01-02", 1162, 12000, 1270, 12000);
        t.Rows.Add("2026-01-03", 1189, 12000, 1324, 12000);
        t.Rows.Add("2026-01-04", 1145, 12000, 1307, 12000);
        t.Rows.Add("2026-01-05", 1175, 12000, 1266, 12000);

        return t;
    }

    private static DataTable BuildMeanInput()
    {
        var t = new DataTable();
        t.Columns.Add("day", typeof(string));
        t.Columns.Add("mean_control", typeof(double));
        t.Columns.Add("std_control", typeof(double));
        t.Columns.Add("n_control", typeof(int));
        t.Columns.Add("mean_treatment", typeof(double));
        t.Columns.Add("std_treatment", typeof(double));
        t.Columns.Add("n_treatment", typeof(int));

        // Matches examples/ParityCheck and verification/cs_python_parity/cs_python_parity_check.py
        t.Rows.Add("2026-01-01", 2.50, 4.20, 12000, 2.58, 4.25, 12000);
        t.Rows.Add("2026-01-02", 2.47, 4.10, 12000, 2.56, 4.15, 12000);
        t.Rows.Add("2026-01-03", 2.51, 4.30, 12000, 2.60, 4.35, 12000);
        t.Rows.Add("2026-01-04", 2.49, 4.25, 12000, 2.57, 4.28, 12000);
        t.Rows.Add("2026-01-05", 2.50, 4.15, 12000, 2.59, 4.22, 12000);

        return t;
    }

    private static (double mean, double std, int n) CombineSampleStats(DataTable table, string meanCol, string stdCol, string nCol)
    {
        var totalN = SumInt(table, nCol);
        if (totalN <= 0) throw new ArgumentOutOfRangeException(nameof(totalN));

        double totalSum = 0;
        foreach (DataRow row in table.Rows)
        {
            var mean = Convert.ToDouble(row[meanCol]);
            var n = Convert.ToInt32(row[nCol]);
            totalSum += mean * n;
        }

        var overallMean = totalSum / totalN;

        double totalSumSq = 0;
        foreach (DataRow row in table.Rows)
        {
            var mean = Convert.ToDouble(row[meanCol]);
            var std = Convert.ToDouble(row[stdCol]);
            var n = Convert.ToInt32(row[nCol]);
            var varSample = std * std;
            totalSumSq += (n - 1) * varSample + n * mean * mean;
        }

        double overallStd;
        if (totalN <= 1)
        {
            overallStd = 0;
        }
        else
        {
            var varNumerator = totalSumSq - totalN * overallMean * overallMean;
            var sampleVar = Math.Max(varNumerator / (totalN - 1), 0.0);
            overallStd = Math.Sqrt(sampleVar);
        }

        return (overallMean, overallStd, totalN);
    }

    [Fact]
    public void ProportionMetric_MatchesKnownParityOutputs()
    {
        var data = BuildProportionInput();

        var test = new ABTest<DataTable>(
            name: "parity_proportion",
            variants: new[] { "control", "treatment" })
            .SetAlpha(0.05);

        test.AddMetric(
            name: "conversion_rate",
            type: MetricType.Proportion,
            compute: d => new ProportionStats(
                ControlSuccesses: SumInt(d, "successes_control"),
                ControlN: SumInt(d, "n_control"),
                TreatmentSuccesses: SumInt(d, "successes_treatment"),
                TreatmentN: SumInt(d, "n_treatment")));

        var results = test.Analyze(data, "conversion_rate");
        var m = results.Metric;

        // Expected values from your parity run (Python + C#)
        Assert.Equal("conversion_rate", m.MetricName);
        Assert.Equal(MetricType.Proportion, m.MetricType);
        Assert.Equal("control", m.ControlVariant);
        Assert.Equal("treatment", m.TreatmentVariant);
        Assert.Equal(60000, m.SampleSizeControl);
        Assert.Equal(60000, m.SampleSizeTreatment);

        AssertClose(0.0978, m.ControlValue, 1e-12, "ControlValue");
        AssertClose(0.10781666666666667, m.TreatmentValue, 1e-12, "TreatmentValue");
        AssertClose(0.10241990456714391, m.Lift, 1e-10, "Lift");

        // For p-value/CI we use the same tolerances as the parity script
        AssertClose(1.11321005746845e-08, m.PValue, 5e-7, "PValue");
        AssertClose(0.006580413290699165, m.CiLower, 5e-7, "CiLower");
        AssertClose(0.013452920042634183, m.CiUpper, 5e-7, "CiUpper");
        Assert.True(m.Significant);

        // Extra stability checks (these were in the C# JSON output)
        Assert.NotNull(m.StandardErrorControl);
        Assert.NotNull(m.StandardErrorTreatment);
        AssertClose(0.0012126772035459395, m.StandardErrorControl!.Value, 1e-12, "StandardErrorControl");
        AssertClose(0.0012661768771618203, m.StandardErrorTreatment!.Value, 1e-12, "StandardErrorTreatment");

        Assert.Null(m.StdDevControl);
        Assert.Null(m.StdDevTreatment);
        Assert.True(string.IsNullOrWhiteSpace(m.Error));
    }

    [Fact]
    public void MeanMetric_MatchesKnownParityOutputs()
    {
        var data = BuildMeanInput();

        var test = new ABTest<DataTable>(
            name: "parity_mean",
            variants: new[] { "control", "treatment" })
            .SetAlpha(0.05);

        test.AddMetric(
            name: "avg_revenue",
            type: MetricType.Mean,
            compute: d =>
            {
                var (meanC, stdC, nC) = CombineSampleStats(d, "mean_control", "std_control", "n_control");
                var (meanT, stdT, nT) = CombineSampleStats(d, "mean_treatment", "std_treatment", "n_treatment");
                return new MeanStats(meanC, stdC, nC, meanT, stdT, nT);
            });

        var results = test.Analyze(data, "avg_revenue");
        var m = results.Metric;

        // Expected values from your parity run (Python + C#)
        Assert.Equal("avg_revenue", m.MetricName);
        Assert.Equal(MetricType.Mean, m.MetricType);
        Assert.Equal("control", m.ControlVariant);
        Assert.Equal("treatment", m.TreatmentVariant);
        Assert.Equal(60000, m.SampleSizeControl);
        Assert.Equal(60000, m.SampleSizeTreatment);

        AssertClose(2.494, m.ControlValue, 1e-12, "ControlValue");
        AssertClose(2.58, m.TreatmentValue, 1e-12, "TreatmentValue");
        AssertClose(0.03448275862068959, m.Lift, 1e-10, "Lift");

        AssertClose(0.00042336975786549935, m.PValue, 5e-7, "PValue");
        AssertClose(0.038184253532374195, m.CiLower, 5e-7, "CiLower");
        AssertClose(0.1338157464676255, m.CiUpper, 5e-7, "CiUpper");
        Assert.True(m.Significant);

        // Extra stability checks (these were in the C# JSON output)
        Assert.NotNull(m.StdDevControl);
        Assert.NotNull(m.StdDevTreatment);
        AssertClose(4.200477074110452, m.StdDevControl!.Value, 1e-12, "StdDevControl");
        AssertClose(4.250394749423332, m.StdDevTreatment!.Value, 1e-12, "StdDevTreatment");

        Assert.Null(m.StandardErrorControl);
        Assert.Null(m.StandardErrorTreatment);
        Assert.True(string.IsNullOrWhiteSpace(m.Error));
    }
}
