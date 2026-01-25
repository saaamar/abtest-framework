using AbFramework.Results;
using AbFramework.Stats;

namespace AbFramework.Backends;

public interface IStatisticalBackend
{
    MetricResult TestProportion(
        string metricName,
        string controlVariant,
        string treatmentVariant,
        ProportionStats stats,
        double alpha);

    MetricResult TestMean(
        string metricName,
        string controlVariant,
        string treatmentVariant,
        MeanStats stats,
        double alpha);

    SrmCheckResult CheckSrm(
        string controlVariant,
        string treatmentVariant,
        int observedControl,
        int observedTreatment,
        double expectedControlFraction,
        double expectedTreatmentFraction,
        double alpha);
}
