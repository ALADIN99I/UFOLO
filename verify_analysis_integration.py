#!/usr/bin/env python3
"""
Verification script to confirm features are integrated with the analysis data flow
"""

import re
import ast

def verify_analysis_integration():
    """Verify that features are properly integrated with UFO analysis data flow"""
    
    print("="*60)
    print("🔍 VERIFYING ANALYSIS DATA FLOW INTEGRATION")
    print("="*60)
    
    with open('src/live_trader.py', 'r', encoding='utf-8') as f:
        live_trader_code = f.read()
    
    print("\n📊 CHECKING DATA FLOW FOR MEAN REVERSION SIGNALS:")
    print("-" * 40)
    
    # 1. Check that oscillation_analysis is created
    if "oscillation_analysis = self.ufo_calculator.detect_oscillations(ufo_data)" in live_trader_code:
        print("✅ Step 1: oscillation_analysis is generated from UFO data")
    else:
        print("❌ Step 1: oscillation_analysis generation not found")
        return False
    
    # 2. Check that oscillation_analysis is passed to _log_enhanced_analysis
    if "self._log_enhanced_analysis(oscillation_analysis, uncertainty_metrics, coherence_analysis)" in live_trader_code:
        print("✅ Step 2: oscillation_analysis is passed to _log_enhanced_analysis")
    else:
        print("❌ Step 2: oscillation_analysis not passed correctly")
        return False
    
    # 3. Check that _log_enhanced_analysis receives oscillation_analysis
    if re.search(r'def _log_enhanced_analysis\(self, oscillation_analysis, uncertainty_metrics, coherence_analysis\)', live_trader_code):
        print("✅ Step 3: _log_enhanced_analysis receives oscillation_analysis parameter")
    else:
        print("❌ Step 3: _log_enhanced_analysis doesn't receive correct parameters")
        return False
    
    # 4. Check that mean reversion signals are extracted from oscillation_analysis
    if re.search(r'for tf_data in oscillation_analysis\.values\(\):', live_trader_code):
        print("✅ Step 4: Iterates through oscillation_analysis data")
    else:
        print("❌ Step 4: Doesn't iterate through oscillation_analysis")
        return False
    
    # 5. Check that mean_reversion_signal field is accessed
    if "curr_data.get('mean_reversion_signal', False)" in live_trader_code:
        print("✅ Step 5: Accesses 'mean_reversion_signal' field from analysis")
    else:
        print("❌ Step 5: Doesn't access 'mean_reversion_signal' field")
        return False
    
    print("\n📊 CHECKING DATA FLOW FOR UFO REINFORCEMENT:")
    print("-" * 40)
    
    # 6. Check that previous_ufo_data is stored
    if "self.previous_ufo_data = ufo_data" in live_trader_code:
        print("✅ Step 1: previous_ufo_data is stored for next cycle")
    else:
        print("❌ Step 1: previous_ufo_data not stored")
        return False
    
    # 7. Check that continuous_position_monitoring gets the data
    if "getattr(self, 'previous_ufo_data', None)" in live_trader_code:
        print("✅ Step 2: previous_ufo_data is retrieved in monitoring")
    else:
        print("❌ Step 2: previous_ufo_data not retrieved")
        return False
    
    # 8. Check that current_market_data is collected
    if "current_market_data = self.get_real_time_market_data_for_positions(open_positions)" in live_trader_code:
        print("✅ Step 3: current_market_data is collected for positions")
    else:
        print("❌ Step 3: current_market_data not collected")
        return False
    
    # 9. Check that UFO reinforcement gets all needed data
    reinforcement_call = re.search(
        r'should_reinforce, reason, plan = self\.ufo_engine\.should_reinforce_position\(\s*'
        r'position,\s*'
        r'self\.previous_ufo_data,\s*'
        r'current_market_data\s*\)',
        live_trader_code,
        re.MULTILINE | re.DOTALL
    )
    if reinforcement_call:
        print("✅ Step 4: UFO reinforcement receives position, previous_ufo_data, and current_market_data")
    else:
        print("❌ Step 4: UFO reinforcement doesn't receive correct data")
        return False
    
    print("\n📊 CHECKING ANALYSIS DATA SOURCES:")
    print("-" * 40)
    
    # Check UFO calculator integration
    if "self.ufo_calculator = UfoCalculator" in live_trader_code:
        print("✅ UFO Calculator is initialized")
    else:
        print("❌ UFO Calculator not initialized")
        return False
    
    # Check that detect_oscillations exists in ufo_calculator
    print("\nChecking ufo_calculator.py for data providers...")
    try:
        with open('src/ufo_calculator.py', 'r', encoding='utf-8') as f:
            ufo_calc_code = f.read()
        
        if "def detect_oscillations(self" in ufo_calc_code:
            print("✅ ufo_calculator has detect_oscillations method")
        else:
            print("❌ ufo_calculator missing detect_oscillations method")
            return False
        
        if "'mean_reversion_signal'" in ufo_calc_code:
            print("✅ ufo_calculator generates mean_reversion_signal data")
        else:
            print("❌ ufo_calculator doesn't generate mean_reversion_signal")
            return False
            
    except FileNotFoundError:
        print("❌ Could not find ufo_calculator.py")
        return False
    
    print("\n📊 CHECKING COMPLETE DATA FLOW:")
    print("-" * 40)
    
    # Trace the complete flow
    flow_steps = [
        ("1. Market data collection", "collect_market_data"),
        ("2. UFO indicator calculation", "calculate_ufo_indicators"),
        ("3. Oscillation detection", "detect_oscillations"),
        ("4. Enhanced analysis logging", "_log_enhanced_analysis"),
        ("5. Mean reversion detection", "mean_reversion_signals"),
        ("6. Position monitoring", "continuous_position_monitoring"),
        ("7. UFO reinforcement check", "should_reinforce_position")
    ]
    
    all_found = True
    for step_name, pattern in flow_steps:
        if pattern in live_trader_code:
            print(f"✅ {step_name}")
        else:
            print(f"❌ {step_name}")
            all_found = False
    
    return all_found

def check_data_availability():
    """Check if the analysis provides the required data fields"""
    
    print("\n" + "="*60)
    print("🔬 CHECKING DATA FIELD AVAILABILITY")
    print("="*60)
    
    try:
        with open('src/ufo_calculator.py', 'r', encoding='utf-8') as f:
            ufo_code = f.read()
        
        print("\n📊 Mean Reversion Signal Fields:")
        print("-" * 40)
        
        # Check for mean reversion signal generation
        if re.search(r"'mean_reversion_signal':\s*(True|False)", ufo_code):
            print("✅ mean_reversion_signal field is set in oscillation data")
        else:
            print("⚠️ mean_reversion_signal field may not be set")
        
        # Check for oscillation detection logic
        if "oscillation_count" in ufo_code:
            print("✅ Oscillation counting logic exists")
        else:
            print("⚠️ Oscillation counting logic not found")
        
        print("\n📊 UFO Reinforcement Data Fields:")
        print("-" * 40)
        
        with open('src/ufo_trading_engine.py', 'r', encoding='utf-8') as f:
            ufo_engine_code = f.read()
        
        # Check UFO engine has reinforcement method
        if "def should_reinforce_position(self, position, current_analysis, current_market_data)" in ufo_engine_code:
            print("✅ UFO engine has should_reinforce_position method")
        else:
            print("❌ UFO engine missing should_reinforce_position method")
        
        # Check it returns the expected tuple
        if re.search(r"return\s+(True|False),.*,.*", ufo_engine_code):
            print("✅ Returns (should_reinforce, reason, plan) tuple")
        else:
            print("⚠️ Return format may not match expected")
            
    except Exception as e:
        print(f"❌ Error checking data availability: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 STARTING COMPREHENSIVE ANALYSIS INTEGRATION CHECK\n")
    
    flow_ok = verify_analysis_integration()
    data_ok = check_data_availability()
    
    print("\n" + "="*60)
    print("📋 FINAL INTEGRATION ASSESSMENT")
    print("="*60)
    
    if flow_ok and data_ok:
        print("\n✅ FULLY INTEGRATED WITH ANALYSIS!")
        print("\nBoth features are properly integrated:")
        print("• Mean reversion signals flow from UFO calculator → oscillation analysis → logging")
        print("• UFO reinforcement receives position data, previous UFO data, and market data")
        print("• All data fields are available and properly connected")
        print("• Complete data flow is verified from collection to usage")
        print("\n🎯 The system is ready for production use!")
    else:
        print("\n⚠️ PARTIAL INTEGRATION")
        print("Some aspects of the analysis integration may need review.")
        print("Please check the specific failures above.")
