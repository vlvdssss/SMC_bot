#!/usr/bin/env python3
"""
V4 Trailing Stop Module - Dynamic trailing with configurable activation

ЛОГИКА:
- Активация: настраиваемая % от TP (из config, например 30%)
- Расстояние стопа: настраиваемая % от текущей цены (из config)
- Стоп ДВИГАЕТСЯ за ценой постоянно (не один раз!)
- Минимальный шаг перемещения: 5% для избежания частых модификаций
"""

from src.core.logger import logger
import yaml
from pathlib import Path


class TrailingStopV4:
    """
    V4 Dynamic Trailing Stop Handler.
    
    ЧИТАЕТ ИЗ config/trading.yaml:
    - activation_profit_percent: % от TP для активации (30% = $4.5)
    - stop_distance_percent: % от TP для расстояния стопа (50% = $7.5)
    
    ДИНАМИЧЕСКОЕ ДВИЖЕНИЕ:
    - После активации стоп следует за ценой
    - Каждые 5% минимум ($0.75) - обновление
    - Только в сторону профита (BUY вверх, SELL вниз)
    """
    
    def __init__(self, mt5_connector, telegram_notifier=None):
        """Initialize V4 trailing stop handler."""
        self.mt5 = mt5_connector
        self.telegram = telegram_notifier
        
        # Load config
        self._load_config()
        
        logger.info(f"[V4-Trailing] Initialized DYNAMIC MODE")
        logger.info(f"[V4-Trailing]    Activation: {self.activation_percent}% of TP")
        logger.info(f"[V4-Trailing]    Stop Distance: {self.stop_percent}% of TP")
    
    def _load_config(self):
        """Load trailing stop parameters from trading.yaml"""
        try:
            config_path = Path('config/trading.yaml')
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    trailing_config = config.get('trading', {}).get('trailing_stop', {})
                    
                    # Read percentages from config (default to 30% and 50%)
                    self.activation_percent = trailing_config.get('activation_profit_percent', 30)
                    self.stop_percent = trailing_config.get('stop_distance_percent', 50)
                    
                    # Convert to decimal (30 -> 0.3)
                    self.ACTIVATION_PERCENT = self.activation_percent / 100.0
                    self.STOP_DISTANCE = self.stop_percent / 100.0
                    
                    # Минимальный шаг перемещения (5% от TP)
                    self.MIN_MOVE_PERCENT = 0.05
                    
                    logger.info(f"[V4-Trailing] Loaded from config: activation={self.activation_percent}%, stop={self.stop_percent}%")
            else:
                # Fallback to defaults
                self.activation_percent = 30
                self.stop_percent = 50
                self.ACTIVATION_PERCENT = 0.3
                self.STOP_DISTANCE = 0.5
                self.MIN_MOVE_PERCENT = 0.05
                logger.warning("[V4-Trailing] Config not found, using defaults: 30%/50%")
        except Exception as e:
            logger.error(f"[V4-Trailing] Failed to load config: {e}")
            # Fallback
            self.activation_percent = 30
            self.stop_percent = 50
            self.ACTIVATION_PERCENT = 0.3
            self.STOP_DISTANCE = 0.5
            self.MIN_MOVE_PERCENT = 0.05
    
    def check_and_apply(self, tracked_positions: dict) -> None:
        """
        ДИНАМИЧЕСКИЙ TRAILING STOP с настраиваемой активацией.
        
        ЛОГИКА (пример для 30% активация, 50% расстояние):
        - TP = $15 от entry
        - Активация: цена прошла $4.5 (30% от $15)
        - Стоп ставится: на расстоянии $7.5 от entry (50% от $15)
        - При росте цены: стоп ДВИГАЕТСЯ сохраняя $7.5 от текущей цены
        
        ПРИМЕР (entry 5000, TP 5015, activation 30%, distance 50%):
        - Цена 5004.5 → SL 5000.0 (активация! entry + 0%)
        - Цена 5006.0 → SL 5001.5 (двигается! держит $7.5 от 5006)
        - Цена 5008.0 → SL 5003.5 (двигается! держит $7.5 от 5008)
        - Цена 5010.0 → SL 5005.5 (двигается!)
        
        Минимальный шаг: 5% от TP ($0.75) - избегаем частых модификаций
        
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
            
            # Calculate thresholds based on config percentages
            activation_threshold = tp_distance * self.ACTIVATION_PERCENT  # 30% = $4.5
            stop_distance = tp_distance * self.STOP_DISTANCE              # 50% = $7.5
            min_move = tp_distance * self.MIN_MOVE_PERCENT                # 5% = $0.75
            
            if direction == 'BUY':
                current_profit = current_price - entry
                
                # Проверка активации: профит >= activation_threshold
                if current_profit >= activation_threshold:
                    # ДИНАМИЧЕСКИЙ РАСЧЁТ: стоп на расстоянии stop_distance от ТЕКУЩЕЙ ЦЕНЫ
                    # Но при первой активации - от entry
                    if not pos_info.get('v4_trailing_activated', False):
                        # Первая активация: SL = entry + 0 (breakeven)
                        new_sl = entry
                    else:
                        # Уже активирован: SL следует за ценой
                        new_sl = current_price - stop_distance
                    
                    # Двигаем ТОЛЬКО ВВЕРХ (защита от возврата назад)
                    if new_sl > current_sl:
                        # Проверка минимального шага (избегаем частых модификаций)
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
                                        f"📏 Distance: ${stop_distance:.2f} ({self.stop_percent}%)"
                                    )
                                    self.telegram.send_message(message)
                            else:
                                logger.error(f"[V4-Trailing] ❌ Failed to modify SL")
            
            elif direction == 'SELL':
                current_profit = entry - current_price
                
                # Проверка активации: профит >= activation_threshold
                if current_profit >= activation_threshold:
                    # ДИНАМИЧЕСКИЙ РАСЧЁТ: стоп на расстоянии stop_distance от ТЕКУЩЕЙ ЦЕНЫ
                    if not pos_info.get('v4_trailing_activated', False):
                        # Первая активация: SL = entry (breakeven)
                        new_sl = entry
                    else:
                        # Уже активирован: SL следует за ценой
                        new_sl = current_price + stop_distance
                    
                    # Двигаем ТОЛЬКО ВНИЗ (защита от возврата назад)
                    if new_sl < current_sl:
                        # Проверка минимального шага
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
                                        f"📏 Distance: ${stop_distance:.2f} ({self.stop_percent}%)"
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
