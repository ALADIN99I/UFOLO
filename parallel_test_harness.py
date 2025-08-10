"""
Parallel Test Harness for Forex Trading System
============================================
This test harness runs both the simulator and live trading system in parallel,
comparing their outputs cycle by cycle to ensure complete alignment.

Test Strategy:
1. Run simulator for historical date
2. Run live system in paper trading mode  
3. Compare outputs cycle by cycle
4. Track and document all differences
"""

import configparser
import pandas as pd
import numpy as np
import datetime
import time
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
import threading
import queue
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

# Import both systems
from full_day_simulation import FullDayTradingSimulation
from src.live_trader import LiveTrader
from src.ufo_calculator import UfoCalculator
from src.portfolio_manager import PortfolioManager
from src.dynamic_reinforcement_engine import DynamicReinforcementEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parallel_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class CycleSnapshot:
    """Snapshot of system state at a specific cycle"""
    cycle_number: int
    timestamp: datetime.datetime
    ufo_scores: Dict[str, float]
    reinforcement_triggers: List[str]
    open_positions: List[Dict]
    closed_trades: List[Dict]
    portfolio_value: float
    realized_pnl: float
    unrealized_pnl: float
    trade_decisions: List[Dict]
    position_closures: List[Dict]
    agent_analyses: Dict[str, Any]
    economic_events: List[Dict]
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'cycle_number': self.cycle_number,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ufo_scores': self.ufo_scores,
            'reinforcement_triggers': self.reinforcement_triggers,
            'open_positions': self.open_positions,
            'closed_trades': self.closed_trades,
            'portfolio_value': self.portfolio_value,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'trade_decisions': self.trade_decisions,
            'position_closures': self.position_closures,
            'agent_analyses': self.agent_analyses,
            'economic_events': self.economic_events
        }

class SystemWrapper:
    """Base wrapper class for both simulator and live systems"""
    
    def __init__(self, config, system_type='simulator'):
        self.config = config
        self.system_type = system_type
        self.snapshots = []
        self.current_cycle = 0
        
    def capture_snapshot(self) -> CycleSnapshot:
        """Capture current system state - to be implemented by subclasses"""
        raise NotImplementedError
        
    def run_cycle(self):
        """Execute one trading cycle - to be implemented by subclasses"""
        raise NotImplementedError

class SimulatorWrapper(SystemWrapper):
    """Wrapper for the simulation system"""
    
    def __init__(self, config, simulation_date=datetime.datetime(2025, 8, 1)):
        super().__init__(config, 'simulator')
        self.simulation = FullDayTradingSimulation(simulation_date)
        self.simulation_date = simulation_date
        
    def capture_snapshot(self) -> CycleSnapshot:
        """Capture current state of the simulator"""
        sim = self.simulation
        
        # Get UFO scores
        ufo_scores = {}
        if hasattr(sim.ufo_engine, 'last_ufo_scores'):
            ufo_scores = sim.ufo_engine.last_ufo_scores or {}
            
        # Get reinforcement triggers
        reinforcement_triggers = []
        if hasattr(sim.dynamic_reinforcement_engine, 'last_triggers'):
            reinforcement_triggers = sim.dynamic_reinforcement_engine.last_triggers or []
            
        # Get trade decisions from last cycle
        trade_decisions = []
        if hasattr(sim, 'last_trade_decisions'):
            trade_decisions = sim.last_trade_decisions or []
            
        # Get position closures from last cycle
        position_closures = []
        if hasattr(sim, 'last_position_closures'):
            position_closures = sim.last_position_closures or []
            
        # Get agent analyses
        agent_analyses = {}
        if hasattr(sim, 'last_agent_analyses'):
            agent_analyses = sim.last_agent_analyses or {}
            
        # Get economic events
        economic_events = []
        if hasattr(sim, 'last_economic_events'):
            economic_events = sim.last_economic_events or []
        
        return CycleSnapshot(
            cycle_number=self.current_cycle,
            timestamp=sim.current_time if hasattr(sim, 'current_time') else self.simulation_date,
            ufo_scores=ufo_scores,
            reinforcement_triggers=reinforcement_triggers,
            open_positions=sim.open_positions.copy(),
            closed_trades=sim.closed_trades.copy(),
            portfolio_value=sim.portfolio_value,
            realized_pnl=sim.realized_pnl,
            unrealized_pnl=sim.portfolio_value - sim.initial_balance - sim.realized_pnl,
            trade_decisions=trade_decisions,
            position_closures=position_closures,
            agent_analyses=agent_analyses,
            economic_events=economic_events
        )
        
    def run_cycle(self, cycle_time):
        """Execute one simulation cycle"""
        self.current_cycle += 1
        logger.info(f"🔄 Simulator - Running cycle {self.current_cycle} at {cycle_time}")
        
        # Store pre-cycle state for comparison
        pre_positions = len(self.simulation.open_positions)
        pre_trades = len(self.simulation.closed_trades)
        
        # Run the simulation cycle
        self.simulation.current_time = cycle_time
        self.simulation.run_trading_cycle(cycle_time)
        
        # Capture post-cycle state
        post_positions = len(self.simulation.open_positions)
        post_trades = len(self.simulation.closed_trades)
        
        logger.info(f"✅ Simulator - Cycle {self.current_cycle} complete: "
                   f"Positions {pre_positions}→{post_positions}, "
                   f"Trades {pre_trades}→{post_trades}")
        
        # Capture snapshot
        snapshot = self.capture_snapshot()
        self.snapshots.append(snapshot)
        return snapshot

class LiveSystemWrapper(SystemWrapper):
    """Wrapper for the live trading system in paper mode"""
    
    def __init__(self, config):
        super().__init__(config, 'live')
        # Modify config for paper trading
        self.config = self._configure_paper_trading(config)
        self.live_trader = LiveTrader(self.config)
        self.live_trader.paper_trading_mode = True
        
    def _configure_paper_trading(self, config):
        """Configure system for paper trading"""
        paper_config = configparser.ConfigParser()
        paper_config.read_dict(config)
        
        # Enable paper trading mode
        if 'trading' not in paper_config:
            paper_config.add_section('trading')
        paper_config.set('trading', 'paper_trading', 'true')
        paper_config.set('trading', 'live_trading_enabled', 'false')
        
        return paper_config
        
    def capture_snapshot(self) -> CycleSnapshot:
        """Capture current state of the live system"""
        trader = self.live_trader
        
        # Get UFO scores
        ufo_scores = {}
        if hasattr(trader, 'ufo_engine') and hasattr(trader.ufo_engine, 'last_ufo_scores'):
            ufo_scores = trader.ufo_engine.last_ufo_scores or {}
            
        # Get reinforcement triggers
        reinforcement_triggers = []
        if hasattr(trader, 'dynamic_reinforcement_engine') and hasattr(trader.dynamic_reinforcement_engine, 'last_triggers'):
            reinforcement_triggers = trader.dynamic_reinforcement_engine.last_triggers or []
            
        # Get current positions
        open_positions = []
        if hasattr(trader, 'portfolio_manager'):
            open_positions = trader.portfolio_manager.get_open_positions()
            
        # Get closed trades
        closed_trades = []
        if hasattr(trader, 'portfolio_manager'):
            closed_trades = trader.portfolio_manager.get_closed_trades()
            
        # Get portfolio metrics
        portfolio_value = trader.portfolio_manager.get_portfolio_value() if hasattr(trader, 'portfolio_manager') else 0
        realized_pnl = trader.portfolio_manager.get_realized_pnl() if hasattr(trader, 'portfolio_manager') else 0
        unrealized_pnl = trader.portfolio_manager.get_unrealized_pnl() if hasattr(trader, 'portfolio_manager') else 0
        
        # Get trade decisions and closures
        trade_decisions = trader.last_trade_decisions if hasattr(trader, 'last_trade_decisions') else []
        position_closures = trader.last_position_closures if hasattr(trader, 'last_position_closures') else []
        
        # Get agent analyses
        agent_analyses = trader.last_agent_analyses if hasattr(trader, 'last_agent_analyses') else {}
        
        # Get economic events
        economic_events = trader.last_economic_events if hasattr(trader, 'last_economic_events') else []
        
        return CycleSnapshot(
            cycle_number=self.current_cycle,
            timestamp=datetime.datetime.now(),
            ufo_scores=ufo_scores,
            reinforcement_triggers=reinforcement_triggers,
            open_positions=open_positions,
            closed_trades=closed_trades,
            portfolio_value=portfolio_value,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            trade_decisions=trade_decisions,
            position_closures=position_closures,
            agent_analyses=agent_analyses,
            economic_events=economic_events
        )
        
    def run_cycle(self, cycle_time=None):
        """Execute one live trading cycle"""
        self.current_cycle += 1
        logger.info(f"🔄 Live System - Running cycle {self.current_cycle}")
        
        # Set up tracking attributes if not present
        if not hasattr(self.live_trader, 'last_trade_decisions'):
            self.live_trader.last_trade_decisions = []
        if not hasattr(self.live_trader, 'last_position_closures'):
            self.live_trader.last_position_closures = []
        if not hasattr(self.live_trader, 'last_agent_analyses'):
            self.live_trader.last_agent_analyses = {}
        if not hasattr(self.live_trader, 'last_economic_events'):
            self.live_trader.last_economic_events = []
        
        # Run the live trading cycle - use simulate_single_cycle which exists in LiveTrader
        current_time = cycle_time if cycle_time else datetime.datetime.now()
        self.live_trader.simulate_single_cycle(current_time)
        
        logger.info(f"✅ Live System - Cycle {self.current_cycle} complete")
        
        # Capture snapshot
        snapshot = self.capture_snapshot()
        self.snapshots.append(snapshot)
        return snapshot

class ParallelTestHarness:
    """Main test harness for parallel execution and comparison"""
    
    def __init__(self, config_path='config/config.ini', test_date=datetime.datetime(2025, 8, 1)):
        self.config = self._load_config(config_path)
        self.test_date = test_date
        self.simulator = SimulatorWrapper(self.config, test_date)
        self.live_system = LiveSystemWrapper(self.config)
        self.comparison_results = []
        self.differences = []
        
    def _load_config(self, config_path):
        """Load configuration file"""
        config = configparser.ConfigParser()
        config.read(config_path)
        return config
        
    def compare_snapshots(self, sim_snapshot: CycleSnapshot, live_snapshot: CycleSnapshot) -> Dict:
        """Compare two system snapshots and identify differences"""
        differences = {}
        
        # Compare UFO scores
        ufo_diff = self._compare_dicts(sim_snapshot.ufo_scores, live_snapshot.ufo_scores, 'UFO Scores')
        if ufo_diff:
            differences['ufo_scores'] = ufo_diff
            
        # Compare reinforcement triggers
        if set(sim_snapshot.reinforcement_triggers) != set(live_snapshot.reinforcement_triggers):
            differences['reinforcement_triggers'] = {
                'simulator': sim_snapshot.reinforcement_triggers,
                'live': live_snapshot.reinforcement_triggers,
                'only_in_sim': list(set(sim_snapshot.reinforcement_triggers) - set(live_snapshot.reinforcement_triggers)),
                'only_in_live': list(set(live_snapshot.reinforcement_triggers) - set(sim_snapshot.reinforcement_triggers))
            }
            
        # Compare positions
        pos_diff = self._compare_positions(sim_snapshot.open_positions, live_snapshot.open_positions)
        if pos_diff:
            differences['positions'] = pos_diff
            
        # Compare portfolio metrics
        portfolio_metrics = {
            'portfolio_value': (sim_snapshot.portfolio_value, live_snapshot.portfolio_value),
            'realized_pnl': (sim_snapshot.realized_pnl, live_snapshot.realized_pnl),
            'unrealized_pnl': (sim_snapshot.unrealized_pnl, live_snapshot.unrealized_pnl)
        }
        
        metric_diffs = {}
        for metric, (sim_val, live_val) in portfolio_metrics.items():
            if abs(sim_val - live_val) > 0.01:  # Allow small floating point differences
                metric_diffs[metric] = {
                    'simulator': sim_val,
                    'live': live_val,
                    'difference': sim_val - live_val,
                    'percentage': ((sim_val - live_val) / live_val * 100) if live_val != 0 else 0
                }
        
        if metric_diffs:
            differences['portfolio_metrics'] = metric_diffs
            
        # Compare trade decisions
        trade_diff = self._compare_trade_decisions(sim_snapshot.trade_decisions, live_snapshot.trade_decisions)
        if trade_diff:
            differences['trade_decisions'] = trade_diff
            
        # Compare position closures
        closure_diff = self._compare_closures(sim_snapshot.position_closures, live_snapshot.position_closures)
        if closure_diff:
            differences['position_closures'] = closure_diff
            
        return differences
        
    def _compare_dicts(self, dict1: Dict, dict2: Dict, name: str) -> Dict:
        """Compare two dictionaries and return differences"""
        differences = {}
        
        all_keys = set(dict1.keys()) | set(dict2.keys())
        for key in all_keys:
            val1 = dict1.get(key)
            val2 = dict2.get(key)
            
            if val1 != val2:
                # For numeric values, check if difference is significant
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    if abs(val1 - val2) > 0.0001:  # Tolerance for floating point
                        differences[key] = {
                            'simulator': val1,
                            'live': val2,
                            'difference': val1 - val2
                        }
                else:
                    differences[key] = {
                        'simulator': val1,
                        'live': val2
                    }
                    
        return differences
        
    def _compare_positions(self, sim_positions: List[Dict], live_positions: List[Dict]) -> Dict:
        """Compare position lists"""
        differences = {}
        
        # Compare count
        if len(sim_positions) != len(live_positions):
            differences['count'] = {
                'simulator': len(sim_positions),
                'live': len(live_positions)
            }
            
        # Create position maps by symbol
        sim_map = {p.get('symbol', ''): p for p in sim_positions}
        live_map = {p.get('symbol', ''): p for p in live_positions}
        
        # Find positions only in one system
        only_in_sim = set(sim_map.keys()) - set(live_map.keys())
        only_in_live = set(live_map.keys()) - set(sim_map.keys())
        
        if only_in_sim:
            differences['only_in_simulator'] = list(only_in_sim)
        if only_in_live:
            differences['only_in_live'] = list(only_in_live)
            
        # Compare common positions
        common_symbols = set(sim_map.keys()) & set(live_map.keys())
        position_diffs = {}
        
        for symbol in common_symbols:
            sim_pos = sim_map[symbol]
            live_pos = live_map[symbol]
            
            pos_diff = {}
            # Compare key fields
            fields_to_compare = ['volume', 'entry_price', 'direction', 'profit']
            
            for field in fields_to_compare:
                sim_val = sim_pos.get(field)
                live_val = live_pos.get(field)
                
                if sim_val != live_val:
                    if isinstance(sim_val, (int, float)) and isinstance(live_val, (int, float)):
                        if abs(sim_val - live_val) > 0.0001:
                            pos_diff[field] = {
                                'simulator': sim_val,
                                'live': live_val,
                                'difference': sim_val - live_val
                            }
                    else:
                        pos_diff[field] = {
                            'simulator': sim_val,
                            'live': live_val
                        }
                        
            if pos_diff:
                position_diffs[symbol] = pos_diff
                
        if position_diffs:
            differences['position_details'] = position_diffs
            
        return differences
        
    def _compare_trade_decisions(self, sim_decisions: List[Dict], live_decisions: List[Dict]) -> Dict:
        """Compare trade decision lists"""
        differences = {}
        
        # Compare counts
        if len(sim_decisions) != len(live_decisions):
            differences['count'] = {
                'simulator': len(sim_decisions),
                'live': len(live_decisions)
            }
            
        # Create decision maps
        sim_symbols = {d.get('symbol', '') for d in sim_decisions}
        live_symbols = {d.get('symbol', '') for d in live_decisions}
        
        only_in_sim = sim_symbols - live_symbols
        only_in_live = live_symbols - sim_symbols
        
        if only_in_sim:
            differences['only_in_simulator'] = list(only_in_sim)
        if only_in_live:
            differences['only_in_live'] = list(only_in_live)
            
        return differences
        
    def _compare_closures(self, sim_closures: List[Dict], live_closures: List[Dict]) -> Dict:
        """Compare position closure lists"""
        differences = {}
        
        # Extract closure reasons
        sim_reasons = [c.get('reason', 'unknown') for c in sim_closures]
        live_reasons = [c.get('reason', 'unknown') for c in live_closures]
        
        # Count by reason
        from collections import Counter
        sim_reason_counts = Counter(sim_reasons)
        live_reason_counts = Counter(live_reasons)
        
        if sim_reason_counts != live_reason_counts:
            differences['closure_reasons'] = {
                'simulator': dict(sim_reason_counts),
                'live': dict(live_reason_counts)
            }
            
        return differences
        
    def run_parallel_test(self, num_cycles=10, cycle_duration_minutes=40):
        """Run parallel test for specified number of cycles"""
        logger.info(f"🚀 Starting parallel test: {num_cycles} cycles, {cycle_duration_minutes} minutes each")
        logger.info(f"📅 Test date: {self.test_date}")
        
        results = {
            'test_date': self.test_date.isoformat(),
            'num_cycles': num_cycles,
            'cycle_duration': cycle_duration_minutes,
            'cycles': [],
            'summary': {}
        }
        
        current_time = self.test_date.replace(hour=8, minute=0, second=0)  # Start at 8 AM
        
        for cycle_num in range(1, num_cycles + 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 CYCLE {cycle_num}/{num_cycles} - Time: {current_time}")
            logger.info(f"{'='*60}")
            
            # Run both systems in parallel
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both tasks
                sim_future = executor.submit(self.simulator.run_cycle, current_time)
                live_future = executor.submit(self.live_system.run_cycle, current_time)
                
                # Wait for both to complete
                sim_snapshot = sim_future.result()
                live_snapshot = live_future.result()
            
            # Compare results
            cycle_differences = self.compare_snapshots(sim_snapshot, live_snapshot)
            
            # Log differences
            if cycle_differences:
                logger.warning(f"⚠️ Differences found in cycle {cycle_num}:")
                for category, diff in cycle_differences.items():
                    logger.warning(f"  - {category}: {json.dumps(diff, indent=2)}")
                self.differences.append({
                    'cycle': cycle_num,
                    'time': current_time.isoformat(),
                    'differences': cycle_differences
                })
            else:
                logger.info(f"✅ Cycle {cycle_num}: Systems in perfect alignment")
            
            # Store cycle results
            cycle_result = {
                'cycle_number': cycle_num,
                'time': current_time.isoformat(),
                'simulator_snapshot': sim_snapshot.to_dict(),
                'live_snapshot': live_snapshot.to_dict(),
                'differences': cycle_differences,
                'aligned': len(cycle_differences) == 0
            }
            results['cycles'].append(cycle_result)
            
            # Advance time
            current_time += datetime.timedelta(minutes=cycle_duration_minutes)
            
            # Small delay between cycles
            time.sleep(1)
        
        # Generate summary
        results['summary'] = self._generate_summary(results['cycles'])
        
        # Save results
        self._save_results(results)
        
        return results
        
    def _generate_summary(self, cycles: List[Dict]) -> Dict:
        """Generate test summary statistics"""
        total_cycles = len(cycles)
        aligned_cycles = sum(1 for c in cycles if c['aligned'])
        
        # Categorize differences
        difference_categories = {}
        for cycle in cycles:
            for category in cycle.get('differences', {}).keys():
                if category not in difference_categories:
                    difference_categories[category] = 0
                difference_categories[category] += 1
        
        summary = {
            'total_cycles': total_cycles,
            'aligned_cycles': aligned_cycles,
            'misaligned_cycles': total_cycles - aligned_cycles,
            'alignment_rate': (aligned_cycles / total_cycles * 100) if total_cycles > 0 else 0,
            'difference_categories': difference_categories,
            'most_common_difference': max(difference_categories.items(), key=lambda x: x[1])[0] if difference_categories else None
        }
        
        # Calculate final portfolio difference
        if cycles:
            last_cycle = cycles[-1]
            sim_portfolio = last_cycle['simulator_snapshot']['portfolio_value']
            live_portfolio = last_cycle['live_snapshot']['portfolio_value']
            
            summary['final_portfolio_difference'] = {
                'simulator': sim_portfolio,
                'live': live_portfolio,
                'difference': sim_portfolio - live_portfolio,
                'percentage': ((sim_portfolio - live_portfolio) / live_portfolio * 100) if live_portfolio != 0 else 0
            }
        
        return summary
        
    def _save_results(self, results: Dict):
        """Save test results to file"""
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'parallel_test_results_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        logger.info(f"📁 Results saved to {filename}")
        
        # Also save a summary report
        self._generate_report(results, f'parallel_test_report_{timestamp}.txt')
        
    def _generate_report(self, results: Dict, filename: str):
        """Generate human-readable test report"""
        with open(filename, 'w') as f:
            f.write("="*80 + "\n")
            f.write("PARALLEL TESTING REPORT\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Test Date: {results['test_date']}\n")
            f.write(f"Number of Cycles: {results['num_cycles']}\n")
            f.write(f"Cycle Duration: {results['cycle_duration']} minutes\n\n")
            
            f.write("SUMMARY\n")
            f.write("-"*40 + "\n")
            summary = results['summary']
            f.write(f"Alignment Rate: {summary['alignment_rate']:.2f}%\n")
            f.write(f"Aligned Cycles: {summary['aligned_cycles']}/{summary['total_cycles']}\n")
            f.write(f"Misaligned Cycles: {summary['misaligned_cycles']}/{summary['total_cycles']}\n\n")
            
            if summary.get('difference_categories'):
                f.write("Difference Categories:\n")
                for category, count in summary['difference_categories'].items():
                    f.write(f"  - {category}: {count} cycles\n")
                f.write(f"\nMost Common Difference: {summary.get('most_common_difference', 'N/A')}\n\n")
            
            if summary.get('final_portfolio_difference'):
                f.write("Final Portfolio Comparison:\n")
                fpd = summary['final_portfolio_difference']
                f.write(f"  Simulator: ${fpd['simulator']:.2f}\n")
                f.write(f"  Live System: ${fpd['live']:.2f}\n")
                f.write(f"  Difference: ${fpd['difference']:.2f} ({fpd['percentage']:.2f}%)\n\n")
            
            # Detailed differences
            if self.differences:
                f.write("DETAILED DIFFERENCES\n")
                f.write("-"*40 + "\n")
                for diff in self.differences:
                    f.write(f"\nCycle {diff['cycle']} ({diff['time']}):\n")
                    for category, details in diff['differences'].items():
                        f.write(f"  {category}:\n")
                        f.write(f"    {json.dumps(details, indent=4)}\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write("END OF REPORT\n")
            f.write("="*80 + "\n")
            
        logger.info(f"📄 Report saved to {filename}")

def main():
    """Main test execution"""
    parser = argparse.ArgumentParser(description='Run parallel testing of simulator and live system')
    parser.add_argument('--cycles', type=int, default=10, help='Number of cycles to run')
    parser.add_argument('--duration', type=int, default=40, help='Duration of each cycle in minutes')
    parser.add_argument('--date', type=str, default='2025-08-01', help='Simulation date (YYYY-MM-DD)')
    parser.add_argument('--config', type=str, default='config/config.ini', help='Path to config file')
    
    args = parser.parse_args()
    
    # Parse test date
    test_date = datetime.datetime.strptime(args.date, '%Y-%m-%d')
    
    # Create and run test harness
    harness = ParallelTestHarness(args.config, test_date)
    results = harness.run_parallel_test(args.cycles, args.duration)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    summary = results['summary']
    print(f"Alignment Rate: {summary['alignment_rate']:.2f}%")
    print(f"Aligned Cycles: {summary['aligned_cycles']}/{summary['total_cycles']}")
    
    if summary.get('final_portfolio_difference'):
        fpd = summary['final_portfolio_difference']
        print(f"\nFinal Portfolio Difference: ${fpd['difference']:.2f} ({fpd['percentage']:.2f}%)")
    
    if summary['alignment_rate'] == 100:
        print("\n✅ PERFECT ALIGNMENT - Systems are completely synchronized!")
    elif summary['alignment_rate'] >= 95:
        print("\n✅ EXCELLENT ALIGNMENT - Minor differences detected")
    elif summary['alignment_rate'] >= 90:
        print("\n⚠️ GOOD ALIGNMENT - Some differences need investigation")
    else:
        print("\n❌ POOR ALIGNMENT - Significant differences detected")

if __name__ == "__main__":
    import argparse
    main()
