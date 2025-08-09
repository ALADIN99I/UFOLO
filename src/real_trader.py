import configparser
import pandas as pd
import numpy as np
import datetime
import time
import json
import re
import os
from pathlib import Path

# Import necessary modules
import MetaTrader5 as mt5

from src.data_collector import MT5DataCollector, EconomicCalendarCollector
from src.ufo_calculator import UfoCalculator
from src.llm.llm_client import LLMClient
from src.agents.trader_agent import TraderAgent
from src.agents.risk_manager_agent import RiskManagerAgent
from src.agents.data_analyst_agent import DataAnalystAgent
from src.agents.market_researcher_agent import MarketResearcherAgent
from src.agents.fund_manager_agent import FundManagerAgent
from src.trade_executor import TradeExecutor
from src.ufo_trading_engine import UFOTradingEngine
from src.portfolio_manager import PortfolioManager
from src.dynamic_reinforcement_engine import DynamicReinforcementEngine

class RealTrader:
    def __init__(self):
        self.config = self.load_config()
        self.trades_executed = []
        self.simulation_log = []
        self.cycle_count = 0
        self.closed_trades = []
        self.portfolio_history = []
        
        self.continuous_monitoring_enabled = True
        self.last_position_update = None
        self.position_update_frequency_minutes = int(self.config['trading'].get('reinforcement_check_frequency_minutes', '5'))
        self.cycle_period_seconds = int(self.config['trading'].get('cycle_period_seconds', '300'))
        
        self.fix_config_values()
        self.initialize_components()

    def load_config(self):
        """Load configuration with error handling"""
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)).parent, 'config', 'config.ini')
        config.read(config_path)
        return config

    def fix_config_values(self):
        """Fix configuration values that have comments."""
        for section in self.config.sections():
            for key, value in self.config.items(section):
                if '#' in value:
                    self.config.set(section, key, value.split('#')[0].strip())

    def log_event(self, message):
        """Log an event."""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.simulation_log.append(log_entry)
        print(log_entry)

    def initialize_components(self):
        """Initialize all trading components."""
        self.log_event("🔧 Initializing components...")
        self.mt5_collector = MT5DataCollector(self.config)
        self.calendar_collector = EconomicCalendarCollector(self.config)
        self.llm_client = LLMClient(self.config)
        self.data_analyst_agent = DataAnalystAgent(self.llm_client, self.config)
        self.market_researcher_agent = MarketResearcherAgent(self.llm_client, self.config)
        self.risk_manager_agent = RiskManagerAgent(self.llm_client, self.config)
        self.trader_agent = TraderAgent(self.llm_client, self.config)
        self.fund_manager_agent = FundManagerAgent(self.llm_client, self.config)
        self.ufo_engine = UFOTradingEngine(self.config)
        self.portfolio_manager = PortfolioManager(self.mt5_collector.get_connection())
        self.trade_executor = TradeExecutor(self.mt5_collector.get_connection(), self.config)
        self.dynamic_reinforcement_engine = DynamicReinforcementEngine(self.config)
        self.log_event("✅ All components initialized successfully")

    def run(self):
        """Main loop for continuous live trading."""
        self.log_event("🚀 Starting UFO Forex Agent v3 - REAL TRADING MODE")
        self.log_event("Cloned from Full Day Simulator logic.")
        
        while True:
            try:
                self.run_trading_cycle()
                
                if self.continuous_monitoring_enabled:
                    self.continuous_position_monitoring()

            except Exception as e:
                self.log_event(f"💥 An error occurred in the main loop: {e}")
                import traceback
                traceback.print_exc()
            
            self.save_results()
            self.log_event(f"Cycle finished. Waiting for {self.cycle_period_seconds} seconds...")
            time.sleep(self.cycle_period_seconds)

    def run_trading_cycle(self):
        """Execute a single trading cycle."""
        self.cycle_count += 1
        self.log_event(f"\n--- 🔄 Cycle {self.cycle_count} | Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        
        economic_events = self.get_economic_events()
        open_positions = self.portfolio_manager.get_positions()
        account_info = self.portfolio_manager.get_account_info()
        
        ufo_data, market_sentiment, recommended_pairs = self.get_ufo_data(economic_events, open_positions)
        if ufo_data is None:
            self.log_event("🔴 UFO data collection failed. Skipping cycle.")
            return
        
        should_trade, reason = self.ufo_engine.should_open_new_trade(
            current_positions=open_positions,
            portfolio_status=account_info,
            economic_events=economic_events
        )
        
        if should_trade:
            self.log_event(f"🟢 Conditions are favorable for new trades: {reason}")
            trading_ideas = self.fund_manager_agent.generate_trading_ideas(ufo_data, market_sentiment, economic_events, recommended_pairs)
            if trading_ideas:
                trade_advice = self.trader_agent.get_trade_advice(ufo_data, trading_ideas, open_positions)
                if trade_advice:
                    risk_assessment = self.risk_manager_agent.assess_risk(ufo_data, trade_advice, open_positions, account_info)
                    if risk_assessment and risk_assessment.get('proceed', False):
                        self.execute_trades(risk_assessment['trades_to_execute'])
                    else:
                        self.log_event("🔴 Trade execution halted by risk manager.")
                else:
                    self.log_event("🔴 No trade advice generated.")
            else:
                self.log_event("🔴 No trading ideas generated.")
        else:
            self.log_event(f"🔴 Not opening new trades: {reason}")
        
        self.update_portfolio_summary(account_info)

    def continuous_position_monitoring(self):
        """Monitor open positions for adjustments."""
        self.log_event("\n--- 🔍 Continuous Position Monitoring ---")
        
        open_positions = self.portfolio_manager.get_positions()
        if open_positions.empty:
            self.log_event("No open positions to monitor.")
            return

        if self.last_position_update and (datetime.datetime.now() - self.last_position_update).total_seconds() < self.position_update_frequency_minutes * 60:
            return

        self.last_position_update = datetime.datetime.now()
        self.check_for_position_closure(open_positions)
        self.check_for_dynamic_reinforcement(open_positions)

    def get_economic_events(self):
        """Fetch economic events."""
        try:
            return self.calendar_collector.get_economic_calendar()
        except Exception as e:
            self.log_event(f"⚠️ Could not fetch economic events: {e}")
            return pd.DataFrame()

    def get_ufo_data(self, economic_events, open_positions=None):
        """Fetch and analyze UFO data."""
        try:
            return self.ufo_engine.get_ufo_data_and_sentiment(
                self.mt5_collector, self.data_analyst_agent, self.market_researcher_agent,
                economic_events, open_positions
            )
        except Exception as e:
            self.log_event(f"⚠️ Could not analyze UFO data: {e}")
            return None, None, None

    def execute_trades(self, trades):
        """Execute trades based on the risk assessment."""
        for trade in trades:
            try:
                success, result = self.trade_executor.execute_trade(
                    symbol=trade['symbol'], direction=trade['direction'], volume=trade['volume'],
                    stop_loss=trade.get('stop_loss'), take_profit=trade.get('take_profit')
                )
                if success:
                    self.log_event(f"  ✅ Executed: {trade['direction']} {trade['volume']} lots of {trade['symbol']} @ {result.price:.5f}")
                    self.trades_executed.append(result)
                else:
                    self.log_event(f"  ❌ Failed to execute trade for {trade['symbol']}: {result}")
            except Exception as e:
                self.log_event(f"  ❌ Error executing trade for {trade['symbol']}: {e}")

    def update_portfolio_summary(self, account_info=None):
        """Log the current portfolio summary."""
        if not account_info:
            account_info = self.portfolio_manager.get_account_info()
        
        if account_info:
            self.log_event(f"--- Portfolio Summary --- Balance: ${account_info.balance:,.2f}, Equity: ${account_info.equity:,.2f}, Profit: ${account_info.profit:,.2f}")
            self.portfolio_history.append({'time': datetime.datetime.now(), 'equity': account_info.equity})
        else:
            self.log_event("  Could not retrieve account info.")

    def save_results(self):
        """Save the trading log and portfolio history to files."""
        log_dir = Path('logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_filename = f"live_trading_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(log_dir / log_filename, 'w') as f:
            f.write("\n".join(self.simulation_log))
        
        if self.portfolio_history:
            df = pd.DataFrame(self.portfolio_history)
            df.to_csv(log_dir / f"portfolio_history_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", index=False)

    def check_for_position_closure(self, open_positions):
        """Check if any open positions should be closed."""
        for _, position in open_positions.iterrows():
            pos_dict = position.to_dict()
            should_close, reason = self.ufo_engine.should_close_position(pos_dict)
            if should_close:
                self.log_event(f"    - Closing {pos_dict['symbol']} due to: {reason}")
                try:
                    success, result = self.trade_executor.close_trade(pos_dict['ticket'])
                    if success:
                        self.log_event(f"    ✅ Closed position ticket {pos_dict['ticket']}")
                        self.closed_trades.append(pos_dict)
                    else:
                        self.log_event(f"    ❌ Failed to close position ticket {pos_dict['ticket']}: {result}")
                except Exception as e:
                    self.log_event(f"    ❌ Error closing position ticket {pos_dict['ticket']}: {e}")

    def check_for_dynamic_reinforcement(self, open_positions):
        """Check if any open positions should be reinforced."""
        if not self.dynamic_reinforcement_engine.is_enabled():
            return

        for _, position in open_positions.iterrows():
            pos_dict = position.to_dict()
            reinforcement_plan = self.dynamic_reinforcement_engine.evaluate_reinforcement(
                pos_dict, self.ufo_engine.get_latest_ufo_data(),
                self.ufo_engine.get_latest_market_sentiment(), self.get_economic_events()
            )
            if reinforcement_plan:
                self.log_event(f"    - Reinforcing {pos_dict['symbol']} due to: {reinforcement_plan['reason']}")
                self.execute_reinforcement(pos_dict, reinforcement_plan)

    def execute_reinforcement(self, position, reinforcement_plan):
        """Execute a reinforcement trade."""
        try:
            direction = 'BUY' if position['type'] == 0 else 'SELL'
            success, result = self.trade_executor.execute_trade(
                symbol=position['symbol'], direction=direction, volume=reinforcement_plan['additional_lots'],
                comment=f"Dynamic {reinforcement_plan.get('type', 'Reinforcement')}"
            )
            if success:
                self.dynamic_reinforcement_engine.record_reinforcement(position, reinforcement_plan)
                self.log_event(f"    ✅ Dynamic reinforcement executed: {position['symbol']} {direction} {reinforcement_plan['additional_lots']:.2f} lots")
                self.trades_executed.append(result)
            else:
                self.log_event(f"    ❌ Failed to execute dynamic reinforcement for {position['symbol']}: {result}")
        except Exception as e:
            self.log_event(f"    ❌ Failed to execute dynamic reinforcement: {e}")
    
    def cleanup_connections(self):
        """Clean up MT5 and other connections"""
        try:
            self.mt5_collector.disconnect()
            self.log_event("✅ MT5 connection closed")
        except Exception as e:
            self.log_event(f"⚠️ Error closing MT5 connection: {e}")
