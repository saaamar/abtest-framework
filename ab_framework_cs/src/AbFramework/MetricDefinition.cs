using AbFramework.Stats;

namespace AbFramework;

public sealed class MetricDefinition<TData>
{
    public MetricDefinition(string name, MetricType type, Func<TData, object> compute)
    {
        if (string.IsNullOrWhiteSpace(name)) throw new ArgumentException("Metric name is required", nameof(name));
        Name = name;
        Type = type;
        Compute = compute ?? throw new ArgumentNullException(nameof(compute));
    }

    public string Name { get; }
    public MetricType Type { get; }

    internal Func<TData, object> Compute { get; }

    internal ProportionStats ComputeProportion(TData data)
    {
        var stats = Compute(data);
        return stats as ProportionStats
               ?? throw new InvalidOperationException($"Metric '{Name}' must return ProportionStats for MetricType.Proportion");
    }

    internal MeanStats ComputeMean(TData data)
    {
        var stats = Compute(data);
        return stats as MeanStats
               ?? throw new InvalidOperationException($"Metric '{Name}' must return MeanStats for MetricType.Mean");
    }
}
