namespace AbFramework.Results;

public sealed record MetricResult(
    string MetricName,
    MetricType MetricType,
    string ControlVariant,
    string TreatmentVariant,
    double ControlValue,
    double TreatmentValue,
    int SampleSizeControl,
    int SampleSizeTreatment,
    double Lift,
    double PValue,
    double CiLower,
    double CiUpper,
    bool Significant,
    double? StandardErrorControl = null,
    double? StandardErrorTreatment = null,
    double? StdDevControl = null,
    double? StdDevTreatment = null,
    string? Error = null
);
