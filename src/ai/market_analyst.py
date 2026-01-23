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
            
            # 6. Validate and add metadata
            validated = self._validate_analysis(analysis)
            
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
        """Capture M5, M15, M30, and H1 chart screenshots (4 timeframes)."""
        try:
            screenshots = {}
            
            # M5 chart
            m5_path = self.screenshot_service.capture_chart(
                symbol=symbol, 
                timeframe=mt5.TIMEFRAME_M5,
                bars=100
            )
            if m5_path:
                with open(m5_path, 'rb') as f:
                    screenshots['M5'] = base64.b64encode(f.read()).decode('utf-8')
            
            # M15 chart
            m15_path = self.screenshot_service.capture_chart(
                symbol=symbol, 
                timeframe=mt5.TIMEFRAME_M15,
                bars=100
            )
            if m15_path:
                with open(m15_path, 'rb') as f:
                    screenshots['M15'] = base64.b64encode(f.read()).decode('utf-8')
            
            # M30 chart
            m30_path = self.screenshot_service.capture_chart(
                symbol=symbol, 
                timeframe=mt5.TIMEFRAME_M30,
                bars=100
            )
            if m30_path:
                with open(m30_path, 'rb') as f:
                    screenshots['M30'] = base64.b64encode(f.read()).decode('utf-8')
            
            # H1 chart
            h1_path = self.screenshot_service.capture_chart(
                symbol=symbol,
                timeframe=mt5.TIMEFRAME_H1,
                bars=100
            )
            if h1_path:
                with open(h1_path, 'rb') as f:
                    screenshots['H1'] = base64.b64encode(f.read()).decode('utf-8')
            
            logger.info(f"[AI] ✅ Captured {len(screenshots)}/4 timeframe screenshots")
            return screenshots
            
        except Exception as e:
            logger.warning(f"[AI] Screenshot capture failed: {e}")
            return {}
    
    def _calculate_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate technical metrics for analysis."""
        try:
            # Get recent data
            rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 200)
            rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 200)
            
            if rates_m15 is None or rates_h1 is None:
                return {}
            
            df_m15 = pd.DataFrame(rates_m15)
            df_h1 = pd.DataFrame(rates_h1)
            
            # ATR calculation
            df_h1['high_low'] = df_h1['high'] - df_h1['low']
            atr = df_h1['high_low'].tail(14).mean()
            
            # Trend detection (EMA cross)
            df_h1['ema_fast'] = df_h1['close'].ewm(span=12).mean()
            df_h1['ema_slow'] = df_h1['close'].ewm(span=26).mean()
            trend = "bullish" if df_h1['ema_fast'].iloc[-1] > df_h1['ema_slow'].iloc[-1] else "bearish"
            
            # Current price and structure
            current_price = df_m15['close'].iloc[-1]
            high_24h = df_h1['high'].tail(24).max()
            low_24h = df_h1['low'].tail(24).min()
            
            # Premium/Discount (from strategy logic)
            range_24h = high_24h - low_24h
            premium_discount = (current_price - low_24h) / range_24h if range_24h > 0 else 0.5
            
            # Volatility
            volatility = df_h1['close'].pct_change().tail(24).std() * 100
            
            metrics = {
                "current_price": round(current_price, 2),
                "atr": round(atr, 2),
                "atr_pct": round((atr / current_price) * 100, 2),
                "trend": trend,
                "high_24h": round(high_24h, 2),
                "low_24h": round(low_24h, 2),
                "premium_discount": round(premium_discount, 3),
                "volatility_pct": round(volatility, 2),
                "ema_fast": round(df_h1['ema_fast'].iloc[-1], 2),
                "ema_slow": round(df_h1['ema_slow'].iloc[-1], 2)
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
        """Build SIMPLE and PROVEN prompt for GPT (back to basics with fixed SL)."""
        
        # Calculate fixed stop-loss distance
        current_price = metrics.get('current_price', 0)
        fixed_stop_distance_pips = 100  # 100 pips = $10 risk for 0.01 lot on XAUUSD
        fixed_stop_distance = fixed_stop_distance_pips * 0.01
        
        prompt = f"""You are an expert trading analyst. Analyze the market and provide ONE clear trading decision.

**MARKET DATA:**
Symbol: {symbol}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Current Price: ${current_price}

Technical Indicators:
- ATR: ${metrics.get('atr', 0)} ({metrics.get('atr_pct', 0)}%)
- Trend: {metrics.get('trend', 'neutral')}
- EMA Fast (12): ${metrics.get('ema_fast', 0)}
- EMA Slow (26): ${metrics.get('ema_slow', 0)}
- 24H High: ${metrics.get('high_24h', 0)}
- 24H Low: ${metrics.get('low_24h', 0)}
- Premium/Discount: {metrics.get('premium_discount', 0.5):.1%}
- Volatility: {metrics.get('volatility_pct', 0):.2f}%

**CHART SCREENSHOTS:**
You will receive 4 timeframe charts:
- M5 (5-minute): for entry timing
- M15 (15-minute): for structure
- M30 (30-minute): for context
- H1 (1-hour): for trend

**HIGH-IMPACT NEWS:**
"""
        
        if news:
            for item in news:
                prompt += f"\n- [{item['impact']}] {item['title']} at {item['time']}"
        else:
            prompt += "\nNo high-impact news in next 12 hours"
        
        prompt += f"""

**YOUR TASK:**
1. Look at ALL 4 charts carefully
2. Identify trend direction (bullish/bearish/neutral)
3. Find key support/resistance levels
4. Check if NOW is good time to enter
5. Make ONE decision: BUY, SELL, or NONE

**DECISION RULES:**
- Entry must be within 5-20 pips of current price
- If no clear setup → action = NONE
- If confidence <60% → action = NONE
- STOP-LOSS: Always FIXED at {fixed_stop_distance_pips} pips (${fixed_stop_distance:.2f})
- TAKE-PROFIT: Minimum 1.5:1 R:R (150 pips), optimal 2:1 or better
- Place TP at next major support/resistance level

**CONFIDENCE LEVELS:**
- 80-100%: Very strong setup (all confirmations)
- 70-79%: Good setup (most confirmations)
- 60-69%: Acceptable setup (key confirmations present)
- Below 60%: WAIT - not clear enough

**RESPONSE FORMAT (JSON ONLY):**

{{
  "timestamp": "{datetime.now().isoformat()}",
  "symbol": "{symbol}",
  "decision": {{
    "action": "BUY|SELL|NONE",
    "confidence": 75,
    "block": "NONE|SOFT|HARD",
    "reasoning": "Brief 1-2 sentence explanation"
  }},
  "trade": {{
    "entry": {current_price},
    "stop_loss": {current_price - fixed_stop_distance},
    "take_profit": {current_price + (fixed_stop_distance * 1.5)},
    "risk_reward": 1.5
  }},
  "analysis": {{
    "trend": "bullish|bearish|neutral",
    "key_level": "Support $X / Resistance $Y",
    "entry_quality": "optimal|good|fair"
  }}
}}

**IMPORTANT:**
- If action=NONE → omit "trade" object
- Stop-Loss MUST be exactly {fixed_stop_distance_pips} pips
- Take-Profit minimum 150 pips (ideally 200+ pips)
- Include brief reasoning (max 2 sentences)
- Return ONLY valid JSON, no extra text

Now analyze the charts and provide your decision!
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
    
    def _validate_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize GPT Decision Engine response (v2.0)."""
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
            
            # Add metadata
            analysis["analyzed_at"] = datetime.now().isoformat()
            analysis["analysis_version"] = "2.0"  # Updated version
            analysis["prompt_version"] = self.PROMPT_VERSION
            
            logger.info(f"[AI] ✅ Validated decision: {analysis.get('decision', {}).get('action')} "
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
