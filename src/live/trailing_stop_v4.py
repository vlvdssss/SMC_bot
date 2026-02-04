#!/usr/bin/env python3
"""
V4 Trailing Stop Module - Dynamic trailing every 10% profit

НОВАЯ ЛОГИКА:
- TP $15 = 100% профита
- При достижении 10% ($1.5) - активация trailing stop
- Дальше каждые 10% ($1.5) - стоп двигается за ценой
- Стоп всегда на расстоянии 10% ($1.5) ОТ ТЕКУЩЕЙ ЦЕНЫ
"""

from src.core.logger import logger
import yaml
from pathlib import Path


class TrailingStopV4:
    """
    V4 Dynamic Trailing Stop Handler.
    
    ЛОГИКА:
    - Активация: 10% от TP ($1.5 из $15)
    - Шаг перемещения: каждые 10% ($1.5)
    - Расстояние стопа: 10% от текущей цены
    """
    
    def __init__(self, mt5_connector, telegram_notifier=None):
        """Initialize V4 trailing stop handler."""
        self.mt5 = mt5_connector
        self.telegram = telegram_notifier
        
        # Fixed parameters for $15 TP
        self.ACTIVATION_PERCENT = 0.10   # 10% - активация ($1.5)
        self.TRAILING_STEP = 0.10        # 10% - шаг перемещения ($1.5)
        self.STOP_DISTANCE = 0.10        # 10% - расстояние стопа от цены
        
        logger.info(f"[V4-Trailing] Initialized DYNAMIC MODE (10% activation, 10% trailing step)")
    
    def _load_config(self):
        """Config loading not used - fixed 10% parameters"""
        pass
    
    def check_and_apply(self, tracked_positions: dict) -> None:
        """
        ДИНАМИЧЕСКИЙ TRAILING STOP - двигается каждые 10%.
        
        ЛОГИКА ДЛЯ BUY:
        - TP = $15 от entry
        - Активация: цена прошла $1.5 (10%)
        - Стоп ставится на: текущая_цена - $1.5
        - При росте цены на +$1.5 - стоп поднимается
        
        ПРИМЕР (entry 5000, TP 5015):
        - Цена 5001.5 → SL 5000.0 (активация)
        - Цена 5003.0 → SL 5001.5 (поднимается)
        - Цена 5004.5 → SL 5003.0 (поднимается)
        - и так далее каждые $1.5
        
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
            
            current_position = positions[0]
            current_price = current_position.price_current
            entry = pos_info['entry_price']
            current_sl = pos_info.get('current_sl', pos_info['sl'])
            direction = pos_info['direction']
            symbol = current_position.symbol
            
            # Get TP distance from position
            tp = pos_info.get('tp', entry + 15.0 if direction == 'BUY' else entry - 15.0)
            tp_distance = abs(tp - entry)
            
            # Calculate thresholds based on TP distance
            activation_threshold = tp_distance * self.ACTIVATION_PERCENT  # $1.5
            stop_distance = tp_distance * self.STOP_DISTANCE              # $1.5
            
            if direction == 'BUY':
                current_profit = current_price - entry
                
                # Проверка активации: профит >= 10% ($1.5)
                if current_profit >= activation_threshold:
                    # Новый SL на расстоянии $1.5 от текущей цены
                    new_sl = current_price - stop_distance
                    
                    # Двигаем ТОЛЬКО ВВЕРХ (защита от возврата назад)
                    if new_sl > current_sl:
                        # Проверка минимального шага (избегаем частых модификаций)
                        min_move = tp_distance * 0.05  # 5% минимум ($0.75)
                        sl_improvement = new_sl - current_sl
                        
                        if sl_improvement >= min_move or not pos_info.get('v4_trailing_activated', False):
                            logger.info(f"[V4-Trailing] 📈 BUY #{ticket} - Moving SL")
                            logger.info(f"[V4-Trailing]    Current: Price ${current_price:.2f}, SL ${current_sl:.2f}")
                            logger.info(f"[V4-Trailing]    Profit: ${current_profit:.2f} (entry ${entry:.2f})")
                            logger.info(f"[V4-Trailing]    New SL: ${new_sl:.2f} (price - ${stop_distance:.2f})")
                            
                            if self._modify_sl(ticket, new_sl, symbol):
                                pos_info['current_sl'] = new_sl
                                
                                # Первая активация?
                                first_activation = not pos_info.get('v4_trailing_activated', False)
                                pos_info['v4_trailing_activated'] = True
                                
                                logger.info(f"[V4-Trailing] ✅ SL Updated: ${current_sl:.2f} → ${new_sl:.2f}")
                                
                                # Уведомление в Telegram
                                if self.telegram:
                                    emoji = "🎯" if first_activation else "📈"
                                    status = "ACTIVATED" if first_activation else "UPDATED"
                                    message = (
                                        f"{emoji} <b>Trailing Stop {status}</b>\n\n"
                                        f"Symbol: <b>{symbol}</b> BUY\n"
                                        f"Ticket: #{ticket}\n\n"
                                        f"💰 Profit: <b>${current_profit:.2f}</b>\n"
                                        f"📊 Price: ${current_price:.2f}\n"
                                        f"🔒 SL: ${current_sl:.2f} → ${new_sl:.2f}\n"
                                        f"📏 Distance: ${stop_distance:.2f} (10%)"
                                    )
                                    self.telegram.send_message(message)
                            else:
                                logger.error(f"[V4-Trailing] ❌ Failed to modify SL")
            
            elif direction == 'SELL':
                current_profit = entry - current_price
                
                # Проверка активации: профит >= 10% ($1.5)
                if current_profit >= activation_threshold:
                    # Новый SL на расстоянии $1.5 от текущей цены
                    new_sl = current_price + stop_distance
                    
                    # Двигаем ТОЛЬКО ВНИЗ (защита от возврата назад)
                    if new_sl < current_sl:
                        # Проверка минимального шага
                        min_move = tp_distance * 0.05  # 5% минимум ($0.75)
                        sl_improvement = current_sl - new_sl
                        
                        if sl_improvement >= min_move or not pos_info.get('v4_trailing_activated', False):
                            logger.info(f"[V4-Trailing] 📉 SELL #{ticket} - Moving SL")
                            logger.info(f"[V4-Trailing]    Current: Price ${current_price:.2f}, SL ${current_sl:.2f}")
                            logger.info(f"[V4-Trailing]    Profit: ${current_profit:.2f} (entry ${entry:.2f})")
                            logger.info(f"[V4-Trailing]    New SL: ${new_sl:.2f} (price + ${stop_distance:.2f})")
                            
                            if self._modify_sl(ticket, new_sl, symbol):
                                pos_info['current_sl'] = new_sl
                                
                                # Первая активация?
                                first_activation = not pos_info.get('v4_trailing_activated', False)
                                pos_info['v4_trailing_activated'] = True
                                
                                logger.info(f"[V4-Trailing] ✅ SL Updated: ${current_sl:.2f} → ${new_sl:.2f}")
                                
                                # Уведомление в Telegram
                                if self.telegram:
                                    emoji = "🎯" if first_activation else "📉"
                                    status = "ACTIVATED" if first_activation else "UPDATED"
                                    message = (
                                        f"{emoji} <b>Trailing Stop {status}</b>\n\n"
                                        f"Symbol: <b>{symbol}</b> SELL\n"
                                        f"Ticket: #{ticket}\n\n"
                                        f"💰 Profit: <b>${current_profit:.2f}</b>\n"
                                        f"📊 Price: ${current_price:.2f}\n"
                                        f"🔒 SL: ${current_sl:.2f} → ${new_sl:.2f}\n"
                                        f"📏 Distance: ${stop_distance:.2f} (10%)"
                                    )
                                    self.telegram.send_message(message)
                            else:
                                logger.error(f"[V4-Trailing] ❌ Failed to modify SL")
    
    def _modify_sl(self, ticket: int, new_sl: float, symbol: str) -> bool:
        """
        Modify position stop loss with proper validation.
        
        ВАЖНО:
        - Проверяем минимальную дистанцию от цены
        - Нормализуем цену по digits символа
        - Логируем все ошибки MT5
        """
        try:
            # Get current position
            pos = self.mt5.positions_get(ticket=ticket)
            if not pos or len(pos) == 0:
                logger.error(f"[V4-Trailing] Position #{ticket} not found")
                return False
            
            position = pos[0]
            current_price = position.price_current
            
            # Get symbol info for validation
            symbol_info = self.mt5.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"[V4-Trailing] Symbol {symbol} info not available")
                return False
            
            # Normalize SL price to symbol digits
            new_sl = round(new_sl, symbol_info.digits)
            
            # Validate SL distance from current price (MT5 minimum)
            # Gold обычно требует минимум 1-2 пункта
            min_distance = 2.0  # $2 минимум для золота
            
            if position.type == 0:  # BUY
                sl_distance = current_price - new_sl
                if sl_distance < min_distance:
                    logger.warning(f"[V4-Trailing] SL too close to price: {sl_distance:.2f} < {min_distance}")
                    new_sl = current_price - min_distance
                    logger.info(f"[V4-Trailing] Adjusted SL to minimum distance: {new_sl:.2f}")
            else:  # SELL
                sl_distance = new_sl - current_price
                if sl_distance < min_distance:
                    logger.warning(f"[V4-Trailing] SL too close to price: {sl_distance:.2f} < {min_distance}")
                    new_sl = current_price + min_distance
                    logger.info(f"[V4-Trailing] Adjusted SL to minimum distance: {new_sl:.2f}")
            
            # Prepare modify request
            request = {
                "action": self.mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": symbol,
                "sl": new_sl,
                "tp": position.tp,
                "magic": 123456,
                "comment": "V4 Dynamic Trailing"
            }
            
            logger.debug(f"[V4-Trailing] MT5 request: {request}")
            
            # Send order
            result = self.mt5.order_send(request)
            
            if result is None:
                logger.error(f"[V4-Trailing] MT5 order_send returned None")
                return False
            
            if result.retcode != self.mt5.TRADE_RETCODE_DONE:
                logger.error(f"[V4-Trailing] ❌ MT5 Error {result.retcode}: {result.comment}")
                logger.error(f"[V4-Trailing]    Price: {current_price:.2f}, Attempted SL: {new_sl:.2f}")
                return False
            
            logger.info(f"[V4-Trailing] ✅ MT5 confirmed SL modification")
            return True
            
        except Exception as e:
            logger.error(f"[V4-Trailing] Exception in _modify_sl: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
