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

var daily = new DataTable();
// NOTE: The framework does not care about this schema. This is caller-owned.
// Using string day keys keeps filtering simple for the demo.
daily.Columns.Add("day", typeof(string));
daily.Columns.Add("successes_control", typeof(int));
daily.Columns.Add("n_control", typeof(int));
daily.Columns.Add("successes_treatment", typeof(int));
daily.Columns.Add("n_treatment", typeof(int));

// Example: one row per day with TRUE integer successes + denominators.
// (These can come from your data pipeline. No raw event logs required here.)
daily.Rows.Add("2026-01-01", 1197, 12000, 1302, 12000);
daily.Rows.Add("2026-01-02", 1162, 12000, 1270, 12000);
daily.Rows.Add("2026-01-03", 1189, 12000, 1324, 12000);
daily.Rows.Add("2026-01-04", 1145, 12000, 1307, 12000);
daily.Rows.Add("2026-01-05", 1175, 12000, 1266, 12000);

var test = new ABTest<DataTable>(
    name: "conversion_rate_demo",
    variants: new[] { "control", "treatment" });

test.AddMetric(
    name: "conversion_rate",
    type: MetricType.Proportion,
    compute: data =>
    {
        // Aggregate across all rows passed in (cumulative or a slice).
        var successesControl = SumInt(data, "successes_control");
        var nControl = SumInt(data, "n_control");
        var successesTreatment = SumInt(data, "successes_treatment");
        var nTreatment = SumInt(data, "n_treatment");

        return new ProportionStats(
            ControlSuccesses: successesControl,
            ControlN: nControl,
            TreatmentSuccesses: successesTreatment,
            TreatmentN: nTreatment);
    });

Console.WriteLine("Daily cumulative workflow (day 1 -> today)");
Console.WriteLine(new string('-', 80));

var days = daily.AsEnumerable()
    .Select(r => (string)r["day"])
    .Distinct()
    .OrderBy(x => x, StringComparer.Ordinal)
    .ToList();

foreach (var day in days)
{
    // Decision view: analyze all data from day 1 up to `day`.
    var cumulative = FilterRows(daily, $"day <= '{day}'");

    var observedControl = SumInt(cumulative, "n_control");
    var observedTreatment = SumInt(cumulative, "n_treatment");

    var results = test.Analyze(
        data: cumulative,
        metricName: "conversion_rate",
        runSrmCheck: true,
        observedControl: observedControl,
        observedTreatment: observedTreatment,
        expectedControlFraction: 0.5,
        expectedTreatmentFraction: 0.5);

    Console.WriteLine($"\n=== CUMULATIVE through {day} ===");
    Console.WriteLine(results.ToSummaryString());
}
