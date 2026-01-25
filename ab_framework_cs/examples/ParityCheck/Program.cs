using System.Data;
using System.Text.Json;
using AbFramework;
using AbFramework.Stats;

static int SumInt(DataTable table, string columnName)
{
    var sum = 0;
    foreach (DataRow row in table.Rows)
        sum += Convert.ToInt32(row[columnName]);
    return sum;
}

static DataTable BuildProportionInput()
{
    var t = new DataTable();
    t.Columns.Add("day", typeof(string));
    t.Columns.Add("successes_control", typeof(int));
    t.Columns.Add("n_control", typeof(int));
    t.Columns.Add("successes_treatment", typeof(int));
    t.Columns.Add("n_treatment", typeof(int));

    // Same numbers as C# DailyAggregatesDemo (and Python parity script)
    t.Rows.Add("2026-01-01", 1197, 12000, 1302, 12000);
    t.Rows.Add("2026-01-02", 1162, 12000, 1270, 12000);
    t.Rows.Add("2026-01-03", 1189, 12000, 1324, 12000);
    t.Rows.Add("2026-01-04", 1145, 12000, 1307, 12000);
    t.Rows.Add("2026-01-05", 1175, 12000, 1266, 12000);

    return t;
}

static DataTable BuildMeanInput()
{
    var t = new DataTable();
    t.Columns.Add("day", typeof(string));
    t.Columns.Add("mean_control", typeof(double));
    t.Columns.Add("std_control", typeof(double));
    t.Columns.Add("n_control", typeof(int));
    t.Columns.Add("mean_treatment", typeof(double));
    t.Columns.Add("std_treatment", typeof(double));
    t.Columns.Add("n_treatment", typeof(int));

    // Same numbers as C# MeanAggregatesDemo (and Python parity script)
    t.Rows.Add("2026-01-01", 2.50, 4.20, 12000, 2.58, 4.25, 12000);
    t.Rows.Add("2026-01-02", 2.47, 4.10, 12000, 2.56, 4.15, 12000);
    t.Rows.Add("2026-01-03", 2.51, 4.30, 12000, 2.60, 4.35, 12000);
    t.Rows.Add("2026-01-04", 2.49, 4.25, 12000, 2.57, 4.28, 12000);
    t.Rows.Add("2026-01-05", 2.50, 4.15, 12000, 2.59, 4.22, 12000);

    return t;
}

static (double mean, double std, int n) CombineSampleStats(DataTable table, string meanCol, string stdCol, string nCol)
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

var jsonOptions = new JsonSerializerOptions { WriteIndented = false };

// PROPORTION
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
    Console.WriteLine(JsonSerializer.Serialize(new { kind = "proportion", metric = results.Metric }, jsonOptions));
}

// MEAN
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
    Console.WriteLine(JsonSerializer.Serialize(new { kind = "mean", metric = results.Metric }, jsonOptions));
}
