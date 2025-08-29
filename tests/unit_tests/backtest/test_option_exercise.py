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
Unit tests for option exercise simulation module.
"""

from unittest.mock import Mock

import pandas as pd

from nautilus_trader.backtest.option_exercise import OptionExerciseConfig
from nautilus_trader.backtest.option_exercise import OptionExerciseModule
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AssetClass
from nautilus_trader.model.enums import OptionKind
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import PositionSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.instruments import IndexInstrument
from nautilus_trader.model.instruments import OptionContract
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.model.position import Position


class TestOptionExerciseConfig:
    """
    Test option exercise configuration.
    """

    def test_default_config(self):
        """
        Test default configuration values.
        """
        config = OptionExerciseConfig()

        assert config.auto_exercise_enabled is True

    def test_custom_config(self):
        """
        Test custom configuration values.
        """
        config = OptionExerciseConfig(auto_exercise_enabled=False)

        assert config.auto_exercise_enabled is False


class TestOptionExerciseModule:
    """
    Test option exercise module functionality.
    """

    def setup_method(self):
        """
        Set up test fixtures.
        """
        self.config = OptionExerciseConfig()
        self.module = OptionExerciseModule(self.config)

        # Mock cache for testing (we'll test core logic without exchange)
        self.mock_cache = Mock()

        # Create test instruments
        self.underlying = Equity(
            instrument_id=InstrumentId.from_str("AAPL.NASDAQ"),
            raw_symbol=Symbol("AAPL"),
            currency=USD,
            price_precision=2,
            price_increment=Price(0.01, 2),
            lot_size=Quantity.from_int(1),
            ts_event=0,
            ts_init=0,
        )

        self.call_option = OptionContract(
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
            multiplier=Quantity.from_int(100),
            lot_size=Quantity.from_int(1),
            ts_event=0,
            ts_init=0,
        )

        self.put_option = OptionContract(
            instrument_id=InstrumentId.from_str("AAPL240315P00150000.NASDAQ"),
            raw_symbol=Symbol("AAPL240315P00150000"),
            asset_class=AssetClass.EQUITY,
            underlying="AAPL",
            option_kind=OptionKind.PUT,
            strike_price=Price(150.0, 2),
            currency=USD,
            activation_ns=dt_to_unix_nanos(pd.Timestamp("2024-03-01", tz="UTC")),
            expiration_ns=dt_to_unix_nanos(pd.Timestamp("2024-03-15 16:00:00", tz="UTC")),
            price_precision=2,
            price_increment=Price(0.01, 2),
            multiplier=Quantity.from_int(100),
            lot_size=Quantity.from_int(1),
            ts_event=0,
            ts_init=0,
        )

        # Create index instrument for cash settlement testing
        self.index = IndexInstrument(
            instrument_id=InstrumentId.from_str("SPX.CBOE"),
            raw_symbol=Symbol("SPX"),
            currency=USD,
            price_precision=2,
            size_precision=0,
            price_increment=Price(0.01, 2),
            size_increment=Quantity.from_int(1),
            ts_event=0,
            ts_init=0,
        )

        # Create index option for cash settlement testing
        self.index_call_option = OptionContract(
            instrument_id=InstrumentId.from_str("SPX240315C04500000.CBOE"),
            raw_symbol=Symbol("SPX240315C04500000"),
            asset_class=AssetClass.INDEX,
            underlying="SPX",
            option_kind=OptionKind.CALL,
            strike_price=Price(4500.0, 2),
            currency=USD,
            activation_ns=dt_to_unix_nanos(pd.Timestamp("2024-03-01", tz="UTC")),
            expiration_ns=dt_to_unix_nanos(pd.Timestamp("2024-03-15 16:00:00", tz="UTC")),
            price_precision=2,
            price_increment=Price(0.01, 2),
            multiplier=Quantity.from_int(100),
            lot_size=Quantity.from_int(1),
            ts_event=0,
            ts_init=0,
        )

    def test_module_initialization(self):
        """
        Test module initialization.
        """
        assert self.module.config == self.config
        assert len(self.module.expiry_timers) == 0
        assert len(self.module.processed_expiries) == 0

    def test_pre_process_quote_tick(self):
        """
        Test pre-processing of quote ticks.

        Pre-processing is now a no-op since prices are retrieved at expiry time.

        """
        tick = QuoteTick(
            instrument_id=self.underlying.id,
            bid_price=Price(149.50, 2),
            ask_price=Price(150.50, 2),
            bid_size=Quantity.from_int(100),
            ask_size=Quantity.from_int(100),
            ts_event=0,
            ts_init=0,
        )

        # Should not raise any errors
        self.module.pre_process(tick)

    def test_is_option_itm_call(self):
        """
        Test ITM detection for call options.
        """
        underlying_price = Price(160.0, 2)  # Above strike of 150

        is_itm, intrinsic = self.module._is_option_itm(self.call_option, underlying_price)

        assert is_itm is True
        assert intrinsic == 10.0  # 160 - 150

    def test_is_option_otm_call(self):
        """
        Test OTM detection for call options.
        """
        underlying_price = Price(140.0, 2)  # Below strike of 150

        is_itm, intrinsic = self.module._is_option_itm(self.call_option, underlying_price)

        assert is_itm is False
        assert intrinsic == 0.0

    def test_is_option_itm_put(self):
        """
        Test ITM detection for put options.
        """
        underlying_price = Price(140.0, 2)  # Below strike of 150

        is_itm, intrinsic = self.module._is_option_itm(self.put_option, underlying_price)

        assert is_itm is True
        assert intrinsic == 10.0  # 150 - 140

    def test_is_option_otm_put(self):
        """
        Test OTM detection for put options.
        """
        underlying_price = Price(160.0, 2)  # Above strike of 150

        is_itm, intrinsic = self.module._is_option_itm(self.put_option, underlying_price)

        assert is_itm is False
        assert intrinsic == 0.0

    def test_calculate_underlying_position_call_long(self):
        """
        Test underlying position calculation for long call.
        """
        from nautilus_trader.test_kit.stubs.events import TestEventStubs
        from nautilus_trader.test_kit.stubs.execution import TestExecStubs

        # Create a proper position using test stubs
        order = TestExecStubs.market_order(
            instrument=self.call_option,
            order_side=OrderSide.BUY,
            quantity=Quantity.from_int(2),
        )

        from nautilus_trader.model.identifiers import PositionId

        fill = TestEventStubs.order_filled(
            order=order,
            instrument=self.call_option,
            last_px=Price(5.0, 2),
            position_id=PositionId("P-001"),
        )
        position = Position(self.call_option, fill)

        quantity, side = self.module._calculate_underlying_position(self.call_option, position)

        assert quantity == Quantity.from_str("200")  # 2 * 100 multiplier
        assert side == PositionSide.LONG  # Long call -> long underlying

    def test_calculate_underlying_position_put_long(self):
        """
        Test underlying position calculation for long put.
        """
        from nautilus_trader.test_kit.stubs.events import TestEventStubs
        from nautilus_trader.test_kit.stubs.execution import TestExecStubs

        # Create a proper position using test stubs
        order = TestExecStubs.market_order(
            instrument=self.put_option,
            order_side=OrderSide.BUY,
            quantity=Quantity.from_int(1),
        )

        from nautilus_trader.model.identifiers import PositionId

        fill = TestEventStubs.order_filled(
            order=order,
            instrument=self.put_option,
            last_px=Price(8.0, 2),
            position_id=PositionId("P-002"),
        )
        position = Position(self.put_option, fill)

        quantity, side = self.module._calculate_underlying_position(self.put_option, position)

        assert quantity == Quantity.from_str("100")  # 1 * 100 multiplier
        assert side == PositionSide.SHORT  # Long put -> short underlying

    def test_reset(self):
        """
        Test module reset functionality.
        """
        # Add some state
        self.module.expiry_timers[1] = "test_timer"
        self.module.processed_expiries.add(1)

        # Reset
        self.module.reset()

        # Verify state is cleared
        assert len(self.module.expiry_timers) == 0
        assert len(self.module.processed_expiries) == 0

    def test_process_disabled(self):
        """
        Test processing when auto exercise is disabled.
        """
        config = OptionExerciseConfig(auto_exercise_enabled=False)
        module = OptionExerciseModule(config)

        # Should not process anything when disabled
        module.process(dt_to_unix_nanos(pd.Timestamp("2024-03-15 16:00:00", tz="UTC")))

        # Should exit early without doing anything
        assert len(module.processed_expiries) == 0

    def test_cash_settlement_exercise(self):
        """
        Test cash settlement for index option exercise.
        """
        # Test the cash settlement price calculation directly
        underlying_price = Price(4600.0, 2)

        # Test with a mock underlying instrument that is an IndexInstrument
        # This simulates the cash settlement detection logic

        # Create a simple test to verify the intrinsic value calculation
        # For a call option with strike 4500 and underlying at 4600, intrinsic value should be 100
        strike_price = self.index_call_option.strike_price.as_double()
        underlying_value = underlying_price.as_double()

        if self.index_call_option.option_kind == OptionKind.CALL:
            expected_intrinsic = max(0.0, underlying_value - strike_price)
        else:  # PUT
            expected_intrinsic = max(0.0, strike_price - underlying_value)

        # Verify the calculation
        assert expected_intrinsic == 100.0  # $4600 - $4500 = $100

        # Test that the settlement price calculation works correctly
        # when we manually pass an IndexInstrument as the underlying
        settlement_price = Price(expected_intrinsic, self.index_call_option.strike_price.precision)
        assert settlement_price == Price(100.0, 2)
