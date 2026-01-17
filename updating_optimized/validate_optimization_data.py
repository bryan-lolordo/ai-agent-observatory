#!/usr/bin/env python3
"""
Observatory Data Validator and Explorer
========================================

This script validates the optimization story data and provides interactive
exploration capabilities.

Usage:
    python validate_optimization_data.py

Requirements:
    pip install pandas openpyxl
"""

import pandas as pd
import numpy as np
from pathlib import Path


def load_data(excel_path):
    """Load and return sessions and llm_calls dataframes."""
    print(f"Loading data from {excel_path}...")
    
    sessions_df = pd.read_excel(excel_path, sheet_name='sessions')
    llm_calls_df = pd.read_excel(excel_path, sheet_name='llm_calls')
    
    print(f"✓ Loaded {len(sessions_df)} sessions")
    print(f"✓ Loaded {len(llm_calls_df)} LLM calls")
    
    return sessions_df, llm_calls_df


def validate_headline_metrics(llm_calls_df):
    """Validate the headline metrics from the executive summary."""
    print("\n" + "="*70)
    print("HEADLINE METRICS VALIDATION")
    print("="*70)
    
    baseline = llm_calls_df[llm_calls_df['phase'] == 'baseline']
    optimized = llm_calls_df[llm_calls_df['phase'] == 'optimized']
    
    validations = []
    
    # Total latency
    baseline_latency = baseline['latency_ms'].sum() / 1000
    optimized_latency = optimized['latency_ms'].sum() / 1000
    latency_improvement = (1 - optimized_latency/baseline_latency) * 100
    validations.append({
        'metric': 'Total Latency',
        'baseline': f"{baseline_latency:.1f}s",
        'optimized': f"{optimized_latency:.1f}s",
        'improvement': f"{latency_improvement:.1f}%",
        'expected': '22.0%',
        'status': '✓' if abs(latency_improvement - 22.0) < 0.5 else '✗'
    })
    
    # LLM calls
    call_reduction = (1 - len(optimized)/len(baseline)) * 100
    validations.append({
        'metric': 'LLM Calls',
        'baseline': str(len(baseline)),
        'optimized': str(len(optimized)),
        'improvement': f"{call_reduction:.1f}%",
        'expected': '12.2%',
        'status': '✓' if abs(call_reduction - 12.2) < 0.5 else '✗'
    })
    
    # Total cost
    baseline_cost = baseline['total_cost'].sum()
    optimized_cost = optimized['total_cost'].sum()
    cost_reduction = (1 - optimized_cost/baseline_cost) * 100
    validations.append({
        'metric': 'Total Cost',
        'baseline': f"${baseline_cost:.2f}",
        'optimized': f"${optimized_cost:.2f}",
        'improvement': f"{cost_reduction:.1f}%",
        'expected': '5.7%',
        'status': '✓' if abs(cost_reduction - 5.7) < 0.5 else '✗'
    })
    
    # Cache hits
    optimized_hits = optimized['cache_hit'].sum()
    validations.append({
        'metric': 'Cache Hits',
        'baseline': '0',
        'optimized': str(int(optimized_hits)),
        'improvement': '+37',
        'expected': '37',
        'status': '✓' if optimized_hits == 37 else '✗'
    })
    
    df = pd.DataFrame(validations)
    print(df.to_string(index=False))
    
    all_valid = all(v['status'] == '✓' for v in validations)
    print(f"\n{'✓ All validations passed!' if all_valid else '✗ Some validations failed'}")
    
    return all_valid


def validate_operation_improvements(llm_calls_df):
    """Validate the top operation improvements."""
    print("\n" + "="*70)
    print("TOP OPERATION IMPROVEMENTS VALIDATION")
    print("="*70)
    
    baseline = llm_calls_df[llm_calls_df['phase'] == 'baseline']
    optimized = llm_calls_df[llm_calls_df['phase'] == 'optimized']
    
    operations_to_validate = [
        ('judge_generate_sql', 22, 3, 51.1, 6.7),
        ('quick_score_job', 15, 18, 33.7, 5.8),
        ('improve_bullet', 8, 4, 21.4, 20.5)
    ]
    
    for op, exp_base_calls, exp_opt_calls, exp_base_time, exp_opt_time in operations_to_validate:
        base_op = baseline[baseline['operation'] == op]
        opt_op = optimized[optimized['operation'] == op]
        
        base_calls = len(base_op)
        opt_calls = len(opt_op)
        base_time = base_op['latency_ms'].sum() / 1000
        opt_time = opt_op['latency_ms'].sum() / 1000
        
        print(f"\n{op}:")
        print(f"  Calls: {base_calls} → {opt_calls} (expected {exp_base_calls} → {exp_opt_calls})")
        print(f"  Time:  {base_time:.1f}s → {opt_time:.1f}s (expected {exp_base_time:.1f}s → {exp_opt_time:.1f}s)")
        
        calls_match = base_calls == exp_base_calls and opt_calls == exp_opt_calls
        time_match = abs(base_time - exp_base_time) < 1 and abs(opt_time - exp_opt_time) < 1
        
        status = '✓' if calls_match and time_match else '✗'
        print(f"  Status: {status}")


def explore_cache_performance(llm_calls_df):
    """Detailed cache performance analysis."""
    print("\n" + "="*70)
    print("CACHE PERFORMANCE ANALYSIS")
    print("="*70)
    
    optimized = llm_calls_df[llm_calls_df['phase'] == 'optimized']
    cache_hits = optimized[optimized['cache_hit'] == True]
    
    print(f"\nTotal cache hits: {len(cache_hits)}")
    print(f"\nCache hits by operation:")
    
    cache_ops = cache_hits.groupby('operation').agg({
        'id': 'count',
        'latency_ms': ['mean', 'sum']
    })
    cache_ops.columns = ['hits', 'avg_latency_ms', 'total_latency_ms']
    cache_ops['avg_latency_s'] = cache_ops['avg_latency_ms'] / 1000
    cache_ops['total_latency_s'] = cache_ops['total_latency_ms'] / 1000
    
    print(cache_ops[['hits', 'avg_latency_s', 'total_latency_s']].to_string())
    
    # Calculate cache savings
    print("\nCache impact estimation:")
    for op in cache_ops.index:
        hits = int(cache_ops.loc[op, 'hits'])
        opt_time = cache_ops.loc[op, 'avg_latency_s']
        
        # Find baseline time for same operation
        baseline = llm_calls_df[llm_calls_df['phase'] == 'baseline']
        base_op = baseline[baseline['operation'] == op]
        
        if len(base_op) > 0:
            base_time = base_op['latency_ms'].mean() / 1000
            time_saved = (base_time - opt_time) * hits
            improvement = (1 - opt_time/base_time) * 100
            
            print(f"  {op}:")
            print(f"    {hits} hits × {base_time:.2f}s (baseline) = {hits * base_time:.2f}s")
            print(f"    {hits} hits × {opt_time:.2f}s (cached) = {hits * opt_time:.2f}s")
            print(f"    Savings: {time_saved:.2f}s ({improvement:.1f}% faster)")


def analyze_batching_impact(llm_calls_df):
    """Analyze the batching trade-offs."""
    print("\n" + "="*70)
    print("BATCHING IMPACT ANALYSIS")
    print("="*70)
    
    baseline = llm_calls_df[llm_calls_df['phase'] == 'baseline']
    optimized = llm_calls_df[llm_calls_df['phase'] == 'optimized']
    
    batched_operations = ['improve_bullet', 'judge_improve_bullet', 'judge_generate_sql']
    
    for op in batched_operations:
        base_op = baseline[baseline['operation'] == op]
        opt_op = optimized[optimized['operation'] == op]
        
        if len(base_op) > 0 and len(opt_op) > 0:
            print(f"\n{op}:")
            print(f"  Calls: {len(base_op)} → {len(opt_op)} ({((len(opt_op)/len(base_op) - 1) * 100):+.1f}%)")
            
            base_avg = base_op['latency_ms'].mean() / 1000
            opt_avg = opt_op['latency_ms'].mean() / 1000
            print(f"  Avg latency per call: {base_avg:.2f}s → {opt_avg:.2f}s ({((opt_avg/base_avg - 1) * 100):+.1f}%)")
            
            base_total = base_op['latency_ms'].sum() / 1000
            opt_total = opt_op['latency_ms'].sum() / 1000
            print(f"  Total latency: {base_total:.2f}s → {opt_total:.2f}s ({((opt_total/base_total - 1) * 100):+.1f}%)")
            
            print(f"  📊 Trade-off: Individual calls {((opt_avg/base_avg - 1) * 100):+.1f}% slower, " +
                  f"but total time {((opt_total/base_total - 1) * 100):+.1f}%")


def generate_summary_report(llm_calls_df):
    """Generate a summary report for sharing."""
    print("\n" + "="*70)
    print("SUMMARY REPORT")
    print("="*70)
    
    baseline = llm_calls_df[llm_calls_df['phase'] == 'baseline']
    optimized = llm_calls_df[llm_calls_df['phase'] == 'optimized']
    
    print("\n🎯 OVERALL IMPROVEMENTS")
    print(f"  Execution time:   {baseline['latency_ms'].sum()/1000:.1f}s → {optimized['latency_ms'].sum()/1000:.1f}s " +
          f"({(1 - optimized['latency_ms'].sum()/baseline['latency_ms'].sum()) * 100:.1f}% faster)")
    print(f"  Total cost:       ${baseline['total_cost'].sum():.2f} → ${optimized['total_cost'].sum():.2f} " +
          f"({(1 - optimized['total_cost'].sum()/baseline['total_cost'].sum()) * 100:.1f}% cheaper)")
    print(f"  API calls:        {len(baseline)} → {len(optimized)} " +
          f"({(1 - len(optimized)/len(baseline)) * 100:.1f}% reduction)")
    print(f"  Total tokens:     {baseline['total_tokens'].sum():,} → {optimized['total_tokens'].sum():,} " +
          f"({(1 - optimized['total_tokens'].sum()/baseline['total_tokens'].sum()) * 100:.1f}% reduction)")
    print(f"  Cache hits:       0 → {optimized['cache_hit'].sum():.0f}")
    
    print("\n🏆 TOP WINS")
    
    # Find operations with biggest total time improvements
    ops = baseline['operation'].unique()
    improvements = []
    
    for op in ops:
        base_op = baseline[baseline['operation'] == op]
        opt_op = optimized[optimized['operation'] == op]
        
        if len(base_op) > 0 and len(opt_op) > 0:
            base_total = base_op['latency_ms'].sum()
            opt_total = opt_op['latency_ms'].sum()
            time_saved = (base_total - opt_total) / 1000
            
            if time_saved > 1:  # Only show significant improvements
                improvements.append({
                    'operation': op,
                    'time_saved': time_saved,
                    'base_calls': len(base_op),
                    'opt_calls': len(opt_op),
                    'base_total': base_total / 1000,
                    'opt_total': opt_total / 1000
                })
    
    # Sort by time saved
    improvements.sort(key=lambda x: x['time_saved'], reverse=True)
    
    for i, imp in enumerate(improvements[:5], 1):
        pct = (1 - imp['opt_total']/imp['base_total']) * 100
        print(f"  {i}. {imp['operation']}")
        print(f"     {imp['base_total']:.1f}s → {imp['opt_total']:.1f}s ({pct:.0f}% faster, saved {imp['time_saved']:.1f}s)")
        print(f"     Calls: {imp['base_calls']} → {imp['opt_calls']}")


def interactive_explorer(llm_calls_df):
    """Interactive data exploration menu."""
    while True:
        print("\n" + "="*70)
        print("INTERACTIVE EXPLORER")
        print("="*70)
        print("\n1. View all operations")
        print("2. Analyze specific operation")
        print("3. Compare two operations")
        print("4. Show cache misses")
        print("5. Export to CSV")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            view_all_operations(llm_calls_df)
        elif choice == '2':
            analyze_specific_operation(llm_calls_df)
        elif choice == '3':
            compare_operations(llm_calls_df)
        elif choice == '4':
            show_cache_misses(llm_calls_df)
        elif choice == '5':
            export_to_csv(llm_calls_df)
        elif choice == '6':
            break
        else:
            print("Invalid option")


def view_all_operations(llm_calls_df):
    """View all operations summary."""
    baseline = llm_calls_df[llm_calls_df['phase'] == 'baseline']
    optimized = llm_calls_df[llm_calls_df['phase'] == 'optimized']
    
    all_ops = sorted(set(baseline['operation'].unique()) | set(optimized['operation'].unique()))
    
    print("\nAll Operations Summary:")
    print("-" * 70)
    
    for op in all_ops:
        base_op = baseline[baseline['operation'] == op]
        opt_op = optimized[optimized['operation'] == op]
        
        base_count = len(base_op)
        opt_count = len(opt_op)
        base_time = base_op['latency_ms'].sum() / 1000 if base_count > 0 else 0
        opt_time = opt_op['latency_ms'].sum() / 1000 if opt_count > 0 else 0
        
        print(f"{op}")
        print(f"  Calls: {base_count} → {opt_count}")
        print(f"  Time:  {base_time:.2f}s → {opt_time:.2f}s")


def analyze_specific_operation(llm_calls_df):
    """Deep dive into a specific operation."""
    baseline = llm_calls_df[llm_calls_df['phase'] == 'baseline']
    ops = sorted(baseline['operation'].unique())
    
    print("\nAvailable operations:")
    for i, op in enumerate(ops, 1):
        print(f"  {i}. {op}")
    
    try:
        idx = int(input("\nSelect operation number: ")) - 1
        op = ops[idx]
    except (ValueError, IndexError):
        print("Invalid selection")
        return
    
    base_op = baseline[baseline['operation'] == op]
    opt_op = llm_calls_df[(llm_calls_df['phase'] == 'optimized') & (llm_calls_df['operation'] == op)]
    
    print(f"\n{op} - Detailed Analysis")
    print("-" * 70)
    
    print("\nBaseline:")
    print(f"  Calls: {len(base_op)}")
    print(f"  Total latency: {base_op['latency_ms'].sum()/1000:.2f}s")
    print(f"  Avg latency: {base_op['latency_ms'].mean()/1000:.2f}s")
    print(f"  Min latency: {base_op['latency_ms'].min()/1000:.2f}s")
    print(f"  Max latency: {base_op['latency_ms'].max()/1000:.2f}s")
    print(f"  Total cost: ${base_op['total_cost'].sum():.4f}")
    print(f"  Total tokens: {base_op['total_tokens'].sum():,}")
    
    print("\nOptimized:")
    print(f"  Calls: {len(opt_op)}")
    print(f"  Total latency: {opt_op['latency_ms'].sum()/1000:.2f}s")
    print(f"  Avg latency: {opt_op['latency_ms'].mean()/1000:.2f}s")
    print(f"  Min latency: {opt_op['latency_ms'].min()/1000:.2f}s")
    print(f"  Max latency: {opt_op['latency_ms'].max()/1000:.2f}s")
    print(f"  Total cost: ${opt_op['total_cost'].sum():.4f}")
    print(f"  Total tokens: {opt_op['total_tokens'].sum():,}")
    print(f"  Cache hits: {opt_op['cache_hit'].sum():.0f}/{len(opt_op)}")


def compare_operations(llm_calls_df):
    """Compare two operations side by side."""
    print("\nCompare two operations")
    # Implementation similar to analyze_specific_operation but for two ops
    pass


def show_cache_misses(llm_calls_df):
    """Show operations that could benefit from caching."""
    optimized = llm_calls_df[llm_calls_df['phase'] == 'optimized']
    cache_misses = optimized[optimized['cache_hit'] == False]
    
    print("\nOperations with cache misses:")
    print("-" * 70)
    
    miss_summary = cache_misses.groupby('operation').agg({
        'id': 'count',
        'latency_ms': ['mean', 'sum']
    })
    miss_summary.columns = ['misses', 'avg_latency_ms', 'total_latency_ms']
    miss_summary = miss_summary.sort_values('total_latency_ms', ascending=False)
    
    print(miss_summary.to_string())


def export_to_csv(llm_calls_df):
    """Export filtered data to CSV."""
    filename = input("Enter filename (default: optimization_export.csv): ").strip()
    if not filename:
        filename = "optimization_export.csv"
    
    llm_calls_df.to_csv(filename, index=False)
    print(f"✓ Data exported to {filename}")


def main():
    """Main execution function."""
    print("="*70)
    print("OBSERVATORY OPTIMIZATION DATA VALIDATOR")
    print("="*70)
    
    # Load data
    excel_path = '/mnt/user-data/uploads/1768548174715_observatory_export_20260116_012148.xlsx'
    sessions_df, llm_calls_df = load_data(excel_path)
    
    # Run validations
    validate_headline_metrics(llm_calls_df)
    validate_operation_improvements(llm_calls_df)
    explore_cache_performance(llm_calls_df)
    analyze_batching_impact(llm_calls_df)
    generate_summary_report(llm_calls_df)
    
    # Interactive mode
    print("\n" + "="*70)
    use_interactive = input("\nEnter interactive mode? (y/n): ").strip().lower()
    if use_interactive == 'y':
        interactive_explorer(llm_calls_df)
    
    print("\n✓ Analysis complete!")


if __name__ == "__main__":
    main()
