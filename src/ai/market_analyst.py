#!/usr/bin/env python3
"""
AI Market Analyst Service - GPT-powered market analysis

Provides deep market analysis using ChatGPT with chart screenshots and metrics.
Returns structured JSON with trading signals, blocks, and confidence levels.
"""

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import MetaTrader5 as mt5
import pandas as pd
from openai import OpenAI

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
        if not self.api_key:
            raise ValueError("OpenAI API key not found")
        
        self.client = OpenAI(api_key=self.api_key)
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
            
            logger.info(f"[AI] Analysis completed: {validated.get('summary', {}).get('sentiment')}")
            return validated
            
        except Exception as e:
            logger.error(f"[AI] Analysis failed: {e}")
            return self._get_fallback_response(str(e))
    
    def _capture_charts(self, symbol: str) -> Dict[str, str]:
        """Capture M15 and H1 chart screenshots."""
        try:
            screenshots = {}
            
            # M15 chart
            m15_path = self.screenshot_service.capture_chart(
                symbol=symbol, 
                timeframe=mt5.TIMEFRAME_M15,
                bars=100
            )
            if m15_path:
                with open(m15_path, 'rb') as f:
                    screenshots['M15'] = base64.b64encode(f.read()).decode('utf-8')
            
            # H1 chart
            h1_path = self.screenshot_service.capture_chart(
                symbol=symbol,
                timeframe=mt5.TIMEFRAME_H1,
                bars=100
            )
            if h1_path:
                with open(h1_path, 'rb') as f:
                    screenshots['H1'] = base64.b64encode(f.read()).decode('utf-8')
            
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
        """Fetch relevant economic news."""
        try:
            # Use existing news fetcher
            news_items = self.news_fetcher.get_relevant_news(symbol, hours=24)
            
            # Format for GPT
            formatted = []
            for item in news_items[:5]:  # Top 5 news
                formatted.append({
                    "title": item.get('title', ''),
                    "impact": item.get('impact', 'medium'),
                    "time": item.get('time', ''),
                    "summary": item.get('summary', '')
                })
            
            return formatted
            
        except Exception as e:
            logger.warning(f"[AI] News fetch failed: {e}")
            return []
    
    def _build_analysis_prompt(self, symbol: str, metrics: Dict, news: List[Dict]) -> str:
        """Build comprehensive prompt for GPT analysis."""
        
        prompt = f"""You are an expert forex/gold trader and market analyst. Analyze the market and provide actionable trading signals with detailed structured reasoning.

**SYMBOL:** {symbol}
**TIMESTAMP:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**TECHNICAL METRICS:**
- Current Price: ${metrics.get('current_price', 'N/A')}
- ATR: ${metrics.get('atr', 'N/A')} ({metrics.get('atr_pct', 'N/A')}%)
- Trend: {metrics.get('trend', 'N/A')}
- 24H Range: ${metrics.get('low_24h', 'N/A')} - ${metrics.get('high_24h', 'N/A')}
- Premium/Discount: {metrics.get('premium_discount', 'N/A')} (0=discount, 1=premium)
- Volatility: {metrics.get('volatility_pct', 'N/A')}%
- EMA Fast: ${metrics.get('ema_fast', 'N/A')}
- EMA Slow: ${metrics.get('ema_slow', 'N/A')}

**RECENT NEWS:**
"""
        
        if news:
            for item in news:
                prompt += f"\n- [{item['impact'].upper()}] {item['title']} at {item['time']}"
        else:
            prompt += "\nNo significant news in past 24 hours"
        
        prompt += """

**TASK:**
Analyze the provided M15 and H1 chart screenshots along with the metrics above. Provide detailed structured reasoning in your analysis field.

**YOUR RESPONSE MUST BE IN STRICT JSON FORMAT WITH DETAILED REASONING:**

{
  "timestamp": "2026-01-07T06:00:00",
  "symbol": "XAUUSD",
  "summary": {
    "market_structure": "bullish|bearish|neutral|ranging",
    "trend_strength": 0-100,
    "sentiment": "strong_bullish|bullish|neutral|bearish|strong_bearish",
    "confidence": 0-100
  },
  "key_levels": {
    "support": [2650.0, 2640.0],
    "resistance": [2680.0, 2690.0],
    "current_value_area": "premium|fair|discount"
  },
  "signals": [
    {
      "type": "BUY|SELL",
      "entry_price": 2665.0,
      "stop_loss": 2660.0,
      "take_profit": 2675.0,
      "trigger_time": "12:00|15:00|immediate|none",
      "reasoning": "Strong bullish structure, price in discount zone",
      "confidence": 75,
      "risk_reward": 2.0
    }
  ],
  "trading_blocks": {
    "block_type": "none|bias|warning|soft_block|hard_block",
    "block_until": null,
    "reason": null
  },
  "risk_factors": [
    "High impact news at 14:00",
    "Price near resistance"
  ],
  "analysis": {
    "trend": "### Тренд:\\nОпишите текущий тренд: восходящий/нисходящий/флэт, сила тренда, ключевые уровни поддержки и сопротивления, которые подтверждают направление.",
    "support_resistance": "### Уровни поддержки и сопротивления:\\n- **Уровень сопротивления:** 2474 (предыдущий локальный максимум)\\n- **Уровень поддержки:** 2442 (предыдущий локальный минимум)\\nОпишите ключевые уровни, которые наблюдаете на графике.",
    "patterns": "### Паттерны:\\nОпишите любые паттерны (V-образная разворотная формация, двойное дно, голова и плечи и т.д.) или их отсутствие.",
    "entry_exit": "### Точки входа и выхода:\\n- **Точка входа на покупку:** При пробое уровня 2474 и закреплении выше\\n- **Точка выхода для продаж:** Возврат к уровню 2442 может привлечь продавцов\\nУкажите конкретные ценовые уровни для входа и выхода.",
    "risk_assessment": "### Оценка риска:\\nВвиду отсутствия значительных экономических событий и стабильного восстановления после падения, риск умеренный. Однако следует проявить осторожность, так как развороты возможны у важных уровней.",
    "news_impact": "### Учет новостей:\\nПоскольку нет запланированных экономических событий на сегодня, можно ожидать меньшую волатильность, но следует быть готовым к внезапным изменениям рынка.\\n\\nОпишите влияние новостей на рынок.",
    "recommendation": "Рекомендуется следить за динамикой объема, которая может указать на сильное движение."
  }
}

**INSTRUCTIONS FOR "analysis" FIELD:**
Structure your analysis with clear sections (use Russian language for better readability):

1. **trend**: Describe current trend (восходящий/нисходящий/флэт), strength, confirm with EMA/structure
2. **support_resistance**: List key support/resistance levels with specific prices
3. **patterns**: Identify chart patterns (V-shape, double top/bottom, head & shoulders, etc.) or note absence
4. **entry_exit**: Specify exact entry points for BUY/SELL with price levels
5. **risk_assessment**: Evaluate risk level considering volatility, news, market conditions
6. **news_impact**: Explain how current/upcoming news affects market
7. **recommendation**: Final actionable recommendation with volume/momentum notes

**BLOCK TYPES:**
- "none": No restrictions (normal trading)
- "bias": Soft suggestion against trading (reduce position size slightly)
- "warning": Reduce risk significantly (50% normal risk)
- "soft_block": Only high confidence trades allowed (>70% confidence)
- "hard_block": Complete trading block (dangerous conditions)

**RULES:**
1. Be specific with entry/SL/TP levels (real prices, not ranges)
2. If you see no clear setup, return empty "signals" array
3. Use "bias" or "warning" instead of hard_block when uncertain
4. Reserve "hard_block" only for extreme danger (major news, no structure)
3. Set "block_trading": true if news or conditions are dangerous
4. "trigger_time" can be specific hour (e.g., "12:00") or "immediate"
5. Confidence should reflect your certainty (>70% = high confidence)
6. Use premium/discount zones and market structure in your analysis
7. Risk_reward should be realistic (minimum 1.5:1)

Provide ONLY the JSON response, no additional text."""

        return prompt
    
    def _call_gpt_api(self, prompt: str, screenshots: Dict[str, str]) -> Dict[str, Any]:
        """Call GPT-4 Vision API with prompt and images."""
        try:
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
            
            # Call API
            response = self.client.chat.completions.create(
                model="gpt-4o",  # or "gpt-4-vision-preview"
                messages=messages,
                max_tokens=2000,
                temperature=0.3  # Lower temperature for more consistent analysis
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Extract JSON if wrapped in markdown
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            analysis = json.loads(content)
            return analysis
            
        except Exception as e:
            logger.error(f"[AI] GPT API call failed: {e}")
            raise
    
    def _validate_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize GPT response."""
        try:
            # Ensure required fields exist
            required_fields = ["timestamp", "symbol", "summary", "key_levels", "signals"]
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = {}
            
            # Validate signals structure
            if "signals" in analysis and analysis["signals"]:
                for signal in analysis["signals"]:
                    required_signal_fields = ["type", "entry_price", "stop_loss", "take_profit", "confidence"]
                    for field in required_signal_fields:
                        if field not in signal:
                            logger.warning(f"[AI] Signal missing field: {field}")
                            signal[field] = None
            
            # Add metadata
            analysis["analyzed_at"] = datetime.now().isoformat()
            analysis["analysis_version"] = self.ANALYSIS_VERSION
            analysis["prompt_version"] = self.PROMPT_VERSION
            
            return analysis
            
        except Exception as e:
            logger.error(f"[AI] Validation failed: {e}")
            return analysis
    
    # Saving removed - SignalManager handles persistence
    
    def _get_fallback_response(self, error: str) -> Dict[str, Any]:
        """Return fallback response on error."""
        return {
            "timestamp": datetime.now().isoformat(),
            "symbol": "XAUUSD",
            "error": error,
            "summary": {
                "market_structure": "unknown",
                "sentiment": "neutral",
                "confidence": 0
            },
            "signals": [],
            "trading_blocks": {
                "block_type": "warning",
                "reason": "Analysis failed - reducing risk for safety"
            }
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
