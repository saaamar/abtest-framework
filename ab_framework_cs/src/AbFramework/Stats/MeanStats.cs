namespace AbFramework.Stats;

public sealed record MeanStats(
    double ControlMean,
    double ControlStdDev,
    int ControlN,
    double TreatmentMean,
    double TreatmentStdDev,
    int TreatmentN
);
