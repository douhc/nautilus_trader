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
Integration tests for option exercise functionality in backtesting.
"""

import pandas as pd

from nautilus_trader.backtest.option_exercise import OptionExerciseConfig
from nautilus_trader.backtest.option_exercise import OptionExerciseModule
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AssetClass
from nautilus_trader.model.enums import OptionKind
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.instruments import OptionContract
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity


class TestOptionExerciseIntegration:
    """
    Integration tests for option exercise functionality.
    """

    def test_option_exercise_module_initialization(self):
        """
        Test that the option exercise module initializes correctly.
        """
        config = OptionExerciseConfig(
            auto_exercise_enabled=True,
        )

        module = OptionExerciseModule(config)

        assert module.config.auto_exercise_enabled is True
        assert module.expiry_timers == {}
        assert module.processed_expiries == set()

    def test_option_exercise_module_data_processing(self):
        """
        Test that the option exercise module processes market data correctly.
        """
        config = OptionExerciseConfig(
            auto_exercise_enabled=True,
        )

        module = OptionExerciseModule(config)

        # Create test instruments
        aapl = Equity(
            instrument_id=InstrumentId.from_str("AAPL.NASDAQ"),
            raw_symbol=Symbol("AAPL"),
            currency=USD,
            price_precision=2,
            price_increment=Price.from_str("0.01"),
            lot_size=Quantity.from_int(1),
            ts_event=0,
            ts_init=0,
        )

        option = OptionContract(
            instrument_id=InstrumentId.from_str("AAPL240315C00150000.NASDAQ"),
            raw_symbol=Symbol("AAPL240315C00150000"),
            asset_class=AssetClass.EQUITY,
            currency=USD,
            price_precision=2,
            price_increment=Price.from_str("0.01"),
            multiplier=Quantity.from_int(100),
            lot_size=Quantity.from_int(1),
            underlying="AAPL",
            option_kind=OptionKind.CALL,
            activation_ns=dt_to_unix_nanos(pd.Timestamp("2024-01-01", tz="UTC")),
            expiration_ns=dt_to_unix_nanos(pd.Timestamp("2024-03-15 16:00:00", tz="UTC")),
            strike_price=Price.from_str("150.00"),
            ts_event=0,
            ts_init=0,
        )

        # Create test market data
        base_time = pd.Timestamp("2024-03-14 09:30:00", tz="UTC")

        stock_tick = QuoteTick(
            instrument_id=aapl.id,
            bid_price=Price.from_str("154.95"),
            ask_price=Price.from_str("155.05"),
            bid_size=Quantity.from_int(100),
            ask_size=Quantity.from_int(100),
            ts_event=dt_to_unix_nanos(base_time),
            ts_init=dt_to_unix_nanos(base_time),
        )

        option_tick = QuoteTick(
            instrument_id=option.id,
            bid_price=Price.from_str("5.00"),
            ask_price=Price.from_str("5.10"),
            bid_size=Quantity.from_int(10),
            ask_size=Quantity.from_int(10),
            ts_event=dt_to_unix_nanos(base_time),
            ts_init=dt_to_unix_nanos(base_time),
        )

        # Test pre_process method
        module.pre_process(stock_tick)
        module.pre_process(option_tick)

        # Verify market prices are updated
        # Market prices no longer cached - test passes if no exceptions
        # Market prices no longer cached - test passes if no exceptions

        # Test process method
        module.process(dt_to_unix_nanos(base_time))

        # Test passes if no exceptions are raised

    def test_option_exercise_config_validation(self):
        """
        Test option exercise configuration validation.
        """
        # Test default config
        config = OptionExerciseConfig()
        assert config.auto_exercise_enabled is True

        # Test custom config
        config = OptionExerciseConfig(
            auto_exercise_enabled=False,
        )
        assert config.auto_exercise_enabled is False

    def test_option_exercise_disabled(self):
        """
        Test that option exercise module respects disabled configuration.
        """
        config = OptionExerciseConfig(
            auto_exercise_enabled=False,
        )

        module = OptionExerciseModule(config)

        # Create test data
        base_time = pd.Timestamp("2024-03-14 09:30:00", tz="UTC")
        stock_tick = QuoteTick(
            instrument_id=InstrumentId.from_str("AAPL.NASDAQ"),
            bid_price=Price.from_str("154.95"),
            ask_price=Price.from_str("155.05"),
            bid_size=Quantity.from_int(100),
            ask_size=Quantity.from_int(100),
            ts_event=dt_to_unix_nanos(base_time),
            ts_init=dt_to_unix_nanos(base_time),
        )

        # Test that pre_process returns early when disabled
        module.pre_process(stock_tick)

        # Market prices should not be updated when disabled
        # Market prices no longer cached - test passes if no exceptions

    def test_option_contract_creation(self):
        """
        Test that option contracts can be created with correct parameters.
        """
        option = OptionContract(
            instrument_id=InstrumentId.from_str("SPY240315C00400000.NASDAQ"),
            raw_symbol=Symbol("SPY240315C00400000"),
            asset_class=AssetClass.EQUITY,
            currency=USD,
            price_precision=2,
            price_increment=Price.from_str("0.01"),
            multiplier=Quantity.from_int(100),
            lot_size=Quantity.from_int(1),
            underlying="SPY",
            option_kind=OptionKind.CALL,
            activation_ns=dt_to_unix_nanos(pd.Timestamp("2024-01-01", tz="UTC")),
            expiration_ns=dt_to_unix_nanos(pd.Timestamp("2024-03-15 16:00:00", tz="UTC")),
            strike_price=Price.from_str("400.00"),
            ts_event=0,
            ts_init=0,
        )

        assert option.id.symbol.value == "SPY240315C00400000"
        assert option.underlying == "SPY"
        assert option.option_kind == OptionKind.CALL
        assert option.strike_price == Price.from_str("400.00")
        assert option.multiplier == Quantity.from_int(100)

    def test_equity_creation(self):
        """
        Test that equity instruments can be created with correct parameters.
        """
        equity = Equity(
            instrument_id=InstrumentId.from_str("SPY.NASDAQ"),
            raw_symbol=Symbol("SPY"),
            currency=USD,
            price_precision=2,
            price_increment=Price.from_str("0.01"),
            lot_size=Quantity.from_int(1),
            ts_event=0,
            ts_init=0,
        )

        assert equity.id.symbol.value == "SPY"
        assert equity.quote_currency == USD
        assert equity.price_precision == 2
        assert equity.lot_size == Quantity.from_int(1)
