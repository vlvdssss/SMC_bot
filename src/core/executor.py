"""Trade executor - manages position lifecycle."""

from ..models import TradeRequest, TradeResult
import logging

logger = logging.getLogger('BAZA')


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

    def __init__(self, broker_sim=None, mt5_connector=None, contract_size: int = 100, magic_number: int = 123456, bot_queue=None):
        if broker_sim is not None:
            self.broker = broker_sim
            self.is_live = False
        elif mt5_connector is not None:
            self.mt5 = mt5_connector
            self.is_live = True
        else:
            raise ValueError("Either broker_sim or mt5_connector must be provided")
        
        self.contract_size = contract_size
        self.magic_number = magic_number
        self.position = None
        self.last_closed_position = None
        
        # Bot queue for event-driven UI updates
        self.bot_queue = bot_queue

    def has_position(self, symbol: str = None) -> bool:
        """
        Check if position is open.
        
        Args:
            symbol: Optional symbol to check. If None, checks for any open position.
        
        Returns:
            True if position exists (for symbol or any), False otherwise
        """
        # Для live режима проверяем реальные позиции в MT5
        if self.is_live and hasattr(self, 'mt5'):
            try:
                if symbol:
                    # Проверяем позицию по конкретному символу
                    positions = self.mt5.positions_get(symbol=symbol)
                    
                    # DETAILED DEBUG: Log what MT5 returned
                    logger.debug(f"[Executor] positions_get({symbol}) returned: {positions}")
                    logger.debug(f"[Executor] Type: {type(positions)}, Is None: {positions is None}, Len: {len(positions) if positions else 0}")
                    
                    # CRITICAL FIX: Filter out invalid/closed positions
                    # positions_get() can return empty tuple or positions with volume=0 (phantom positions)
                    if positions is not None and len(positions) > 0:
                        # Only count positions with actual volume (open positions)
                        real_positions = [pos for pos in positions if hasattr(pos, 'volume') and pos.volume > 0]
                        
                        if real_positions:
                            logger.info(f"[Executor] ✅ Found {len(real_positions)} REAL position(s) for {symbol}")
                            for pos in real_positions:
                                logger.debug(f"[Executor]    Position: ticket={pos.ticket}, volume={pos.volume}, profit={pos.profit}")
                            return True
                        else:
                            logger.debug(f"[Executor] ❌ No REAL positions for {symbol} (found {len(positions)} phantom/closed)")
                            return False
                    else:
                        logger.debug(f"[Executor] ❌ No positions for {symbol}")
                        return False
                else:
                    # Проверяем любую позицию
                    positions = self.mt5.positions_total()
                    has_pos = positions > 0
                    if has_pos:
                        logger.debug(f"[Executor] Live MT5 positions: {positions}")
                    return has_pos
            except Exception as e:
                logger.error(f"[Executor] ❌ Failed to check MT5 positions: {e}")
                logger.exception(e)
                # Fallback to self.position
                return self.position is not None
        
        # Для backtest режима используем self.position
        # В backtest нет multi-symbol поддержки, поэтому игнорируем symbol
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
            # Конвертация direction: 'long'/'short' -> 'BUY'/'SELL'
            raw_direction = signal.get('direction', '').lower()
            if raw_direction == 'long':
                direction = 'BUY'
            elif raw_direction == 'short':
                direction = 'SELL'
            else:
                # Уже в формате BUY/SELL
                direction = signal.get('direction', '').upper()
            
            lot_size = signal.get('lot_size', signal.get('volume', 0.01))
            sl = signal.get('sl')
            tp = signal.get('tp')

            if direction not in ['BUY', 'SELL']:
                logger.error(f"[Executor] Invalid direction: {signal.get('direction')}")
                return False

            # Get current price and check spread
            tick = self.mt5.symbol_info_tick(symbol)
            if not tick:
                logger.error(f"[Executor] ❌ Cannot get tick data for {symbol} - [NO PRICES]")
                logger.error(f"[Executor]    Possible reasons: market closed, symbol unavailable, or no connection")
                return False
            
            # Validate prices are available
            if tick.bid <= 0 or tick.ask <= 0:
                logger.error(f"[Executor] ❌ Invalid prices for {symbol}: bid={tick.bid}, ask={tick.ask} - [NO PRICES]")
                logger.error(f"[Executor]    Market may be closed or symbol not available")
                return False

            # NEW: Spread filter (symbol-specific pip calculation)
            # Determine pip value based on symbol
            if 'XAU' in symbol or 'GOLD' in symbol:
                pip_multiplier = 10  # Gold: 1 pip = $0.1
            elif 'JPY' in symbol:
                pip_multiplier = 100  # JPY pairs: 1 pip = 0.01
            else:
                pip_multiplier = 10000  # Most pairs: 1 pip = 0.0001
            
            spread_pips = (tick.ask - tick.bid) * pip_multiplier
            MAX_SPREAD_PIPS = signal.get('max_spread_pips', 3.0)  # Default 3 pips
            
            if spread_pips > MAX_SPREAD_PIPS:
                logger.warning(f"[Executor] ❌ SPREAD TOO HIGH: {spread_pips:.1f} pips > {MAX_SPREAD_PIPS} pips - SKIPPING TRADE")
                logger.warning(f"[Executor]    Symbol: {symbol}, Bid: {tick.bid:.5f}, Ask: {tick.ask:.5f}")
                return False
            
            logger.info(f"[Executor] ✅ Spread OK: {spread_pips:.1f} pips <= {MAX_SPREAD_PIPS} pips")

            price = tick.ask if direction == 'BUY' else tick.bid

            # Prepare order
            order_type = self.mt5.ORDER_TYPE_BUY if direction == 'BUY' else self.mt5.ORDER_TYPE_SELL
            sl_price = sl if sl else 0
            tp_price = tp if tp else 0
            
            # ✅ CRITICAL FIX: Recalculate SL/TP from CURRENT price instead of stale entry price
            # AI calculates SL/TP from entry_price, but by the time we execute, market may have moved
            # This can cause "invalid stops" if price moved too much
            if sl_price > 0 and tp_price > 0:
                # Get original entry price from signal for comparison
                entry_from_ai = signal.get('entry', price)
                
                # Calculate intended distances from AI
                if direction == 'BUY':
                    intended_sl_distance = entry_from_ai - sl_price
                    intended_tp_distance = tp_price - entry_from_ai
                else:  # SELL
                    intended_sl_distance = sl_price - entry_from_ai
                    intended_tp_distance = entry_from_ai - tp_price
                
                # Check if entry price is stale (moved more than 10 pips from current)
                entry_drift = abs(price - entry_from_ai)
                drift_pips = entry_drift * 10000 if 'EUR' in symbol else entry_drift
                
                if drift_pips > 5.0:  # More than 5 pips drift
                    logger.warning(f"[Executor] ⚠️ Entry price drifted {drift_pips:.1f} pips (AI: {entry_from_ai:.5f} → Current: {price:.5f})")
                    logger.warning(f"[Executor] Recalculating SL/TP from current price to preserve distances")
                    
                    # Recalculate SL/TP from CURRENT price using AI's intended distances
                    if direction == 'BUY':
                        sl_price = price - intended_sl_distance
                        tp_price = price + intended_tp_distance
                    else:  # SELL
                        sl_price = price + intended_sl_distance
                        tp_price = price - intended_tp_distance
                    
                    logger.info(f"[Executor] Adjusted SL/TP: SL={sl_price:.5f}, TP={tp_price:.5f}")
            
            # Determine supported filling mode for this symbol
            symbol_info = self.mt5.symbol_info(symbol)
            if symbol_info:
                filling_mode = symbol_info.filling_mode
                # Try FOK first (most common), then IOC, then RETURN
                if filling_mode & 0x01:  # FOK supported
                    type_filling = self.mt5.ORDER_FILLING_FOK
                elif filling_mode & 0x02:  # IOC supported
                    type_filling = self.mt5.ORDER_FILLING_IOC
                else:  # RETURN
                    type_filling = self.mt5.ORDER_FILLING_RETURN
            else:
                type_filling = self.mt5.ORDER_FILLING_FOK  # Default
            
            # ✅ CHECK MARGIN: Ensure we have enough money for this lot size
            account_info = self.mt5.account_info()
            if account_info:
                free_margin = account_info.margin_free
                
                # Calculate required margin for this trade
                required_margin = self.mt5.order_calc_margin(order_type, symbol, lot_size, price)
                
                if required_margin is not None and required_margin > free_margin:
                    # Not enough margin - try to reduce lot size
                    logger.warning(f"[Executor] ⚠️ Insufficient margin: need ${required_margin:.2f}, have ${free_margin:.2f}")
                    
                    # Calculate maximum affordable lot size
                    max_lot = (free_margin * lot_size) / required_margin
                    max_lot = round(max_lot * 0.95, 2)  # Use 95% for safety margin
                    
                    # Get symbol's minimum lot
                    min_lot = symbol_info.volume_min if symbol_info else 0.01
                    
                    if max_lot >= min_lot:
                        lot_size = max_lot
                        logger.info(f"[Executor] 💡 Adjusted lot size to {lot_size:.2f} (max affordable)")
                    else:
                        logger.error(f"[Executor] ❌ Insufficient funds: cannot even trade minimum lot {min_lot:.2f}")
                        logger.error(f"[Executor] Required: ${required_margin:.2f}, Available: ${free_margin:.2f}")
                        return False
                else:
                    logger.debug(f"[Executor] Margin OK: need ${required_margin:.2f}, have ${free_margin:.2f}")
            else:
                logger.warning("[Executor] Could not get account info for margin check")

            # ✅ CRITICAL: Validate and adjust SL/TP to meet broker's STOPS_LEVEL requirement
            if symbol_info and sl_price > 0 and tp_price > 0:
                stops_level = symbol_info.trade_stops_level  # Minimum distance in points
                point = symbol_info.point  # Point size (0.00001 for EURUSD)
                
                # Convert stops_level to price distance
                min_distance = stops_level * point
                
                # FALLBACK: If broker returns 0 stops_level, use safe defaults
                if min_distance < 0.00001:  # Less than 0.1 pip
                    # Set minimum based on instrument type
                    if 'XAU' in symbol or 'GOLD' in symbol:
                        min_distance = 3.0  # $3 for gold
                    else:  # Forex
                        min_distance = 0.00025  # 25 pips for forex
                    logger.warning(f"[Executor] Broker stops_level=0, using fallback: {min_distance:.5f}")
                
                logger.debug(f"[Executor] Broker stops_level: {stops_level} points = {min_distance:.5f} price distance")
                logger.debug(f"[Executor] Current price: {price:.5f}, SL: {sl_price:.5f}, TP: {tp_price:.5f}")
                
                # Check and adjust SL distance
                if direction == 'BUY':
                    # For BUY: SL must be < price, TP must be > price
                    sl_distance = price - sl_price
                    tp_distance = tp_price - price
                    
                    logger.debug(f"[Executor] BUY distances - SL: {sl_distance:.5f}, TP: {tp_distance:.5f}, Min: {min_distance:.5f}")
                    
                    if sl_distance < min_distance:
                        old_sl = sl_price
                        sl_price = price - min_distance
                        logger.warning(f"[Executor] ⚠️ SL too close! Adjusted: {old_sl:.5f} → {sl_price:.5f} (min distance: {min_distance:.5f})")
                    
                    if tp_distance < min_distance:
                        old_tp = tp_price
                        tp_price = price + min_distance
                        logger.warning(f"[Executor] ⚠️ TP too close! Adjusted: {old_tp:.5f} → {tp_price:.5f} (min distance: {min_distance:.5f})")
                else:  # SELL
                    # For SELL: SL must be > price, TP must be < price
                    sl_distance = sl_price - price
                    tp_distance = price - tp_price
                    
                    logger.debug(f"[Executor] SELL distances - SL: {sl_distance:.5f}, TP: {tp_distance:.5f}, Min: {min_distance:.5f}")
                    
                    if sl_distance < min_distance:
                        old_sl = sl_price
                        sl_price = price + min_distance
                        logger.warning(f"[Executor] ⚠️ SL too close! Adjusted: {old_sl:.5f} → {sl_price:.5f} (min distance: {min_distance:.5f})")
                    
                    if tp_distance < min_distance:
                        old_tp = tp_price
                        tp_price = price - min_distance
                        logger.warning(f"[Executor] ⚠️ TP too close! Adjusted: {old_tp:.5f} → {tp_price:.5f} (min distance: {min_distance:.5f})")
                
                logger.info(f"[Executor] ✅ Stops validated: SL={sl_price:.5f}, TP={tp_price:.5f}")
            else:
                if not symbol_info:
                    logger.warning("[Executor] No symbol_info - cannot validate stops")
                elif sl_price == 0 or tp_price == 0:
                    logger.warning("[Executor] SL or TP is 0 - skipping stops validation")

            # FINAL LOG: Show exactly what we're sending to MT5
            logger.info(f"[Executor] 📤 Sending order: {symbol} {direction} {lot_size} lots")
            logger.info(f"[Executor]    Price: {price:.5f}, SL: {sl_price:.5f}, TP: {tp_price:.5f}")

            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "sl": sl_price,
                "tp": tp_price,
                "deviation": 10,
                "magic": self.magic_number,
                "comment": "BAZA Live Trade",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": type_filling,
            }

            # Emit order_sent event
            signal_id = signal.get('ai_signal_id')
            if hasattr(self, 'bot_queue') and self.bot_queue and signal_id:
                try:
                    signal_id_short = signal_id[-6:] if len(signal_id) >= 6 else signal_id
                    self.bot_queue.put({
                        'type': 'order_sent',
                        'signal_id': signal_id,
                        'signal_id_short': signal_id_short,
                        'symbol': symbol,
                        'direction': direction,
                        'lot_size': lot_size,
                        'price': price
                    })
                    logger.debug(f"[Executor] Event emitted: order_sent (ID: {signal_id_short})")
                except Exception as e:
                    logger.error(f"[Executor] Failed to emit order_sent event: {e}")

            # Отправляем ордер и проверяем результат
            result = self.mt5.order_send(request)
            
            if result is None:
                logger.error(f"[Executor] order_send returned None for {symbol}")
                return False
            
            # Проверяем код возврата
            if result.retcode == self.mt5.TRADE_RETCODE_DONE:
                logger.info(f"[Executor] Order executed: {symbol} {direction} {lot_size} lots at {price}")
                
                # Emit order_filled event
                if hasattr(self, 'bot_queue') and self.bot_queue and signal_id:
                    try:
                        signal_id_short = signal_id[-6:] if len(signal_id) >= 6 else signal_id
                        # Get ticket from result
                        ticket = result.order if hasattr(result, 'order') else None
                        self.bot_queue.put({
                            'type': 'order_filled',
                            'signal_id': signal_id,
                            'signal_id_short': signal_id_short,
                            'symbol': symbol,
                            'ticket': ticket,
                            'filled_price': price
                        })
                        logger.debug(f"[Executor] Event emitted: order_filled (ID: {signal_id_short}, Ticket: {ticket})")
                    except Exception as e:
                        logger.error(f"[Executor] Failed to emit order_filled event: {e}")
                
                # Emit position_opened event
                if hasattr(self, 'bot_queue') and self.bot_queue and signal_id:
                    try:
                        signal_id_short = signal_id[-6:] if len(signal_id) >= 6 else signal_id
                        ticket = result.order if hasattr(result, 'order') else None
                        self.bot_queue.put({
                            'type': 'position_opened',
                            'signal_id': signal_id,
                            'signal_id_short': signal_id_short,
                            'symbol': symbol,
                            'ticket': ticket,
                            'direction': direction,
                            'lot_size': lot_size,
                            'entry_price': price
                        })
                        logger.debug(f"[Executor] Event emitted: position_opened (ID: {signal_id_short}, Ticket: {ticket})")
                    except Exception as e:
                        logger.error(f"[Executor] Failed to emit position_opened event: {e}")
                
                return True
            else:
                # Логируем детали ошибки
                error_desc = {
                    self.mt5.TRADE_RETCODE_REJECT: "Request rejected",
                    self.mt5.TRADE_RETCODE_CANCEL: "Request canceled",
                    self.mt5.TRADE_RETCODE_INVALID: "Invalid request",
                    self.mt5.TRADE_RETCODE_INVALID_VOLUME: "Invalid volume",
                    self.mt5.TRADE_RETCODE_INVALID_PRICE: "Invalid price",
                    self.mt5.TRADE_RETCODE_NO_MONEY: "Not enough money",
                }.get(result.retcode, f"Unknown error code: {result.retcode}")
                
                # Emit order_failed event
                if hasattr(self, 'bot_queue') and self.bot_queue and signal_id:
                    try:
                        signal_id_short = signal_id[-6:] if len(signal_id) >= 6 else signal_id
                        self.bot_queue.put({
                            'type': 'order_failed',
                            'signal_id': signal_id,
                            'signal_id_short': signal_id_short,
                            'symbol': symbol,
                            'reason': f"{error_desc}: {result.comment}",
                            'retcode': result.retcode
                        })
                        logger.debug(f"[Executor] Event emitted: order_failed (ID: {signal_id_short})")
                    except Exception as e:
                        logger.error(f"[Executor] Failed to emit order_failed event: {e}")
                
                logger.error(f"[Executor] ❌ Order failed: {error_desc}")
                logger.error(f"[Executor]    Comment: {result.comment}")
                logger.error(f"[Executor]    Symbol: {symbol}, Direction: {direction}, Lot: {lot_size}")
                logger.error(f"[Executor]    Request Price: {price:.5f}, SL: {sl_price:.5f}, TP: {tp_price:.5f}")
                
                # Special handling for Invalid stops error
                if "invalid stops" in result.comment.lower():
                    if symbol_info:
                        stops_level = symbol_info.trade_stops_level
                        point = symbol_info.point
                        logger.error(f"[Executor]    Broker stops_level: {stops_level} points ({stops_level * point:.5f} price)")
                        
                        if direction == 'SELL':
                            sl_dist = sl_price - price
                            tp_dist = price - tp_price
                            logger.error(f"[Executor]    SELL distances: SL={sl_dist:.5f} ({sl_dist/point:.0f} points), TP={tp_dist:.5f} ({tp_dist/point:.0f} points)")
                        else:
                            sl_dist = price - sl_price
                            tp_dist = tp_price - price
                            logger.error(f"[Executor]    BUY distances: SL={sl_dist:.5f} ({sl_dist/point:.0f} points), TP={tp_dist:.5f} ({tp_dist/point:.0f} points)")
                
                return False

        except AttributeError as e:
            logger.error(f"[Executor] MT5 attribute error (check if MT5 is initialized): {e}")
            return False
        except Exception as e:
            logger.error(f"[Executor] Live trade execution error: {e}", exc_info=True)
            return False

    def open_position(self, signal: dict, lot_size: float, current_price: float,
                     current_time, balance: float, equity: float, used_margin: float) -> bool:
        """
        Try to open position.

        Returns:
            True if opened, False if rejected
        """
        # Проверка размера позиции через AlertManager
        try:
            from src.core.bot_manager import BotManager
            bot_manager = BotManager()
            if bot_manager.alert_manager:
                bot_manager.alert_manager.check_position_size(lot_size)
        except Exception:
            pass
        
        # Check if can open
        if not self.broker.can_open_position(balance, equity, used_margin, lot_size, current_price):
            return False

        # Use signal entry_price if provided, otherwise use current_price
        desired_entry = signal.get('entry_price', current_price)
        
        # Apply spread
        entry_price = self.broker.apply_spread(desired_entry, signal['direction'])

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
        
        # ЧИСТОЕ ЛОГИРОВАНИЕ ОТКРЫТИЯ
        symbol = self.position.instrument or "UNKNOWN"
        direction = "BUY" if signal['direction'] == 'long' else "SELL"
        logger.trade(f"Position opened - {direction} {symbol} @ {entry_price:.2f}, waiting...")
        
        # Telegram уведомление об открытии
        self._notify_position_opened(signal, lot_size, entry_price)

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
    
    def _notify_position_opened(self, signal: dict, lot_size: float, entry_price: float):
        """Уведомление о открытии позиции."""
        try:
            # Получаем telegram из BotManager
            from src.core.bot_manager import BotManager
            bot_manager = BotManager()
            
            if bot_manager.telegram and bot_manager.notify_config.get('trade_opened', True):
                symbol = signal.get('symbol', signal.get('instrument', 'UNKNOWN'))
                direction = "BUY" if signal['direction'] == 'long' else "SELL"
                
                bot_manager.telegram.send_trade_opened(
                    symbol=symbol,
                    direction=direction,
                    lot=lot_size,
                    entry=entry_price,
                    sl=signal['sl'],
                    tp=signal['tp']
                )
        except Exception as e:
            from src.core.logger import logger
            logger.debug(f"Failed to send telegram notification: {e}")
    
    def _notify_position_closed(self, symbol: str, direction: str, profit: float, pips: float, duration_str: str):
        """Уведомление о закрытии позиции."""
        try:
            from src.core.bot_manager import BotManager
            bot_manager = BotManager()
            
            if bot_manager.telegram and bot_manager.notify_config.get('trade_closed', True):
                bot_manager.telegram.send_trade_closed(
                    symbol=symbol,
                    direction=direction,
                    profit=profit,
                    pips=pips,
                    duration=duration_str
                )
        except Exception as e:
            from src.core.logger import logger
            logger.debug(f"Failed to send telegram notification: {e}")

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

        # Telegram уведомление
        try:
            symbol = self.position.instrument or "UNKNOWN"
            direction = "BUY" if self.position.direction == 'long' else "SELL"
            pips = abs(exit_price - self.position.entry_price) * (10000 if 'JPY' not in symbol else 100)
            duration = exit_time - self.position.entry_time
            duration_str = str(duration).split('.')[0]  # Убираем микросекунды
            
            # ЧИСТОЕ ЛОГИРОВАНИЕ ЗАКРЫТИЯ
            logger.profit(f"Position closed - {direction} {symbol}", amount=pnl)
            
            self._notify_position_closed(symbol, direction, pnl, pips, duration_str)
            
            # Проверка серии убытков
            if pnl < 0:
                from src.core.bot_manager import BotManager
                bot_manager = BotManager()
                if bot_manager.alert_manager and hasattr(bot_manager, 'stats'):
                    # Подсчитываем серию убытков
                    consecutive_losses = 0
                    recent_trades = bot_manager.stats.get('recent_trades', [])
                    for trade in reversed(recent_trades[-10:]):  # Последние 10 сделок
                        if trade.get('pnl', 0) < 0:
                            consecutive_losses += 1
                        else:
                            break
                    bot_manager.alert_manager.check_consecutive_losses(consecutive_losses)
        except Exception as e:
            from src.core.logger import logger
            logger.debug(f"Failed to send telegram notification: {e}")

        # Clear position
        self.position = None
        
        # Trigger immediate signal check after position close
        self._trigger_signal_check_after_close()

        return pnl
    
    def _trigger_signal_check_after_close(self):
        """Trigger immediate signal check after position closes."""
        try:
            from src.core.logger import logger
            logger.info("[Executor] Position closed - triggering immediate signal check")
            
            # Reset AI scheduler last_run to allow immediate analysis
            from src.ai.analyst_scheduler import get_scheduler
            scheduler = get_scheduler()
            if scheduler and scheduler.running:
                scheduler.last_run = None  # Reset cooldown
                logger.info("[Executor] AI Scheduler cooldown reset - next analysis will run immediately")
        except Exception as e:
            from src.core.logger import logger
            logger.debug(f"[Executor] Failed to trigger signal check: {e}")

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

            # Проверяем, что нет открытой позиции ДЛЯ ЭТОГО СИМВОЛА
            if self.has_position(symbol=trade_request.symbol):
                return TradeResult(
                    success=False,
                    error_message=f"Cannot open manual trade for {trade_request.symbol}: position already exists"
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
