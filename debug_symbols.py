import configparser
import sys
try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 module not found")
    sys.exit(1)

# Load config
config = configparser.ConfigParser()
config.read('config/config.ini')

# Initialize MT5
if not mt5.initialize(
    path=config['mt5']['path'],
    login=int(config['mt5']['login']),
    password=config['mt5']['password'],
    server=config['mt5']['server']
):
    print(f"Failed to initialize MT5: {mt5.last_error()}")
    sys.exit(1)

print("✅ MT5 initialized successfully")

# Get all symbols
symbols = mt5.symbols_get()
if symbols is None:
    print("❌ Failed to get symbols list")
    mt5.shutdown()
    sys.exit(1)

print(f"\n📊 Found {len(symbols)} symbols in MT5")
print("\n🔍 Looking for forex symbols...")

# Filter for forex symbols
forex_symbols = []
for symbol in symbols:
    symbol_name = symbol.name.upper()
    # Look for common forex patterns
    if any(pair in symbol_name for pair in ['EUR', 'GBP', 'USD', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD']):
        forex_symbols.append({
            'name': symbol.name,
            'visible': symbol.visible,
            'description': symbol.description,
            'currency_base': getattr(symbol, 'currency_base', 'N/A'),
            'currency_profit': getattr(symbol, 'currency_profit', 'N/A')
        })

print(f"Found {len(forex_symbols)} forex symbols:")
for i, sym in enumerate(forex_symbols[:20]):  # Show first 20
    status = "✅" if sym['visible'] else "❌"
    print(f"{status} {sym['name']} - {sym['description']}")

if len(forex_symbols) > 20:
    print(f"... and {len(forex_symbols) - 20} more forex symbols")

# Test specific symbols we're interested in
test_symbols = ['EURUSD-ECN', 'EURUSD', 'GBPUSD-ECN', 'GBPUSD', 'USDJPY-ECN', 'USDJPY']
print(f"\n🧪 Testing specific symbols:")
for test_sym in test_symbols:
    symbol_info = mt5.symbol_info(test_sym)
    if symbol_info:
        print(f"✅ {test_sym} - FOUND (visible: {symbol_info.visible})")
        # Try to get tick data
        tick = mt5.symbol_info_tick(test_sym)
        if tick:
            print(f"   📊 Tick data: bid={tick.bid:.5f}, ask={tick.ask:.5f}")
        else:
            print(f"   ❌ No tick data, error: {mt5.last_error()}")
    else:
        print(f"❌ {test_sym} - NOT FOUND")

mt5.shutdown()
print("\n🔚 MT5 connection closed")
