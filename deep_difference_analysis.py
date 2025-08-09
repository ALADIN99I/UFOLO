"""
Deep analysis to find ALL remaining differences between simulator and live system
"""

import re
import ast

def deep_analyze_differences():
    print("=" * 80)
    print("DEEP ANALYSIS: FINDING ALL REMAINING DIFFERENCES")
    print("=" * 80)
    
    # Read both files
    with open('full_day_simulation.py', 'r', encoding='utf-8') as f:
        sim_content = f.read()
    
    with open('src/live_trader.py', 'r', encoding='utf-8') as f:
        live_content = f.read()
    
    # 1. CHECK ECONOMIC EVENTS PROCESSING
    print("\n1. ECONOMIC EVENTS PROCESSING:")
    print("-" * 40)
    
    economic_patterns = [
        ('process_simulation_economic_events', 'Process simulation economic events'),
        ('cache/economic_calendar_cache.json', 'Economic calendar cache file'),
        ('news_avoidance_window', 'News avoidance window logic'),
        ('high_impact_events', 'High impact event filtering'),
        ('event_impact_score', 'Event impact scoring')
    ]
    
    for pattern, desc in economic_patterns:
        if pattern in sim_content and pattern not in live_content:
            print(f"❌ {desc}: MISSING in live")
    
    # 2. CHECK PORTFOLIO VALUE CALCULATION
    print("\n2. PORTFOLIO VALUE CALCULATION:")
    print("-" * 40)
    
    portfolio_patterns = [
        ('update_portfolio_value', 'Portfolio value update method'),
        ('total_unrealized_pnl', 'Total unrealized P&L calculation'),
        ('portfolio_change', 'Portfolio change tracking'),
        ('previous_portfolio_value', 'Previous portfolio value storage'),
        ('portfolio_history.append', 'Portfolio history tracking')
    ]
    
    for pattern, desc in portfolio_patterns:
        if pattern in sim_content:
            if pattern not in live_content:
                print(f"❌ {desc}: MISSING in live")
            else:
                print(f"✅ {desc}: Found")
    
    # 3. CHECK POSITION CLOSURE LOGIC
    print("\n3. POSITION CLOSURE LOGIC:")
    print("-" * 40)
    
    closure_patterns = [
        ('positions_to_close', 'Position closure list'),
        ('close_on_profit', 'Close on profit logic'),
        ('close_on_loss', 'Close on loss logic'),
        ('close_on_time', 'Close on time logic'),
        ('close_on_trailing', 'Close on trailing stop'),
        ('peak_pnl', 'Peak P&L tracking'),
        ('position_age', 'Position age calculation')
    ]
    
    for pattern, desc in closure_patterns:
        if pattern in sim_content and pattern not in live_content:
            print(f"❌ {desc}: MISSING in live")
    
    # 4. CHECK UFO COMPENSATION LOGIC
    print("\n4. UFO COMPENSATION & REINFORCEMENT:")
    print("-" * 40)
    
    compensation_patterns = [
        ('positions_requiring_reinforcement', 'Positions requiring reinforcement list'),
        ('compensation_type', 'Compensation type determination'),
        ('additional_lots', 'Additional lots calculation'),
        ('compensation_position', 'Compensation position creation'),
        ('original_position_ticket', 'Original position ticket tracking'),
        ('reinforcement_reason', 'Reinforcement reason tracking')
    ]
    
    for pattern, desc in compensation_patterns:
        if pattern in sim_content and pattern not in live_content:
            print(f"❌ {desc}: MISSING in live")
    
    # 5. CHECK DATA COLLECTION METHODS
    print("\n5. DATA COLLECTION METHODS:")
    print("-" * 40)
    
    data_patterns = [
        ('collect_market_data', 'Market data collection'),
        ('get_real_time_market_data_for_positions', 'Real-time position data'),
        ('mt5.copy_rates_from', 'Historical rates fetching'),
        ('mt5.symbol_info_tick', 'Tick data fetching'),
        ('reshape_data_for_ufo', 'Data reshaping for UFO')
    ]
    
    for pattern, desc in data_patterns:
        sim_has = pattern in sim_content
        live_has = pattern in live_content
        if sim_has and not live_has:
            print(f"❌ {desc}: MISSING in live")
        elif sim_has and live_has:
            print(f"✅ {desc}: Present in both")
    
    # 6. CHECK CYCLE SUMMARY & REPORTING
    print("\n6. CYCLE SUMMARY & REPORTING:")
    print("-" * 40)
    
    summary_patterns = [
        ('generate_cycle_summary', 'Generate cycle summary'),
        ('generate_final_summary', 'Generate final summary'),
        ('save_full_day_report', 'Save full day report'),
        ('simulation_log.append', 'Simulation log appending'),
        ('Total trades executed this cycle', 'Cycle trade count'),
        ('Current portfolio performance', 'Portfolio performance summary')
    ]
    
    for pattern, desc in summary_patterns:
        if pattern in sim_content and pattern not in live_content:
            print(f"❌ {desc}: MISSING in live")
    
    # 7. CHECK RISK ASSESSMENT
    print("\n7. RISK ASSESSMENT:")
    print("-" * 40)
    
    risk_patterns = [
        ('assess_risk', 'Risk assessment method'),
        ('assess_portfolio', 'Portfolio assessment'),
        ('check_portfolio_equity_stop', 'Portfolio equity stop check'),
        ('portfolio_stop_breached', 'Portfolio stop breach detection'),
        ('risk_scale_factor', 'Risk scale factor application')
    ]
    
    for pattern, desc in risk_patterns:
        sim_has = pattern in sim_content
        live_has = pattern in live_content
        if sim_has and not live_has:
            print(f"❌ {desc}: MISSING in live")
        elif sim_has and live_has:
            print(f"✅ {desc}: Present in both")
    
    # 8. CHECK TRADE EXECUTION DETAILS
    print("\n8. TRADE EXECUTION DETAILS:")
    print("-" * 40)
    
    execution_patterns = [
        ('execute_approved_trades', 'Execute approved trades method'),
        ('validate_and_correct_currency_pair', 'Currency pair validation'),
        ('calculate_ufo_entry_price', 'UFO entry price calculation'),
        ('was_inverted', 'Direction inversion tracking'),
        ('risk_adjusted_volume', 'Risk adjusted volume calculation')
    ]
    
    for pattern, desc in execution_patterns:
        sim_has = pattern in sim_content
        live_has = pattern in live_content
        if sim_has and not live_has:
            print(f"❌ {desc}: MISSING in live")
        elif sim_has and live_has:
            print(f"✅ {desc}: Present in both")
    
    # 9. CHECK FUND MANAGER INTEGRATION
    print("\n9. FUND MANAGER INTEGRATION:")
    print("-" * 40)
    
    fund_patterns = [
        ('get_fund_authorization', 'Fund authorization method'),
        ('fund_manager_response', 'Fund manager response handling'),
        ('authorization_result', 'Authorization result processing'),
        ('trades_to_execute', 'Trades to execute determination')
    ]
    
    for pattern, desc in fund_patterns:
        if pattern in sim_content and pattern not in live_content:
            print(f"❌ {desc}: MISSING in live")
    
    # 10. CHECK MAIN LOOP STRUCTURE
    print("\n10. MAIN LOOP & TIMING:")
    print("-" * 40)
    
    loop_patterns = [
        ('run_full_day_simulation', 'Full day simulation method'),
        ('simulation_start_time', 'Simulation start time'),
        ('simulation_end_time', 'Simulation end time'),
        ('cycle_duration', 'Cycle duration tracking'),
        ('inter_cycle_monitoring', 'Inter-cycle monitoring')
    ]
    
    for pattern, desc in loop_patterns:
        if pattern in sim_content and pattern not in live_content:
            print(f"❌ {desc}: MISSING in live")
    
    # 11. CHECK OSCILLATION & UNCERTAINTY
    print("\n11. OSCILLATION & UNCERTAINTY DETECTION:")
    print("-" * 40)
    
    oscillation_patterns = [
        ('detect_oscillation', 'Oscillation detection'),
        ('detect_uncertainty', 'Uncertainty detection'),
        ('oscillation_detected', 'Oscillation flag'),
        ('uncertainty_metrics', 'Uncertainty metrics'),
        ('market_uncertainty', 'Market uncertainty assessment')
    ]
    
    for pattern, desc in oscillation_patterns:
        sim_has = pattern in sim_content
        live_has = pattern in live_content
        if sim_has and not live_has:
            print(f"❌ {desc}: MISSING in live")
        elif sim_has and live_has:
            print(f"✅ {desc}: Present in both")
    
    # 12. CHECK AGENT COMMUNICATIONS
    print("\n12. AGENT COMMUNICATIONS:")
    print("-" * 40)
    
    agent_patterns = [
        ('conduct_market_research', 'Market research conducting'),
        ('generate_trade_decisions', 'Trade decision generation'),
        ('trader_decision', 'Trader decision processing'),
        ('risk_assessment_result', 'Risk assessment result'),
        ('fund_authorization', 'Fund authorization check')
    ]
    
    for pattern, desc in agent_patterns:
        sim_has = pattern in sim_content
        live_has = pattern in live_content
        if sim_has and not live_has:
            print(f"❌ {desc}: MISSING in live")
        elif sim_has and live_has:
            print(f"✅ {desc}: Present in both")
    
    print("\n" + "=" * 80)
    print("SUMMARY OF ALL MISSING FEATURES:")
    print("=" * 80)
    
    # Count all missing features
    all_patterns = (economic_patterns + portfolio_patterns + closure_patterns + 
                   compensation_patterns + data_patterns + summary_patterns + 
                   risk_patterns + execution_patterns + fund_patterns + 
                   loop_patterns + oscillation_patterns + agent_patterns)
    
    missing_count = 0
    missing_features = []
    
    for pattern, desc in all_patterns:
        if pattern in sim_content and pattern not in live_content:
            missing_count += 1
            missing_features.append(desc)
    
    print(f"\n📊 TOTAL MISSING FEATURES: {missing_count}")
    
    if missing_features:
        print("\n❌ Missing features list:")
        for i, feature in enumerate(missing_features, 1):
            print(f"   {i}. {feature}")
    
    return missing_features

if __name__ == "__main__":
    missing = deep_analyze_differences()
