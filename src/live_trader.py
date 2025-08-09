import time
import pandas as pd
import numpy as np
import re
import json
from datetime import datetime, timedelta
try:
    import MetaTrader5 as mt5
except ImportError:
    from . import mock_metatrader5 as mt5
from .data_collector import MT5DataCollector, EconomicCalendarCollector
from .agents.data_analyst_agent import DataAnalystAgent
from .agents.market_researcher_agent import MarketResearcherAgent
from .agents.trader_agent import TraderAgent
from .agents.risk_manager_agent import RiskManagerAgent
from .agents.fund_manager_agent import FundManagerAgent
from .communication import CommunicationBus
from .ufo_calculator import UfoCalculator
from .llm.llm_client import LLMClient
from .trade_executor import TradeExecutor
from .ufo_trading_engine import UFOTradingEngine
from .portfolio_manager import PortfolioManager
from .dynamic_reinforcement_engine import DynamicReinforcementEngine
from .utils.pair_validator import PairValidator

class LiveTrader:
    def __init__(self, config):
        self.config = config
        # SIMULATOR CLONING: Add all simulator variables
        self.trades_executed = []  # Track all trades executed like simulator
        self.closed_trades = []    # Track completed trades like simulator
        self.cycle_count = 0       # Track cycle counter like simulator
        self.simulation_log = []   # Track all events like simulator
        self.previous_ufo_data = None  # Store UFO data for next cycle comparison
        
        self.position_pnl_tracker = {} # To track P&L for trailing stops
        
        # Helper function to parse config values with comments
        def parse_config_value(value, default):
            if isinstance(value, str):
                # Remove inline comments and extra spaces
                clean_value = value.split('#')[0].split('(')[0].strip()
                try:
                    return float(clean_value) if '.' in clean_value else int(clean_value)
                except ValueError:
                    return default
            return value

        # --- Simulator-style config parsing ---
        portfolio_stop_raw = self.config['trading'].get('portfolio_equity_stop', '-7.0')
        self.portfolio_equity_stop = parse_config_value(portfolio_stop_raw, -7.0)
        
        # Read cycle period from config (default 40 minutes if not specified)
        cycle_period_raw = config['trading'].get('cycle_period_minutes', '40')
        self.cycle_period_minutes = parse_config_value(cycle_period_raw, 40)
        self.cycle_period_seconds = self.cycle_period_minutes * 60
        
        # Continuous monitoring variables - FULLY CONFIG-DRIVEN
        self.last_position_update = None
        position_freq_raw = config['trading'].get('position_update_frequency_minutes', '5')
        self.position_update_frequency_minutes = parse_config_value(position_freq_raw, 5)
        self.position_update_frequency_seconds = self.position_update_frequency_minutes * 60
        self.continuous_monitoring_enabled = True
        self.portfolio_history = []  # Track portfolio value over time
        
        # Priority check frequency from config
        priority_check_raw = config['trading'].get('priority_check_frequency_minutes', '10')
        self.priority_check_frequency_minutes = parse_config_value(priority_check_raw, 10)
        self.priority_check_frequency_seconds = self.priority_check_frequency_minutes * 60
        
        # Position Management Thresholds - FULLY CONFIG-DRIVEN
        max_lot_raw = config['trading'].get('max_lot_size', '0.10')
        self.max_lot_size = parse_config_value(max_lot_raw, 0.10)
        
        # Risk-based position sizing parameters
        risk_per_trade_raw = config['trading'].get('risk_per_trade_percent', '1.0')
        self.risk_per_trade_percent = parse_config_value(risk_per_trade_raw, 1.0)
        
        use_dynamic_sizing_raw = config['trading'].get('use_dynamic_position_sizing', 'true')
        self.use_dynamic_position_sizing = use_dynamic_sizing_raw.lower().strip() == 'true'
        
        default_sl_pips_raw = config['trading'].get('default_stop_loss_pips', '30')
        self.default_stop_loss_pips = parse_config_value(default_sl_pips_raw, 30)
        
        min_lot_raw = config['trading'].get('min_lot_size', '0.01')
        self.min_lot_size = parse_config_value(min_lot_raw, 0.01)
        
        take_profit_raw = config['trading'].get('take_profit_threshold', '75')
        self.take_profit_threshold = parse_config_value(take_profit_raw, 75)
        
        stop_loss_amount_raw = config['trading'].get('stop_loss_threshold_amount', '-50')
        self.stop_loss_threshold_amount = parse_config_value(stop_loss_amount_raw, -50)
        
        time_exit_raw = config['trading'].get('time_based_exit_hours', '4')
        self.time_based_exit_hours = parse_config_value(time_exit_raw, 4)
        
        trailing_activation_raw = config['trading'].get('trailing_stop_activation', '30')
        self.trailing_stop_activation = parse_config_value(trailing_activation_raw, 30)
        
        trailing_ratio_raw = config['trading'].get('trailing_stop_ratio', '0.7')
        self.trailing_stop_ratio = parse_config_value(trailing_ratio_raw, 0.7)
        
        high_risk_raw = config['trading'].get('high_risk_alert_threshold', '-75')
        self.high_risk_alert_threshold = parse_config_value(high_risk_raw, -75)
        
        rapid_change_raw = config['trading'].get('rapid_portfolio_change_threshold', '1.0')
        self.rapid_portfolio_change_threshold = parse_config_value(rapid_change_raw, 1.0)
        
        warning_ratio_raw = config['trading'].get('portfolio_stop_warning_ratio', '0.8')
        self.portfolio_stop_warning_ratio = parse_config_value(warning_ratio_raw, 0.8)
        
        # UFO Analysis Parameters - FULLY CONFIG-DRIVEN
        ufo_change_raw = config['trading'].get('ufo_strength_change_threshold', '2.5')
        self.ufo_strength_change_threshold = parse_config_value(ufo_change_raw, 2.5)
        
        ufo_exit_raw = config['trading'].get('ufo_exit_signals_threshold', '3')
        self.ufo_exit_signals_threshold = parse_config_value(ufo_exit_raw, 3)
        
        ufo_adj_threshold_raw = config['trading'].get('ufo_price_adjustment_threshold', '1.0')
        self.ufo_price_adjustment_threshold = parse_config_value(ufo_adj_threshold_raw, 1.0)
        
        ufo_adj_pips_raw = config['trading'].get('ufo_price_adjustment_pips', '1')
        self.ufo_price_adjustment_pips = parse_config_value(ufo_adj_pips_raw, 1)
        
        # Data Collection Parameters - FULLY CONFIG-DRIVEN
        self.data_collection_bars = {
            mt5.TIMEFRAME_M5: parse_config_value(config['trading'].get('data_collection_bars_m5', '240'), 240),
            mt5.TIMEFRAME_M15: parse_config_value(config['trading'].get('data_collection_bars_m15', '80'), 80),
            mt5.TIMEFRAME_H1: parse_config_value(config['trading'].get('data_collection_bars_h1', '20'), 20),
            mt5.TIMEFRAME_H4: parse_config_value(config['trading'].get('data_collection_bars_h4', '120'), 120),
            mt5.TIMEFRAME_D1: parse_config_value(config['trading'].get('data_collection_bars_d1', '100'), 100)
        }
        
        # Session Timing Parameters - FULLY CONFIG-DRIVEN
        session_start_hour_raw = config['trading'].get('session_start_hour', '8')
        self.session_start_hour = parse_config_value(session_start_hour_raw, 8)
        
        session_start_minute_raw = config['trading'].get('session_start_minute', '0')
        self.session_start_minute = parse_config_value(session_start_minute_raw, 0)
        
        session_end_hour_raw = config['trading'].get('session_end_hour', '20')
        self.session_end_hour = parse_config_value(session_end_hour_raw, 20)
        
        session_end_minute_raw = config['trading'].get('session_end_minute', '0')
        self.session_end_minute = parse_config_value(session_end_minute_raw, 0)
        
        self.llm_client = LLMClient(api_key=config['openrouter']['api_key'])

        self.mt5_collector = MT5DataCollector(
            login=config['mt5']['login'],
            password=config['mt5']['password'],
            server=config['mt5']['server'],
            path=config['mt5']['path']
        )

        # --- Simulator-style Initial Balance ---
        self.initial_balance = 0.0
        try:
            if self.mt5_collector.connect():
                account_info = mt5.account_info()
                if account_info:
                    self.initial_balance = account_info.balance
                    print(f"✅ Initial balance set to: ${self.initial_balance:,.2f}")
                else:
                    print("⚠️ Could not retrieve account info to set initial balance.")
            else:
                print("⚠️ MT5 connection failed, could not set initial balance.")
        except Exception as e:
            print(f"❌ Error setting initial balance: {e}")


        self.trade_executor = TradeExecutor(self.mt5_collector, self.config)
        self.ufo_engine = UFOTradingEngine(config)

        # Get symbols from config for TraderAgent
        symbols_str = config['trading'].get('symbols', '')
        symbols_list = [s.strip() for s in symbols_str.split(',') if s.strip()]
        
        self.agents = {
            "data_analyst": DataAnalystAgent("DataAnalyst", self.mt5_collector),
            "researcher": MarketResearcherAgent("MarketResearcher", self.llm_client),
            "trader": TraderAgent("Trader", self.llm_client, self.mt5_collector, symbols=symbols_list),
            "risk_manager": RiskManagerAgent("RiskManager", self.llm_client, self.mt5_collector, self.config),
            "fund_manager": FundManagerAgent("FundManager", self.llm_client)
        }

        self.communication_bus = CommunicationBus()
        self.ufo_calculator = UfoCalculator(config['trading']['currencies'].split(','))

        # Initialize Dynamic Reinforcement Engine (respects config setting)
        self.dynamic_reinforcement_engine = DynamicReinforcementEngine(config)
        config_setting = config['trading'].get('dynamic_reinforcement_enabled', 'false').split('#')[0].strip()
        if self.dynamic_reinforcement_engine.enabled:
            print(f"✅ Dynamic Reinforcement Engine enabled per config.ini (dynamic_reinforcement_enabled = {config_setting})")
        else:
            print(f"⚠️ Dynamic Reinforcement Engine disabled per config.ini (dynamic_reinforcement_enabled = {config_setting})")

        # For UFO exit signal logic
        self.previous_ufo_data = None

    def check_portfolio_equity_stop_simulator_style(self, current_equity):
        """
        Check if portfolio-level stop loss is breached, using the simulator's logic.
        """
        if self.initial_balance <= 0:
            return False, "Invalid initial balance for drawdown calculation"

        current_drawdown = ((current_equity - self.initial_balance) / self.initial_balance) * 100

        if current_drawdown <= self.portfolio_equity_stop:
            return True, f"Portfolio stop breached: {current_drawdown:.2f}% (limit: {self.portfolio_equity_stop}%)"

        return False, f"Portfolio healthy: {current_drawdown:.2f}% drawdown"

    def calculate_dynamic_lot_size(self, symbol, stop_loss_pips=None):
        """
        Calculate dynamic lot size based on risk management parameters.
        Uses account balance, risk percentage, and stop loss to determine position size.
        """
        try:
            # Skip dynamic sizing if disabled
            if not self.use_dynamic_position_sizing:
                return self.max_lot_size  # Return max configured lot size
            
            # Connect to MT5 to get account info
            if not self.mt5_collector.connect():
                print(f"⚠️ Failed to connect to MT5 for lot size calculation, using min lot size")
                return self.min_lot_size
            
            account_info = mt5.account_info()
            if not account_info:
                print(f"⚠️ Could not get account info for lot size calculation")
                return self.min_lot_size
            
            # Get account balance and calculate risk amount
            account_balance = account_info.balance
            risk_amount = account_balance * (self.risk_per_trade_percent / 100)
            
            # Use provided stop loss or default from config
            sl_pips = stop_loss_pips if stop_loss_pips else self.default_stop_loss_pips
            
            # Get symbol info for pip value calculation
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                print(f"⚠️ Could not get symbol info for {symbol}, using min lot size")
                return self.min_lot_size
            
            # Calculate pip value per standard lot
            # For most pairs: 1 pip = 0.0001, for JPY pairs: 1 pip = 0.01
            pip_multiplier = self.get_pip_value_multiplier(symbol)
            
            # Get current price for pip value calculation
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                print(f"⚠️ Could not get tick data for {symbol}, using min lot size")
                return self.min_lot_size
            
            # Calculate pip value in account currency
            # This is simplified - in production you'd need to handle currency conversions
            point_value = symbol_info.trade_tick_value
            point_size = symbol_info.point
            
            # Calculate pip value for 1 standard lot
            if point_size > 0:
                pip_value_per_lot = (point_value * 10) if 'JPY' not in symbol else point_value
            else:
                # Fallback calculation
                pip_value_per_lot = 10  # Default $10 per pip for standard lot
            
            # Calculate lot size: Risk Amount / (Stop Loss in Pips × Pip Value per Lot)
            if sl_pips > 0 and pip_value_per_lot > 0:
                calculated_lot_size = risk_amount / (sl_pips * pip_value_per_lot)
            else:
                calculated_lot_size = self.min_lot_size
            
            # Round to broker's lot step (usually 0.01)
            lot_step = symbol_info.volume_step
            if lot_step > 0:
                calculated_lot_size = round(calculated_lot_size / lot_step) * lot_step
            
            # Apply min and max constraints
            final_lot_size = max(self.min_lot_size, min(calculated_lot_size, self.max_lot_size))
            
            # Log the calculation
            print(f"📊 Dynamic Lot Size Calculation for {symbol}:")
            print(f"   Account Balance: ${account_balance:,.2f}")
            print(f"   Risk per Trade: {self.risk_per_trade_percent}% = ${risk_amount:,.2f}")
            print(f"   Stop Loss: {sl_pips} pips")
            print(f"   Pip Value per Lot: ${pip_value_per_lot:.2f}")
            print(f"   Calculated Size: {calculated_lot_size:.2f} lots")
            print(f"   Final Size (after limits): {final_lot_size:.2f} lots")
            
            return final_lot_size
            
        except Exception as e:
            print(f"❌ Error calculating dynamic lot size: {e}")
            return self.min_lot_size  # Return minimum on error
    
    def validate_and_correct_currency_pair(self, pair):
        """
        Validate and correct currency pair format using centralized validator.
        Handles invalid pairs like JPYUSD -> USDJPY, CADUSD -> USDCAD, etc.
        """
        symbol_suffix = self.config['mt5'].get('symbol_suffix', '')
        corrected_pair, was_inverted = PairValidator.validate_and_correct(pair, symbol_suffix)
        
        if corrected_pair:
            if was_inverted:
                print(f"⚠️ Correcting currency pair: {pair} -> {corrected_pair} (direction will be inverted)")
            return corrected_pair, was_inverted
        else:
            print(f"❌ Invalid currency pair: {pair} - skipping trade")
            return None, False

    def calculate_ufo_entry_price(self, symbol, direction, ufo_data):
        """
        Calculate optimal entry price based on UFO methodology and live market data.
        Adapted from the simulator.
        """
        try:
            # Always try to connect fresh for this operation
            connected = self.mt5_collector.connect()
            if not connected:
                print(f"⚠️ Failed to connect to MT5 for symbol {symbol}")
                return None

            # First check if symbol exists and add to Market Watch if needed
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                print(f"⚠️ Symbol {symbol} not found in MT5. Trying to add to Market Watch...")
                if not mt5.symbol_select(symbol, True):
                    print(f"⚠️ Failed to add {symbol} to Market Watch, MT5 error: {mt5.last_error()}")
                    self.mt5_collector.disconnect()
                    return None
                # Check again after adding
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info is None:
                    print(f"⚠️ Symbol {symbol} still not available after adding to Market Watch")
                    self.mt5_collector.disconnect()
                    return None
                print(f"✅ Successfully added {symbol} to Market Watch")

            # Ensure symbol is visible
            if not symbol_info.visible:
                print(f"⚠️ Symbol {symbol} is not visible, trying to make it visible...")
                if not mt5.symbol_select(symbol, True):
                    print(f"⚠️ Failed to make {symbol} visible")
                    self.mt5_collector.disconnect()
                    return None
                # Wait a moment for the symbol to become available
                time.sleep(0.5)
                # Refresh symbol info after selection
                symbol_info = mt5.symbol_info(symbol)
                print(f"✅ Symbol {symbol} visibility status: {symbol_info.visible if symbol_info else 'None'}")

            # Ensure symbol is selected for Market Watch (even if visible)
            mt5.symbol_select(symbol, True)
            time.sleep(0.2)  # Small delay to ensure selection is processed

            # Get tick data
            print(f"🔍 Attempting to get tick data for {symbol}...")
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                error_code, error_desc = mt5.last_error()
                print(f"⚠️ Could not get live tick for {symbol}, MT5 error: {error_code} - {error_desc}")
                
                # Try alternative approach - get latest M1 bar instead
                print(f"🔄 Fallback: Trying to get latest M1 bar for {symbol}...")
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1)
                if rates is not None and len(rates) > 0:
                    # Use the close price from the latest M1 bar
                    latest_close = rates[0]['close']
                    print(f"✅ Got fallback price from M1 bar: {latest_close:.5f}")
                    return latest_close
                else:
                    print(f"⚠️ Could not get M1 bar data either for {symbol}")
                    self.mt5_collector.disconnect()
                    return None
            
            print(f"✅ Got tick data for {symbol}: bid={tick.bid:.5f}, ask={tick.ask:.5f}")

            try:
                base_price = tick.ask if direction == 'BUY' else tick.bid

                if ufo_data:
                    clean_symbol = symbol.replace(self.config['mt5'].get('symbol_suffix', ''), '')
                    
                    if len(clean_symbol) >= 6:
                        base_currency = clean_symbol[:3]
                        quote_currency = clean_symbol[3:6]

                        primary_tf = mt5.TIMEFRAME_M5
                        raw_ufo_data = ufo_data.get('raw_data', ufo_data)

                        if primary_tf in raw_ufo_data:
                            strength_data = raw_ufo_data[primary_tf]
                            
                            # Safely get currency strength data with proper fallbacks
                            base_data = strength_data.get(base_currency, None)
                            quote_data = strength_data.get(quote_currency, None)
                            
                            # Handle different data types (Series, list, or None)
                            if base_data is not None and hasattr(base_data, '__len__') and len(base_data) > 0:
                                if hasattr(base_data, 'iloc'):
                                    # pandas Series
                                    base_strength = base_data.iloc[-1] if len(base_data) > 0 else 0.0
                                else:
                                    # list or array
                                    base_strength = base_data[-1] if len(base_data) > 0 else 0.0
                            else:
                                base_strength = 0.0
                                
                            if quote_data is not None and hasattr(quote_data, '__len__') and len(quote_data) > 0:
                                if hasattr(quote_data, 'iloc'):
                                    # pandas Series
                                    quote_strength = quote_data.iloc[-1] if len(quote_data) > 0 else 0.0
                                else:
                                    # list or array
                                    quote_strength = quote_data[-1] if len(quote_data) > 0 else 0.0
                            else:
                                quote_strength = 0.0
                                
                            strength_diff = base_strength - quote_strength

                            # CONFIG-DRIVEN UFO PRICE ADJUSTMENT LOGIC
                            price_adjustment = 0.0
                            if abs(strength_diff) > self.ufo_price_adjustment_threshold:
                                pip_size = 0.0001 * self.ufo_price_adjustment_pips  # Config-driven pip count
                                if direction == 'BUY' and strength_diff > 0:
                                    price_adjustment = -base_price * pip_size  # Config-driven pip improvement
                                elif direction == 'SELL' and strength_diff < 0:
                                    price_adjustment = base_price * pip_size  # Config-driven pip improvement

                            optimal_price = base_price + price_adjustment
                            print(f"UFO Entry Price for {symbol}: Base={base_price:.5f}, Adj={price_adjustment:.5f}, Optimal={optimal_price:.5f}")
                            return max(optimal_price, base_price * 0.98) # Safety net

                return base_price
                
            except Exception as ufo_error:
                print(f"❌ UFO calculation error for {symbol}: {ufo_error}")
                import traceback
                traceback.print_exc()
                # Still return the base price if UFO calculations fail
                base_price = tick.ask if direction == 'BUY' else tick.bid
                return base_price

        except Exception as e:
            print(f"⚠️ Error calculating UFO entry price for {symbol}: {e}")
            return None

    def get_pip_value_multiplier(self, symbol):
        """Get correct pip value multiplier for different currency pairs, as in the simulator."""
        symbol_clean = symbol.replace('-ECN', '').upper()

        # JPY pairs use 1000 multiplier (pip = 0.01)
        jpy_pairs = ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY', 'CHFJPY', 'CADJPY']
        if any(jpy_pair in symbol_clean for jpy_pair in jpy_pairs):
            return 1000

        # Most other forex pairs use 10000 multiplier (pip = 0.0001)
        return 10000

    def _log_enhanced_analysis(self, oscillation_analysis, uncertainty_metrics, coherence_analysis):
        """Log enhanced UFO analysis results, from simulator."""
        try:
            # Log market state summary across timeframes
            for timeframe, metrics in uncertainty_metrics.items():
                overall_state = metrics.get('overall_state', 'unknown')
                confidence = metrics.get('confidence_level', 'unknown')
                scaling = metrics.get('recommended_position_scaling', 1.0)

                print(f"🔍 {timeframe}: {overall_state} (confidence: {confidence}, scaling: {scaling:.2f})")

            # Log coherence insights
            strong_coherence_count = sum(1 for curr_data in coherence_analysis.values()
                                       if curr_data.get('coherence_level') == 'strong')
            total_currencies = len(coherence_analysis)

            if total_currencies > 0:
                coherence_ratio = strong_coherence_count / total_currencies
                print(f"📊 Timeframe Coherence: {strong_coherence_count}/{total_currencies} currencies show strong coherence ({coherence_ratio:.1%})")
            
            # ADDED: Log mean reversion opportunities (EXACT CLONE from simulator lines 576-583)
            mean_reversion_signals = 0
            for tf_data in oscillation_analysis.values():
                mean_reversion_signals += sum(1 for curr_data in tf_data.values() 
                                             if curr_data.get('mean_reversion_signal', False))
            
            if mean_reversion_signals > 0:
                self.log_event(f"🔄 Mean Reversion Signals: {mean_reversion_signals} detected across timeframes")

        except Exception as e:
            print(f"⚠️ Error logging enhanced analysis: {e}")

    def analyze_ufo_exit_signals(self, current_ufo_data, previous_ufo_data):
        """Analyze UFO data for exit signals based on currency strength changes, from simulator."""
        exit_signals = []

        if previous_ufo_data is None:
            return exit_signals

        # Extract raw UFO data from enhanced structure
        current_raw_data = current_ufo_data.get('raw_data', {})
        previous_raw_data = previous_ufo_data.get('raw_data', {})

        # Check for currency strength reversals across timeframes
        for timeframe in current_raw_data.keys():
            if timeframe not in previous_raw_data:
                continue

            current_strengths = current_raw_data[timeframe]
            previous_strengths = previous_raw_data[timeframe]

            currency_list = list(current_strengths.keys())

            # Detect significant strength changes
            for currency in currency_list:
                if currency not in previous_strengths:
                    continue

                # Safely get current strength value
                current_currency_data = current_strengths[currency]
                if hasattr(current_currency_data, '__len__') and len(current_currency_data) > 0:
                    if hasattr(current_currency_data, 'iloc'):
                        # pandas Series
                        current_strength = current_currency_data.iloc[-1] if len(current_currency_data) > 0 else 0.0
                    else:
                        # list or array
                        current_strength = current_currency_data[-1] if len(current_currency_data) > 0 else 0.0
                else:
                    continue  # Skip if no valid data
                
                # Use last 5 values for a more stable average
                previous_currency_data = previous_strengths[currency]
                if hasattr(previous_currency_data, '__len__') and len(previous_currency_data) > 0:
                    if hasattr(previous_currency_data, 'iloc'):
                        # pandas Series
                        recent_count = min(5, len(previous_currency_data))
                        previous_strength_values = [previous_currency_data.iloc[i] for i in range(-recent_count, 0)]
                    else:
                        # list or array
                        previous_strength_values = previous_currency_data[-5:] if len(previous_currency_data) >= 5 else list(previous_currency_data)
                else:
                    continue  # Skip if no valid previous data
                    
                if not previous_strength_values: 
                    continue
                avg_previous = sum(previous_strength_values) / len(previous_strength_values)

                # SIGNAL STRENGTH REVERSAL - USE CONFIG-DRIVEN THRESHOLD
                if abs(current_strength - avg_previous) > self.ufo_strength_change_threshold:
                    direction_change = "strengthening" if current_strength > avg_previous else "weakening"
                    exit_signals.append({
                        'currency': currency,
                        'timeframe': timeframe,
                        'change': current_strength - avg_previous,
                        'reason': f"{currency} now significantly {direction_change} on {timeframe}"
                    })

        return exit_signals

    def close_affected_positions(self, exit_signals):
        """Close positions affected by strong exit signals, adapted for live trading."""
        positions_closed = 0
        if not exit_signals:
            return positions_closed

        print("🚨 UFO Exit Signals detected. Checking for positions to close.")
        currencies_to_close = {signal['currency'] for signal in exit_signals}

        open_positions = self.agents['risk_manager'].portfolio_manager.get_positions()
        if open_positions is None or open_positions.empty:
            return positions_closed

        suffix = self.config['mt5'].get('symbol_suffix', '')

        for _, position in open_positions.iterrows():
            symbol = position.symbol.replace(suffix, '')

            if len(symbol) >= 6:
                base_currency = symbol[:3]
                quote_currency = symbol[3:6]

                if base_currency in currencies_to_close or quote_currency in currencies_to_close:
                    print(f"🎯 Closing {position.symbol} ({position.ticket}) due to exit signal for {base_currency} or {quote_currency}.")
                    
                    # ADDED: Track closed trade (EXACT CLONE from simulator)
                    closed_trade_info = {
                        'ticket': position.ticket,
                        'symbol': position.symbol,
                        'type': position.type,
                        'volume': position.volume,
                        'price_open': position.price_open,
                        'price_close': position.price_current,
                        'profit': position.profit,
                        'open_time': position.time,
                        'close_time': datetime.now(),
                        'close_reason': f'UFO exit signal for {base_currency}/{quote_currency}'
                    }
                    self.closed_trades.append(closed_trade_info)
                    
                    self.trade_executor.close_trade(position.ticket)
                    positions_closed += 1

        if positions_closed > 0:
            print(f"✅ Closed {positions_closed} positions based on UFO exit signals.")

        return positions_closed

    def _manage_open_positions_simulator_style(self):
        """
        Manages open positions using the logic from the full_day_simulation.
        This includes custom P&L calculation and rule-based closures.
        """
        try:
            open_positions = self.agents['risk_manager'].portfolio_manager.get_positions()
            if open_positions is None or open_positions.empty:
                if self.position_pnl_tracker:
                    print("All positions closed, clearing P&L tracker.")
                    self.position_pnl_tracker.clear()
                return

            # Get current prices for all position symbols
            market_data = self.get_real_time_market_data_for_positions(open_positions)

            # Clean up tracker from closed positions
            open_tickets = [pos.ticket for _, pos in open_positions.iterrows()]
            for ticket in list(self.position_pnl_tracker.keys()):
                if ticket not in open_tickets:
                    print(f"Position {ticket} closed, removing from P&L tracker.")
                    del self.position_pnl_tracker[ticket]

            positions_to_close = []

            for _, position in open_positions.iterrows():
                ticket = position.ticket
                symbol = position.symbol

                if symbol not in market_data:
                    print(f"⚠️ No market data for {symbol}, cannot manage position {ticket}.")
                    continue

                # For BUY (type 0), we close at 'bid'. For SELL (type 1), we close at 'ask'.
                current_price = market_data[symbol]['bid'] if position.type == 0 else market_data[symbol]['ask']

                # --- P&L Calculation (from simulator) ---
                pip_multiplier = self.get_pip_value_multiplier(symbol)
                price_diff = current_price - position.price_open
                if position.type == 1: # SELL
                    price_diff = -price_diff

                pnl = price_diff * position.volume * pip_multiplier

                # --- Trailing Stop Logic (from simulator) ---
                if ticket not in self.position_pnl_tracker:
                    self.position_pnl_tracker[ticket] = {'peak_pnl': pnl}
                elif pnl > self.position_pnl_tracker[ticket]['peak_pnl']:
                    self.position_pnl_tracker[ticket]['peak_pnl'] = pnl

                peak_pnl = self.position_pnl_tracker[ticket]['peak_pnl']

                # --- CONFIG-DRIVEN Closing Conditions ---
                close_reason = None
                position_age_hours = (datetime.utcnow() - pd.to_datetime(position.time, unit='s')).total_seconds() / 3600

                if pnl > self.take_profit_threshold:
                    close_reason = f"take profit (P&L: ${pnl:.2f})"
                elif pnl < self.stop_loss_threshold_amount:
                    close_reason = f"stop loss (P&L: ${pnl:.2f})"
                elif position_age_hours > self.time_based_exit_hours:
                    close_reason = f"time-based exit (age: {position_age_hours:.1f} hours)"
                elif peak_pnl > self.trailing_stop_activation and pnl < peak_pnl * self.trailing_stop_ratio:
                    close_reason = f"trailing stop (P&L dropped to ${pnl:.2f} from peak of ${peak_pnl:.2f})"

                if close_reason:
                    positions_to_close.append({'ticket': ticket, 'symbol': symbol, 'reason': close_reason})

            # --- Execute Closures ---
            if positions_to_close:
                print(f"\n--- Simulator-Style Position Management ---")
                for closure in positions_to_close:
                    print(f"🎯 Closing {closure['symbol']} ({closure['ticket']}): {closure['reason']}")
                    
                    # ADDED: Track closed trade before closing (EXACT CLONE from simulator)
                    # Get the full position data to save
                    position_data = next((pos for _, pos in open_positions.iterrows() if pos.ticket == closure['ticket']), None)
                    if position_data is not None:
                        # Calculate final P&L for the closed trade
                        closed_trade_info = {
                            'ticket': closure['ticket'],
                            'symbol': closure['symbol'],
                            'type': position_data.type,
                            'volume': position_data.volume,
                            'price_open': position_data.price_open,
                            'price_close': market_data[closure['symbol']]['bid'] if position_data.type == 0 else market_data[closure['symbol']]['ask'],
                            'profit': closure.get('pnl', 0.0),  # Use calculated P&L
                            'open_time': position_data.time,
                            'close_time': datetime.now(),
                            'close_reason': closure['reason']
                        }
                        self.closed_trades.append(closed_trade_info)
                        self.log_event(f"📝 Added to closed trades: {closure['symbol']} P&L: ${closed_trade_info['profit']:.2f}")
                    
                    self.trade_executor.close_trade(closure['ticket'])

        except Exception as e:
            print(f"❌ Error in simulator-style position management: {e}")

    def _perform_dynamic_reinforcement(self, ufo_data):
        """
        Performs dynamic reinforcement checks and executions, fully config-driven.
        """
        if not self.dynamic_reinforcement_engine.enabled:
            return

        # Check if it's time to perform reinforcement check based on config frequency
        current_time = datetime.now()
        if not self.dynamic_reinforcement_engine.should_check_reinforcement(current_time):
            return

        print(f"🎯 Checking for Dynamic Reinforcement opportunities (frequency: {self.dynamic_reinforcement_engine.check_frequency_minutes} min)...")
        try:
            open_positions = self.agents['risk_manager'].portfolio_manager.get_positions()
            if open_positions is None or open_positions.empty:
                # Update the check time even if no positions
                self.dynamic_reinforcement_engine.last_reinforcement_check = current_time
                return

            current_market_data = self.get_real_time_market_data_for_positions(open_positions)

            # The DRE in the simulator uses a pandas DataFrame, so we convert the MT5 position objects
            # to a compatible format.
            sim_positions_list = []
            for _, pos in open_positions.iterrows():
                sim_positions_list.append({
                    'ticket': pos.ticket, 'symbol': pos.symbol, 'direction': 'BUY' if pos.type == 0 else 'SELL',
                    'volume': pos.volume, 'entry_price': pos.price_open, 'current_price': pos.price_current,
                    'pnl': pos.profit, 'timestamp': pd.to_datetime(pos.time, unit='s')
                })

            market_events = self.dynamic_reinforcement_engine.detect_market_events(
                sim_positions_list, current_market_data, ufo_data
            )

            # Update check time regardless of events found
            self.dynamic_reinforcement_engine.last_reinforcement_check = current_time

            if not market_events:
                print("No dynamic reinforcement events detected.")
                return

            print(f"🎯 Dynamic Reinforcement: {len(market_events)} market events detected")
            for event in market_events:
                position_dict = event.get('position')
                if not position_dict:
                    continue

                reinforcement_plan, message = self.dynamic_reinforcement_engine.calculate_dynamic_reinforcement(
                    position_dict, event, current_market_data, ufo_data
                )

                if reinforcement_plan:
                    print(f"  ⚡ {event['type']}: {position_dict['symbol']} - {message}")
                    print(f"    📊 Reinforcement: {reinforcement_plan['additional_lots']:.2f} lots")
                    print(f"    🔧 Config-driven parameters: trigger={self.dynamic_reinforcement_engine.price_movement_trigger_pips} pips, max={self.dynamic_reinforcement_engine.max_reinforcements_per_position}")

                    # Execute the reinforcement trade
                    trade_type = mt5.ORDER_TYPE_BUY if position_dict['direction'] == 'BUY' else mt5.ORDER_TYPE_SELL
                    success = self.trade_executor.execute_ufo_trade(
                        symbol=position_dict['symbol'],
                        trade_type=trade_type,
                        volume=reinforcement_plan['additional_lots'],
                        comment=f"Dynamic {reinforcement_plan.get('type', 'Reinforcement')}"
                    )
                    
                    # Record the reinforcement execution if successful
                    if success:
                        self.dynamic_reinforcement_engine.record_reinforcement(position_dict, reinforcement_plan)
                        print(f"    ✅ Reinforcement recorded and executed")
                    else:
                        print(f"    ❌ Reinforcement execution failed")
                else:
                    print(f"  ⏸️ {position_dict['symbol']}: {message}")

        except Exception as e:
            print(f"❌ Error during config-driven dynamic reinforcement: {e}")
            # Ensure check time is updated even on error
            self.dynamic_reinforcement_engine.last_reinforcement_check = current_time


    def _run_continuous_monitoring(self, ufo_data):
        """
        Runs the faster, inner loop for continuous monitoring tasks.
        This includes managing open positions and dynamic reinforcement.
        """
        print("\n--- Continuous Monitoring ---")
        self._manage_open_positions_simulator_style()
        self._perform_dynamic_reinforcement(ufo_data)
        print("--- End Continuous Monitoring ---\n")

    def simulate_single_cycle(self, current_time):
        """Simulate a single trading cycle - EXACT CLONE from simulator"""
        self.cycle_count += 1
        cycle_time_str = current_time.strftime('%H:%M')
        
        self.log_event(f"\n" + "="*60)
        self.log_event(f"CYCLE {self.cycle_count} - {cycle_time_str} GMT")
        self.log_event("="*60)
        
        # Check session status
        session_active = self.check_session_status(current_time)
        if not session_active:
            self.log_event(f"⏰ Outside trading hours at {cycle_time_str} GMT - Skipping cycle")
            return True
        
        # 1. Data Collection
        self.log_event("📊 PHASE 1: Data Collection")
        price_data = self.collect_market_data()
        
        # 2. UFO Analysis
        self.log_event("🛸 PHASE 2: UFO Analysis")
        ufo_data = self.calculate_ufo_indicators(price_data)
        
        # 3. Economic Calendar
        self.log_event("📅 PHASE 3: Economic Calendar")
        economic_events = self.get_economic_events()
        
        # 4. Market Research
        self.log_event("🔍 PHASE 4: Market Research")
        research_result = self.conduct_market_research(ufo_data, economic_events)
        
        # 5. UFO Portfolio Management (Priority Check)
        self.log_event("💼 PHASE 5: UFO Portfolio Management")
        
        # UFO METHODOLOGY: Check portfolio-level stop FIRST
        portfolio_stop_breached, stop_reason = self.check_portfolio_equity_stop_live()
        if portfolio_stop_breached:
            self.log_event(f"🚨 UFO PORTFOLIO STOP TRIGGERED: {stop_reason}")
            self.log_event("🚨 Closing ALL positions - no individual stops needed!")
            
            # ADDED: Track all closed trades before closing (EXACT CLONE from simulator)
            open_positions = self.agents['risk_manager'].portfolio_manager.get_positions()
            if open_positions is not None and not open_positions.empty:
                for _, position in open_positions.iterrows():
                    closed_trade_info = {
                        'ticket': position.ticket,
                        'symbol': position.symbol,
                        'type': position.type,
                        'volume': position.volume,
                        'price_open': position.price_open,
                        'price_close': position.price_current,
                        'profit': position.profit,
                        'open_time': position.time,
                        'close_time': datetime.now(),
                        'close_reason': f'Portfolio stop: {stop_reason}'
                    }
                    self.closed_trades.append(closed_trade_info)
            
            self.trade_executor.close_all_positions()
            self.log_event("🚨 All positions closed. UFO Portfolio Stop engaged.")
            return True
        
        # UFO: Check session end timing (with actual economic events)
        should_close, close_reason = self.ufo_engine.should_close_for_session_end(economic_events)
        if should_close:
            self.log_event(f"🌅 UFO SESSION END: {close_reason}")
            self.log_event("🌅 Closing all positions for session end")
            
            # ADDED: Track all closed trades before closing for session end
            open_positions = self.agents['risk_manager'].portfolio_manager.get_positions()
            if open_positions is not None and not open_positions.empty:
                for _, position in open_positions.iterrows():
                    closed_trade_info = {
                        'ticket': position.ticket,
                        'symbol': position.symbol,
                        'type': position.type,
                        'volume': position.volume,
                        'price_open': position.price_open,
                        'price_close': position.price_current,
                        'profit': position.profit,
                        'open_time': position.time,
                        'close_time': datetime.now(),
                        'close_reason': f'Session end: {close_reason}'
                    }
                    self.closed_trades.append(closed_trade_info)
            
            self.trade_executor.close_all_positions()
            return True
        
        # UFO: Analyze exit signals based on currency strength changes
        if self.previous_ufo_data and ufo_data:
            exit_signals = self.analyze_ufo_exit_signals(ufo_data, self.previous_ufo_data)
            if exit_signals:
                self.log_event(f"📈 UFO Exit Signals detected: {len(exit_signals)} currency changes")
                for signal in exit_signals:
                    self.log_event(f"⚠️ {signal['reason']} (change: {signal['change']:.2f})")
                
                # CONFIG-DRIVEN AUTO-CLOSE ON STRONG SIGNALS
                if len(exit_signals) >= self.ufo_exit_signals_threshold:
                    self.log_event("🚨 STRONG EXIT SIGNALS detected: Auto-closing positions")
                    positions_closed = self.close_affected_positions(exit_signals)
                    self.log_event(f"🚨 Auto-closed {positions_closed} positions based on strong exit signals")
        
        # Store UFO data for next cycle comparison
        if ufo_data:
            self.previous_ufo_data = ufo_data
        
        current_positions = self.assess_portfolio(current_time)
        
        # 6. Trading Decisions
        self.log_event("🎯 PHASE 6: Trading Decisions")
        trade_decisions = self.generate_trade_decisions(research_result, current_positions)
        
        # 7. Risk Assessment
        self.log_event("⚖️ PHASE 7: Risk Assessment")
        risk_assessment = self.assess_risk(trade_decisions)
        
        # 8. Fund Manager Authorization
        self.log_event("💰 PHASE 8: Fund Manager Authorization")
        authorization = self.get_fund_authorization(trade_decisions, risk_assessment)
        
        # 9. Trade Execution
        self.log_event("⚡ PHASE 9: Trade Execution")
        executed_trades = self.execute_approved_trades_live(authorization, trade_decisions, current_positions, ufo_data, current_time)
        
        # 10. Cycle Summary
        self.log_event("📋 PHASE 10: Cycle Summary")
        self.generate_cycle_summary(cycle_time_str, executed_trades)
        
        return True
    
    def log_event(self, message):
        """Log events with timestamp - EXACT CLONE from simulator"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.simulation_log.append(log_entry)
        print(log_entry)
    
    def check_session_status(self, current_time):
        """Check if current time is within active trading hours - CONFIG DRIVEN with economic event awareness"""
        hour = current_time.hour
        minute = current_time.minute
        
        # Get session times from config
        start_hour = self.session_start_hour
        start_minute = self.session_start_minute
        end_hour = self.session_end_hour
        end_minute = self.session_end_minute
        
        # Convert current time to minutes for comparison
        current_minutes = hour * 60 + minute
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        
        # Check basic session times first
        if start_minutes >= end_minutes:
            # Session crosses midnight (e.g., 20:00 to 08:00)
            is_active = current_minutes >= start_minutes or current_minutes < end_minutes
        else:
            # Normal session (e.g., 01:00 to 20:00)
            is_active = start_minutes <= current_minutes < end_minutes
        
        if not is_active:
            self.log_event(f"⏰ Outside trading hours: {hour:02d}:{minute:02d} GMT (Session: {start_hour:02d}:{start_minute:02d}-{end_hour:02d}:{end_minute:02d} GMT)")
            return False
        
        # NEW: Check for high-impact economic events in next 90 minutes
        try:
            economic_events = self.get_economic_events()
            if not economic_events.empty:
                # Convert to timezone-aware comparison
                current_dt = pd.to_datetime(current_time, utc=True)
                
                # Look for High impact events within next 90 minutes
                for _, event in economic_events.iterrows():
                    if event.get('impact') == 'High':
                        event_dt = pd.to_datetime(event['date'], utc=True)
                        minutes_until = (event_dt - current_dt).total_seconds() / 60
                        
                        # Check events within next 90 minutes
                        if 0 <= minutes_until <= 90:
                            event_time = event_dt.strftime('%H:%M')
                            self.log_event(f"⚠️ HIGH IMPACT EVENT APPROACHING: {event_time} GMT - {event['country']} {event['title']} (in {minutes_until:.0f} min)")
                            
                            # Close positions before ALL high-impact economic events (60 min before)
                            if minutes_until <= 60:
                                self.log_event(f"🚨 HIGH-IMPACT ECONOMIC EVENT DETECTED - CLOSING ALL POSITIONS FOR RISK MANAGEMENT")
                                self.log_event(f"🚨 Event: {event['country']} - {event['title']} at {event_time} GMT")
                                
                                # ADDED: Track all closed trades before closing for economic event
                                open_positions = self.agents['risk_manager'].portfolio_manager.get_positions()
                                if open_positions is not None and not open_positions.empty:
                                    for _, position in open_positions.iterrows():
                                        closed_trade_info = {
                                            'ticket': position.ticket,
                                            'symbol': position.symbol,
                                            'type': position.type,
                                            'volume': position.volume,
                                            'price_open': position.price_open,
                                            'price_close': position.price_current,
                                            'profit': position.profit,
                                            'open_time': position.time,
                                            'close_time': datetime.now(),
                                            'close_reason': f"High-impact event: {event['country']} - {event['title']}"
                                        }
                                        self.closed_trades.append(closed_trade_info)
                                
                                self.trade_executor.close_all_positions()
                                return False  # Stop trading
        except Exception as e:
            self.log_event(f"⚠️ Error checking economic events: {e}")
        
        return True
    
    def collect_market_data(self):
        """Collect market data for analysis for all symbols - EXACT CLONE from simulator"""
        try:
            symbols = self.config['trading']['symbols'].split(',')
            symbol_suffix = self.config['mt5'].get('symbol_suffix', '')
            all_data = {}
            for symbol in symbols:
                symbol_with_suffix = symbol + symbol_suffix
                timeframes = [mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1, mt5.TIMEFRAME_H4, mt5.TIMEFRAME_D1]
                # USE CONFIG-DRIVEN DATA COLLECTION BARS
                timeframe_bars = self.data_collection_bars

                data = self.agents['data_analyst'].execute({
                    'source': 'mt5',
                    'symbol': symbol_with_suffix,
                    'timeframes': timeframes,
                    'num_bars': timeframe_bars
                })
                if data:
                    all_data[symbol] = data
            
            self.log_event(f"✅ Collected data for {len(all_data)} symbols")
            return all_data
        except Exception as e:
            self.log_event(f"❌ Data collection error: {e}")
            return None
    
    def calculate_ufo_indicators(self, price_data):
        """Calculate UFO indicators with enhanced analysis - EXACT CLONE from simulator"""
        if not price_data:
            return None
            
        try:
            # Reshape the data for the UfoCalculator
            reshaped_data = {}
            for symbol, timeframe_data in price_data.items():
                for timeframe, df in timeframe_data.items():
                    if timeframe not in reshaped_data:
                        reshaped_data[timeframe] = pd.DataFrame()
                    if df is not None and 'close' in df.columns:
                        reshaped_data[timeframe][symbol] = df['close']

            incremental_sums_dict = {}
            for timeframe, price_df in reshaped_data.items():
                variation_data = self.ufo_calculator.calculate_percentage_variation(price_df)
                incremental_sums_dict[timeframe] = self.ufo_calculator.calculate_incremental_sum(variation_data)
            
            ufo_data = self.ufo_calculator.generate_ufo_data(incremental_sums_dict)
            
            # ENHANCED UFO ANALYSIS: Apply new oscillation and uncertainty detection
            oscillation_analysis = self.ufo_calculator.detect_oscillations(ufo_data)
            uncertainty_metrics = self.ufo_calculator.analyze_market_uncertainty(ufo_data, oscillation_analysis)
            coherence_analysis = self.ufo_calculator.detect_timeframe_coherence(ufo_data)
            
            # Store enhanced analysis for decision making
            enhanced_ufo_data = {
                'raw_data': ufo_data,
                'oscillation_analysis': oscillation_analysis,
                'uncertainty_metrics': uncertainty_metrics,
                'coherence_analysis': coherence_analysis
            }
            
            # Log enhanced analysis results
            self._log_enhanced_analysis(oscillation_analysis, uncertainty_metrics, coherence_analysis)
            
            self.log_event(f"✅ Enhanced UFO analysis completed for {len(ufo_data)} timeframes")
            return enhanced_ufo_data
        except Exception as e:
            self.log_event(f"❌ UFO calculation error: {e}")
            return None
    
    def get_economic_events(self):
        """Get economic calendar events - EXACT CLONE from simulator"""
        try:
            raw_events = self.agents['data_analyst'].execute({'source': 'economic_calendar'})
            
            if raw_events is None or raw_events.empty:
                self.log_event("❌ No economic calendar data available")
                return pd.DataFrame()
            
            event_count = len(raw_events)
            self.log_event(f"✅ Retrieved {event_count} economic events")
            return raw_events
            
        except Exception as e:
            self.log_event(f"❌ Economic calendar error: {e}")
            return pd.DataFrame()
    
    def conduct_market_research(self, ufo_data, economic_events):
        """Conduct market research using LLM - EXACT CLONE from simulator"""
        try:
            if not ufo_data:
                return {'consensus': 'No market research due to missing UFO data', 'analysis': 'Error'}
                
            result = self.agents['researcher'].execute(ufo_data, economic_events)
            self.log_event("✅ Market research completed")
            return result
        except Exception as e:
            self.log_event(f"❌ Market research error: {e}")
            return {'consensus': 'Market research error', 'analysis': 'Error occurred'}
    
    def check_portfolio_equity_stop_live(self):
        """Check if portfolio-level stop loss is breached (UFO methodology) - LIVE VERSION"""
        try:
            account_info = self.mt5_collector.connect() and mt5.account_info()
            if not account_info:
                return False, "Could not get account info"
                
            if self.initial_balance <= 0:
                return False, "Invalid initial balance"
                
            current_drawdown = ((account_info.equity - self.initial_balance) / self.initial_balance) * 100
            
            if current_drawdown <= self.portfolio_equity_stop:
                return True, f"Portfolio stop breached: {current_drawdown:.2f}% (limit: {self.portfolio_equity_stop}%)"
            
            return False, f"Portfolio healthy: {current_drawdown:.2f}% drawdown"
        except Exception as e:
            self.log_event(f"❌ Error checking portfolio stop: {e}")
            return False, "Error checking portfolio"
    
    def assess_portfolio(self, current_time=None):
        """Assess current portfolio positions - EXACT CLONE from simulator"""
        try:
            positions = self.agents['risk_manager'].portfolio_manager.get_positions()
            position_count = len(positions) if positions is not None and not positions.empty else 0
            self.log_event(f"✅ Portfolio assessed: {position_count} open positions")
            return positions
        except Exception as e:
            self.log_event(f"❌ Portfolio assessment error: {e}")
            return pd.DataFrame()
    
    def generate_trade_decisions(self, research_result, current_positions):
        """Generate trading decisions using TraderAgent - EXACT CLONE from simulator"""
        try:
            diversification_config = {
                'min_positions_for_session': self.ufo_engine.min_positions_for_session,
                'target_positions_when_available': self.ufo_engine.target_positions_when_available,
                'max_concurrent_positions': self.ufo_engine.max_concurrent_positions
            }
            
            decisions = self.agents['trader'].execute(
                research_result['consensus'],
                current_positions,
                diversification_config=diversification_config
            )
            self.log_event("✅ Trading decisions generated")
            return decisions
        except Exception as e:
            self.log_event(f"❌ Trading decision error: {e}")
            return '{"trades": []}'
    
    def assess_risk(self, trade_decisions):
        """Assess risk of proposed trades - EXACT CLONE from simulator"""
        try:
            assessment = self.agents['risk_manager'].execute(trade_decisions)
            status = assessment.get('portfolio_risk_status', 'Unknown')
            self.log_event(f"✅ Risk assessment: {status}")
            return assessment
        except Exception as e:
            self.log_event(f"❌ Risk assessment error: {e}")
            return {'trade_risk_assessment': 'Error', 'portfolio_risk_status': 'OK'}
    
    def get_fund_authorization(self, trade_decisions, risk_assessment):
        """Get Fund Manager authorization - EXACT CLONE from simulator"""
        try:
            authorization = self.agents['fund_manager'].execute(trade_decisions, risk_assessment)
            decision = "APPROVED" if "APPROVE" in authorization.upper() else "REJECTED"
            self.log_event(f"✅ Fund Manager decision: {decision}")
            return authorization
        except Exception as e:
            self.log_event(f"❌ Fund authorization error: {e}")
            return "REJECT: Authorization error"
    
    def generate_cycle_summary(self, cycle_time, executed_trades):
        """Generate summary for this cycle - EXACT CLONE from simulator"""
        try:
            account_info = self.mt5_collector.connect() and mt5.account_info()
            current_equity = account_info.equity if account_info else self.initial_balance
            open_positions = self.agents['risk_manager'].portfolio_manager.get_positions()
            position_count = len(open_positions) if open_positions is not None and not open_positions.empty else 0
            total_pnl = current_equity - self.initial_balance
            
            self.log_event(f"📊 Cycle {self.cycle_count} Summary ({cycle_time} GMT):")
            self.log_event(f"   Trades Executed: {executed_trades}")
            self.log_event(f"   Total Trades Today: {len(self.trades_executed)}")
            self.log_event(f"   Open Positions: {position_count}/{self.ufo_engine.max_concurrent_positions}")
            self.log_event(f"   Portfolio Value: ${current_equity:,.2f} (Total P&L: ${total_pnl:+,.2f})")
        except Exception as e:
            self.log_event(f"❌ Error generating cycle summary: {e}")
    
    def execute_approved_trades_live(self, authorization, trade_decisions, current_positions, ufo_data, current_time=None):
        """Execute trades if approved - LIVE VERSION of simulator method"""
        executed_count = 0
        
        if "APPROVE" not in authorization.upper():
            self.log_event("❌ Trades not approved - No execution")
            return executed_count
        
        # Check UFO engine conditions
        try:
            account_info = self.mt5_collector.connect() and mt5.account_info()
            portfolio_status = {'balance': account_info.balance, 'equity': account_info.equity} if account_info else None
            
            should_trade, reason = self.ufo_engine.should_open_new_trades(
                current_positions=current_positions,
                portfolio_status=portfolio_status,
                ufo_data=ufo_data
            )
            
            if not should_trade:
                self.log_event(f"❌ UFO Engine blocked trades: {reason}")
                return executed_count
            
            self.log_event(f"✅ UFO Engine approved: {reason}")
            
            # Execute trade - EXACT CLONE from simulator parsing logic
            try:
                json_match = re.search(r'{.*}', trade_decisions, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    json_str = re.sub(r'//.*?\n', '\n', json_str)
                    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
                    
                    parsed_data = json.loads(json_str)
                    
                    # Extract trades - EXACT CLONE from simulator
                    actions_list = []
                    if 'actions' in parsed_data:
                        actions_list = parsed_data['actions']
                    elif 'trade_plan' in parsed_data:
                        actions_list = parsed_data['trade_plan']
                    elif 'trades' in parsed_data:
                        for trade in parsed_data['trades']:
                            action_type = trade.get('action', 'new_trade')
                            if action_type == 'new_trade':
                                actions_list.append({
                                    'action': 'new_trade',
                                    'currency_pair': trade['currency_pair'],
                                    'direction': trade.get('direction', 'BUY').upper(),
                                    'volume': trade.get('lot_size', 0.1)
                                })
                            elif action_type == 'close_trade':
                                actions_list.append({
                                    'action': 'close_trade',
                                    'trade_id': trade.get('trade_id'),
                                    'currency_pair': trade.get('currency_pair')
                                })
                    
                    # Execute each trade - EXACT CLONE from simulator
                    symbol_suffix = self.config['mt5'].get('symbol_suffix', '')
                    for action in actions_list:
                        if action.get('action') == 'new_trade':
                            symbol = action.get('symbol') or action.get('currency_pair', '')
                            direction = action.get('direction', '').upper()
                            requested_volume = action.get('volume') or action.get('lot_size', 0.1)
                            
                            # Validate and correct currency pair format - EXACT CLONE
                            base_symbol = symbol.replace("/", "")
                            corrected_symbol, was_inverted = self.validate_and_correct_currency_pair(base_symbol)
                            
                            if corrected_symbol is None:
                                self.log_event(f"⚠️ Skipping invalid currency pair: {symbol}")
                                continue
                            
                            # Handle direction inversion if pair was inverted - EXACT CLONE
                            if was_inverted:
                                direction = 'SELL' if direction == 'BUY' else 'BUY'
                                self.log_event(f"⚠️ Direction inverted due to pair correction: {direction}")
                            
                            # Add symbol suffix - EXACT CLONE
                            full_symbol = corrected_symbol + symbol_suffix
                            
                            # DYNAMIC POSITION SIZING - Calculate lot size based on risk management
                            if self.use_dynamic_position_sizing:
                                # Calculate dynamic lot size based on risk parameters
                                volume = self.calculate_dynamic_lot_size(full_symbol)
                                self.log_event(f"📊 Using dynamic position sizing: {volume:.2f} lots for {full_symbol}")
                            else:
                                # Use requested volume but enforce max limit
                                volume = min(self.max_lot_size, requested_volume)
                                if requested_volume > self.max_lot_size:
                                    self.log_event(f"⚠️ Position size reduced from {requested_volume:.2f} to {volume:.2f} lots (max configured: {self.max_lot_size:.2f})")
                            
                            # Calculate UFO-based entry price - EXACT CLONE
                            entry_price = self.calculate_ufo_entry_price(full_symbol, direction, ufo_data)
                            if entry_price is None:
                                self.log_event(f"⚠️ Could not calculate entry price for {full_symbol}. Skipping.")
                                continue
                            
                            # Execute the trade - LIVE EXECUTION
                            trade_type = mt5.ORDER_TYPE_BUY if direction == 'BUY' else mt5.ORDER_TYPE_SELL
                            success = self.trade_executor.execute_trade(
                                symbol=full_symbol, 
                                trade_type=trade_type, 
                                volume=volume, 
                                price=entry_price,
                                comment=f'UFO Cycle {self.cycle_count}'
                            )
                            
                            if success:
                                # Track executed trade like simulator
                                trade_info = {
                                    'symbol': full_symbol,
                                    'direction': direction,
                                    'volume': volume,
                                    'entry_price': entry_price,
                                    'timestamp': current_time or datetime.now(),
                                    'comment': f'UFO Cycle {self.cycle_count}'
                                }
                                self.trades_executed.append(trade_info)
                                executed_count += 1
                                
                                self.log_event(f"🔹 Trade executed: {full_symbol} {direction} {volume} lots @ {entry_price:.5f}")
                            else:
                                self.log_event(f"❌ Trade execution failed: {full_symbol}")

                        elif action.get('action') == 'close_trade':
                            trade_id = action.get('trade_id')
                            if trade_id:
                                success = self.trade_executor.close_trade(trade_id)
                                if success:
                                    executed_count += 1
                                    self.log_event(f"🔹 Trade closed by LLM: {trade_id}")
                                    
            except Exception as e:
                self.log_event(f"❌ Trade execution error: {e}")
                
        except Exception as e:
            self.log_event(f"❌ UFO engine error: {e}")
        
        return executed_count

    def _execute_trades_from_decision(self, trade_decision_str, ufo_data, symbol_suffix):
        """Helper to parse and execute trades from an LLM decision string."""
        try:
            json_match = re.search(r'{.*}', trade_decision_str, re.DOTALL)
            if not json_match:
                print("No JSON object found in the LLM decision.")
                return

            json_str = re.sub(r'//.*?\n', '\n', json_match.group(0))
            json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
            parsed_data = json.loads(json_str)

            actions_list = parsed_data.get('actions', parsed_data.get('trade_plan', parsed_data.get('trades', [])))
            if 'trades' in parsed_data and 'actions' not in parsed_data: # Convert format if needed
                actions_list = [
                    {'action': 'new_trade', 'currency_pair': t['currency_pair'], 'direction': t.get('direction', 'BUY').upper(), 'volume': t.get('lot_size', 0.1)}
                    for t in actions_list
                ]

            print("Executing trades with simulator logic (validation, optimal price, raw volume)...")
            for action in actions_list:
                if action.get('action') == 'new_trade':
                    symbol = action.get('symbol') or action.get('currency_pair', '')
                    direction = action.get('direction', '').upper()
                    volume = action.get('volume') or action.get('lot_size', 0.1)

                    base_symbol = symbol.replace("/", "")
                    corrected_symbol, was_inverted = self.validate_and_correct_currency_pair(base_symbol)

                    if corrected_symbol is None: continue

                    if was_inverted:
                        direction = 'SELL' if direction == 'BUY' else 'BUY'
                        print(f"⚠️ Direction inverted to {direction} due to pair correction.")

                    full_symbol = corrected_symbol + symbol_suffix
                    trade_type = mt5.ORDER_TYPE_BUY if direction == 'BUY' else mt5.ORDER_TYPE_SELL
                    optimal_price = self.calculate_ufo_entry_price(full_symbol, direction, ufo_data)
                    
                    if optimal_price is None:
                        print(f"⚠️ Could not calculate optimal entry price for {full_symbol}. Skipping trade.")
                        continue

                    final_volume = max(0.01, volume)
                    print(f"📊 Executing trade: {full_symbol} {direction} {final_volume} lots @ optimal price {optimal_price:.5f}")
                    self.trade_executor.execute_trade(
                        symbol=full_symbol, trade_type=trade_type, volume=final_volume, price=optimal_price,
                        comment=action.get('comment', 'UFO Sim-Style Trade')
                    )

                elif action.get('action') == 'close_trade':
                    print(f"Closing trade by LLM request: {action.get('trade_id')}")
                    self.trade_executor.close_trade(action['trade_id'])

        except Exception as e:
            print(f"Error during UFO trade execution: {e}")

    def run(self):
        """
        Run live trading with simulator's EXACT behavior - 100% CLONE
        Uses cycle-based approach like simulator with real environment
        """
        self.log_event(f"🚀 Starting LIVE UFO Trading - Full Day Simulator Clone Mode")
        self.log_event(f"📅 Trading Hours: {self.session_start_hour:02d}:{self.session_start_minute:02d} GMT to {self.session_end_hour:02d}:{self.session_end_minute:02d} GMT")
        self.log_event(f"⏰ Cycle Frequency: Every {self.cycle_period_minutes} minutes")
        self.log_event(f"📊 Continuous Monitoring: Position updates every {self.position_update_frequency_seconds // 60} minutes")
        
        # EXACT CLONE: Start continuous trading like simulator
        while True:
            try:
                current_time = datetime.now()
                
                # EXACT CLONE: Check session status exactly like simulator
                session_active = self.check_session_status(current_time)
                if not session_active:
                    self.log_event(f"⏰ Outside trading hours at {current_time.strftime('%H:%M')} GMT - Waiting {self.cycle_period_minutes} minutes...")
                    time.sleep(self.cycle_period_seconds)
                    continue
                
                # Continuous position monitoring between cycles - EXACT CLONE behavior
                if self.continuous_monitoring_enabled:
                    self.continuous_position_monitoring(current_time)
                
                # Run single cycle - EXACT CLONE from simulator
                cycle_success = self.simulate_single_cycle(current_time)
                
                if not cycle_success:
                    self.log_event("❌ Cycle failed, waiting before retry...")
                    time.sleep(300)  # 5 minute wait on failure
                    continue
                
                # EXACT CLONE: Perform additional position updates between cycles
                next_cycle_time = current_time
                monitoring_intervals = self.cycle_period_minutes // (self.position_update_frequency_seconds // 60)
                
                for i in range(monitoring_intervals - 1):  # -1 because we already did one monitoring
                    time.sleep(self.position_update_frequency_seconds)
                    
                    # Check if we should stop trading
                    current_monitoring_time = datetime.now()
                    if not self.check_session_status(current_monitoring_time):
                        break
                        
                    if self.continuous_monitoring_enabled:
                        self.log_event(f"[{current_monitoring_time.strftime('%H:%M:%S')}] Inter-cycle monitoring {i+1}/{monitoring_intervals-1}")
                        self.continuous_position_monitoring(current_monitoring_time)
                
                # Wait for remainder of cycle period
                remaining_sleep = self.cycle_period_seconds - (monitoring_intervals * self.position_update_frequency_seconds)
                if remaining_sleep > 0:
                    time.sleep(remaining_sleep)
                
            except KeyboardInterrupt:
                self.log_event("\nTrading interrupted by user. Generating final summary...")
                self.generate_final_summary()
                self.mt5_collector.disconnect()
                break
            except Exception as e:
                self.log_event(f"❌❌❌ An unexpected error occurred in the main loop: {e}")
                import traceback
                traceback.print_exc()
                self.log_event("Waiting 60 seconds before retrying...")
                time.sleep(60)
    
    def generate_final_summary(self):
        """Generate final summary when trading ends - EXACT CLONE from simulator"""
        try:
            account_info = self.mt5_collector.connect() and mt5.account_info()
            current_equity = account_info.equity if account_info else self.initial_balance
            total_pnl = current_equity - self.initial_balance
            
            self.log_event("\n" + "="*80)
            self.log_event("🎯 LIVE UFO TRADING SESSION COMPLETED")
            self.log_event("="*80)
            self.log_event(f"📅 Session Date: {datetime.now().strftime('%A, %B %d, %Y')}")
            self.log_event(f"⏰ Total Cycles: {self.cycle_count}")
            self.log_event(f"💼 Total Trades Executed: {len(self.trades_executed)}")
            self.log_event(f"💰 Final Portfolio Value: ${current_equity:,.2f}")
            self.log_event(f"💰 Total P&L: ${total_pnl:+,.2f}")
            
            if self.trades_executed:
                self.log_event("\n📈 EXECUTED TRADES SUMMARY:")
                for i, trade in enumerate(self.trades_executed, 1):
                    self.log_event(f"  {i}. {trade['symbol']} {trade['direction']} {trade['volume']} @ {trade['entry_price']:.5f} ({trade['comment']})")
            
            # Save trading log to file
            log_filename = f"live_trading_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(log_filename, 'w', encoding='utf-8') as f:
                f.write("UFO FOREX AGENT v3 - LIVE TRADING LOG\n")
                f.write("=" * 60 + "\n")
                f.write(f"Session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Cycles: {self.cycle_count}\n\n")
                
                for log_entry in self.simulation_log:
                    f.write(log_entry + "\n")
            
            self.log_event(f"\n📁 Trading log saved: {log_filename}")
            
        except Exception as e:
            self.log_event(f"❌ Error generating final summary: {e}")

    def get_real_time_market_data_for_positions(self, open_positions):
        """
        Collect real-time market data for all open positions
        This replaces the empty current_market_data = {} with actual price data
        """
        current_market_data = {}
        
        if open_positions is None or len(open_positions) == 0:
            return current_market_data
            
        try:
            # Connect to MT5 to get current prices
            if not self.mt5_collector.connect():
                print("⚠️ Failed to connect to MT5 for market data collection")
                return current_market_data
                
            # Extract unique symbols from positions
            symbols_to_fetch = set()
            for _, position in open_positions.iterrows():
                symbols_to_fetch.add(position['symbol'])
            
            # Get current tick data for each symbol
            for symbol in symbols_to_fetch:
                try:
                    tick = mt5.symbol_info_tick(symbol)
                    if tick is not None:
                        current_market_data[symbol] = {
                            'close': tick.bid,  # Use bid for current price
                            'ask': tick.ask,
                            'bid': tick.bid,
                            'spread': tick.ask - tick.bid,
                            'timestamp': pd.Timestamp.now()
                        }
                        print(f"📊 Real-time data: {symbol} @ {tick.bid:.5f} (spread: {(tick.ask - tick.bid):.5f})")
                    else:
                        print(f"⚠️ No tick data available for {symbol}")
                        # Fallback: try to get recent bar data
                        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1)
                        if rates is not None and len(rates) > 0:
                            current_market_data[symbol] = {
                                'close': rates[0]['close'],
                                'ask': rates[0]['close'] + 0.0001,  # Estimated spread
                                'bid': rates[0]['close'],
                                'spread': 0.0001,
                                'timestamp': pd.Timestamp.now()
                            }
                            print(f"📊 Fallback data: {symbol} @ {rates[0]['close']:.5f} (from M1 bar)")
                        
                except Exception as e:
                    print(f"❌ Error getting market data for {symbol}: {e}")
                    continue
            
            self.mt5_collector.disconnect()
            print(f"✅ Collected real-time market data for {len(current_market_data)} symbols")
            
        except Exception as e:
            print(f"❌ Error in market data collection: {e}")
            
        return current_market_data
    
    def continuous_position_monitoring(self, current_time):
        """Perform continuous position monitoring between trading cycles - EXACT CLONE from simulator"""
        try:
            open_positions = self.agents['risk_manager'].portfolio_manager.get_positions()
            if open_positions is None or open_positions.empty:
                return
            
            # Check if we've already monitored this exact time to prevent loops
            if hasattr(self, '_last_monitoring_time') and self._last_monitoring_time == current_time:
                return
            self._last_monitoring_time = current_time
            
            # CRITICAL: Check portfolio stop EVERY monitoring cycle to prevent breach
            portfolio_stop_breached, stop_reason = self.check_portfolio_equity_stop_live()
            if portfolio_stop_breached:
                self.log_event(f"🚨 PORTFOLIO STOP BREACHED DURING MONITORING: {stop_reason}")
                self.log_event("🚨 Emergency closing ALL positions immediately!")
                self.trade_executor.close_all_positions()
                return  # Exit monitoring
            
            # CRITICAL FIX: Apply individual position P&L-based auto-closing rules
            # This ensures positions are closed when they hit +$75 profit or -$50 loss
            # just like in the simulator
            self._manage_open_positions_simulator_style()
            
            # Get account info for portfolio analysis
            account_info = self.mt5_collector.connect() and mt5.account_info()
            if account_info:
                current_equity = account_info.equity
                
                # Check portfolio status like simulator
                if len(self.portfolio_history) >= 2:
                    # Check for rapid changes like simulator
                    previous_equity = getattr(self, '_last_equity', self.initial_balance)
                    if previous_equity > 0:
                        rapid_change = abs(current_equity - previous_equity) / previous_equity * 100
                        if rapid_change > self.rapid_portfolio_change_threshold:  # CONFIG-DRIVEN RAPID CHANGE THRESHOLD
                            self.log_event(f"⚡ Rapid portfolio change: {rapid_change:.2f}% in {self.position_update_frequency_seconds // 60} min")
                            
                            # Check if portfolio stop is approaching - CONFIG-DRIVEN WARNING RATIO
                            current_drawdown = ((current_equity - self.initial_balance) / self.initial_balance) * 100
                            if current_drawdown < (self.portfolio_equity_stop * self.portfolio_stop_warning_ratio):
                                self.log_event(f"⚠️ Approaching portfolio stop: {current_drawdown:.2f}% (threshold: {self.portfolio_equity_stop}%)")
                
                self._last_equity = current_equity
                
                # Update portfolio history like simulator
                total_pnl = current_equity - self.initial_balance
                self.portfolio_history.append({
                    'timestamp': current_time,
                    'portfolio_value': current_equity,
                    'total_pnl': total_pnl,
                    'position_count': len(open_positions)
                })
                
                # Keep only last 10 entries to prevent memory bloat
                if len(self.portfolio_history) > 10:
                    self.portfolio_history = self.portfolio_history[-10:]
            
            # Re-fetch positions after potential closures from _manage_open_positions_simulator_style
            open_positions = self.agents['risk_manager'].portfolio_manager.get_positions()
            if open_positions is None or open_positions.empty:
                return
            
            # Check for positions with high unrealized losses during monitoring
            high_risk_positions = []
            market_data = self.get_real_time_market_data_for_positions(open_positions)
            
            for _, position in open_positions.iterrows():
                if position.symbol in market_data:
                    # Calculate current P&L like simulator
                    current_price = market_data[position.symbol]['bid'] if position.type == 0 else market_data[position.symbol]['ask']
                    pip_multiplier = self.get_pip_value_multiplier(position.symbol)
                    price_diff = current_price - position.price_open
                    if position.type == 1:  # SELL
                        price_diff = -price_diff
                    pnl = price_diff * position.volume * pip_multiplier
                    
                    if pnl < self.high_risk_alert_threshold:  # CONFIG-DRIVEN HIGH RISK THRESHOLD
                        high_risk_positions.append({'symbol': position.symbol, 'ticket': position.ticket, 'pnl': pnl})
            
            if high_risk_positions:
                self.log_event(f"🚨 Monitoring alert: {len(high_risk_positions)} positions with high unrealized losses")
                for pos in high_risk_positions[:3]:  # Log top 3
                    self.log_event(f"  ⚠️ {pos['symbol']}: P&L ${pos['pnl']:.2f}")
            
            # Enhanced Dynamic Reinforcement monitoring like simulator
            if self.dynamic_reinforcement_engine.enabled and self.dynamic_reinforcement_engine.should_check_reinforcement(current_time):
                current_market_data = self.get_real_time_market_data_for_positions(open_positions)
                
                # Convert positions to simulator format
                sim_positions_list = []
                for _, pos in open_positions.iterrows():
                    sim_positions_list.append({
                        'ticket': pos.ticket, 'symbol': pos.symbol, 'direction': 'BUY' if pos.type == 0 else 'SELL',
                        'volume': pos.volume, 'entry_price': pos.price_open, 'current_price': pos.price_current,
                        'pnl': pos.profit, 'timestamp': pd.to_datetime(pos.time, unit='s')
                    })
                
                # Detect market events that trigger reinforcement
                market_events = self.dynamic_reinforcement_engine.detect_market_events(
                    sim_positions_list, 
                    current_market_data, 
                    getattr(self, 'previous_ufo_data', None)
                )
                
                if market_events:
                    self.log_event(f"🎯 Dynamic Reinforcement: {len(market_events)} market events detected")
                    
                    # Process each event for reinforcement
                    for event in market_events:
                        position = event.get('position')
                        if position:
                            # Calculate dynamic reinforcement for this event
                            reinforcement_plan, message = self.dynamic_reinforcement_engine.calculate_dynamic_reinforcement(
                                position, 
                                event, 
                                current_market_data, 
                                getattr(self, 'previous_ufo_data', None)
                            )
                            
                            if reinforcement_plan:
                                self.log_event(f"  ⚡ {event['type']}: {position['symbol']} - {message}")
                                self.log_event(f"    📊 Reinforcement: {reinforcement_plan['additional_lots']:.2f} lots")
                                
                                # Execute reinforcement (LIVE execution)
                                self.execute_dynamic_reinforcement_live(position, reinforcement_plan, current_time)
                            else:
                                self.log_event(f"  ⏸️ {position['symbol']}: {message}")
                
                # ADDED: UFO-based reinforcement check (EXACT CLONE from simulator lines 1468-1478)
                # This ensures 100% feature parity with the simulator
                if hasattr(self, 'previous_ufo_data'):
                    for position in sim_positions_list:
                        # Check if UFO engine also suggests reinforcement
                        should_reinforce, reason, plan = self.ufo_engine.should_reinforce_position(
                            position, 
                            self.previous_ufo_data,
                            current_market_data
                        )
                        if should_reinforce and plan:
                            self.log_event(f"  🛸 UFO reinforcement suggestion: {position['symbol']} - {reason}")
                            # Note: We log the suggestion but don't execute it separately
                            # The Dynamic Reinforcement Engine already handles execution
            
        except Exception as e:
            self.log_event(f"❌ Error in continuous position monitoring: {e}")
    
    def execute_dynamic_reinforcement_live(self, position, reinforcement_plan, current_time):
        """Execute dynamic reinforcement trade in LIVE environment - adapted from simulator"""
        try:
            # Execute reinforcement trade
            trade_type = mt5.ORDER_TYPE_BUY if position['direction'] == 'BUY' else mt5.ORDER_TYPE_SELL
            success = self.trade_executor.execute_ufo_trade(
                symbol=position['symbol'],
                trade_type=trade_type,
                volume=reinforcement_plan['additional_lots'],
                comment=f"Dynamic {reinforcement_plan.get('type', 'Reinforcement')}"
            )
            
            if success:
                # Record in dynamic reinforcement engine
                self.dynamic_reinforcement_engine.record_reinforcement(position, reinforcement_plan)
                
                # Track like simulator
                trade_info = {
                    'symbol': position['symbol'],
                    'direction': position['direction'],
                    'volume': reinforcement_plan['additional_lots'],
                    'entry_price': 0.0,  # Will be filled by MT5
                    'timestamp': current_time,
                    'comment': f'Dynamic {reinforcement_plan.get("type", "Reinforcement")}',
                    'reinforcement_details': reinforcement_plan
                }
                self.trades_executed.append(trade_info)
                
                self.log_event(f"    ✅ Dynamic reinforcement executed: {position['symbol']} "
                              f"{position['direction']} {reinforcement_plan['additional_lots']:.2f} lots")
            else:
                self.log_event(f"    ❌ Failed to execute dynamic reinforcement: {position['symbol']}")
            
        except Exception as e:
            self.log_event(f"    ❌ Error executing dynamic reinforcement: {e}")
    
    def check_portfolio_status(self):
        """
        Checks overall portfolio status using UFO methodology.
        """
        try:
            positions = self.agents['risk_manager'].portfolio_manager.get_positions()
            if positions is None or len(positions) == 0:
                return
                
            portfolio_value = self.ufo_engine.calculate_portfolio_synthetic_value()
            print(f"Portfolio synthetic value: {portfolio_value:.2f}%")
            
            if portfolio_value <= -5.0:  # Portfolio stop loss threshold
                print("Portfolio stop loss triggered - closing all positions")
                for position in positions:
                    self.trade_executor.close_trade(position.ticket)
                    
        except Exception as e:
            print(f"Error checking portfolio status: {e}")
