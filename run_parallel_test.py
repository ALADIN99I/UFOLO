#!/usr/bin/env python3
"""
Run Parallel Test - Simple Execution Script
===========================================
This script runs the parallel test harness to compare simulator and live system outputs.
"""

import sys
import os
import datetime
import argparse

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Run parallel testing of simulator and live system')
    parser.add_argument('--cycles', type=int, default=5, 
                       help='Number of cycles to run (default: 5)')
    parser.add_argument('--duration', type=int, default=40, 
                       help='Duration of each cycle in minutes (default: 40)')
    parser.add_argument('--date', type=str, default='2025-08-01', 
                       help='Simulation date YYYY-MM-DD (default: 2025-08-01)')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick test with 3 cycles of 10 minutes each')
    
    args = parser.parse_args()
    
    # Override for quick test
    if args.quick:
        args.cycles = 3
        args.duration = 10
        print("🚀 Running QUICK TEST: 3 cycles, 10 minutes each")
    
    # Parse test date
    try:
        test_date = datetime.datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print(f"❌ Invalid date format: {args.date}. Use YYYY-MM-DD format.")
        sys.exit(1)
    
    print("="*60)
    print("PARALLEL TEST HARNESS")
    print("="*60)
    print(f"📅 Test Date: {test_date.strftime('%A, %B %d, %Y')}")
    print(f"🔄 Cycles: {args.cycles}")
    print(f"⏱️  Duration: {args.duration} minutes per cycle")
    print(f"⏰ Total Test Time: ~{args.cycles * args.duration} minutes")
    print("="*60)
    
    try:
        # Import the test harness
        from parallel_test_harness import ParallelTestHarness
        
        # Create test harness
        print("\n📋 Initializing test harness...")
        harness = ParallelTestHarness(
            config_path='config/config.ini',
            test_date=test_date
        )
        
        # Run the parallel test
        print("🚀 Starting parallel test...\n")
        results = harness.run_parallel_test(
            num_cycles=args.cycles,
            cycle_duration_minutes=args.duration
        )
        
        # Display results summary
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        
        summary = results['summary']
        
        # Alignment statistics
        print(f"\n📊 ALIGNMENT STATISTICS:")
        print(f"   Total Cycles: {summary['total_cycles']}")
        print(f"   Aligned: {summary['aligned_cycles']}")
        print(f"   Misaligned: {summary['misaligned_cycles']}")
        print(f"   Alignment Rate: {summary['alignment_rate']:.1f}%")
        
        # Difference categories
        if summary.get('difference_categories'):
            print(f"\n🔍 DIFFERENCE CATEGORIES:")
            for category, count in summary['difference_categories'].items():
                print(f"   - {category}: {count} cycles")
            if summary.get('most_common_difference'):
                print(f"   Most Common: {summary['most_common_difference']}")
        
        # Portfolio comparison
        if summary.get('final_portfolio_difference'):
            fpd = summary['final_portfolio_difference']
            print(f"\n💰 FINAL PORTFOLIO COMPARISON:")
            print(f"   Simulator: ${fpd['simulator']:,.2f}")
            print(f"   Live System: ${fpd['live']:,.2f}")
            print(f"   Difference: ${fpd['difference']:,.2f} ({fpd['percentage']:.2f}%)")
        
        # Overall assessment
        print(f"\n🎯 OVERALL ASSESSMENT:")
        if summary['alignment_rate'] == 100:
            print("   ✅ PERFECT ALIGNMENT - Systems are completely synchronized!")
            print("   All UFO calculations, trade decisions, and portfolio management are identical.")
        elif summary['alignment_rate'] >= 95:
            print("   ✅ EXCELLENT ALIGNMENT - Minor differences detected")
            print("   Systems are well-synchronized with only small discrepancies.")
        elif summary['alignment_rate'] >= 90:
            print("   ⚠️ GOOD ALIGNMENT - Some differences need investigation")
            print("   Systems are mostly aligned but have notable differences.")
        elif summary['alignment_rate'] >= 80:
            print("   ⚠️ MODERATE ALIGNMENT - Significant differences detected")
            print("   Systems show considerable divergence that requires attention.")
        else:
            print("   ❌ POOR ALIGNMENT - Major differences detected")
            print("   Systems are significantly out of sync and need immediate fixes.")
        
        # Recommendations
        print(f"\n📝 RECOMMENDATIONS:")
        if summary['alignment_rate'] < 100:
            print("   1. Review the detailed difference report for specific issues")
            print("   2. Check the log files for timing discrepancies")
            print("   3. Verify UFO calculations are using same data sources")
            print("   4. Ensure both systems have identical configuration")
            
            if 'ufo_scores' in summary.get('difference_categories', {}):
                print("   5. UFO score differences detected - check calculation methods")
            if 'positions' in summary.get('difference_categories', {}):
                print("   6. Position management differences - verify execution logic")
            if 'portfolio_metrics' in summary.get('difference_categories', {}):
                print("   7. Portfolio calculation differences - check P&L formulas")
        else:
            print("   ✅ No issues detected - systems are perfectly aligned!")
        
        print("\n" + "="*60)
        print("Test complete. Check the generated reports for full details.")
        print("="*60)
        
        return 0 if summary['alignment_rate'] >= 90 else 1
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required modules are installed.")
        return 1
    except FileNotFoundError as e:
        print(f"❌ Configuration file not found: {e}")
        print("Make sure config/config.ini exists.")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
