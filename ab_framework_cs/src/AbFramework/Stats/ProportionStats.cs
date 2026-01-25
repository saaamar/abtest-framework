namespace AbFramework.Stats;

public sealed record ProportionStats(
    int ControlSuccesses,
    int ControlN,
    int TreatmentSuccesses,
    int TreatmentN
);
