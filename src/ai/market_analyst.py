#!/usr/bin/env python3
"""
AI Market Analyst Service - GPT-powered market analysis

Provides deep market analysis using ChatGPT with chart screenshots and metrics.
Returns structured JSON with trading signals, blocks, and confidence levels.
"""

import base64
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import MetaTrader5 as mt5
import pandas as pd
import threading
from openai import OpenAI, APIError, RateLimitError, APIConnectionError, Timeout

from src.core.logger import logger
from src.ai.news_fetcher import RealTimeNewsFetcher
from src.ai.screenshot_service import ChartScreenshotService


class MarketAnalystService:
    """
    AI-powered market analyst using GPT-4 Vision v2.0.
    Analyzes charts, metrics, and news to provide trading signals.
    
    VERSION 2.0: No longer saves files - returns analysis to SignalManager
    """
    
    # Versions
    ANALYSIS_VERSION = "2.0"
    PROMPT_VERSION = "2026-01"
    
    def __init__(self, api_key: str = None):
        """Initialize Market Analyst Service v2.0."""
        # Пробуем загрузить API ключ в порядке приоритета:
        # 1. Параметр api_key  
        # 2. Credentials файл
        # 3. .env файл
        if not api_key:
            try:
                from src.core.credentials import get_credential
                api_key = get_credential('OPENAI_API_KEY')
            except Exception:
                pass
        
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        # GPT Connection Recovery State
        self.gpt_available = True  # Assume available if API key exists, will disable on failures
        self.gpt_failed_attempts = 0
        self.gpt_last_failure_time = None
        self.gpt_recovery_thread = None
        self._recovery_lock = threading.Lock()
        
        # Детальная проверка API ключа
        if not self.api_key:
            logger.warning("[AI] ⚠️ OpenAI API key not configured")
            logger.warning("[AI] 💡 Bot will work in MANUAL mode without AI analysis")
            logger.warning("[AI] 🔧 To enable AI:")
            logger.warning("[AI]    1. Open .env file in project root")
            logger.warning("[AI]    2. Set: OPENAI_API_KEY=sk-proj-your_key_here")
            logger.warning("[AI]    3. Get key at: https://platform.openai.com/api-keys")
            # НЕ падаем, просто работаем без AI
            self.client = None
            return
        
        # Проверка формата ключа
        if not self.api_key.startswith('sk-'):
            logger.warning(f"[AI] ⚠️ API key format looks incorrect: {self.api_key[:15]}...")
            logger.warning(f"[AI] 💡 OpenAI keys should start with 'sk-' or 'sk-proj-'")
            logger.warning(f"[AI] 🔧 Check your .env file for typos")
            # Пробуем всё равно использовать, может это новый формат
        
        logger.info(f"[AI] ✅ API Key loaded: {self.api_key[:15]}...{self.api_key[-4:]}")
        
        try:
            # Увеличенный timeout для медленного интернета
            self.client = OpenAI(api_key=self.api_key, timeout=60.0)  # 60 секунд для OpenAI
            logger.info("[AI] ✅ OpenAI client initialized successfully (timeout=60s)")
            
            # Test connection with a minimal request
            try:
                logger.info("[AI] 🔍 Testing API connection...")
                test_response = self.client.models.list()
                logger.info("[AI] ✅ API connection test successful")
                logger.debug(f"[AI] Available models: {len(test_response.data)} models found")
            except RateLimitError as e:
                logger.error("[AI] ⚠️ API ключ работает, но превышен лимит запросов")
                logger.error(f"[AI] Детали: {e}")
                logger.error("[AI] 💡 Проверь квоту: https://platform.openai.com/account/usage")
                # Don't raise - allow initialization, will fail later with better error
            except APIError as e:
                if "invalid" in str(e).lower() and "key" in str(e).lower():
                    logger.error("[AI] ❌ API ключ НЕВЕРНЫЙ!")
                    logger.error(f"[AI] Детали: {e}")
                    logger.error("[AI] 💡 Проверь ключ на: https://platform.openai.com/api-keys")
                    raise ValueError(f"Invalid API key: {e}")
                else:
                    logger.warning(f"[AI] ⚠️ API test failed: {e}")
                    logger.warning("[AI] Продолжаю инициализацию, но API может не работать")
            except Exception as e:
                logger.warning(f"[AI] ⚠️ Connection test failed: {type(e).__name__}: {e}")
                logger.warning("[AI] Продолжаю инициализацию...")
                
        except Exception as e:
            logger.error(f"[AI] ❌ Failed to initialize OpenAI client: {e}")
            raise
        
        self.screenshot_service = ChartScreenshotService()
        self.news_fetcher = RealTimeNewsFetcher()
        
        # Load config for GPT settings
        self.config = self._load_config()
        
        logger.info(f"[AI] MarketAnalystService v{self.ANALYSIS_VERSION} initialized")
    
    def _load_config(self) -> dict:
        """Load AI config from ai.yaml."""
        try:
            import yaml
            config_path = Path("config/ai.yaml")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"[AI] Failed to load config: {e}")
        return {}
    
    def is_gpt_available(self) -> bool:
        """Check if GPT is available for trading."""
        return self.gpt_available
    
    def analyze_market(self, symbol: str = "XAUUSD") -> Dict[str, Any]:
        """
        Perform full market analysis with GPT.
        
        Args:
            symbol: Trading symbol (default: XAUUSD)
        
        Returns:
            Dict with analysis results in structured format
        """
        # Проверка: если API key не настроен, работаем без AI
        if not self.client:
            logger.warning(f"[AI] ⚠️ Analysis skipped - API key not configured")
            logger.warning(f"[AI] 💡 Configure OPENAI_API_KEY in .env file to enable AI")
            return self._get_fallback_response("API key not configured")
        
        try:
            logger.info(f"[AI] Starting market analysis for {symbol}...")
            
            # 1. Capture chart screenshots
            screenshots = self._capture_charts(symbol)
            
            # 2. Calculate metrics
            metrics = self._calculate_metrics(symbol)
            
            # 3. Fetch news
            news = self._fetch_news(symbol)
            
            # 4. Build GPT prompt
            prompt = self._build_analysis_prompt(symbol, metrics, news)
            
            # 5. Call GPT API
            analysis = self._call_gpt_api(prompt, screenshots)
            
            # 6. Validate and add metadata (pass metrics for entry validation)
            validated = self._validate_analysis(analysis, metrics)
            
            # Log completion
            decision = validated.get('decision', {})
            action = decision.get('action', 'HOLD')
            confidence = decision.get('confidence', 0)
            logger.info(f"[AI] ✅ Analysis completed: {action} ({confidence}% confidence)")
            return validated
            
        except Exception as e:
            logger.error(f"[AI] Analysis failed: {e}")
            return self._get_fallback_response(str(e))
    
    def _capture_charts(self, symbol: str) -> Dict[str, str]:
        """Capture M5 and M15 chart screenshots (V5: two timeframes for better analysis)."""
        try:
            screenshots = {}
            
            # M5 chart - fast intraday trading
            m5_path = self.screenshot_service.capture_chart(
                symbol=symbol, 
                timeframe=mt5.TIMEFRAME_M5,
                bars=200  # 200 M5 bars = ~16 hours of data
            )
            if m5_path:
                with open(m5_path, 'rb') as f:
                    screenshots['M5'] = base64.b64encode(f.read()).decode('utf-8')
            
            # M15 chart - trend confirmation
            m15_path = self.screenshot_service.capture_chart(
                symbol=symbol,
                timeframe=mt5.TIMEFRAME_M15,
                bars=200  # 200 M15 bars = ~50 hours of data
            )
            if m15_path:
                with open(m15_path, 'rb') as f:
                    screenshots['M15'] = base64.b64encode(f.read()).decode('utf-8')
            
            logger.info(f"[AI] Captured {len(screenshots)}/2 screenshots (M5, M15) for analysis")
            return screenshots
            
        except Exception as e:
            logger.warning(f"[AI] Screenshot capture failed: {e}")
            return {}
    
    def _calculate_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate technical metrics for M5 analysis (V4 logic)."""
        try:
            # Get recent M5 data only
            rates_m5 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 200)
            
            if rates_m5 is None:
                return {}
            
            df_m5 = pd.DataFrame(rates_m5)
            
            # ATR calculation (на M5, 14 периодов)
            df_m5['high_low'] = df_m5['high'] - df_m5['low']
            atr = df_m5['high_low'].tail(14).mean()
            
            # Trend detection (EMA cross на M5)
            df_m5['ema_fast'] = df_m5['close'].ewm(span=12).mean()
            df_m5['ema_slow'] = df_m5['close'].ewm(span=26).mean()
            trend = "bullish" if df_m5['ema_fast'].iloc[-1] > df_m5['ema_slow'].iloc[-1] else "bearish"
            
            # Current price and structure
            current_price = df_m5['close'].iloc[-1]
            
            # Support/Resistance (последние 50 свечей M5 = ~4 часа)
            high_recent = df_m5['high'].tail(50).max()
            low_recent = df_m5['low'].tail(50).min()
            
            # Premium/Discount
            range_recent = high_recent - low_recent
            premium_discount = (current_price - low_recent) / range_recent if range_recent > 0 else 0.5
            
            # Volatility (M5 последние 50 свечей)
            volatility = df_m5['close'].pct_change().tail(50).std() * 100
            
            metrics = {
                "current_price": round(current_price, 2),
                "atr": round(atr, 2),
                "atr_pct": round((atr / current_price) * 100, 2),
                "trend": trend,
                "high_recent": round(high_recent, 2),
                "low_recent": round(low_recent, 2),
                "premium_discount": round(premium_discount, 3),
                "volatility_pct": round(volatility, 2),
                "ema_fast": round(df_m5['ema_fast'].iloc[-1], 2),
                "ema_slow": round(df_m5['ema_slow'].iloc[-1], 2)
            }
            
            return metrics
            
        except Exception as e:
            logger.warning(f"[AI] Metrics calculation failed: {e}")
            return {}
    
    def _fetch_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch HIGH-IMPACT economic news only (v2.0)."""
        try:
            # Use high-impact events only (HIGH, EXTREME)
            high_impact_events = self.news_fetcher.get_high_impact_events(hours_ahead=12)
            
            # Format for GPT (simplified)
            formatted = []
            for event in high_impact_events[:5]:  # Top 5 high-impact only
                formatted.append({
                    "title": event.title,
                    "impact": event.impact,
                    "time": event.time,
                    "currency": event.currency
                })
            
            logger.info(f"[AI] Found {len(formatted)} high-impact news events")
            return formatted
            
        except Exception as e:
            logger.warning(f"[AI] News fetch failed: {e}")
            return []
    
    def _build_analysis_prompt(self, symbol: str, metrics: Dict, news: List[Dict]) -> str:
        """Build simplified M5 prompt for V4 fast intraday analysis."""
        
        prompt = f"""You are an expert forex/gold scalper trading on M5 timeframe. Analyze ONLY the M5 chart and give a fast decision.

**SYMBOL:** {symbol}
**TIMESTAMP:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**M5 TECHNICAL DATA:**
- Current Price: ${metrics.get('current_price', 'N/A')}
- ATR: ${metrics.get('atr', 'N/A')} ({metrics.get('atr_pct', 'N/A')}%)
- Trend (EMA 12/26): {metrics.get('trend', 'N/A')}
- Recent Range: ${metrics.get('low_recent', 'N/A')} - ${metrics.get('high_recent', 'N/A')} (last 50 M5 candles = ~4 hours)
- Premium/Discount: {metrics.get('premium_discount', 'N/A')} (0=support, 1=resistance)
- Volatility: {metrics.get('volatility_pct', 'N/A')}%
- EMA Fast: ${metrics.get('ema_fast', 'N/A')}
- EMA Slow: ${metrics.get('ema_slow', 'N/A')}

**M5 CHART:**
You will receive ONE screenshot of M5 timeframe (last 200 candles = ~16 hours).

**HIGH-IMPACT NEWS:**
"""
        
        if news:
            for item in news:
                prompt += f"\n- [{item['impact'].upper()}] {item['title']} at {item['time']}"
        else:
            prompt += "\nNo significant news in next 12 hours"
        
        prompt += """

**YOUR TASK:**
Look at the LAST 20-30 M5 candles and decide: BUY, SELL, or HOLD.

**SMART TRADING - QUALITY OVER QUANTITY:**
- **You CAN say HOLD** if market is unclear, choppy, or no clear setup
- Only BUY/SELL when you see a CLEAR high-probability setup
- Better to skip 5 unclear situations than enter 1 bad trade
- **SL/TP are FIXED** by user config (you don't set them)
- **Confidence must be ≥75%** for BUY/SELL (otherwise HOLD)

**TAKE PROFIT LIMITS:**
- Maximum TP distance: **$20 for GOLD** (e.g. if entry $2650, TP max $2670 or $2630)
- Prefer smaller TPs ($10-$15) for safer exits
- Never exceed $20 TP distance regardless of confidence

**BUY signals when:**
- Bullish momentum visible (more green candles)
- Price near recent lows/support areas
- EMA trending up or crossing bullish
- Recent bounce pattern forming

**SELL signals when:**
- Bearish momentum visible (more red candles)
- Price near recent highs/resistance areas  
- EMA trending down or crossing bearish
- Recent rejection pattern forming

**When market is unclear:**
- Pick direction based on dominant EMA trend
- Or pick based on which side has more recent candles
- Or pick based on premium/discount (discount=BUY, premium=SELL)
- NEVER skip - always choose one direction

**RESPONSE FORMAT (JSON ONLY):**

{
  "timestamp": "2026-01-27T12:00:00",
  "symbol": "XAUUSD",
  "decision": {
    "action": "BUY|SELL",
    "confidence": 75,
    "reasoning": "Brief explanation (1-2 sentences max)"
  },
  "trade": {
    "entry": 2665.0,
    "stop_loss": 2660.0,
    "take_profit": 2675.0,
    "risk_reward": 2.0
  },
  "analysis": {
    "trend": "bullish|bearish",
    "key_level": "Support $2660 / Resistance $2670",
    "entry_quality": "optimal|good|fair"
  }
}

**CONFIDENCE RATING (60-100%):**
Rate your confidence in this trade setup:

- **90-100%**: PERFECT SETUP - Strong momentum (5+ candles), clear support/rejection, trend aligned, high volume
  Example: Price bounced from key support with 6 strong green candles, EMA crossed bullish, ATR expanding

- **80-89%**: VERY GOOD - Clear pattern (3-4 candles), momentum visible, trend confirmation
  Example: Price rejected resistance with 4 red candles, EMA trending down, clear lower highs

- **70-79%**: GOOD - Decent setup, 2-3 candles showing direction, some trend alignment
  Example: Recent 3 green candles after pullback, trend is upward but weak

- **60-69%**: ACCEPTABLE - Weak setup but has some merit, unclear momentum, mixed signals but one side slightly better
  Example: Market choppy but last 2 candles slightly bullish, EMA flat

- **Below 60%**: DON'T TRADE - Return NO_ACTION instead

**IMPORTANT**: Most trades should be 70-85%. Reserve 90+ for exceptional setups only. Be honest about setup quality!

**CRITICAL REQUIREMENTS:**
1. **MUST return either BUY or SELL** - no NONE allowed
2. Pick the direction with higher probability based on chart
3. **SL/TP will be calculated by system** - just provide entry price and direction
4. Entry must be close to current price (within $1)
5. Focus on LAST 20-30 candles for scalping setup
6. Return ONLY valid JSON, no extra text

**EXAMPLES OF GOOD M5 SETUPS:**
- Price touched recent low ($2660), bounced with 3+ strong green candles, forming higher low → BUY
- Price rejected recent high ($2670), dropped with 3+ strong red candles, forming lower high → SELL
- Last 5 candles show clear upward momentum, pullback to support → BUY
- Last 5 candles show clear downward momentum, rejection at resistance → SELL
- **SKIP WEAK SETUPS**: Single candle moves, overlapping candles, or choppy 10-candle range

**RISK MANAGEMENT PRIORITY:**
- **Preserve capital first**: Only take high-quality setups with clear directional bias
- **M5 SCALPING = MOMENTUM TRADING**: Need clear directional move, not guessing reversals
- **Better to miss a trade than take a bad one**
- Let trailing stop (40% activation) protect profits

Analyze the M5 chart NOW and give your decision!
"""

        return prompt
    
    def _call_gpt_api(self, prompt: str, screenshots: Dict[str, str]) -> Dict[str, Any]:
        """Call GPT-4 Vision API with prompt and images."""
        try:
            logger.info(f"[AI] 📤 Sending request to GPT-4o with {len(screenshots)} screenshots...")
            
            # Build messages with images
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert forex/gold trader. Always respond in valid JSON format."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            # Add screenshots if available
            for timeframe, b64_image in screenshots.items():
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64_image}",
                        "detail": "high"
                    }
                })
                logger.info(f"[AI] Added {timeframe} screenshot to request")
            
            # Warn if GPT was previously disabled (but still try to connect)
            if not self.gpt_available:
                logger.warning("[AI] ⚠️ GPT was previously disabled - attempting connection...")
            
            # Call API with retry logic
            logger.info("[AI] Calling OpenAI API...")
            
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(1, max_retries + 1):
                try:
                    # Load from config or use defaults
                    gpt_config = self.config.get('market_analyst', {}).get('gpt', {})
                    max_tokens = gpt_config.get('max_tokens', 4000)
                    temperature = gpt_config.get('temperature', 0.4)
                    model = gpt_config.get('model', 'gpt-4o')
                    
                    # Добавлен timeout для медленного интернета
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        timeout=60.0  # 60 секунд на ответ
                    )
                    
                    logger.info("[AI] ✅ Received response from OpenAI")
                    # Reset failure counter on success
                    self._on_gpt_success()
                    break  # Success - exit retry loop
                    
                except RateLimitError as e:
                    logger.error(f"[AI] ❌ RATE LIMIT ERROR (попытка {attempt}/{max_retries})")
                    logger.error(f"[AI] Детали: {e}")
                    logger.error("[AI] 💡 Проблема: превышен лимит запросов API. Проверь квоту на https://platform.openai.com/account/usage")
                    if attempt < max_retries:
                        wait_time = retry_delay * attempt * 2  # Exponential backoff
                        logger.warning(f"[AI] ⏳ Жду {wait_time} секунд перед повтором...")
                        time.sleep(wait_time)
                    else:
                        raise  # Last attempt failed
                
                except APIConnectionError as e:
                    logger.error(f"[AI] ❌ CONNECTION ERROR (попытка {attempt}/{max_retries})")
                    logger.error(f"[AI] Детали: {e}")
                    logger.error("[AI] 💡 Проблема: нет соединения с OpenAI. Проверь интернет или proxy")
                    if attempt < max_retries:
                        logger.warning(f"[AI] ⏳ Жду {retry_delay} секунд перед повтором...")
                        time.sleep(retry_delay)
                    else:
                        raise
                
                except Timeout as e:
                    logger.error(f"[AI] ❌ TIMEOUT ERROR (попытка {attempt}/{max_retries})")
                    logger.error(f"[AI] Детали: {e}")
                    logger.error("[AI] 💡 Проблема: запрос к API занял слишком много времени")
                    if attempt < max_retries:
                        logger.warning(f"[AI] ⏳ Жду {retry_delay} секунд перед повтором...")
                        time.sleep(retry_delay)
                    else:
                        raise
                
                except APIError as e:
                    logger.error(f"[AI] ❌ API ERROR (попытка {attempt}/{max_retries})")
                    logger.error(f"[AI] Код ошибки: {e.code if hasattr(e, 'code') else 'N/A'}")
                    logger.error(f"[AI] Детали: {e}")
                    
                    # Check if it's an invalid API key error
                    if "invalid" in str(e).lower() and "api" in str(e).lower() and "key" in str(e).lower():
                        logger.error("[AI] 💡 КРИТИЧЕСКАЯ ОШИБКА: неверный API ключ!")
                        logger.error("[AI] 🔧 Решение: проверь OPENAI_API_KEY в config/.env или Settings")
                        logger.error(f"[AI] Текущий ключ: {self.api_key[:15]}...{self.api_key[-4:]}")
                    
                    if attempt < max_retries and "server" in str(e).lower():
                        logger.warning(f"[AI] ⏳ Серверная ошибка - жду {retry_delay} секунд...")
                        time.sleep(retry_delay)
                    else:
                        raise
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Логируем полный ответ для отладки
            logger.debug("[AI] 📝 Полный ответ GPT:")
            logger.debug("-" * 80)
            logger.debug(content)
            logger.debug("-" * 80)
            
            # Extract JSON if wrapped in markdown
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            analysis = json.loads(content)
            logger.info("[AI] ✅ Successfully parsed GPT response")
            return analysis
            
        except RateLimitError as e:
            logger.error(f"[AI] ❌ ОКОНЧАТЕЛЬНАЯ ОШИБКА: Rate Limit")
            logger.error("[AI] 🚫 Все попытки исчерпаны - превышен лимит API")
            logger.error("[AI] 💡 Проверь квоту: https://platform.openai.com/account/usage")
            self._on_gpt_failure()
            raise
        
        except APIConnectionError as e:
            logger.error(f"[AI] ❌ ОКОНЧАТЕЛЬНАЯ ОШИБКА: Connection Failed")
            logger.error("[AI] 🚫 Не удалось подключиться к OpenAI API")
            logger.error("[AI] 💡 Проверь интернет, firewall, proxy настройки")
            self._on_gpt_failure()
            raise
        
        except APIError as e:
            logger.error(f"[AI] ❌ ОКОНЧАТЕЛЬНАЯ ОШИБКА: API Error")
            logger.error(f"[AI] Код: {e.code if hasattr(e, 'code') else 'N/A'}")
            logger.error(f"[AI] Детали: {e}")
            self._on_gpt_failure()
            raise
        
        except json.JSONDecodeError as e:
            logger.error(f"[AI] ❌ JSON PARSE ERROR: {e}")
            logger.error(f"[AI] Не удалось распарсить ответ GPT")
            logger.error(f"[AI] Ответ: {content[:500]}...")
            raise
        
        except Exception as e:
            logger.error(f"[AI] ❌ НЕИЗВЕСТНАЯ ОШИБКА: {type(e).__name__}")
            logger.error(f"[AI] Детали: {e}")
            self._on_gpt_failure()
            raise
    
    def _validate_analysis(self, analysis: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize GPT Decision Engine response (v2.0) + V4 entry price check."""
        try:
            # New format: decision instead of signals[]
            required_fields = ["timestamp", "symbol", "decision"]
            for field in required_fields:
                if field not in analysis:
                    logger.error(f"[AI] Missing required field: {field}")
                    analysis[field] = {}
            
            # Validate decision structure
            if "decision" in analysis:
                decision = analysis["decision"]
                required_decision_fields = ["action", "reasoning"]
                for field in required_decision_fields:
                    if field not in decision:
                        logger.warning(f"[AI] Decision missing field: {field}")
                        decision[field] = "BUY" if field == "action" else "No reasoning provided"
                
                # Validate action - only BUY or SELL allowed
                if decision.get("action") not in ["BUY", "SELL"]:
                    logger.warning(f"[AI] Invalid action: {decision.get('action')}, forcing to BUY")
                    decision["action"] = "BUY"
                
                # FIXED: Handle confidence conversion properly
                # GPT sometimes returns 1.0 (decimal 0-1) or "1.0" (string) which gets misinterpreted as 1%
                raw_confidence = decision.get("confidence", None)
                
                if raw_confidence is None:
                    logger.warning(f"[AI] ⚠️ GPT did NOT return confidence - using default 100%")
                    logger.warning(f"[AI] 💡 This means ALL signals pass confidence filter!")
                    raw_confidence = 100
                
                # Convert to float if string
                if isinstance(raw_confidence, str):
                    try:
                        raw_confidence = float(raw_confidence)
                    except (ValueError, TypeError):
                        logger.warning(f"[AI] Invalid confidence string: '{raw_confidence}' - using 100%")
                        raw_confidence = 100
                
                # Check if decimal format (0-1) and convert to percentage
                if isinstance(raw_confidence, (int, float)) and raw_confidence <= 1.0:
                    # Convert decimal (0-1) to percentage (0-100)
                    confidence_percentage = int(raw_confidence * 100)
                    logger.info(f"[AI] Converting decimal confidence {raw_confidence} → {confidence_percentage}%")
                    decision["confidence"] = confidence_percentage
                else:
                    # Already in percentage format (1-100), use as-is
                    decision["confidence"] = int(raw_confidence)
                    if raw_confidence == 100:
                        logger.debug(f"[AI] Using confidence: {decision['confidence']}%")
                    else:
                        logger.info(f"[AI] 📊 GPT confidence: {decision['confidence']}%")
                
                decision["block"] = "NONE"  # No blocks
            
            # Validate trade data if action is not NONE
            if analysis.get("decision", {}).get("action") in ["BUY", "SELL"]:
                if "trade" not in analysis:
                    logger.error("[AI] Missing trade data for BUY/SELL action")
                    analysis["decision"]["action"] = "NONE"
                else:
                    trade = analysis["trade"]
                    required_trade_fields = ["entry", "stop_loss", "take_profit", "risk_reward"]
                    for field in required_trade_fields:
                        if field not in trade:
                            logger.error(f"[AI] Trade missing field: {field}")
                            analysis["decision"]["action"] = "NONE"
                            break
                    
                    # V4 LOGIC: Apply FIXED SL/TP ($5/$10)
                    if analysis["decision"]["action"] in ["BUY", "SELL"]:
                        entry = float(trade.get("entry", 0))
                        action = analysis["decision"]["action"]
                        current_price = metrics.get("current_price", 0)
                        
                        # Log what GPT returned BEFORE we override
                        gpt_sl = trade.get("stop_loss", 0)
                        gpt_tp = trade.get("take_profit", 0)
                        logger.debug(f"[AI] 📥 GPT RAW VALUES: Entry={entry:.5f}, SL={gpt_sl:.5f}, TP={gpt_tp:.5f}")
                        
                        # V4 VALIDATION: Entry must be close to current price (within $2)
                        if current_price > 0:
                            entry_distance = abs(entry - current_price)
                            MAX_ENTRY_DISTANCE = 2.0  # $2 maximum
                            
                            if entry_distance > MAX_ENTRY_DISTANCE:
                                logger.warning(f"[AI] ❌ REJECTING signal: Entry too far from market!")
                                logger.warning(f"[AI]    Current Price: ${current_price:.2f}")
                                logger.warning(f"[AI]    Entry Price: ${entry:.2f}")
                                logger.warning(f"[AI]    Distance: ${entry_distance:.2f} > ${MAX_ENTRY_DISTANCE:.2f}")
                                analysis["decision"]["action"] = "NONE"
                                analysis["decision"]["reasoning"] = f"Entry ${entry:.2f} too far from market ${current_price:.2f}"
                                return analysis
                            
                            logger.info(f"[AI] ✅ Entry validation OK: ${entry:.2f} (distance: ${entry_distance:.2f})")
                        
                        # IMPROVED V5: DYNAMIC SL/TP with SESSION AWARENESS
                        # Detect instrument type (XAUUSD vs EURUSD)
                        symbol = analysis.get("symbol", "XAUUSD")
                        is_forex = symbol in ["EURUSD", "GBPUSD", "USDJPY", "EURJPY"]
                        
                        # Validate entry price
                        if entry <= 0:
                            logger.error(f"[AI] Invalid entry price: {entry}")
                            analysis["decision"]["action"] = "NONE"
                            return analysis
                        
                        # CRITICAL: Override ANY SL/TP from GPT with our fixed values
                        # GPT often returns unrealistic values like TP=1.21 when entry=1.18
                        # We MUST recalculate everything based on entry price
                        
                        # 🎮 CHECK MANUAL OVERRIDES FIRST
                        manual_overrides = self.config.get('manual_overrides', {})
                        manual_enabled = manual_overrides.get('enabled', False)
                        
                        if manual_enabled:
                            # USER CONTROLS SL/TP manually
                            symbol_lower = symbol.lower()
                            manual_settings = manual_overrides.get(symbol_lower, {})
                            
                            if is_forex:
                                # FOREX: pips → price
                                manual_sl_pips = manual_settings.get('sl_pips', 30)
                                manual_tp_pips = manual_settings.get('tp_pips', 50)
                                FIXED_SL_DISTANCE = manual_sl_pips * 0.0001  # pips to price
                                FIXED_TP_DISTANCE = manual_tp_pips * 0.0001
                                logger.info(f"[AI] 🎮 MANUAL MODE: SL={manual_sl_pips} pips, TP={manual_tp_pips} pips")
                            else:
                                # GOLD: dollars
                                manual_sl_dollars = manual_settings.get('sl_dollars', 4.5)
                                manual_tp_dollars = manual_settings.get('tp_dollars', 12.0)
                                FIXED_SL_DISTANCE = manual_sl_dollars
                                FIXED_TP_DISTANCE = manual_tp_dollars
                                logger.info(f"[AI] 🎮 MANUAL MODE: SL=${manual_sl_dollars:.1f}, TP=${manual_tp_dollars:.1f}")
                        else:
                            # AI ADAPTIVE MODE - calculate based on volatility
                            logger.debug(f"[AI] 🤖 AI ADAPTIVE MODE: SL/TP based on volatility & session")
                            
                            # Base distances adjusted by instrument AND volatility
                            if is_forex:
                                # FOREX (EURUSD): Use pips (0.0001 = 1 pip) - SAFE BROKER MINIMUMS
                                MIN_SL_DISTANCE = 0.0025   # 25 pips (broker minimum compliance)
                                MAX_SL_DISTANCE = 0.0050   # 50 pips
                                BASE_SL = 0.0030           # 30 pips base (standard safe value)
                                BASE_TP_DISTANCE = 0.0050  # 50 pips base (R:R ~1.67)
                            else:
                                # GOLD (XAUUSD): Use dollars
                                MIN_SL_DISTANCE = 3.0   # Minimum $3
                                MAX_SL_DISTANCE = 8.0   # Maximum $8
                                BASE_SL = 4.5           # Base SL $4.5
                                BASE_TP_DISTANCE = 12.0 # Base TP $12
                            
                            # Get ATR and session info
                            atr_value = analysis.get('analysis', {}).get('atr', 5.0 if not is_forex else 0.003)
                            current_hour = datetime.now().hour
                            
                            # Session-based adjustments
                            # Asian (0-8): Tight SL/TP (low volatility)
                            # European (8-16): Normal SL/TP  
                            # US (16-24): Wide SL/TP (high volatility)
                            if 0 <= current_hour < 8:  # Asian
                                session_sl_mult = 0.85
                                session_tp_mult = 0.9
                                session_name = "ASIAN"
                            elif 8 <= current_hour < 16:  # European
                                session_sl_mult = 1.0
                                session_tp_mult = 1.0
                                session_name = "EUROPEAN"
                            else:  # US
                                session_sl_mult = 1.15
                                session_tp_mult = 1.2
                                session_name = "US"
                            
                            # ATR-based adjustment (volatility adaptation)
                            if is_forex:
                                # FOREX volatility thresholds (in pips)
                                if atr_value < 0.0020:
                                    # Low volatility - tight SL (but respecting broker minimums)
                                    FIXED_SL_DISTANCE = 0.0025  # 25 pips (matches MIN_SL_DISTANCE)
                                    FIXED_TP_DISTANCE = 0.0045  # 45 pips
                                    volatility_state = "LOW"
                                elif atr_value > 0.0045:
                                    # High volatility - wider SL
                                    FIXED_SL_DISTANCE = min(MAX_SL_DISTANCE, BASE_SL + (atr_value - 0.0045) * 2.0)
                                    FIXED_TP_DISTANCE = BASE_TP_DISTANCE * 1.3
                                    volatility_state = "HIGH"
                                    logger.info(f"[AI] ⚠️ High volatility (ATR {atr_value:.5f}) - wider SL {FIXED_SL_DISTANCE:.5f}")
                                else:
                                    # Normal volatility
                                    FIXED_SL_DISTANCE = BASE_SL
                                    FIXED_TP_DISTANCE = BASE_TP_DISTANCE
                                    volatility_state = "NORMAL"
                            else:
                                # GOLD (XAUUSD) volatility thresholds (in dollars)
                                if atr_value < 3.0:
                                    # Low volatility - tight SL
                                    FIXED_SL_DISTANCE = 3.5
                                    FIXED_TP_DISTANCE = 9.0
                                    volatility_state = "LOW"
                                elif atr_value > 7.0:
                                    # High volatility - wider SL to avoid stop hunting
                                    FIXED_SL_DISTANCE = min(MAX_SL_DISTANCE, BASE_SL + (atr_value - 7.0) * 0.35)
                                    FIXED_TP_DISTANCE = BASE_TP_DISTANCE * 1.3
                                    volatility_state = "HIGH"
                                    logger.info(f"[AI] ⚠️ High volatility (ATR ${atr_value:.2f}) - wider SL ${FIXED_SL_DISTANCE:.2f}")
                                else:
                                    # Normal volatility
                                    FIXED_SL_DISTANCE = BASE_SL
                                    FIXED_TP_DISTANCE = BASE_TP_DISTANCE
                                    volatility_state = "NORMAL"
                            
                            # Apply session multipliers
                            FIXED_SL_DISTANCE *= session_sl_mult
                            FIXED_TP_DISTANCE *= session_tp_mult
                        
                        # Calculate fixed SL/TP based on direction (works for both manual and AI modes)
                        if action == "BUY":
                            new_sl = entry - FIXED_SL_DISTANCE
                            new_tp = entry + FIXED_TP_DISTANCE
                        else:  # SELL
                            new_sl = entry + FIXED_SL_DISTANCE
                            new_tp = entry - FIXED_TP_DISTANCE
                        
                        # LIMIT TP: Max $20 for GOLD (safety limit)
                        if not is_forex:  # GOLD
                            tp_distance = abs(new_tp - entry)
                            MAX_TP_DOLLARS = 20.0
                            if tp_distance > MAX_TP_DOLLARS:
                                logger.warning(f"[AI] ⚠️ TP too large (${tp_distance:.1f}) - limiting to ${MAX_TP_DOLLARS}")
                                if action == "BUY":
                                    new_tp = entry + MAX_TP_DOLLARS
                                else:
                                    new_tp = entry - MAX_TP_DOLLARS
                                FIXED_TP_DISTANCE = MAX_TP_DOLLARS
                        
                        # CRITICAL VALIDATION: Ensure SL/TP are in correct direction
                        if action == "BUY":
                            if new_sl >= entry:
                                logger.error(f"[AI] ❌ INVALID SL for BUY: SL {new_sl:.5f} >= Entry {entry:.5f}")
                                analysis["decision"]["action"] = "NONE"
                                return analysis
                            if new_tp <= entry:
                                logger.error(f"[AI] ❌ INVALID TP for BUY: TP {new_tp:.5f} <= Entry {entry:.5f}")
                                analysis["decision"]["action"] = "NONE"
                                return analysis
                        else:  # SELL
                            if new_sl <= entry:
                                logger.error(f"[AI] ❌ INVALID SL for SELL: SL {new_sl:.5f} <= Entry {entry:.5f}")
                                analysis["decision"]["action"] = "NONE"
                                return analysis
                            if new_tp >= entry:
                                logger.error(f"[AI] ❌ INVALID TP for SELL: TP {new_tp:.5f} >= Entry {entry:.5f}")
                                analysis["decision"]["action"] = "NONE"
                                return analysis
                        
                        # Override GPT values with calculated ones
                        # Round to appropriate precision (2 decimals for gold, 5 for forex)
                        precision = 5 if is_forex else 2
                        analysis["trade"]["stop_loss"] = round(new_sl, precision)
                        analysis["trade"]["take_profit"] = round(new_tp, precision)
                        
                        # Calculate actual R:R
                        actual_sl_distance = abs(entry - new_sl)
                        actual_tp_distance = abs(entry - new_tp)
                        actual_rr = actual_tp_distance / actual_sl_distance if actual_sl_distance > 0 else 2.0
                        analysis["trade"]["risk_reward"] = round(actual_rr, 2)
                        
                        # Logging: different for manual vs AI mode
                        if manual_enabled:
                            # MANUAL MODE: Simple logging
                            if is_forex:
                                sl_pips = FIXED_SL_DISTANCE * 10000
                                tp_pips = FIXED_TP_DISTANCE * 10000
                                logger.info(f"[AI] ✅ MANUAL SL/TP Applied:")
                                logger.info(f"[AI]    Symbol: {symbol} (FOREX)")
                                logger.info(f"[AI]    Entry: {entry:.5f}")
                                logger.info(f"[AI]    SL: {new_sl:.5f} ({sl_pips:.1f} pips)")
                                logger.info(f"[AI]    TP: {new_tp:.5f} ({tp_pips:.1f} pips)")
                                logger.info(f"[AI]    R:R: {actual_rr:.2f}:1")
                            else:
                                logger.info(f"[AI] ✅ MANUAL SL/TP Applied:")
                                logger.info(f"[AI]    Symbol: {symbol} (GOLD)")
                                logger.info(f"[AI]    Entry: ${entry:.2f}")
                                logger.info(f"[AI]    SL: ${new_sl:.2f} (${FIXED_SL_DISTANCE:.1f})")
                                logger.info(f"[AI]    TP: ${new_tp:.2f} (${FIXED_TP_DISTANCE:.1f})")
                                logger.info(f"[AI]    R:R: {actual_rr:.2f}:1")
                        else:
                            # AI ADAPTIVE MODE: Detailed logging with session/volatility info
                            # Warning if GPT values were very different from ours
                            gpt_sl_diff = abs(gpt_sl - new_sl) if gpt_sl > 0 else 0
                            gpt_tp_diff = abs(gpt_tp - new_tp) if gpt_tp > 0 else 0
                            
                            if is_forex:
                                # Check if difference > 20 pips
                                if gpt_sl_diff > 0.0020 or gpt_tp_diff > 0.0020:
                                    logger.warning(f"[AI] ⚠️ GPT values significantly different from calculated:")
                                    logger.warning(f"[AI]    SL: GPT {gpt_sl:.5f} vs Calculated {new_sl:.5f} (diff: {gpt_sl_diff*10000:.1f} pips)")
                                    logger.warning(f"[AI]    TP: GPT {gpt_tp:.5f} vs Calculated {new_tp:.5f} (diff: {gpt_tp_diff*10000:.1f} pips)")
                            else:
                                # Check if difference > $2
                                if gpt_sl_diff > 2.0 or gpt_tp_diff > 2.0:
                                    logger.warning(f"[AI] ⚠️ GPT values significantly different from calculated:")
                                    logger.warning(f"[AI]    SL: GPT ${gpt_sl:.2f} vs Calculated ${new_sl:.2f} (diff: ${gpt_sl_diff:.2f})")
                                    logger.warning(f"[AI]    TP: GPT ${gpt_tp:.2f} vs Calculated ${new_tp:.2f} (diff: ${gpt_tp_diff:.2f})")
                            
                            # Format log messages based on instrument type
                            if is_forex:
                                # FOREX: Show in pips (multiply by 10000)
                                sl_pips = FIXED_SL_DISTANCE * 10000
                                tp_pips = FIXED_TP_DISTANCE * 10000
                                logger.info(f"[AI] ✅ V5 ADAPTIVE SL/TP Applied:")
                                logger.info(f"[AI]    Symbol: {symbol} (FOREX)")
                                logger.info(f"[AI]    Session: {session_name} (SL×{session_sl_mult:.2f}, TP×{session_tp_mult:.2f})")
                                logger.info(f"[AI]    Volatility: {volatility_state} (ATR {atr_value:.5f})")
                                logger.info(f"[AI]    Entry: {entry:.5f}")
                                logger.info(f"[AI]    SL: {new_sl:.5f} ({sl_pips:.1f} pips)")
                                logger.info(f"[AI]    TP: {new_tp:.5f} ({tp_pips:.1f} pips)")
                                logger.info(f"[AI]    R:R: {actual_rr:.2f}:1")
                            else:
                                # GOLD: Show in dollars
                                logger.info(f"[AI] ✅ V5 ADAPTIVE SL/TP Applied:")
                                logger.info(f"[AI]    Symbol: {symbol} (GOLD)")
                                logger.info(f"[AI]    Session: {session_name} (SL×{session_sl_mult:.2f}, TP×{session_tp_mult:.2f})")
                                logger.info(f"[AI]    Volatility: {volatility_state} (ATR ${atr_value:.2f})")
                                logger.info(f"[AI]    Entry: ${entry:.2f}")
                                logger.info(f"[AI]    SL: ${new_sl:.2f} (${FIXED_SL_DISTANCE:.1f})")
                                logger.info(f"[AI]    TP: ${new_tp:.2f} (${FIXED_TP_DISTANCE:.1f})")
                                logger.info(f"[AI]    R:R: {actual_rr:.2f}:1")
            
            # Add metadata
            analysis["analyzed_at"] = datetime.now().isoformat()
            analysis["analysis_version"] = "4.0"  # V4: M5 + Fixed SL/TP
            analysis["prompt_version"] = "2026-01-V4"
            
            logger.info(f"[AI] ✅ V4 Validated decision: {analysis.get('decision', {}).get('action')} "
                       f"(always trade - no filters)")
            
            return analysis
            
        except Exception as e:
            logger.error(f"[AI] Validation failed: {e}")
            return analysis
    
    # Saving removed - SignalManager handles persistence
    
    def _get_fallback_response(self, error: str) -> Dict[str, Any]:
        """Return fallback response on error (v2.0 format)."""
        return {
            "timestamp": datetime.now().isoformat(),
            "symbol": "XAUUSD",
            "error": error,
            "decision": {
                "action": "NONE",
                "confidence": 0,
                "block": "HARD"
            },
            "analyzed_at": datetime.now().isoformat(),
            "analysis_version": "2.0"
        }
    
    def _on_gpt_success(self):
        """Reset failure counter on successful GPT call."""
        with self._recovery_lock:
            if self.gpt_failed_attempts > 0:
                logger.info(f"[AI-Recovery] ✅ GPT connection restored (was {self.gpt_failed_attempts} failures)")
            self.gpt_failed_attempts = 0
            if not self.gpt_available:
                logger.info("[AI-Recovery] ✅ Trading RE-ENABLED after recovery")
                self.gpt_available = True
    
    def _on_gpt_failure(self):
        """
        Handle GPT connection failure.
        After 3 failures: disable trading, start 30-min recovery loop.
        """
        with self._recovery_lock:
            self.gpt_failed_attempts += 1
            logger.warning(f"[AI-Recovery] ⚠️ GPT failure #{self.gpt_failed_attempts}/3")
            
            if self.gpt_failed_attempts >= 3:
                logger.error("[AI-Recovery] 🚫 3 FAILURES REACHED - DISABLING TRADING")
                self.gpt_available = False
                self.gpt_last_failure_time = time.time()
                
                # Start recovery thread if not already running
                if self.gpt_recovery_thread is None or not self.gpt_recovery_thread.is_alive():
                    logger.info("[AI-Recovery] 🔄 Starting 30-min recovery loop...")
                    self.gpt_recovery_thread = threading.Thread(
                        target=self._recovery_loop,
                        daemon=True,
                        name="GPT-Recovery"
                    )
                    self.gpt_recovery_thread.start()
    
    def _recovery_loop(self):
        """
        Recovery loop: Try to reconnect every 30 minutes.
        Runs in background until connection restored.
        """
        logger.info("[AI-Recovery] 🔄 Recovery thread started")
        
        while True:
            # Wait 30 minutes
            logger.info("[AI-Recovery] ⏳ Waiting 30 minutes before next recovery attempt...")
            time.sleep(30 * 60)  # 30 minutes
            
            # Check if GPT is still disabled
            with self._recovery_lock:
                if self.gpt_available:
                    logger.info("[AI-Recovery] ✅ GPT already recovered - stopping recovery thread")
                    break
            
            # Try to reconnect
            logger.info("[AI-Recovery] 🔄 Attempting GPT connection recovery...")
            try:
                # Simple test request
                test_response = self.client.models.list()
                logger.info("[AI-Recovery] ✅ Connection test SUCCESSFUL")
                
                with self._recovery_lock:
                    self.gpt_available = True
                    self.gpt_failed_attempts = 0
                    logger.info("[AI-Recovery] ✅ Trading RE-ENABLED")
                break  # Exit loop on success
                
            except Exception as e:
                logger.error(f"[AI-Recovery] ❌ Recovery attempt failed: {type(e).__name__}")
                logger.error(f"[AI-Recovery] Details: {e}")
                logger.info("[AI-Recovery] Will retry in 30 minutes...")
                # Continue loop
        
        logger.info("[AI-Recovery] 🏁 Recovery thread finished")
    
    def get_latest_analysis(self) -> Optional[Dict[str, Any]]:
        """Get the latest saved analysis."""
        try:
            latest_path = self.analysis_dir / "latest.json"
            if latest_path.exists():
                with open(latest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"[AI] Failed to load latest analysis: {e}")
            return None


# Convenience function for quick analysis
def run_analysis(symbol: str = "XAUUSD") -> Dict[str, Any]:
    """Quick function to run market analysis."""
    analyst = MarketAnalystService()
    return analyst.analyze_market(symbol)


if __name__ == "__main__":
    # Test run
    print("Running market analysis...")
    result = run_analysis()
    print(json.dumps(result, indent=2))
