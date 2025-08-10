# Parallel Test Harness Documentation

## Overview

The Parallel Test Harness is a comprehensive testing framework designed to verify that the simulator and live trading systems produce identical outputs when given the same inputs. This ensures complete alignment between development/testing (simulator) and production (live) environments.

## Architecture

### Components

1. **ParallelTestHarness** - Main orchestrator that manages the test execution
2. **SimulatorWrapper** - Wraps the simulation system for testing
3. **LiveSystemWrapper** - Wraps the live trading system in paper mode
4. **CycleSnapshot** - Data structure capturing system state at each cycle

### Test Flow

```
┌─────────────────┐
│  Test Harness   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼───┐
│Simulator│ │Live  │
│         │ │System│
└───┬───┘ └──┬───┘
    │         │
    └────┬────┘
         │
    ┌────▼────┐
    │Compare  │
    │Results  │
    └────┬────┘
         │
    ┌────▼────┐
    │Generate │
    │ Report  │
    └─────────┘
```

## Installation & Setup

### Prerequisites

1. Ensure both systems are properly configured:
   ```
   config/config.ini  # Main configuration file
   ```

2. Required Python packages:
   ```bash
   pip install pandas numpy
   ```

3. MetaTrader 5 connection (or mock data for testing)

## Usage

### Quick Test (3 cycles, 10 minutes each)

```bash
python run_parallel_test.py --quick
```

### Standard Test (5 cycles, 40 minutes each)

```bash
python run_parallel_test.py
```

### Custom Test

```bash
python run_parallel_test.py --cycles 10 --duration 30 --date 2025-08-01
```

### Command Line Arguments

- `--cycles`: Number of trading cycles to run (default: 5)
- `--duration`: Duration of each cycle in minutes (default: 40)
- `--date`: Simulation date in YYYY-MM-DD format (default: 2025-08-01)
- `--quick`: Run quick test with 3 cycles of 10 minutes each
- `--config`: Path to configuration file (default: config/config.ini)

## Key Verification Points

### 1. UFO Calculations
- Currency strength scores
- Market opportunity identification
- Entry/exit signal generation

### 2. Trade Decisions
- Symbol selection
- Direction (BUY/SELL)
- Volume calculation
- Entry timing

### 3. Position Management
- Open position tracking
- P&L calculations
- Position reinforcement decisions
- Closure timing and reasons

### 4. Portfolio Metrics
- Total portfolio value
- Realized P&L
- Unrealized P&L
- Risk metrics

### 5. Economic Events
- Event processing
- Impact assessment
- Trading restrictions

## Output Files

### 1. JSON Results File
`parallel_test_results_YYYYMMDD_HHMMSS.json`
- Complete test data
- All snapshots from both systems
- Detailed differences per cycle

### 2. Text Report
`parallel_test_report_YYYYMMDD_HHMMSS.txt`
- Human-readable summary
- Key statistics
- Detailed difference analysis

### 3. Log File
`parallel_test_results.log`
- Real-time execution log
- Debug information
- Error messages

## Interpreting Results

### Alignment Ratings

| Rating | Alignment % | Interpretation |
|--------|------------|----------------|
| PERFECT | 100% | Systems are completely synchronized |
| EXCELLENT | 95-99% | Minor differences, likely floating point |
| GOOD | 90-94% | Some differences need investigation |
| MODERATE | 80-89% | Significant differences requiring attention |
| POOR | <80% | Major issues, immediate fixes needed |

### Common Difference Categories

1. **ufo_scores**: UFO calculation discrepancies
   - Check data sources
   - Verify calculation timing
   - Review currency pair lists

2. **positions**: Position management differences
   - Verify execution logic
   - Check position tracking
   - Review P&L calculations

3. **portfolio_metrics**: Portfolio value differences
   - Check calculation formulas
   - Verify fee/commission handling
   - Review pip value calculations

4. **trade_decisions**: Trading decision mismatches
   - Check LLM responses
   - Verify decision parsing
   - Review risk filters

5. **reinforcement_triggers**: Reinforcement logic differences
   - Check trigger conditions
   - Verify position analysis
   - Review UFO compensation logic

## Troubleshooting

### Issue: Import Errors
**Solution**: Ensure all required modules are in the Python path
```python
import sys
sys.path.append('/path/to/forex_agent_v3')
```

### Issue: MT5 Connection Failures
**Solution**: The test can run with mock data if MT5 is unavailable
- Check MT5 credentials in config.ini
- Ensure MT5 terminal is running
- Verify network connectivity

### Issue: Different Results Between Runs
**Possible Causes**:
1. LLM non-deterministic responses
2. Market data timing differences
3. Random number generation in mock data

**Solutions**:
- Use fixed seeds for reproducibility
- Run multiple tests and check consistency
- Focus on patterns rather than exact values

### Issue: Memory/Performance Problems
**Solutions**:
- Reduce number of cycles
- Decrease cycle duration
- Run with `--quick` flag for faster testing

## Best Practices

1. **Regular Testing**
   - Run tests after any code changes
   - Test with different dates/market conditions
   - Maintain test history for regression detection

2. **Configuration Consistency**
   - Keep config files synchronized
   - Document any config changes
   - Use version control for configs

3. **Difference Analysis**
   - Investigate all differences, even small ones
   - Document known acceptable differences
   - Create fixes for unexpected differences

4. **Performance Monitoring**
   - Track test execution times
   - Monitor resource usage
   - Optimize slow components

## Advanced Usage

### Custom Comparison Logic

You can extend the comparison logic by modifying the `compare_snapshots` method:

```python
def compare_snapshots(self, sim_snapshot, live_snapshot):
    differences = {}
    
    # Add custom comparison logic
    custom_diff = self.compare_custom_metric(
        sim_snapshot.custom_data,
        live_snapshot.custom_data
    )
    if custom_diff:
        differences['custom_metric'] = custom_diff
    
    return differences
```

### Adding New Metrics

To track additional metrics, extend the `CycleSnapshot` class:

```python
@dataclass
class CycleSnapshot:
    # Existing fields...
    
    # Add new metrics
    custom_metric: float
    additional_data: Dict
```

### Integration with CI/CD

The test harness can be integrated into CI/CD pipelines:

```yaml
# .github/workflows/parallel_test.yml
name: Parallel System Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Parallel Test
        run: python run_parallel_test.py --quick
      - name: Check Results
        run: |
          if [ $? -ne 0 ]; then
            echo "Test failed - systems not aligned"
            exit 1
          fi
```

## Example Analysis Workflow

1. **Run Initial Test**
   ```bash
   python run_parallel_test.py --quick
   ```

2. **Review Summary**
   - Check alignment rate
   - Identify difference categories
   - Note problematic cycles

3. **Analyze Detailed Report**
   - Open `parallel_test_report_*.txt`
   - Review specific differences
   - Identify patterns

4. **Debug Specific Issues**
   - Check logs for error messages
   - Review code in identified problem areas
   - Add debug logging if needed

5. **Fix and Retest**
   - Implement fixes
   - Run focused tests
   - Verify improvements

6. **Document Findings**
   - Record issue and solution
   - Update this documentation
   - Share with team

## Contact & Support

For questions or issues with the parallel test harness:
1. Check this documentation
2. Review the test logs
3. Examine the source code comments
4. Contact the development team

## Version History

- v1.0.0 - Initial release with basic comparison
- v1.1.0 - Added UFO calculation verification
- v1.2.0 - Enhanced position tracking comparison
- v1.3.0 - Added economic event handling
- v1.4.0 - Improved reporting and analysis tools

---

Last Updated: December 2024
