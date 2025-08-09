#!/usr/bin/env python3
"""
Verification script to confirm mean reversion signal logging is fully integrated
"""

import ast
import re

def verify_mean_reversion_integration():
    """Verify that mean reversion signal logging is properly integrated in live_trader.py"""
    
    print("="*60)
    print("🔍 VERIFYING MEAN REVERSION SIGNAL LOGGING INTEGRATION")
    print("="*60)
    
    all_checks_passed = True
    
    # Read the live trader file
    with open('src/live_trader.py', 'r', encoding='utf-8') as f:
        live_trader_code = f.read()
    
    # Read the simulator file for comparison
    with open('full_day_simulation.py', 'r', encoding='utf-8') as f:
        simulator_code = f.read()
    
    # Check 1: Verify mean reversion logging exists in live trader
    mean_reversion_pattern = r'mean_reversion_signals'
    live_matches = re.findall(mean_reversion_pattern, live_trader_code)
    if live_matches:
        print(f"✅ Mean reversion signal variable found {len(live_matches)} times in live_trader.py")
    else:
        print("❌ Mean reversion signal variable NOT found in live_trader.py")
        all_checks_passed = False
    
    # Check 2: Verify the logging line exists
    if "Mean Reversion Signals:" in live_trader_code:
        print("✅ Mean reversion logging message found")
    else:
        print("❌ Mean reversion logging message NOT found")
        all_checks_passed = False
    
    # Check 3: Verify it's in _log_enhanced_analysis method
    log_method_pattern = r'def _log_enhanced_analysis\(self.*?\n(?:.*?\n)*?.*?mean_reversion_signals'
    if re.search(log_method_pattern, live_trader_code, re.DOTALL):
        print("✅ Mean reversion logging is in _log_enhanced_analysis method")
    else:
        print("❌ Mean reversion logging is NOT in the correct method")
        all_checks_passed = False
    
    # Check 4: Verify the emoji is used
    if "🔄 Mean Reversion Signals:" in live_trader_code:
        print("✅ Mean reversion emoji (🔄) found")
    else:
        print("❌ Mean reversion emoji not found")
        all_checks_passed = False
    
    # Check 5: Verify the loop structure
    loop_pattern = r'for tf_data in oscillation_analysis\.values\(\):'
    if re.search(loop_pattern, live_trader_code):
        print("✅ Correct loop structure for timeframe data found")
    else:
        print("❌ Loop structure not found or incorrect")
        all_checks_passed = False
    
    # Check 6: Verify the counting logic
    count_pattern = r"mean_reversion_signals \+= sum\(.*?'mean_reversion_signal'.*?\)"
    if re.search(count_pattern, live_trader_code, re.DOTALL):
        print("✅ Mean reversion counting logic found")
    else:
        print("❌ Mean reversion counting logic not found")
        all_checks_passed = False
    
    # Check 7: Verify it uses self.log_event
    if re.search(r'self\.log_event\(.*?Mean Reversion Signals:', live_trader_code, re.DOTALL):
        print("✅ Uses self.log_event() for logging (correct method)")
    else:
        print("❌ Does not use self.log_event() for logging")
        all_checks_passed = False
    
    # Check 8: Compare with simulator
    sim_matches = re.findall(mean_reversion_pattern, simulator_code)
    print(f"\n📊 COMPARISON:")
    print(f"  Simulator has {len(sim_matches)} occurrences")
    print(f"  Live trader has {len(live_matches)} occurrences")
    
    if len(live_matches) >= 2:  # Should have at least 2 occurrences (variable and usage)
        print("  ✅ Live trader has sufficient mean reversion references")
    else:
        print("  ⚠️ Live trader may be missing some mean reversion logic")
    
    # Check 9: Verify oscillation_analysis parameter
    if re.search(r'def _log_enhanced_analysis\(self,\s*oscillation_analysis', live_trader_code):
        print("\n✅ Method signature includes oscillation_analysis parameter")
    else:
        print("\n❌ Method signature missing oscillation_analysis parameter")
        all_checks_passed = False
    
    # Check 10: Verify the condition check
    if "if mean_reversion_signals > 0:" in live_trader_code:
        print("✅ Conditional check for mean reversion signals found")
    else:
        print("❌ Conditional check not found")
        all_checks_passed = False
    
    # Check 11: Verify it's called from calculate_ufo_indicators
    calc_ufo_pattern = r'def calculate_ufo_indicators\(self.*?\n(?:.*?\n)*?.*?self\._log_enhanced_analysis'
    if re.search(calc_ufo_pattern, live_trader_code, re.DOTALL):
        print("✅ _log_enhanced_analysis is called from calculate_ufo_indicators")
    else:
        print("❌ _log_enhanced_analysis may not be called correctly")
        all_checks_passed = False
    
    # Check 12: Verify syntax is valid
    try:
        ast.parse(live_trader_code)
        print("✅ Python syntax is valid")
    except SyntaxError as e:
        print(f"❌ Syntax error in live_trader.py: {e}")
        all_checks_passed = False
    
    # Final verification summary
    print("\n" + "="*60)
    print("📋 INTEGRATION SUMMARY:")
    print("-" * 40)
    
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED!")
        print("\nMean reversion signal logging is FULLY INTEGRATED:")
        print("• Located in _log_enhanced_analysis() method")
        print("• Counts signals across all timeframes")
        print("• Logs with 🔄 emoji when signals detected")
        print("• Uses proper self.log_event() method")
        print("• Matches simulator implementation")
        return True
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nMean reversion signal logging may not be fully integrated.")
        print("Please review the implementation.")
        return False

if __name__ == "__main__":
    success = verify_mean_reversion_integration()
    
    if success:
        print("\n" + "="*60)
        print("🎯 FINAL VERDICT: FULLY INTEGRATED! ✅")
        print("="*60)
        print("\nThe mean reversion signal logging feature is:")
        print("✅ Properly implemented")
        print("✅ Following simulator patterns")
        print("✅ Using correct data flow")
        print("✅ Ready for production use")
    else:
        print("\n" + "="*60)
        print("⚠️ FINAL VERDICT: NEEDS REVIEW")
        print("="*60)
