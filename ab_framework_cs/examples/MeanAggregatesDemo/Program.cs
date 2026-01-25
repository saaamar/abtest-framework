using System.Data;
using AbFramework;
using AbFramework.Stats;

static int SumInt(DataTable table, string columnName)
{
    if (!table.Columns.Contains(columnName))
        throw new ArgumentException($"Missing required column '{columnName}'", nameof(columnName));

    var sum = 0;
    foreach (DataRow row in table.Rows)
        sum += Convert.ToInt32(row[columnName]);

    return sum;
}

static DataTable FilterRows(DataTable source, string filterExpression)
{
    var rows = source.Select(filterExpression);
    if (rows.Length == 0)
        return source.Clone();

    var filtered = source.Clone();
    foreach (var row in rows)
        filtered.ImportRow(row);

    return filtered;
}

// Combine daily (mean, std, n) into overall (mean, std, n).
// Assumes `std` is a SAMPLE standard deviation computed within each day-bucket.
static (double mean, double std, int n) CombineSampleStats(DataTable table, string meanCol, string stdCol, string nCol)
{
    var totalN = SumInt(table, nCol);
    if (totalN <= 0)
        throw new ArgumentOutOfRangeException(nameof(totalN), "Total n must be > 0");

    // Weighted mean: sum(mean_i * n_i) / sum(n_i)
    double totalSum = 0;
    foreach (DataRow row in table.Rows)
    {
        var mean = Convert.ToDouble(row[meanCol]);
        var n = Convert.ToInt32(row[nCol]);
        totalSum += mean * n;
    }

    var overallMean = totalSum / totalN;

    // Reconstruct sumsq from per-bucket sample std dev:
    // sumsq_i = (n_i - 1) * s_i^2 + n_i * mean_i^2
    double totalSumSq = 0;
    foreach (DataRow row in table.Rows)
    {
        var mean = Convert.ToDouble(row[meanCol]);
        var std = Convert.ToDouble(row[stdCol]);
        var n = Convert.ToInt32(row[nCol]);

        if (n <= 0) continue;
        if (std < 0) throw new ArgumentOutOfRangeException(stdCol, "Std dev must be >= 0");

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
        // sample variance: (sumsq - n * mean^2) / (n - 1)
        var varNumerator = totalSumSq - totalN * overallMean * overallMean;
        var sampleVar = Math.Max(varNumerator / (totalN - 1), 0.0);
        overallStd = Math.Sqrt(sampleVar);
    }

    return (overallMean, overallStd, totalN);
}

var daily = new DataTable();
// NOTE: The framework does not care about this schema. This is caller-owned.
daily.Columns.Add("day", typeof(string));

// For a mean metric, each row has (mean, std, n) per variant (often per day).
daily.Columns.Add("mean_control", typeof(double));
daily.Columns.Add("std_control", typeof(double));
daily.Columns.Add("n_control", typeof(int));
daily.Columns.Add("mean_treatment", typeof(double));
daily.Columns.Add("std_treatment", typeof(double));
daily.Columns.Add("n_treatment", typeof(int));

// Example daily aggregates (made-up numbers):
// Think of this as average revenue per user per day bucket, with sample std dev and n.
daily.Rows.Add("2026-01-01", 2.50, 4.20, 12000, 2.58, 4.25, 12000);
daily.Rows.Add("2026-01-02", 2.47, 4.10, 12000, 2.56, 4.15, 12000);
daily.Rows.Add("2026-01-03", 2.51, 4.30, 12000, 2.60, 4.35, 12000);
daily.Rows.Add("2026-01-04", 2.49, 4.25, 12000, 2.57, 4.28, 12000);
daily.Rows.Add("2026-01-05", 2.50, 4.15, 12000, 2.59, 4.22, 12000);

var test = new ABTest<DataTable>(
    name: "mean_metric_demo",
    variants: new[] { "control", "treatment" });

test.AddMetric(
    name: "avg_revenue",
    type: MetricType.Mean,
    compute: data =>
    {
        // Caller-owned aggregation: combine per-day mean/std/n into overall mean/std/n.
        var (meanC, stdC, nC) = CombineSampleStats(data, "mean_control", "std_control", "n_control");
        var (meanT, stdT, nT) = CombineSampleStats(data, "mean_treatment", "std_treatment", "n_treatment");

        return new MeanStats(
            ControlMean: meanC,
            ControlStdDev: stdC,
            ControlN: nC,
            TreatmentMean: meanT,
            TreatmentStdDev: stdT,
            TreatmentN: nT);
    });

Console.WriteLine("Daily cumulative workflow for a MEAN metric (day 1 -> today)");
Console.WriteLine(new string('-', 90));

var days = daily.AsEnumerable()
    .Select(r => (string)r["day"])
    .Distinct()
    .OrderBy(x => x, StringComparer.Ordinal)
    .ToList();

foreach (var day in days)
{
    var cumulative = FilterRows(daily, $"day <= '{day}'");

    var observedControl = SumInt(cumulative, "n_control");
    var observedTreatment = SumInt(cumulative, "n_treatment");

    var results = test.Analyze(
        data: cumulative,
        metricName: "avg_revenue",
        runSrmCheck: true,
        observedControl: observedControl,
        observedTreatment: observedTreatment,
        expectedControlFraction: 0.5,
        expectedTreatmentFraction: 0.5);

    Console.WriteLine($"\n=== CUMULATIVE through {day} ===");
    Console.WriteLine(results.ToSummaryString());
}
