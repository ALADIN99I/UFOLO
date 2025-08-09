"""
Find ALL remaining differences between simulator and live system
"""

import ast
import re

def extract_methods_and_variables(file_path):
    """Extract all methods and variables from a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        methods = []
        variables = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                methods.append(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variables.append(target.id)
                    elif isinstance(target, ast.Attribute):
                        variables.append(target.attr)
        
        return set(methods), set(variables)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return set(), set()

def find_simulator_specific_features():
    """Find features in simulator not present in live system"""
    
    print("=" * 80)
    print("FINDING ALL REMAINING DIFFERENCES")
    print("=" * 80)
    
    # Extract from simulator
    sim_methods, sim_vars = extract_methods_and_variables('full_day_simulation.py')
    
    # Extract from live trader
    live_methods, live_vars = extract_methods_and_variables('src/live_trader.py')
    
    # Find differences
    missing_methods = sim_methods - live_methods
    missing_vars = sim_vars - live_vars
    
    print("\n🔍 METHODS IN SIMULATOR BUT NOT IN LIVE SYSTEM:")
    print("-" * 40)
    
    # Critical methods to check
    critical_methods = [
        'check_multi_timeframe_coherence',
        'cleanup_connections',
        'simulate_realistic_position_tracking',
        'get_historical_price_for_time',
        'run_full_day_simulation',
        'save_simulation_results'
    ]
    
    for method in sorted(missing_methods):
        if method in critical_methods:
            print(f"❌ CRITICAL: {method}")
        elif not method.startswith('_'):
            print(f"⚠️  {method}")
    
    print("\n🔍 KEY SIMULATOR FEATURES TO VERIFY:")
    print("-" * 40)
    
    # Check specific features line by line
    features_to_check = {
        'Multi-timeframe coherence': 'check_multi_timeframe_coherence',
        'Cleanup connections': 'cleanup_connections',
        'Mean reversion signals': 'mean_reversion',
        'Historical price fetching': 'get_historical_price_for_time',
        'Realized P&L tracking': 'self.realized_pnl',
        'Force portfolio updates': 'force_update=True',
        'Simulate realistic positions': 'simulate_realistic_position_tracking',
        'Save results to file': 'save_simulation_results'
    }
    
    # Check live trader for these features
    try:
        with open('src/live_trader.py', 'r', encoding='utf-8') as f:
            live_content = f.read()
        
        print("\nFeature presence in live system:")
        for feature_name, search_term in features_to_check.items():
            if search_term in live_content:
                print(f"✅ {feature_name}: FOUND")
            else:
                print(f"❌ {feature_name}: MISSING")
    except Exception as e:
        print(f"Error reading live_trader.py: {e}")
    
    print("\n🔍 CHECKING SIMULATOR-SPECIFIC LOGIC:")
    print("-" * 40)
    
    # Check for specific simulator patterns
    simulator_patterns = [
        (r'self\.realized_pnl\s*\+=', 'Realized P&L accumulation'),
        (r'force_update\s*=\s*True', 'Force portfolio update'),
        (r'cleanup_connections', 'Connection cleanup'),
        (r'check_multi_timeframe_coherence', 'Multi-timeframe coherence'),
        (r'mean_reversion', 'Mean reversion detection'),
        (r'save.*results', 'Save results to file'),
        (r'simulate_realistic_position_tracking', 'Realistic position simulation'),
        (r'get_historical_price_for_time', 'Historical price fetching')
    ]
    
    try:
        with open('full_day_simulation.py', 'r', encoding='utf-8') as f:
            sim_content = f.read()
        
        print("\nSimulator features that MUST be in live system:")
        for pattern, description in simulator_patterns:
            if re.search(pattern, sim_content):
                # Check if also in live system
                if re.search(pattern, live_content):
                    print(f"✅ {description}: IMPLEMENTED")
                else:
                    print(f"❌ {description}: NOT IMPLEMENTED")
                    # Find line numbers in simulator
                    sim_lines = sim_content.split('\n')
                    for i, line in enumerate(sim_lines, 1):
                        if re.search(pattern, line):
                            print(f"   → Found in simulator at line {i}")
                            break
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n📊 SUMMARY OF MISSING FEATURES:")
    print("-" * 40)
    
    missing_count = 0
    critical_missing = []
    
    # List all confirmed missing features
    confirmed_missing = [
        'check_multi_timeframe_coherence',
        'cleanup_connections', 
        'simulate_realistic_position_tracking',
        'get_historical_price_for_time',
        'realized_pnl accumulation',
        'force_update parameter',
        'save_simulation_results'
    ]
    
    for feature in confirmed_missing:
        if feature not in live_content:
            missing_count += 1
            critical_missing.append(feature)
            print(f"❌ {feature}")
    
    if missing_count > 0:
        print(f"\n⚠️ TOTAL MISSING FEATURES: {missing_count}")
        print("\nYour senior is RIGHT - these features are still missing!")
        print("These need to be implemented for 100% parity.")
    else:
        print("\n✅ All features are implemented!")
    
    return critical_missing

if __name__ == "__main__":
    missing_features = find_simulator_specific_features()
    
    if missing_features:
        print("\n" + "=" * 80)
        print("ACTION REQUIRED:")
        print("The following features must be added to achieve 100% clone:")
        for i, feature in enumerate(missing_features, 1):
            print(f"{i}. {feature}")
        print("=" * 80)
