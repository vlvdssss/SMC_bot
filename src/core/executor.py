"""Trade executor - manages position lifecycle."""

from ..models import TradeRequest, TradeResult


class Position:
    """Single position."""

    def __init__(self, direction: str, entry_price: float, sl: float, tp: float,
                 lot_size: float, entry_time, commission: float):
        self.direction = direction
        self.entry_price = entry_price
        self.sl = sl
        self.tp = tp
        self.lot_size = lot_size
        self.entry_time = entry_time
        self.commission = commission
        self.instrument = None
        self.exit_price = None
        self.exit_time = None
        self.pnl = 0.0
        self.exit_reason = None
        self.be_moved = False  # Track if SL moved to BE

    def update_sl_to_be(self, be_price: float):
        """Move SL to breakeven."""
        self.sl = be_price
        self.be_moved = True


class Executor:
    """Execute and manage trades."""

    def __init__(self, broker_sim=None, mt5_connector=None, contract_size: int = 100):
        if broker_sim is not None:
            self.broker = broker_sim
            self.is_live = False
        elif mt5_connector is not None:
            self.mt5 = mt5_connector
            self.is_live = True
        else:
            raise ValueError("Either broker_sim or mt5_connector must be provided")
        
        self.contract_size = contract_size
        self.position = None
        self.last_closed_position = None

    def has_position(self) -> bool:
        """Check if position is open."""
        return self.position is not None

    def execute_signal(self, symbol: str, signal: dict) -> bool:
        """Execute trading signal using MT5 for live trading."""
        if not self.is_live:
            # For backtest mode, use simulation
            return self._execute_signal_backtest(symbol, signal)
        else:
            # For live mode, use MT5
            return self._execute_signal_live(symbol, signal)

    def _execute_signal_backtest(self, symbol: str, signal: dict) -> bool:
        """Execute signal in backtest mode (simulation)."""
        # This would need current market data, balance, etc.
        # For now, just return True as placeholder
        return True

    def _execute_signal_live(self, symbol: str, signal: dict) -> bool:
        """Execute signal in live mode using MT5."""
        try:
            direction = signal.get('direction', '').upper()
            lot_size = signal.get('lot_size', 0.01)
            sl = signal.get('sl')
            tp = signal.get('tp')

            if direction not in ['BUY', 'SELL']:
                return False

            # Get current price
            tick = self.mt5.symbol_info_tick(symbol)
            if not tick:
                return False

            price = tick.ask if direction == 'BUY' else tick.bid

            # Prepare order
            order_type = self.mt5.ORDER_TYPE_BUY if direction == 'BUY' else self.mt5.ORDER_TYPE_SELL
            sl_price = sl if sl else 0
            tp_price = tp if tp else 0

            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "sl": sl_price,
                "tp": tp_price,
                "deviation": 10,
                "magic": 123456,
                "comment": "BAZA Live Trade",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }

            result = self.mt5.order_send(request)
            return result.retcode == self.mt5.TRADE_RETCODE_DONE

        except Exception as e:
            print(f"Live trade execution error: {e}")
            return False

    def open_position(self, signal: dict, lot_size: float, current_price: float,
                     current_time, balance: float, equity: float, used_margin: float) -> bool:
        """
        Try to open position.

        Returns:
            True if opened, False if rejected
        """
        # Check if can open
        if not self.broker.can_open_position(balance, equity, used_margin, lot_size, current_price):
            return False

        # Apply spread
        entry_price = self.broker.apply_spread(current_price, signal['direction'])

        # Apply slippage
        entry_price = self.broker.apply_slippage(entry_price, signal['direction'])

        # Calculate commission
        commission = self.broker.calculate_commission(lot_size)

        # Create position
        self.position = Position(
            direction=signal['direction'],
            entry_price=entry_price,
            sl=signal['sl'],
            tp=signal['tp'],
            lot_size=lot_size,
            entry_time=current_time,
            commission=commission
        )

        # Try to capture instrument name if provided in signal
        try:
            self.position.instrument = signal.get('symbol') or signal.get('instrument') or None
        except Exception:
            self.position.instrument = None

        return True

    def update_position(self, current_price: float, current_time) -> dict:
        """
        Update position and check for exit.

        Returns:
            dict with 'closed' (bool) and 'pnl' (float)
        """
        if not self.position:
            return {'closed': False, 'pnl': 0.0}

        # Check SL/TP hit
        exit_triggered = False
        exit_reason = None

        if self.position.direction == 'BUY':
            if current_price <= self.position.sl:
                exit_triggered = True
                exit_reason = 'SL'
            elif current_price >= self.position.tp:
                exit_triggered = True
                exit_reason = 'TP'
        else:  # SELL
            if current_price >= self.position.sl:
                exit_triggered = True
                exit_reason = 'SL'
            elif current_price <= self.position.tp:
                exit_triggered = True
                exit_reason = 'TP'

        if exit_triggered:
            pnl = self._close_position(current_price, current_time, exit_reason)
            return {'closed': True, 'pnl': pnl}

        # Check for BE move
        if not self.position.be_moved:
            current_rr = self._calculate_current_rr(current_price)
            if current_rr >= 1.0:
                # Move SL to BE (entry price)
                self.position.update_sl_to_be(self.position.entry_price)

        return {'closed': False, 'pnl': 0.0}

    def _calculate_current_rr(self, current_price: float) -> float:
        """Calculate current risk-reward ratio."""
        risk = abs(self.position.entry_price - self.position.sl)
        if risk == 0:
            return 0.0

        if self.position.direction == 'BUY':
            current_profit = current_price - self.position.entry_price
        else:
            current_profit = self.position.entry_price - current_price

        return current_profit / risk

    def _close_position(self, exit_price: float, exit_time, reason: str) -> float:
        """Close position and calculate PnL."""
        self.position.exit_price = exit_price
        self.position.exit_time = exit_time
        self.position.exit_reason = reason

        # Calculate PnL
        if self.position.direction == 'BUY':
            price_diff = exit_price - self.position.entry_price
        else:
            price_diff = self.position.entry_price - exit_price

        pnl = (price_diff * self.contract_size * self.position.lot_size) - self.position.commission
        self.position.pnl = pnl

        # Save closed position before clearing
        self.last_closed_position = self.position

        # Attempt to record trade into central bot_manager (if available)
        try:
            from src.core.bot_manager import bot_manager

            trade = {
                'id': int(exit_time.timestamp()) if hasattr(exit_time, 'timestamp') else 0,
                'date': exit_time.strftime('%Y-%m-%d') if hasattr(exit_time, 'strftime') else str(exit_time),
                'time': exit_time.strftime('%H:%M') if hasattr(exit_time, 'strftime') else '',
                'instrument': getattr(self.last_closed_position, 'instrument', None) or 'UNKNOWN',
                'direction': self.last_closed_position.direction,
                'pnl': round(float(self.last_closed_position.pnl), 2),
                'volume': float(self.last_closed_position.lot_size),
                'price': float(exit_price)
            }

            try:
                bot_manager.add_trade(trade)
            except Exception:
                # Do not fail closing if stats update fails
                pass
        except Exception:
            # bot_manager not available or import failed — ignore
            pass

        # Clear position
        self.position = None

        return pnl

    def get_used_margin(self, current_price: float) -> float:
        """Get currently used margin."""
        if not self.position:
            return 0.0

        return self.broker.calculate_margin_required(self.position.lot_size, current_price)

    def get_floating_pnl(self, current_price: float) -> float:
        """Get floating PnL."""
        if not self.position:
            return 0.0

        if self.position.direction == 'BUY':
            price_diff = current_price - self.position.entry_price
        else:
            price_diff = self.position.entry_price - current_price

        return price_diff * self.contract_size * self.position.lot_size

    def execute_manual_trade(self, trade_request: TradeRequest) -> TradeResult:
        """
        Execute manual trade request.

        Args:
            trade_request: TradeRequest with manual trade parameters

        Returns:
            TradeResult with execution status
        """
        try:
            # Проверяем, что это ручная сделка
            if trade_request.source != 'manual':
                return TradeResult(
                    success=False,
                    error_message="Only manual trades can be executed through this method"
                )

            # Проверяем, что нет открытой позиции
            if self.has_position():
                return TradeResult(
                    success=False,
                    error_message="Cannot open manual trade: position already exists"
                )

            if self.is_live:
                # Live режим - используем MT5
                signal = {
                    'direction': trade_request.direction.upper(),
                    'lot_size': trade_request.lot_size,
                    'sl': trade_request.stop_loss,
                    'tp': trade_request.take_profit,
                    'symbol': trade_request.symbol
                }
                
                success = self._execute_signal_live(trade_request.symbol, signal)
                
                if success:
                    # В Live режиме MT5 возвращает реальный тикет
                    # Но для простоты возвращаем заглушку
                    return TradeResult(
                        success=True,
                        ticket=123456,  # Заглушка
                        executed_price=trade_request.entry_price,
                        timestamp=trade_request.timestamp
                    )
                else:
                    return TradeResult(
                        success=False,
                        error_message="MT5 order failed"
                    )
            else:
                # Backtest режим - симуляция
                signal = {
                    'direction': trade_request.direction.upper(),
                    'sl': trade_request.stop_loss,
                    'tp': trade_request.take_profit,
                    'symbol': trade_request.symbol
                }

                current_price = self._get_current_price(trade_request.symbol)
                current_time = trade_request.timestamp

                balance = 10000.0  # Заглушка
                equity = 10000.0   # Заглушка
                used_margin = 0.0  # Заглушка

                success = self.open_position(
                    signal=signal,
                    lot_size=trade_request.lot_size,
                    current_price=current_price,
                    current_time=current_time,
                    balance=balance,
                    equity=equity,
                    used_margin=used_margin
                )

                if success:
                    ticket = self._generate_ticket()
                    return TradeResult(
                        success=True,
                        ticket=ticket,
                        executed_price=self.position.entry_price,
                        timestamp=current_time
                    )
                else:
                    return TradeResult(
                        success=False,
                        error_message="Position opening rejected by broker"
                    )

        except Exception as e:
            return TradeResult(
                success=False,
                error_message=f"Manual trade execution failed: {str(e)}"
            )

    def _get_current_price(self, symbol: str) -> float:
        """
        Получить текущую цену для символа.
        В реальной интеграции это будет через MT5 API.
        """
        # Заглушка - возвращаем типичную цену EURUSD
        if symbol == 'EURUSD':
            return 1.0850
        elif symbol == 'XAUUSD':
            return 1950.0
        else:
            return 1.0

    def _generate_ticket(self) -> int:
        """Генерация фейкового тикета для демо."""
        import random
        return random.randint(1000000, 9999999)
