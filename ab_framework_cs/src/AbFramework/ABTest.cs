using AbFramework.Backends;
using AbFramework.Results;
using AbFramework.Stats;

namespace AbFramework;

public sealed class ABTest<TData>
{
    private readonly Dictionary<string, MetricDefinition<TData>> _metrics = new(StringComparer.Ordinal);

    public ABTest(string name, IReadOnlyList<string> variants, IStatisticalBackend? backend = null)
    {
        if (string.IsNullOrWhiteSpace(name)) throw new ArgumentException("Experiment name is required", nameof(name));
        if (variants is null) throw new ArgumentNullException(nameof(variants));
        if (variants.Count != 2) throw new ArgumentException("Exactly 2 variant labels are required for v1", nameof(variants));
        if (string.IsNullOrWhiteSpace(variants[0]) || string.IsNullOrWhiteSpace(variants[1]))
            throw new ArgumentException("Variant labels must be non-empty strings", nameof(variants));
        if (string.Equals(variants[0], variants[1], StringComparison.Ordinal))
            throw new ArgumentException("Variant labels must be distinct", nameof(variants));

        Name = name;
        ControlVariant = variants[0];
        TreatmentVariant = variants[1];
        Backend = backend ?? new DefaultBackend();
    }

    public string Name { get; }

    public string ControlVariant { get; }

    public string TreatmentVariant { get; }

    public IStatisticalBackend Backend { get; }

    public double Alpha { get; private set; } = 0.05;

    public IReadOnlyCollection<string> ActiveMetrics => _metrics.Keys;

    public ABTest<TData> SetAlpha(double alpha)
    {
        if (alpha <= 0 || alpha >= 1) throw new ArgumentOutOfRangeException(nameof(alpha), "Alpha must be in (0,1)");
        Alpha = alpha;
        return this;
    }

    public void AddMetric(string name, MetricType type, Func<TData, object> compute)
    {
        if (_metrics.ContainsKey(name))
            throw new InvalidOperationException($"Metric '{name}' is already registered");

        _metrics[name] = new MetricDefinition<TData>(name, type, compute);
    }

    public ExperimentResults Analyze(
        TData data,
        string metricName,
        bool runSrmCheck = false,
        int? observedControl = null,
        int? observedTreatment = null,
        double expectedControlFraction = 0.5,
        double expectedTreatmentFraction = 0.5,
        DateTimeOffset? timestamp = null)
    {
        if (data is null) throw new ArgumentNullException(nameof(data));
        if (string.IsNullOrWhiteSpace(metricName)) throw new ArgumentException("Metric name is required", nameof(metricName));

        var ts = timestamp ?? DateTimeOffset.UtcNow;

        MetricResult metricResult;
        try
        {
            if (!_metrics.TryGetValue(metricName, out var metric))
                throw new KeyNotFoundException($"Metric '{metricName}' is not registered");

            metricResult = metric.Type switch
            {
                MetricType.Proportion => Backend.TestProportion(
                    metricName,
                    ControlVariant,
                    TreatmentVariant,
                    metric.ComputeProportion(data),
                    Alpha),

                MetricType.Mean => Backend.TestMean(
                    metricName,
                    ControlVariant,
                    TreatmentVariant,
                    metric.ComputeMean(data),
                    Alpha),

                _ => throw new NotSupportedException($"Unsupported MetricType '{metric.Type}'")
            };
        }
        catch (Exception ex)
        {
            metricResult = new MetricResult(
                MetricName: metricName,
                MetricType: _metrics.TryGetValue(metricName, out var m) ? m.Type : MetricType.Proportion,
                ControlVariant: ControlVariant,
                TreatmentVariant: TreatmentVariant,
                ControlValue: double.NaN,
                TreatmentValue: double.NaN,
                SampleSizeControl: 0,
                SampleSizeTreatment: 0,
                Lift: double.NaN,
                PValue: double.NaN,
                CiLower: double.NaN,
                CiUpper: double.NaN,
                Significant: false,
                Error: ex.Message);
        }

        SrmCheckResult? srm = null;
        if (runSrmCheck)
        {
            if (observedControl is null || observedTreatment is null)
                throw new ArgumentException("When runSrmCheck=true, observedControl and observedTreatment must be provided");

            srm = Backend.CheckSrm(
                ControlVariant,
                TreatmentVariant,
                observedControl.Value,
                observedTreatment.Value,
                expectedControlFraction,
                expectedTreatmentFraction,
                Alpha);
        }

        return new ExperimentResults(Name, ts, Alpha, metricResult, srm);
    }
}
