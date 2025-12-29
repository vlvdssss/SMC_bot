import sys
import os
import yaml
from datetime import datetime

# Ensure project root is on sys.path so `src` package can be imported when running as script
sys.path.insert(0, os.path.abspath(os.getcwd()))

from src.manual_trading.controller import ManualTradingController
from src.models import AIPrediction

# Load manual config
with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)
manual_cfg = cfg.get('manual_trading', {})

# Create controller
controller = ManualTradingController(manual_cfg, executor=None, llm_client=None)

# Create a mock analyzer that returns a valid AIPrediction
class MockAnalyzer:
    def analyze_manual_trade(self, ctx):
        return AIPrediction(
            market_bias='bullish',
            trade_alignment='aligned',
            scenarios={'best_case': 'price rallies 2%', 'worst_case': 'price drops 1%'},
            invalidation_levels=['below 4500', 'close below 4480'],
            confidence='high',
            comment='Mock prediction OK',
            timestamp=datetime.now(),
            context=ctx
        )

controller.ai_analyzer = MockAnalyzer()

# Prepare a simple context
context = {
    'symbol': 'XAUUSD',
    'timeframe': 'H1',
    'direction': 'buy',
    'entry_price': 4500.0,
    'stop_loss': 4490.0,
    'take_profit': 4520.0,
    'risk_amount': 1.0
}

pred = controller.get_ai_prediction(context)

if pred:
    print('Prediction OK:', pred.market_bias, pred.confidence)
    print('Comment:', pred.comment)
else:
    print('Prediction failed')
