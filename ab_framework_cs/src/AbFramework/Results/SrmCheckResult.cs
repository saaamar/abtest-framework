namespace AbFramework.Results;

public sealed record SrmCheckResult(
    string ControlVariant,
    string TreatmentVariant,
    int ObservedControl,
    int ObservedTreatment,
    double ExpectedControlFraction,
    double ExpectedTreatmentFraction,
    double PValue,
    bool Pass,
    string Recommendation
);
