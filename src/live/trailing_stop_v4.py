#!/usr/bin/env python3
"""
V4 Trailing Stop Module - Dynamic 10% step trailing

НОВАЯ ЛОГИКА:
- Активация: настраиваемая % от TP (из config, например 30%)
- Первый стоп: активация - 10% (30% → 20%)
- Дальше: каждые 10% профита → стоп +10%
- Расстояние: фиксированное 10% от TP

ПРИМЕРЫ:
1. Activation 30%:
   - Цена +$4.5 (30%) → SL на $3.0 (20%)
   - Цена +$6.0 (40%) → SL на $4.5 (30%)
   - Цена +$7.5 (50%) → SL на $6.0 (40%)

2. Activation 60%:
   - Цена +$9.0 (60%) → SL на $7.5 (50%)
   - Цена +$10.5 (70%) → SL на $9.0 (60%)
"""

from src.core.logger import logger
import yaml
from pathlib import Path


class TrailingStopV4:
    """
    V4 Dynamic Trailing Stop Handler.
    
    ЧИТАЕТ ИЗ config/trading.yaml:
    - activation_profit_percent: % от TP для активации (30%)
    
    ФИКСИРОВАННЫЕ ПАРАМЕТРЫ:
    - Первый стоп: activation - 10%
    - Шаг движения: 10% от TP
    - Дистанция стопа: 10% от TP
    """
    
    def __init__(self, mt5_connector, telegram_notifier=None):
        """Initialize V4 trailing stop handler."""
        self.mt5 = mt5_connector
        self.telegram = telegram_notifier
        
        # Load config
        self._load_config()
        
        logger.info(f"[V4-Trailing] Initialized DYNAMIC TRAILING")
        logger.info(f"[V4-Trailing]    Activation: {self.activation_percent}% of TP")
        logger.info(f"[V4-Trailing]    Step: {self.step_percent}% every {self.step_percent}% profit")
        logger.info(f"[V4-Trailing]    First Stop: {self.first_stop_percent}% (activation - step)")
    
    def _load_config(self):
        """Load trailing stop parameters from trading.yaml"""
        try:
            config_path = Path('config/trading.yaml')
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    trailing_config = config.get('trading', {}).get('trailing_stop', {})
                    
                    # Read activation from config (default 40%)
                    self.activation_percent = trailing_config.get('activation_profit_percent', 40)
                    
                    # Read trailing step from config (default 10%)
                    self.step_percent = trailing_config.get('trailing_step_percent', 10)
                    
                    # Первый стоп: activation - step
                    self.first_stop_percent = max(0, self.activation_percent - self.step_percent)
                    
                    # Convert to decimal
                    self.ACTIVATION_PERCENT = self.activation_percent / 100.0
                    self.FIRST_STOP_PERCENT = self.first_stop_percent / 100.0
                    self.TRAILING_STEP_PERCENT = self.step_percent / 100.0
                    self.STOP_DISTANCE_PERCENT = self.step_percent / 100.0  # Distance = step
                    
                    logger.info(f"[V4-Trailing] Config loaded: activation={self.activation_percent}%, step={self.step_percent}%, first_stop={self.first_stop_percent}%")
            else:
                # Fallback to defaults
                self.activation_percent = 40
                self.step_percent = 10
                self.first_stop_percent = 30
                self.ACTIVATION_PERCENT = 0.4
                self.FIRST_STOP_PERCENT = 0.3
                self.TRAILING_STEP_PERCENT = 0.10
                self.STOP_DISTANCE_PERCENT = 0.10
                logger.warning("[V4-Trailing] Config not found, using defaults: 40% activation, 10% step, 30% first stop")
        except Exception as e:
            logger.error(f"[V4-Trailing] Failed to load config: {e}")
            # Fallback
            self.activation_percent = 40
            self.step_percent = 10
            self.first_stop_percent = 30
            self.ACTIVATION_PERCENT = 0.4
            self.FIRST_STOP_PERCENT = 0.3
            self.TRAILING_STEP_PERCENT = 0.10
            self.STOP_DISTANCE_PERCENT = 0.10
    
    def check_and_apply(self, tracked_positions: dict) -> None:
        """
        ДИНАМИЧЕСКИЙ TRAILING STOP - шаг 10% каждые 10% профита.
        
        ЛОГИКА (для activation 30%, TP $15):
        - Активация: цена +$4.5 (30%) → SL на entry + $3.0 (20%)
        - Цена +$6.0 (40%) → SL на entry + $4.5 (30%)
        - Цена +$7.5 (50%) → SL на entry + $6.0 (40%)
        - Каждые +$1.5 (10%) → стоп +$1.5 (10%)
        
        ПРИМЕРЫ:
        1. Entry 5000, TP 5015 (activation 30%):
           - Цена 5004.5 → SL 5003.0 (первый стоп 20%)
           - Цена 5006.0 → SL 5004.5 (стоп 30%)
           - Цена 5007.5 → SL 5006.0 (стоп 40%)
        
        2. Entry 5000, TP 5015 (activation 60%):
           - Цена 5009.0 → SL 5007.5 (первый стоп 50%)
           - Цена 5010.5 → SL 5009.0 (стоп 60%)
        
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
            
            # Calculate thresholds
            activation_threshold = tp_distance * self.ACTIVATION_PERCENT      # 30% = $4.5
            first_stop_distance = tp_distance * self.FIRST_STOP_PERCENT       # 20% = $3.0
            trailing_step = tp_distance * self.TRAILING_STEP_PERCENT          # 10% = $1.5
            
            if direction == 'BUY':
                current_profit = current_price - entry
                
                # Проверка активации
                if current_profit >= activation_threshold:
                    # Вычисляем новый SL на основе текущего профита
                    # Профит $4.5 → SL на $3.0 (первый стоп 20%)
                    # Профит $6.0 → SL на $4.5 (стоп 30%)
                    # Профит $7.5 → SL на $6.0 (стоп 40%)
                    
                    # Сколько "шагов" по 10% прошла цена после активации?
                    profit_above_activation = current_profit - activation_threshold
                    steps = int(profit_above_activation / trailing_step)
                    
                    # Новый SL = entry + первый_стоп + (шаги * 10%)
                    new_sl = entry + first_stop_distance + (steps * trailing_step)
                    
                    # Двигаем ТОЛЬКО ВВЕРХ
                    if new_sl > current_sl:
                        profit_percent = (current_profit / tp_distance) * 100
                        sl_percent = ((new_sl - entry) / tp_distance) * 100
                        
                        logger.info(f"[V4-Trailing] 📈 BUY #{ticket} - Moving SL")
                        logger.info(f"[V4-Trailing]    Price: ${current_price:.2f} (profit: ${current_profit:.2f} = {profit_percent:.0f}%)")
                        logger.info(f"[V4-Trailing]    New SL: ${new_sl:.2f} (${new_sl - entry:.2f} = {sl_percent:.0f}% from entry)")
                        logger.info(f"[V4-Trailing]    Steps: {steps} x 10% after activation")
                        
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
                                    f"💰 Profit: <b>${current_profit:.2f}</b> ({profit_percent:.0f}%)\n"
                                    f"📊 Price: ${current_price:.2f}\n"
                                    f"🔒 SL: ${current_sl:.2f} → ${new_sl:.2f}\n"
                                    f"📏 SL Position: {sl_percent:.0f}% from entry"
                                )
                                self.telegram.send_message(message)
                        else:
                            logger.error(f"[V4-Trailing] ❌ Failed to modify SL")
            
            elif direction == 'SELL':
                current_profit = entry - current_price
                
                # Проверка активации
                if current_profit >= activation_threshold:
                    # Аналогично для SELL
                    profit_above_activation = current_profit - activation_threshold
                    steps = int(profit_above_activation / trailing_step)
                    
                    # Новый SL = entry - первый_стоп - (шаги * 10%)
                    new_sl = entry - first_stop_distance - (steps * trailing_step)
                    
                    # Двигаем ТОЛЬКО ВНИЗ
                    if new_sl < current_sl:
                        profit_percent = (current_profit / tp_distance) * 100
                        sl_percent = ((entry - new_sl) / tp_distance) * 100
                        
                        logger.info(f"[V4-Trailing] 📉 SELL #{ticket} - Moving SL")
                        logger.info(f"[V4-Trailing]    Price: ${current_price:.2f} (profit: ${current_profit:.2f} = {profit_percent:.0f}%)")
                        logger.info(f"[V4-Trailing]    New SL: ${new_sl:.2f} (${entry - new_sl:.2f} = {sl_percent:.0f}% from entry)")
                        logger.info(f"[V4-Trailing]    Steps: {steps} x 10% after activation")
                        
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
                                    f"💰 Profit: <b>${current_profit:.2f}</b> ({profit_percent:.0f}%)\n"
                                    f"📊 Price: ${current_price:.2f}\n"
                                    f"🔒 SL: ${current_sl:.2f} → ${new_sl:.2f}\n"
                                    f"📏 SL Position: {sl_percent:.0f}% from entry"
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
