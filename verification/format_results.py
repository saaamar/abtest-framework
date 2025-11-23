"""
Helper functions for formatting A/B test results in a professional, publication-ready format
"""

def format_conclusion(
    metric_name: str,
    variant_a_value: float,
    variant_b_value: float,
    p_value: float,
    ci_lower: float = None,
    ci_upper: float = None,
    alpha: float = 0.05,
    is_percentage: bool = False,
    currency: bool = False
) -> str:
    """
    Format a professional statistical conclusion for an A/B test result
    
    Args:
        metric_name: Name of the metric being tested (e.g., "conversion rate", "revenue per user")
        variant_a_value: Metric value for control group
        variant_b_value: Metric value for treatment group
        p_value: P-value from statistical test
        ci_lower: Lower bound of 95% CI for difference
        ci_upper: Upper bound of 95% CI for difference
        alpha: Significance level (default 0.05)
        is_percentage: Whether to format as percentage
        currency: Whether to format as currency
    
    Returns:
        Professional conclusion statement
    """
    # Format values
    if is_percentage:
        val_a_str = f"{variant_a_value*100:.2f}%"
        val_b_str = f"{variant_b_value*100:.2f}%"
        diff = (variant_b_value - variant_a_value) * 100
        diff_str = f"{abs(diff):.2f} percentage points"
    elif currency:
        val_a_str = f"${variant_a_value:.2f}"
        val_b_str = f"${variant_b_value:.2f}"
        diff = variant_b_value - variant_a_value
        diff_str = f"${abs(diff):.2f}"
    else:
        val_a_str = f"{variant_a_value:.4f}"
        val_b_str = f"{variant_b_value:.4f}"
        diff = variant_b_value - variant_a_value
        diff_str = f"{abs(diff):.4f}"
    
    # Calculate relative change
    if variant_a_value != 0:
        rel_change = ((variant_b_value - variant_a_value) / abs(variant_a_value)) * 100
        rel_change_str = f"{abs(rel_change):.1f}%"
    else:
        rel_change = 0
        rel_change_str = "N/A"
    
    # Determine direction
    direction = "higher" if variant_b_value > variant_a_value else "lower"
    
    # Statistical significance
    is_significant = p_value < alpha
    
    # Build conclusion
    conclusion_parts = []
    
    conclusion_parts.append(f"\n{'='*70}")
    conclusion_parts.append("STATISTICAL CONCLUSION")
    conclusion_parts.append('='*70)
    
    if is_significant:
        conclusion_parts.append(
            f"The treatment group showed a statistically significant {direction} {metric_name} "
            f"compared to the control group (Treatment: {val_b_str} vs. Control: {val_a_str}, "
            f"difference: {diff_str}, relative change: {rel_change_str}, p = {p_value:.4f})."
        )
        
        if ci_lower is not None and ci_upper is not None:
            if is_percentage:
                ci_str = f"[{ci_lower*100:.2f}%, {ci_upper*100:.2f}%]"
            elif currency:
                ci_str = f"[${ci_lower:.2f}, ${ci_upper:.2f}]"
            else:
                ci_str = f"[{ci_lower:.4f}, {ci_upper:.4f}]"
            conclusion_parts.append(f"The 95% confidence interval for the difference is {ci_str}.")
        
        conclusion_parts.append(
            f"\n✅ RECOMMENDATION: The treatment variant shows a significant improvement. "
            f"Consider implementing this change."
        )
    else:
        conclusion_parts.append(
            f"There was no statistically significant difference in {metric_name} between "
            f"the treatment and control groups (Treatment: {val_b_str} vs. Control: {val_a_str}, "
            f"p = {p_value:.4f})."
        )
        
        conclusion_parts.append(
            f"\n⚠️  RECOMMENDATION: The treatment variant did not show a significant effect. "
            f"Consider running the test longer or with a larger sample size, or abandon this variant."
        )
    
    conclusion_parts.append('='*70)
    
    return "\n".join(conclusion_parts)


def format_multi_metric_conclusion(results: dict, bonferroni_alpha: float = 0.0167) -> str:
    """
    Format conclusion for multi-metric A/B test with multiple comparison correction
    
    Args:
        results: Dictionary with results for each metric
        bonferroni_alpha: Adjusted alpha level after Bonferroni correction
    
    Returns:
        Professional conclusion statement for multi-metric test
    """
    conclusion_parts = []
    
    conclusion_parts.append(f"\n{'='*70}")
    conclusion_parts.append("MULTI-METRIC STATISTICAL CONCLUSION")
    conclusion_parts.append('='*70)
    conclusion_parts.append(
        f"Note: Bonferroni correction applied (α = {bonferroni_alpha:.4f}) "
        f"to control family-wise error rate across {len(results)} metrics."
    )
    conclusion_parts.append("")
    
    significant_metrics = []
    non_significant_metrics = []
    
    for metric_name, result in results.items():
        p_value = result.get('p_value')
        if p_value is not None and p_value < bonferroni_alpha:
            significant_metrics.append(metric_name)
        else:
            non_significant_metrics.append(metric_name)
    
    if significant_metrics:
        conclusion_parts.append(f"✅ SIGNIFICANT METRICS ({len(significant_metrics)}):")
        for metric in significant_metrics:
            conclusion_parts.append(f"   • {metric.replace('_', ' ').title()}")
        conclusion_parts.append("")
    
    if non_significant_metrics:
        conclusion_parts.append(f"⚠️  NON-SIGNIFICANT METRICS ({len(non_significant_metrics)}):")
        for metric in non_significant_metrics:
            conclusion_parts.append(f"   • {metric.replace('_', ' ').title()}")
        conclusion_parts.append("")
    
    # Overall recommendation
    if len(significant_metrics) >= len(results) / 2:
        conclusion_parts.append(
            "RECOMMENDATION: The treatment shows improvement on a majority of metrics. "
            "Strong evidence to implement this change."
        )
    elif len(significant_metrics) > 0:
        conclusion_parts.append(
            "RECOMMENDATION: The treatment shows mixed results. Review which metrics align "
            "with business goals before deciding whether to implement."
        )
    else:
        conclusion_parts.append(
            "RECOMMENDATION: No significant improvements detected across any metrics. "
            "Do not implement this change."
        )
    
    conclusion_parts.append('='*70)
    
    return "\n".join(conclusion_parts)
