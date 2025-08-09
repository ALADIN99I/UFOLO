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
from src.simulation_ufo_engine import SimulationUFOTradingEngine
from src.portfolio_manager import PortfolioManager
from src.dynamic_reinforcement_engine import DynamicReinforcementEngine

class FullDayTradingSimulation:
    def __init__(self, simulation_date=datetime.datetime(2025, 8, 8)):
        self.simulation_date = simulation_date
        self.config = self.load_config()
        self.trades_executed = []
        self.portfolio_value = 10000.0  # Starting balance
        self.initial_balance = 10000.0
        self.realized_pnl = 0.0  # Track cumulative realized P&L from closed trades
        self.simulation_log = []
        self.cycle_count = 0
        self.open_positions = []  # Track simulated positions
        self.closed_trades = []   # Track completed trades
        
        # Continuous monitoring variables
        self.last_position_update = None
        self.position_update_frequency_minutes = 5  # Update positions every 5 minutes
        self.continuous_monitoring_enabled = True
        self.portfolio_history = []  # Track portfolio value over time
        
        # Fix config parsing issues
        self.fix_config_values()
        
        # Initialize components
        self.initialize_components()
        
    def load_config(self):
        """Load configuration with error handling"""
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.ini')
        config.read(config_path)
        return config
    
    def fix_config_values(self):
        """Fix configuration values that have comments or multiple values"""
        # Parse values with inline comments
        def parse_value(value, default):
            if isinstance(value, str) and '#' in value:
                return value.split('#')[0].strip()
            return value if value else default

        # Safely get boolean
        def get_boolean_safe(section, option, default=False):
            try:
                return self.config.getboolean(section, option)
            except (configparser.NoOptionError, ValueError):
                return default

        # Safely get int
        def get_int_safe(section, option, default=0):
            try:
                return self.config.getint(section, option)
            except (configparser.NoOptionError, ValueError):
                return default

        # Safely get float
        def get_float_safe(section, option, default=0.0):
            try:
                return self.config.getfloat(section, option)
            except (configparser.NoOptionError, ValueError):
                return default

        # Fix for 'risk_management' section
        if 'risk_management' in self.config:
            self.config['risk_management']['max_daily_drawdown'] = str(get_float_safe('risk_management', 'max_daily_drawdown', 0.05))
            self.config['risk_management']['max_trade_drawdown'] = str(get_float_safe('risk_management', 'max_trade_drawdown', 0.02))

        # Fix for 'trading_params' section
        if 'trading_params' in self.config:
            self.config['trading_params']['trade_risk_percentage'] = str(get_float_safe('trading_params', 'trade_risk_percentage', 1.0))
            self.config['trading_params']['min_volume'] = str(get_float_safe('trading_params', 'min_volume', 0.01))
            self.config['trading_params']['max_volume'] = str(get_float_safe('trading_params', 'max_volume', 1.0))

        # Fix for 'pairs' section
        if 'pairs' in self.config:
            self.config['pairs']['forex_pairs'] = parse_value(self.config['pairs'].get('forex_pairs'), "EURUSD,GBPUSD,USDJPY")

    def initialize_components(self):
        """Initialize all trading components"""
        # MT5 Data Collector
        self.mt5_collector = MT5DataCollector(self.config)
        
        # Economic Calendar
        self.economic_calendar = EconomicCalendarCollector(self.config)
        
        # UFO Calculator
        self.ufo_calculator = UfoCalculator(self.config, self.mt5_collector)
        
        # LLM Client
        self.llm_client = LLMClient(self.config)
        
        # Portfolio Manager
        self.portfolio_manager = PortfolioManager(self.config, self.mt5_collector)
        
        # Trade Executor
        self.trade_executor = TradeExecutor(self.config, self.mt5_collector, self.portfolio_manager)
        
        # Agents
        self.trader_agent = TraderAgent(self.llm_client)
        self.risk_manager_agent = RiskManagerAgent(self.llm_client)
        self.data_analyst_agent = DataAnalystAgent(self.llm_client)
        self.market_researcher_agent = MarketResearcherAgent(self.llm_client)
        self.fund_manager_agent = FundManagerAgent(self.llm_client)
        
        # Dynamic Reinforcement Engine
        self.dynamic_reinforcement_engine = DynamicReinforcementEngine(
            config=self.config,
            trade_executor=self.trade_executor,
            portfolio_manager=self.portfolio_manager,
            data_collector=self.mt5_collector,
            ufo_calculator=self.ufo_calculator,
            risk_manager_agent=self.risk_manager_agent,
            trader_agent=self.trader_agent
        )
        
        # Main UFO Trading Engine
        self.ufo_engine = SimulationUFOTradingEngine(
            config=self.config,
            mt5_collector=self.mt5_collector,
            ufo_calculator=self.ufo_calculator,
            llm_client=self.llm_client,
            trader_agent=self.trader_agent,
            risk_manager_agent=self.risk_manager_agent,
            data_analyst_agent=self.data_analyst_agent,
            market_researcher_agent=self.market_researcher_agent,
            fund_manager_agent=self.fund_manager_agent,
            trade_executor=self.trade_executor,
            portfolio_manager=self.portfolio_manager,
            dynamic_reinforcement_engine=self.dynamic_reinforcement_engine,
            economic_calendar=self.economic_calendar
        )

def main():
    """Main function to run the full day simulation"""
    print("🚀 Starting UFO Forex Agent v3 - FULL DAY SIMULATION")
    
    try:
        # Create and run simulation for the current day
        simulation = FullDayTradingSimulation(datetime.datetime.now())
        simulation.run_full_day_simulation()
        
    except Exception as e:
        print(f"💥 Simulation failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

