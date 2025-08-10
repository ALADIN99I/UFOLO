# UFO INTEGRATION FIX: Matching Simulator's Batch Processing Behavior
# =====================================================================
# This file contains the engineering fix to make the live system process
# UFO reinforcements exactly like the simulator does.

"""
PROBLEM IDENTIFIED:
- Simulator: Collects all positions needing reinforcement in a list, then processes batch
- Live System: Processes positions immediately one-by-one without collection

SOLUTION:
Replace the immediate processing with batch collection and processing
"""

def continuous_position_monitoring_FIXED(self, current_time):
    """
    FIXED VERSION: Monitors open positions continuously with BATCH PROCESSING
    matching the simulator's behavior exactly.
    """
    try:
        # ... [Previous code remains unchanged up to line 2042] ...
        
        # ===============================================================
        # FIX STARTS HERE: UFO-based reinforcement with BATCH PROCESSING
        # ===============================================================
        
        if hasattr(self, 'previous_ufo_data'):
            # STEP 1: COLLECT all positions requiring reinforcement (like simulator)
            positions_requiring_reinforcement = []  # ← CRITICAL: Create the list
            
            # STEP 2: IDENTIFY positions needing reinforcement
            for position in sim_positions_list:
                # Check if UFO engine suggests reinforcement
                should_reinforce, reason, plan = self.ufo_engine.should_reinforce_position(
                    position, 
                    self.previous_ufo_data,
                    current_market_data
                )
                
                # COLLECT instead of immediately processing
                if should_reinforce and plan:
                    positions_requiring_reinforcement.append({
                        'position': position,
                        'plan': plan,
                        'reason': reason
                    })
            
            # STEP 3: LOG the batch summary
            if positions_requiring_reinforcement:
                self.log_event(f"🛸 UFO Analysis: {len(positions_requiring_reinforcement)} positions require reinforcement")
            
            # STEP 4: PROCESS the batch (matching simulator lines 308-338)
            for reinforcement_data in positions_requiring_reinforcement:
                position = reinforcement_data['position']
                plan = reinforcement_data['plan']
                reason = reinforcement_data['reason']
                
                # Extract compensation type (matching simulator line 309)
                compensation_type = plan.get('type', 'unknown')
                additional_lots = plan.get('additional_lots', 0.0)
                
                # Log with compensation type (matching simulator line 314)
                self.log_event(f"🔧 UFO {compensation_type}: {position['symbol']} - {reason}")
                
                if additional_lots > 0:
                    # Calculate optimal entry price (if needed)
                    optimal_entry_price = self.calculate_ufo_entry_price(
                        position['symbol'],
                        position['direction'],
                        self.previous_ufo_data,
                        current_time
                    )
                    
                    # Create compensation position structure (matching simulator lines 324-336)
                    compensation_position = {
                        'ticket': None,  # Will be assigned by MT5
                        'symbol': position['symbol'],
                        'direction': position['direction'],
                        'volume': additional_lots,
                        'entry_price': optimal_entry_price,
                        'current_price': optimal_entry_price,
                        'pnl': 0.0,
                        'timestamp': current_time,
                        'comment': f'UFO {compensation_type}',
                        'original_position_ticket': position.get('ticket', 0),  # ← Track parent
                        'reinforcement_reason': reason  # ← Store reason
                    }
                    
                    # Execute the UFO reinforcement trade
                    success = self.execute_ufo_reinforcement_with_tracking(
                        compensation_position, 
                        plan, 
                        current_time
                    )
                    
                    if success:
                        self.log_event(f"✅ UFO reinforcement executed: {additional_lots:.2f} lots @ {optimal_entry_price:.5f}")
                    else:
                        self.log_event(f"❌ Failed to execute UFO reinforcement for {position['symbol']}")
    
    except Exception as e:
        self.log_event(f"❌ Error in continuous position monitoring: {e}")


def execute_ufo_reinforcement_with_tracking(self, compensation_position, plan, current_time):
    """
    NEW METHOD: Execute UFO reinforcement with full tracking like simulator
    """
    try:
        # Determine trade type
        trade_type = mt5.ORDER_TYPE_BUY if compensation_position['direction'] == 'BUY' else mt5.ORDER_TYPE_SELL
        
        # Execute the trade
        result = self.trade_executor.execute_ufo_trade(
            symbol=compensation_position['symbol'],
            trade_type=trade_type,
            volume=compensation_position['volume'],
            comment=compensation_position['comment']
        )
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            # Update compensation_position with actual ticket
            compensation_position['ticket'] = result.order
            compensation_position['entry_price'] = result.price
            
            # Store the compensation position with full tracking
            # This maintains the relationship with original position
            self.ufo_compensation_positions.append(compensation_position)
            
            # Also track in trades_executed for compatibility
            trade_info = {
                'ticket': result.order,
                'symbol': compensation_position['symbol'],
                'direction': compensation_position['direction'],
                'volume': compensation_position['volume'],
                'entry_price': result.price,
                'timestamp': current_time,
                'comment': compensation_position['comment'],
                'original_position_ticket': compensation_position['original_position_ticket'],
                'reinforcement_reason': compensation_position['reinforcement_reason'],
                'reinforcement_details': plan
            }
            self.trades_executed.append(trade_info)
            
            return True
        
        return False
        
    except Exception as e:
        self.log_event(f"❌ Error executing UFO reinforcement: {e}")
        return False


def calculate_ufo_entry_price(self, symbol, direction, previous_ufo_data, current_time):
    """
    NEW METHOD: Calculate optimal entry price for UFO compensation
    (Matching simulator's logic)
    """
    try:
        # Get current market data
        symbol_info = mt5.symbol_info_tick(symbol)
        if symbol_info is None:
            # Fallback to last known price
            return self.get_last_known_price(symbol, direction)
        
        # Use bid/ask based on direction
        if direction == 'BUY':
            base_price = symbol_info.ask
        else:
            base_price = symbol_info.bid
        
        # Apply UFO optimization if available
        if previous_ufo_data and symbol in previous_ufo_data:
            ufo_adjustment = previous_ufo_data[symbol].get('price_adjustment', 0)
            optimal_price = base_price + ufo_adjustment
        else:
            optimal_price = base_price
        
        return optimal_price
        
    except Exception as e:
        self.log_event(f"Error calculating UFO entry price: {e}")
        return self.get_last_known_price(symbol, direction)


# =====================================================================
# IMPLEMENTATION INSTRUCTIONS
# =====================================================================

"""
TO IMPLEMENT THIS FIX IN YOUR LIVE SYSTEM:

1. ADD CLASS ATTRIBUTE (in __init__ method):
   ```python
   self.ufo_compensation_positions = []  # Track all UFO compensations
   ```

2. REPLACE the UFO reinforcement section (lines 2044-2055) with:
   ```python
   # Enhanced UFO compensation and reinforcement logic (BATCH PROCESSING)
   if hasattr(self, 'previous_ufo_data'):
       positions_requiring_reinforcement = []
       
       # Collect positions needing reinforcement
       for position in sim_positions_list:
           should_reinforce, reason, plan = self.ufo_engine.should_reinforce_position(
               position, self.previous_ufo_data, current_market_data
           )
           if should_reinforce and plan:
               positions_requiring_reinforcement.append({
                   'position': position, 'plan': plan, 'reason': reason
               })
       
       # Process batch
       if positions_requiring_reinforcement:
           self.log_event(f"🛸 UFO Analysis: {len(positions_requiring_reinforcement)} positions require reinforcement")
           
           for reinforcement_data in positions_requiring_reinforcement:
               position = reinforcement_data['position']
               plan = reinforcement_data['plan']
               reason = reinforcement_data['reason']
               
               compensation_type = plan.get('type', 'unknown')
               additional_lots = plan.get('additional_lots', 0.0)
               
               self.log_event(f"🔧 UFO {compensation_type}: {position['symbol']} - {reason}")
               
               if additional_lots > 0:
                   # Execute with full tracking
                   self.execute_ufo_reinforcement_with_tracking(position, plan, reason, current_time)
   ```

3. ADD the new helper methods to your LiveTrader class:
   - execute_ufo_reinforcement_with_tracking()
   - calculate_ufo_entry_price()

4. BENEFITS OF THIS FIX:
   ✅ Batch processing like simulator
   ✅ Full position relationship tracking
   ✅ Compensation type extraction and logging
   ✅ Reinforcement reason storage
   ✅ Parent-child position linking
   ✅ Better audit trail for analysis

5. TESTING:
   - Run parallel tests with simulator
   - Verify batch collection happens before execution
   - Check that ufo_compensation_positions list contains all reinforcements
   - Confirm parent-child relationships are maintained
"""

# =====================================================================
# COMPLETE DIFF FOR EASY INTEGRATION
# =====================================================================

INTEGRATION_DIFF = """
--- live_trader.py (ORIGINAL)
+++ live_trader.py (FIXED)

@@ __init__ method @@+        self.ufo_compensation_positions = []  # Track all UFO compensations

@@ lines 2044-2055 (REPLACE ENTIRE BLOCK)
-                if hasattr(self, 'previous_ufo_data'):
-                    for position in sim_positions_list:
-                        should_reinforce, reason, plan = self.ufo_engine.should_reinforce_position(
-                            position, 
-                            self.previous_ufo_data,
-                            current_market_data
-                        )
-                        if should_reinforce and plan:
-                            self.log_event(f"  🛸 UFO reinforcement suggestion: {position['symbol']} - {reason}")
+                # Enhanced UFO compensation and reinforcement logic (BATCH PROCESSING)
+                if hasattr(self, 'previous_ufo_data'):
+                    positions_requiring_reinforcement = []
+                    
+                    # STEP 1: Collect all positions needing reinforcement
+                    for position in sim_positions_list:
+                        should_reinforce, reason, plan = self.ufo_engine.should_reinforce_position(
+                            position, self.previous_ufo_data, current_market_data
+                        )
+                        if should_reinforce and plan:
+                            positions_requiring_reinforcement.append({
+                                'position': position, 'plan': plan, 'reason': reason
+                            })
+                    
+                    # STEP 2: Process the batch
+                    if positions_requiring_reinforcement:
+                        self.log_event(f"🛸 UFO Analysis: {len(positions_requiring_reinforcement)} positions require reinforcement")
+                        
+                        for reinforcement_data in positions_requiring_reinforcement:
+                            position = reinforcement_data['position']
+                            plan = reinforcement_data['plan']
+                            reason = reinforcement_data['reason']
+                            
+                            compensation_type = plan.get('type', 'unknown')
+                            additional_lots = plan.get('additional_lots', 0.0)
+                            
+                            self.log_event(f"🔧 UFO {compensation_type}: {position['symbol']} - {reason}")
+                            
+                            if additional_lots > 0:
+                                compensation_position = {
+                                    'ticket': None,
+                                    'symbol': position['symbol'],
+                                    'direction': position['direction'],
+                                    'volume': additional_lots,
+                                    'entry_price': 0,  # Will be set by execution
+                                    'timestamp': current_time,
+                                    'comment': f'UFO {compensation_type}',
+                                    'original_position_ticket': position.get('ticket', 0),
+                                    'reinforcement_reason': reason
+                                }
+                                
+                                self.execute_ufo_reinforcement_with_tracking(
+                                    compensation_position, plan, current_time
+                                )

@@ END OF FILE (ADD NEW METHODS)
+    def execute_ufo_reinforcement_with_tracking(self, compensation_position, plan, current_time):
+        [Add method implementation from above]
+    
+    def calculate_ufo_entry_price(self, symbol, direction, previous_ufo_data, current_time):
+        [Add method implementation from above]
"""
