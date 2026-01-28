#!/usr/bin/env python3
"""
V4 Trailing Stop Module - Fixed parameters for M5 scalping

LOGIC:
- Activation: 60% of TP ($6 profit for $10 TP)
- Stop placement: 50% of TP ($5 profit = breakeven+)
- Triggers ONLY ONCE per trade
"""

from src.core.logger import logger


class TrailingStopV4:
    """
    V4 Trailing Stop Handler.
    
    Fixed parameters for consistent risk management:
    - TP: $10
    - SL: $5
    - Trailing activation: 60% of TP ($6)
    - Trailing stop: 50% of TP ($5)
    """
    
    # V4 FIXED PARAMETERS
    FIXED_TP_DISTANCE = 10.0  # $10
    TRAILING_ACTIVATION_PERCENT = 0.6  # 60% от TP
    TRAILING_STOP_PERCENT = 0.5  # 50% от TP
    
    def __init__(self, mt5_connector, telegram_notifier=None):
        """Initialize V4 trailing stop handler."""
        self.mt5 = mt5_connector
        self.telegram = telegram_notifier  # Может быть None, установим позже
        logger.info("[V4-Trailing] Initialized (Activation: 60% TP, Stop: 50% TP)")
    
    def check_and_apply(self, tracked_positions: dict) -> None:
        """
        Check all positions and apply V4 trailing stop logic.
        
        DYNAMIC TP-BASED ACTIVATION:
        - Uses actual TP distance from tracked position
        - Activation: 60% of actual TP distance
        - Stop placement: 50% of actual TP distance
        
        Args:
            tracked_positions: Dict of {ticket: position_info}
        """
        if not tracked_positions:
            return
        
        for ticket, pos_info in list(tracked_positions.items()):
            # Check position still exists
            positions = self.mt5.positions_get(ticket=ticket)
            if not positions or len(positions) == 0:
                continue
            
            # Already activated? Skip
            if pos_info.get('v4_trailing_activated', False):
                continue
            
            current_position = positions[0]
            current_price = current_position.price_current
            entry = pos_info['entry_price']
            current_sl = pos_info.get('current_sl', pos_info['sl'])
            direction = pos_info['direction']
            symbol = current_position.symbol
            
            # 🔥 DYNAMIC: Calculate TP distance from tracked position
            tp = pos_info.get('tp', entry + self.FIXED_TP_DISTANCE if direction == 'BUY' else entry - self.FIXED_TP_DISTANCE)
            tp_distance = abs(tp - entry)
            
            # 🔥 DYNAMIC activation based on actual TP
            activation_profit = tp_distance * self.TRAILING_ACTIVATION_PERCENT  # 60% of actual TP
            trailing_stop_profit = tp_distance * self.TRAILING_STOP_PERCENT     # 50% of actual TP
            
            # Calculate current profit in dollars
            if direction == 'BUY':
                current_profit = current_price - entry
                
                # Check if activation threshold reached
                if current_profit >= activation_profit:
                    # Move SL to +trailing_stop_profit from entry (breakeven+)
                    new_sl = entry + trailing_stop_profit
                    
                    if new_sl > current_sl:
                        logger.info(f"[V4-Trailing] Attempting to move SL for BUY #{ticket}")
                        logger.info(f"[V4-Trailing]    Current SL: {current_sl:.2f}, New SL: {new_sl:.2f}")
                        
                        if self._modify_sl(ticket, new_sl, symbol):
                            pos_info['current_sl'] = new_sl
                            pos_info['v4_trailing_activated'] = True
                            logger.info(f"[V4-Trailing] ✅ BUY #{ticket} {symbol} - SL modified successfully")
                            logger.info(f"[V4-Trailing]    TP Distance: ${tp_distance:.2f}, Activation: ${activation_profit:.2f} (60%)")
                            logger.info(f"[V4-Trailing]    Current Profit: ${current_profit:.2f} >= ${activation_profit:.2f} ✓")
                            logger.info(f"[V4-Trailing]    SL: ${current_sl:.2f} → ${new_sl:.2f} (BE + ${trailing_stop_profit:.2f})")
                            
                            # Отправляем уведомление в Telegram ТОЛЬКО ПОСЛЕ успешной модификации
                            if self.telegram:
                                message = (
                                    f"🔒 <b>Trailing Stop Activated</b>\n\n"
                                    f"Symbol: <b>{symbol}</b>\n"
                                    f"Direction: <b>BUY</b>\n"
                                    f"Ticket: #{ticket}\n\n"
                                    f"💰 Profit: <b>${current_profit:.2f}</b>\n"
                                    f"🎯 TP Distance: ${tp_distance:.2f}\n"
                                    f"📊 Activation: ${activation_profit:.2f} (60%)\n\n"
                                    f"SL moved: ${current_sl:.2f} → ${new_sl:.2f}"
                                )
                                self.telegram.send_message(message)
                                logger.info(f"[V4-Trailing] Telegram notification sent for #{ticket}")
                        else:
                            logger.error(f"[V4-Trailing] ❌ Failed to modify SL for #{ticket} - check MT5 logs")
                            logger.error(f"[V4-Trailing]    Attempted: {current_sl:.2f} → {new_sl:.2f}")
            
            elif direction == 'SELL':
                current_profit = entry - current_price
                
                # Check if activation threshold reached
                if current_profit >= activation_profit:
                    # Move SL to -trailing_stop_profit from entry (breakeven+)
                    new_sl = entry - trailing_stop_profit
                    
                    if new_sl < current_sl:
                        logger.info(f"[V4-Trailing] Attempting to move SL for SELL #{ticket}")
                        logger.info(f"[V4-Trailing]    Current SL: {current_sl:.2f}, New SL: {new_sl:.2f}")
                        
                        if self._modify_sl(ticket, new_sl, symbol):
                            pos_info['current_sl'] = new_sl
                            pos_info['v4_trailing_activated'] = True
                            logger.info(f"[V4-Trailing] ✅ SELL #{ticket} {symbol} - SL modified successfully")
                            logger.info(f"[V4-Trailing]    TP Distance: ${tp_distance:.2f}, Activation: ${activation_profit:.2f} (60%)")
                            logger.info(f"[V4-Trailing]    Current Profit: ${current_profit:.2f} >= ${activation_profit:.2f} ✓")
                            logger.info(f"[V4-Trailing]    SL: ${current_sl:.2f} → ${new_sl:.2f} (BE - ${trailing_stop_profit:.2f})")
                            
                            # Отправляем уведомление в Telegram ТОЛЬКО ПОСЛЕ успешной модификации
                            if self.telegram:
                                message = (
                                    f"🔒 <b>Trailing Stop Activated</b>\n\n"
                                    f"Symbol: <b>{symbol}</b>\n"
                                    f"Direction: <b>SELL</b>\n"
                                    f"Ticket: #{ticket}\n\n"
                                    f"💰 Profit: <b>${current_profit:.2f}</b>\n"
                                    f"🎯 TP Distance: ${tp_distance:.2f}\n"
                                    f"📊 Activation: ${activation_profit:.2f} (60%)\n\n"
                                    f"SL moved: ${current_sl:.2f} → ${new_sl:.2f}"
                                )
                                self.telegram.send_message(message)
                                logger.info(f"[V4-Trailing] Telegram notification sent for #{ticket}")
                        else:
                            logger.error(f"[V4-Trailing] ❌ Failed to modify SL for #{ticket} - check MT5 logs")
                            logger.error(f"[V4-Trailing]    Attempted: {current_sl:.2f} → {new_sl:.2f}")
    
    def _modify_sl(self, ticket: int, new_sl: float, symbol: str) -> bool:
        """Modify position stop loss."""
        try:
            # Get current position
            pos = self.mt5.positions_get(ticket=ticket)
            if not pos or len(pos) == 0:
                logger.error(f"[V4-Trailing] Position #{ticket} not found")
                return False
            
            position = pos[0]
            
            # Normalize SL price to symbol digits
            symbol_info = self.mt5.symbol_info(symbol)
            if symbol_info:
                new_sl = round(new_sl, symbol_info.digits)
            
            # Prepare modify request
            request = {
                "action": self.mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": symbol,
                "sl": new_sl,
                "tp": position.tp,
                "magic": 123456,
                "comment": "V4 Trailing Stop"
            }
            
            logger.debug(f"[V4-Trailing] Sending MT5 modify request: {request}")
            
            # Send order
            result = self.mt5.order_send(request)
            
            if result is None:
                logger.error(f"[V4-Trailing] MT5 order_send returned None")
                return False
            
            if result.retcode != self.mt5.TRADE_RETCODE_DONE:
                logger.error(f"[V4-Trailing] MT5 modify failed - Code: {result.retcode}, Comment: {result.comment}")
                return False
            
            logger.info(f"[V4-Trailing] ✅ MT5 confirmed SL modification for #{ticket}")
            return True
            
        except Exception as e:
            logger.error(f"[V4-Trailing] Exception in _modify_sl: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
