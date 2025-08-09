from src.real_trader import RealTrader
import os

def main():
    """
    Main entry point for the live trading bot.
    This runs the RealTrader, which is a clone of the full day simulator's logic,
    adapted for a continuous, live trading environment.
    """
    print("🚀 Starting UFO Forex Agent v3 - Real Environment Clone")
    print("----------------------------------------------------")
    print("This system runs a real-time trading bot that mirrors the")
    print("exact logic and behavior of the full day simulator.")
    print("----------------------------------------------------")
    
    try:
        # Instantiate and run the RealTrader
        real_trader = RealTrader()
        real_trader.run()
        
    except Exception as e:
        print(f"\n💥 A critical error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nBot has been terminated.")

if __name__ == "__main__":
    main()
