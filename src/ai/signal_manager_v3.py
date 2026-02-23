#!/usr/bin/env python3
"""
Signal Manager Integration v3.0 - Новая архитектура Accuracy + Quality

ИНТЕГРАЦИЯ:
1. Заменяет старую логику block_level (SOFT/HARD) на систему Accuracy/Quality
2. Интегрирует GoldNewsFilter для фильтрации HIGH IMPACT новостей
3. Использует SignalEvaluator для принятия решений о входе и лоте

ИЗМЕНЕНИЯ В signal_manager.py:
- Вместо _process_block_level() используем SignalEvaluator.evaluate()
- Добавляем проверку GoldNewsFilter перед созданием сигнала
- lot_multiplier теперь зависит от Quality, а не от block_level
"""

from typing import Dict, Any, Tuple
from src.core.logger import logger
from src.ai.signal_quality import SignalEvaluator, RiskMode, SignalDecision
from src.ai.gold_news_filter import GoldNewsFetcher


class SignalManagerV3:
    """
    Обновлённый Signal Manager с раздел
ением Accuracy и Quality.
    
    Интегрируется с существующим AISignalManager через monkey-patching
    или наследование.
    """
    
    def __init__(self, news_fetcher=None, risk_mode: RiskMode = RiskMode.BALANCED):
        """
        Args:
            news_fetcher: Экземпляр NewsFetcher для проверки новостей
            risk_mode: Режим риска (CONSERVATIVE/BALANCED/AGGRESSIVE)
        """
        # Инициализируем оценщик сигналов
        self.evaluator = SignalEvaluator(risk_mode=risk_mode)
        
        # Инициализируем фильтр новостей
        if news_fetcher:
            self.gold_news = GoldNewsFetcher(news_fetcher)
            logger.info("[Signal Manager V3] Gold news filter enabled")
        else:
            self.gold_news = None
            logger.warning("[Signal Manager V3] News filter disabled - no news_fetcher provided")
    
    def process_decision_v3(
        self,
        decision: Dict[str, Any],
        trade_data: Dict[str, Any],
        symbol: str = "XAUUSD"
    ) -> Tuple[bool, SignalDecision, Dict[str, Any]]:
        """
        Обрабатывает решение GPT с новой архитектурой.
        
        Args:
            decision: {"action": "BUY/SELL/NONE", "confidence": 0-100, "block": "..."}
            trade_data: {"entry": float, "stop_loss": float, "take_profit": float, "risk_reward": float}
            symbol: Торговый инструмент
        
        Returns:
            (entry_allowed: bool, signal_decision: SignalDecision, summary: dict)
        """
        # Извлекаем параметры
        action = decision.get("action", "NONE").upper()
        
        # FIXED: Handle decimal confidence (GPT returns 1.0 or "1.0" instead of 100)
        raw_confidence = decision.get("confidence", 100)
        
        # Convert to float if string
        if isinstance(raw_confidence, str):
            try:
                raw_confidence = float(raw_confidence)
            except (ValueError, TypeError):
                raw_confidence = 100
        
        # Check if decimal format (0-1) and convert to percentage
        if isinstance(raw_confidence, (int, float)) and raw_confidence <= 1.0:
            # Convert decimal (0-1) to percentage (0-100)
            confidence = int(raw_confidence * 100)
            logger.info(f"[Signal V3] Converting decimal confidence {raw_confidence} → {confidence}%")
        else:
            # Already in percentage format (1-100), use as-is
            confidence = int(raw_confidence)
            logger.debug(f"[Signal V3] Using confidence: {confidence}%")
        
        risk_reward = trade_data.get("risk_reward", 1.5)
        
        # Создаём summary
        summary = {
            "action": action,
            "confidence": confidence,
            "symbol": symbol,
            "entry_allowed": False,
            "lot_multiplier": 0.0,
            "block_reason": None
        }
        
        # Если NONE - сразу возвращаем
        if action == "NONE":
            logger.info(f"[Signal V3] NONE decision - no entry evaluation needed")
            summary["block_reason"] = "GPT returned NONE - no trading opportunity"
            return False, None, summary
        
        # Проверяем новости (только для золота) - БЕЗ БЛОКИРОВКИ
        news_block = False  # ВСЕГДА False - новости не блокируют торговлю
        if symbol in ["XAUUSD", "GOLD"] and self.gold_news:
            try:
                safe, reason = self.gold_news.check_trading_safety_for_gold()
                if not safe:
                    # Логируем новость, но НЕ блокируем
                    logger.info(f"[Signal V3] 📰 High impact news detected: {reason} (trading allowed)")
            except Exception as e:
                logger.error(f"[Signal V3] News check error: {e}")
        
        # TODO: Определить has_confirmation из индикаторов
        # Пока заглушка - берём из confidence
        has_confirmation = confidence >= 70
        
        # Оцениваем сигнал
        signal_decision = self.evaluator.evaluate(
            confidence=confidence,
            risk_reward=risk_reward,
            has_confirmation=has_confirmation,
            news_block=news_block
        )
        
        # Обновляем summary
        summary["entry_allowed"] = signal_decision.entry_allowed
        summary["lot_multiplier"] = signal_decision.lot_multiplier
        summary["block_reason"] = signal_decision.block_reason
        summary["accuracy"] = signal_decision.accuracy.key
        summary["quality"] = signal_decision.quality.key
        summary["risk_mode"] = signal_decision.risk_mode.key
        
        # Логируем результат
        if signal_decision.entry_allowed:
            logger.info(
                f"[Signal V3] ✅ ENTRY ALLOWED | {action} {symbol} | "
                f"Accuracy: {signal_decision.accuracy.key.upper()} | "
                f"Quality: {signal_decision.quality.key.upper()} | "
                f"Lot: {signal_decision.lot_multiplier:.2f}x"
            )
        else:
            logger.warning(
                f"[Signal V3] ❌ ENTRY BLOCKED | {action} {symbol} | "
                f"Reason: {signal_decision.block_reason}"
            )
        
        return signal_decision.entry_allowed, signal_decision, summary
    
    def set_risk_mode(self, mode: RiskMode):
        """Изменить режим риска."""
        self.evaluator.set_risk_mode(mode)


# ============================================================
# MONKEY PATCH для интеграции с существующим Signal Manager
# ============================================================

def patch_signal_manager(signal_manager, news_fetcher=None):
    """
    Добавляет новую логику V3 к существующему AISignalManager.
    
    Args:
        signal_manager: Экземпляр AISignalManager
        news_fetcher: Экземпляр NewsFetcher (опционально)
    
    Usage:
        from src.ai.signal_manager_v3 import patch_signal_manager
        
        signal_manager = AISignalManager()
        patch_signal_manager(signal_manager, news_fetcher)
        
        # Теперь доступен метод process_analysis_v3()
    """
    # Создаём экземпляр V3
    v3 = SignalManagerV3(news_fetcher=news_fetcher, risk_mode=RiskMode.BALANCED)
    
    # Сохраняем ссылку на V3
    signal_manager._v3_processor = v3
    
    # Добавляем новый метод process_analysis_v3
    def process_analysis_v3(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает анализ с новой архитектурой V3.
        
        Заменяет process_analysis() для использования Accuracy/Quality системы.
        """
        try:
            decision = analysis.get("decision", {})
            trade_data = analysis.get("trade", {})
            symbol = analysis.get("symbol", "XAUUSD")
            
            # Используем V3 обработку
            entry_allowed, signal_decision, summary = self._v3_processor.process_decision_v3(
                decision=decision,
                trade_data=trade_data,
                symbol=symbol
            )
            
            # Если вход запрещён - возвращаем summary
            if not entry_allowed:
                return summary
            
            # Если вход разрешён - создаём сигнал с lot_multiplier из V3
            # (Дальше используем существующую логику создания сигнала)
            
            # Проверяем позицию ПО КОНКРЕТНОМУ СИМВОЛУ (не блокировать другие инструменты)
            if hasattr(self, 'executor') and self.executor:
                if self.executor.has_position(symbol=symbol):
                    logger.warning(f"[AI-Signal V3] Position already open for {symbol}")
                    summary["block_reason"] = "position_already_open"
                    summary["entry_allowed"] = False
                    return summary
            
            # Проверяем pending signals
            pending_count = sum(
                1 for s in self.active_signals
                if s.symbol == symbol and s.status == "pending"
            )
            
            if pending_count >= 1:
                logger.warning(f"[AI-Signal V3] Already {pending_count} pending signal(s)")
                summary["block_reason"] = "max_pending_signals_reached"
                summary["entry_allowed"] = False
                return summary
            
            # Формируем signal_data
            signal_data = {
                "type": decision["action"],
                "entry_price": trade_data.get("entry"),
                "stop_loss": trade_data.get("stop_loss"),
                "take_profit": trade_data.get("take_profit"),
                "confidence": summary["confidence"],  # Use validated confidence from summary (always 100%)
                "risk_reward": trade_data.get("risk_reward", 1.5),
                "reasoning": (
                    f"GPT V3: {signal_decision.accuracy.key.upper()} accuracy, "
                    f"{signal_decision.quality.key.upper()} quality, "
                    f"lot {signal_decision.lot_multiplier:.2f}x"
                ),
                "trigger_time": "immediate",
                # ВАЖНО: Передаём lot_multiplier из V3
                "lot_multiplier": signal_decision.lot_multiplier
            }
            
            # Валидация
            if not self._validate_signal(signal_data):
                logger.warning("[AI-Signal V3] Signal validation failed")
                summary["block_reason"] = "validation_failed"
                summary["entry_allowed"] = False
                return summary
            
            # Создаём сигнал
            signal = self._create_signal(
                symbol=symbol,
                signal_data=signal_data,
                version=analysis.get("analysis_version", "3.0")
            )
            
            self.active_signals.append(signal)
            summary["signals_created"] = 1
            summary["signal_id"] = signal.id
            
            # Логируем
            ttl_minutes = self.config.get('trading', {}).get('signal_ttl', {}).get('ttl_minutes', 60)
            
            logger.info(
                f"[AI-Signal V3] ✅ Signal created: {signal.type} {symbol} @ {signal.entry_price:.5f} "
                f"| SL: {signal.stop_loss:.5f} | TP: {signal.take_profit:.5f} "
                f"| Accuracy: {signal_decision.accuracy.key} ({signal.confidence}%) "
                f"| Quality: {signal_decision.quality.key} (lot: {signal_decision.lot_multiplier:.2f}x) "
                f"| TTL: {ttl_minutes}min"
            )
            
            # Отправляем уведомление в Telegram
            try:
                from src.core.bot_manager import BotManager
                bot_manager = BotManager()
                
                if bot_manager.telegram and bot_manager.notify_config.get('ai_signal', True):
                    bot_manager.telegram.send_signal(
                        symbol=symbol,
                        direction=signal.type,
                        entry=signal.entry_price,
                        sl=signal.stop_loss,
                        tp=signal.take_profit,
                        confidence=signal.confidence,
                        quality=signal_decision.quality.key,
                        accuracy=signal_decision.accuracy.key,
                        lot_multiplier=signal_decision.lot_multiplier,
                        signal_id=signal.id
                    )
                    logger.info(f"[Telegram] Signal notification sent for {symbol}")
            except Exception as tg_error:
                logger.error(f"[Telegram] Failed to send signal notification: {tg_error}")
            
            # Сохраняем
            self._save_state()
            
            return summary
            
        except Exception as e:
            logger.error(f"[AI-Signal V3] Error processing analysis: {e}", exc_info=True)
            return {"error": str(e), "signals_created": 0}
    
    # Привязываем метод к signal_manager
    import types
    signal_manager.process_analysis_v3 = types.MethodType(process_analysis_v3, signal_manager)
    
    logger.info("[Signal Manager V3] Successfully patched AISignalManager with V3 methods")
    
    return signal_manager


# ============================================================
# УТИЛИТЫ ДЛЯ ПЕРЕХОДА
# ============================================================

def migrate_to_v3(signal_manager, news_fetcher, enable_v3: bool = True):
    """
    Мигрирует Signal Manager на V3 с возможностью переключения.
    
    Args:
        signal_manager: AISignalManager
        news_fetcher: NewsFetcher
        enable_v3: Использовать V3 (True) или старую логику (False)
    
    Returns:
        signal_manager с добавленными методами
    """
    # Патчим signal_manager
    patch_signal_manager(signal_manager, news_fetcher)
    
    # Если V3 включён - подменяем основной метод
    if enable_v3:
        # Сохраняем старый метод как fallback
        signal_manager._process_analysis_v2 = signal_manager.process_analysis
        
        # Подменяем на V3
        signal_manager.process_analysis = signal_manager.process_analysis_v3
        
        logger.info("[Migration] ✅ V3 enabled as primary analysis processor")
    else:
        logger.info("[Migration] V2 remains active, V3 available as process_analysis_v3()")
    
    return signal_manager
