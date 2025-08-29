#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2025 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------
"""
Example demonstrating automatic option exercise during backtesting.

This example shows how to use the OptionExerciseModule to automatically exercise ITM
options at expiry, creating appropriate underlying positions.

"""


import pandas as pd

from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.option_exercise import OptionExerciseConfig
from nautilus_trader.backtest.option_exercise import OptionExerciseModule
from nautilus_trader.config import LoggingConfig
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import AssetClass
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.enums import OptionKind
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.instruments import OptionContract
from nautilus_trader.model.objects import Money
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy


class OptionExerciseStrategy(Strategy):
    """
    Simple strategy to demonstrate option exercise functionality.

    This strategy buys an ITM call option and holds it until expiry to demonstrate
    automatic exercise.

    """

    def __init__(self, config=None):
        super().__init__(config)
        self.option_bought = False

    def on_start(self):
        """
        Actions to be performed on strategy start.
        """
        self.subscribe_quote_ticks(InstrumentId.from_str("AAPL.NASDAQ"))
        self.subscribe_quote_ticks(InstrumentId.from_str("AAPL240315C00150000.NASDAQ"))

    def on_quote_tick(self, tick: QuoteTick):
        """
        Handle quote tick updates.
        """
        if not self.option_bought and tick.instrument_id.value.startswith("AAPL240315C"):
            # Buy the call option
            order = self.order_factory.market(
                instrument_id=tick.instrument_id,
                order_side=OrderSide.BUY,
                quantity=Quantity.from_int(1),  # 1 contract
                time_in_force=TimeInForce.GTC,
            )
            self.submit_order(order)
            self.option_bought = True
            self.log.info(f"Submitted buy order for option {tick.instrument_id}")


def create_sample_data():
    """
    Create sample market data for the example.
    """
    # Create timestamps
    start_time = pd.Timestamp("2024-03-01", tz="UTC")
    expiry_time = pd.Timestamp("2024-03-15", tz="UTC")

    timestamps = pd.date_range(start_time, expiry_time, freq="1D")

    # Create underlying stock data (AAPL rising from $140 to $160)
    stock_prices = []
    option_prices = []

    for i, ts in enumerate(timestamps):
        # Stock price rises over time
        stock_price = 140.0 + (20.0 * i / len(timestamps))

        # Option intrinsic value (strike = $150)
        strike = 150.0
        intrinsic = max(0.0, stock_price - strike)
        time_value = max(0.5, 5.0 * (1 - i / len(timestamps)))  # Decaying time value
        option_price = intrinsic + time_value

        # Create stock quote tick
        stock_tick = QuoteTick(
            instrument_id=InstrumentId.from_str("AAPL.NASDAQ"),
            bid_price=Price(stock_price - 0.01, 2),
            ask_price=Price(stock_price + 0.01, 2),
            bid_size=Quantity.from_int(100),
            ask_size=Quantity.from_int(100),
            ts_event=dt_to_unix_nanos(ts),
            ts_init=dt_to_unix_nanos(ts),
        )
        stock_prices.append(stock_tick)

        # Create option quote tick
        option_tick = QuoteTick(
            instrument_id=InstrumentId.from_str("AAPL240315C00150000.NASDAQ"),
            bid_price=Price(option_price - 0.05, 2),
            ask_price=Price(option_price + 0.05, 2),
            bid_size=Quantity.from_int(10),
            ask_size=Quantity.from_int(10),
            ts_event=dt_to_unix_nanos(ts),
            ts_init=dt_to_unix_nanos(ts),
        )
        option_prices.append(option_tick)

    return stock_prices + option_prices


def run_example():
    """
    Run the option exercise example.
    """
    # Create backtest engine
    config = BacktestEngineConfig(
        logging=LoggingConfig(log_level="INFO"),
    )
    engine = BacktestEngine(config)

    # Create option exercise module
    exercise_config = OptionExerciseConfig(
        auto_exercise_enabled=True,
        log_exercises=True,
        detailed_logging=True,
    )
    exercise_module = OptionExerciseModule(exercise_config)

    # Add venue with option exercise module
    engine.add_venue(
        venue=Venue("NASDAQ"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        starting_balances=[Money(100_000, USD)],
        modules=[exercise_module],  # Add the option exercise module
    )

    # Create instruments
    # Underlying stock
    aapl = Equity(
        instrument_id=InstrumentId.from_str("AAPL.NASDAQ"),
        raw_symbol=Symbol("AAPL"),
        currency=USD,
        price_precision=2,
        price_increment=Price(0.01, 2),
        lot_size=Quantity.from_int(1),
        ts_event=0,
        ts_init=0,
    )

    # Call option (strike $150, expiry March 15, 2024)
    option = OptionContract(
        instrument_id=InstrumentId.from_str("AAPL240315C00150000.NASDAQ"),
        raw_symbol=Symbol("AAPL240315C00150000"),
        asset_class=AssetClass.EQUITY,
        underlying="AAPL",
        option_kind=OptionKind.CALL,
        strike_price=Price(150.0, 2),
        currency=USD,
        activation_ns=dt_to_unix_nanos(pd.Timestamp("2024-03-01", tz="UTC")),
        expiration_ns=dt_to_unix_nanos(pd.Timestamp("2024-03-15 16:00:00", tz="UTC")),
        price_precision=2,
        price_increment=Price(0.01, 2),
        multiplier=Quantity.from_int(100),  # 100 shares per contract
        lot_size=Quantity.from_int(1),
        ts_event=0,
        ts_init=0,
    )

    # Add instruments to engine
    engine.add_instrument(aapl)
    engine.add_instrument(option)

    # Add strategy
    strategy = OptionExerciseStrategy()
    engine.add_strategy(strategy)

    # Add market data
    data = create_sample_data()
    engine.add_data(data)

    # Run backtest
    print("Running option exercise backtest...")
    engine.run()

    # Print results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)

    # Get final portfolio state
    portfolio = engine.portfolio
    account = portfolio.account(Venue("NASDAQ"))
    print(f"Final account balance: {account.balance_total(USD)}")

    # Show positions
    positions = engine.cache.positions_open()
    print(f"\nFinal positions ({len(positions)}):")
    for position in positions:
        print(f"  {position.instrument_id}: {position.side} {position.quantity}")

    # Note: Timer diagnostics are shown in the engine logs above
    # The OptionExerciseModule reports: "0 expiry timers set, 0 expiries processed, 2 market prices cached"

    print("\nOption exercise example completed!")


if __name__ == "__main__":
    run_example()
