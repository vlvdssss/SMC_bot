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
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        # Детальная проверка API ключа
        if not self.api_key:
            logger.error("[AI] ❌ OpenAI API key not found!")
            logger.error("[AI] 💡 Решение:")
            logger.error("[AI]    1. Создай файл config/.env")
            logger.error("[AI]    2. Добавь строку: OPENAI_API_KEY=sk-proj-...")
            logger.error("[AI]    3. Или передай api_key в конструктор")
            raise ValueError("OpenAI API key not found. Please configure API key in Settings.")
        
        # Проверка формата ключа
        if not self.api_key.startswith('sk-'):
            logger.error(f"[AI] ❌ INVALID API KEY FORMAT!")
            logger.error(f"[AI] Текущий ключ: {self.api_key[:30]}...")
            logger.error(f"[AI] 💡 OpenAI ключи начинаются с 'sk-' или 'sk-proj-'")
            logger.error(f"[AI] 🔧 Проверь правильность ключа в config/.env или Settings")
            raise ValueError(f"Invalid OpenAI API key format. Key should start with 'sk-'")
        
        logger.info(f"[AI] ✅ API Key validated: {self.api_key[:15]}...{self.api_key[-4:]}")
        
        try:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("[AI] ✅ OpenAI client initialized successfully")
            
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
        
        logger.info(f"[AI] MarketAnalystService v{self.ANALYSIS_VERSION} initialized")
    
    def analyze_market(self, symbol: str = "XAUUSD") -> Dict[str, Any]:
        """
        Perform full market analysis with GPT.
        
        Args:
            symbol: Trading symbol (default: XAUUSD)
        
        Returns:
            Dict with analysis results in structured format
        """
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
            
            # Log completion with correct field
            decision = validated.get('decision', {})
            action = decision.get('action', 'NONE')
            confidence = decision.get('confidence', 0)
            logger.info(f"[AI] Analysis completed: {action} (confidence: {confidence}%)")
            return validated
            
        except Exception as e:
            logger.error(f"[AI] Analysis failed: {e}")
            return self._get_fallback_response(str(e))
    
    def _capture_charts(self, symbol: str) -> Dict[str, str]:
        """Capture M5 chart screenshot (V4: single timeframe for fast intraday analysis)."""
        try:
            screenshots = {}
            
            # M5 chart - fast intraday trading (V4 logic)
            m5_path = self.screenshot_service.capture_chart(
                symbol=symbol, 
                timeframe=mt5.TIMEFRAME_M5,
                bars=200  # 200 M5 bars = ~16 hours of data
            )
            if m5_path:
                with open(m5_path, 'rb') as f:
                    screenshots['M5'] = base64.b64encode(f.read()).decode('utf-8')
            
            logger.info(f"[AI] Captured M5 screenshot for V4 analysis ({len(screenshots)}/1)")
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
Look at the LAST 20-30 M5 candles. Find quick scalping setups based on:
- Recent support/resistance bounces
- 2-3 candle reversal patterns
- EMA crossovers
- Quick momentum shifts

**TRADING RULES (V4 LOGIC):**
- **FIXED SL**: $5 from entry (DO NOT CALCULATE, ALWAYS $5)
- **FIXED TP**: $10 from entry (DO NOT CALCULATE, ALWAYS $10)
- **BUY ONLY if**: price bounced from support and moving up 2-3 candles OR bullish momentum
- **SELL ONLY if**: price rejected resistance and moving down 2-3 candles OR bearish momentum
- **WAIT if**: no clear setup, consolidation, or low confidence

**RESPONSE FORMAT (JSON ONLY):**

{
  "timestamp": "2026-01-27T12:00:00",
  "symbol": "XAUUSD",
  "decision": {
    "action": "BUY|SELL|NONE",
    "confidence": 75,
    "block": "NONE",
    "reasoning": "Brief explanation (1-2 sentences max)"
  },
  "trade": {
    "entry": 2665.0,
    "stop_loss": 2660.0,
    "take_profit": 2675.0,
    "risk_reward": 2.0
  },
  "analysis": {
    "trend": "bullish|bearish|neutral",
    "key_level": "Support $2660 / Resistance $2670",
    "entry_quality": "optimal|good|fair"
  }
}

**CRITICAL (V4 REQUIREMENTS):**
1. **SL/TP are FIXED** - system will calculate automatically as entry ± $5/$10
2. Entry must be close to current price (within $1)
3. If confidence <70% → action = NONE (V4: higher threshold for M5)
4. Focus on LAST 20-30 candles only (not full chart history)
5. Look for quick reversals and momentum - this is scalping!
6. Return ONLY valid JSON, no extra text

**EXAMPLES OF GOOD M5 SETUPS:**
- Price touched recent low ($2660), bounced with 2 green candles → BUY
- Price rejected recent high ($2670), dropped with 2 red candles → SELL
- EMA fast crossed above slow with momentum → BUY
- Clear consolidation or choppy → NONE/WAIT

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
            
            # Call API with retry logic
            logger.info("[AI] Calling OpenAI API...")
            
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(1, max_retries + 1):
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o",  # or "gpt-4-vision-preview"
                        messages=messages,
                        max_tokens=2000,
                        temperature=0.3  # Lower temperature for more consistent analysis
                    )
                    
                    logger.info("[AI] ✅ Received response from OpenAI")
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
            raise
        
        except APIConnectionError as e:
            logger.error(f"[AI] ❌ ОКОНЧАТЕЛЬНАЯ ОШИБКА: Connection Failed")
            logger.error("[AI] 🚫 Не удалось подключиться к OpenAI API")
            logger.error("[AI] 💡 Проверь интернет, firewall, proxy настройки")
            raise
        
        except APIError as e:
            logger.error(f"[AI] ❌ ОКОНЧАТЕЛЬНАЯ ОШИБКА: API Error")
            logger.error(f"[AI] Код: {e.code if hasattr(e, 'code') else 'N/A'}")
            logger.error(f"[AI] Детали: {e}")
            raise
        
        except json.JSONDecodeError as e:
            logger.error(f"[AI] ❌ JSON PARSE ERROR: {e}")
            logger.error(f"[AI] Не удалось распарсить ответ GPT")
            logger.error(f"[AI] Ответ: {content[:500]}...")
            raise
        
        except Exception as e:
            logger.error(f"[AI] ❌ НЕИЗВЕСТНАЯ ОШИБКА: {type(e).__name__}")
            logger.error(f"[AI] Детали: {e}")
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
                required_decision_fields = ["action", "confidence", "block"]
                for field in required_decision_fields:
                    if field not in decision:
                        logger.warning(f"[AI] Decision missing field: {field}")
                        decision[field] = "NONE" if field in ["action", "block"] else 0
                
                # Validate action
                if decision.get("action") not in ["BUY", "SELL", "NONE"]:
                    logger.warning(f"[AI] Invalid action: {decision.get('action')}, defaulting to NONE")
                    decision["action"] = "NONE"
                
                # Validate block
                if decision.get("block") not in ["NONE", "SOFT", "HARD"]:
                    logger.warning(f"[AI] Invalid block: {decision.get('block')}, defaulting to NONE")
                    decision["block"] = "NONE"
                
                # Validate confidence
                try:
                    conf = float(decision.get("confidence", 0))
                    decision["confidence"] = max(0, min(100, conf))
                except:
                    decision["confidence"] = 0
                    logger.warning("[AI] Invalid confidence value, set to 0")
            
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
                        
                        # FIXED PARAMETERS (V4)
                        FIXED_SL_DISTANCE = 5.0   # $5
                        FIXED_TP_DISTANCE = 10.0  # $10
                        
                        # Calculate fixed SL/TP based on direction
                        if action == "BUY":
                            new_sl = entry - FIXED_SL_DISTANCE
                            new_tp = entry + FIXED_TP_DISTANCE
                        else:  # SELL
                            new_sl = entry + FIXED_SL_DISTANCE
                            new_tp = entry - FIXED_TP_DISTANCE
                        
                        # Override GPT values with fixed ones
                        analysis["trade"]["stop_loss"] = round(new_sl, 2)
                        analysis["trade"]["take_profit"] = round(new_tp, 2)
                        analysis["trade"]["risk_reward"] = 2.0  # Always 2:1 (10/5)
                        
                        logger.info(f"[AI] ✅ V4 FIXED SL/TP Applied:")
                        logger.info(f"[AI]    Entry: ${entry:.2f}")
                        logger.info(f"[AI]    SL: ${new_sl:.2f} (fixed $5)")
                        logger.info(f"[AI]    TP: ${new_tp:.2f} (fixed $10)")
                        logger.info(f"[AI]    R:R: 2:1")
            
            # Add metadata
            analysis["analyzed_at"] = datetime.now().isoformat()
            analysis["analysis_version"] = "4.0"  # V4: M5 + Fixed SL/TP
            analysis["prompt_version"] = "2026-01-V4"
            
            logger.info(f"[AI] ✅ V4 Validated decision: {analysis.get('decision', {}).get('action')} "
                       f"(confidence: {analysis.get('decision', {}).get('confidence')}%, "
                       f"block: {analysis.get('decision', {}).get('block')})")
            
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
