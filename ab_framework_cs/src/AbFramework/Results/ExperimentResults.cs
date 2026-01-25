using System.Text;

namespace AbFramework.Results;

public sealed class ExperimentResults
{
    public ExperimentResults(
        string experimentName,
        DateTimeOffset timestamp,
        double alpha,
        MetricResult metric,
        SrmCheckResult? srm)
    {
        ExperimentName = experimentName;
        Timestamp = timestamp;
        Alpha = alpha;
        Metric = metric;
        Srm = srm;
    }

    public string ExperimentName { get; }
    public DateTimeOffset Timestamp { get; }
    public double Alpha { get; }

    public MetricResult Metric { get; }

    public SrmCheckResult? Srm { get; }

    public string ToSummaryString()
    {
        var sb = new StringBuilder();
        sb.AppendLine($"# {ExperimentName}");
        sb.AppendLine($"**Analysis Date:** {Timestamp:O}");
        sb.AppendLine($"**Significance Level:** alpha = {Alpha}");
        sb.AppendLine();

        if (Srm is not null)
        {
            sb.AppendLine("## Sample Ratio Mismatch Check");
            sb.AppendLine(Srm.Recommendation);
            sb.AppendLine();
        }

        sb.AppendLine("## Metric Result");
        sb.AppendLine();

        if (!string.IsNullOrWhiteSpace(Metric.Error))
        {
            sb.AppendLine($"### [ERROR] {Metric.MetricName}");
            sb.AppendLine($"Error: {Metric.Error}");
            return sb.ToString();
        }

        var sigIcon = Metric.Significant ? "[SIG]" : "[NOT-SIG]";
        sb.AppendLine($"### {sigIcon} {Metric.MetricName}");
        sb.AppendLine($"- **Type:** {Metric.MetricType}");
        sb.AppendLine($"- **Control ({Metric.ControlVariant}):** {Metric.ControlValue:F4} (n={Metric.SampleSizeControl})");
        sb.AppendLine($"- **Treatment ({Metric.TreatmentVariant}):** {Metric.TreatmentValue:F4} (n={Metric.SampleSizeTreatment})");

        if (Metric.MetricType == MetricType.Proportion)
        {
            if (Metric.StandardErrorControl is not null)
                sb.AppendLine($"- **SE (control):** {Metric.StandardErrorControl.Value:F6}");
            if (Metric.StandardErrorTreatment is not null)
                sb.AppendLine($"- **SE (treatment):** {Metric.StandardErrorTreatment.Value:F6}");
        }
        else
        {
            if (Metric.StdDevControl is not null)
                sb.AppendLine($"- **Std (control):** {Metric.StdDevControl.Value:F6}");
            if (Metric.StdDevTreatment is not null)
                sb.AppendLine($"- **Std (treatment):** {Metric.StdDevTreatment.Value:F6}");
        }

        sb.AppendLine($"- **Lift:** {Metric.Lift:P2}");
        sb.AppendLine($"- **P-value:** {Metric.PValue:F6}");
        sb.AppendLine($"- **95% CI:** [{Metric.CiLower:F4}, {Metric.CiUpper:F4}]");

        return sb.ToString();
    }
}
