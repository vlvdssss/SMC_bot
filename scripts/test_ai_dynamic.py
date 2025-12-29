import sys, os, json
sys.path.insert(0, os.path.abspath(os.getcwd()))
from datetime import datetime
from src.manual_trading.ai_analyzer import ManualAIAnalyzer

# Fake LLM client that returns a JSON response based on context
class FakeResponse:
    def __init__(self, content):
        self.choices = [type('C', (), {'message': type('M', (), {'content': content})})()]

class FakeLLM:
    def __init__(self):
        pass
    class chat:
        class completions:
            @staticmethod
            def create(model, messages, max_tokens, temperature):
                # Build a JSON reply influenced by prompt content
                user_msg = messages[-1]['content']
                # crude heuristic: if 'volatility' in prompt and >0.5 => range
                vol = 0.0
                if 'Волатильность' in user_msg:
                    try:
                        part = user_msg.split('Волатильность (приблиз.):')[1].split('\n')[0]
                        vol = float(part.strip())
                    except Exception:
                        vol = 0.0
                bias = 'bullish' if 'buy' in user_msg.lower() and vol < 1 else 'range'
                confidence = 'low' if vol > 2 else 'high'
                content = json.dumps({
                    'market_bias': bias,
                    'trade_alignment': 'aligned' if bias=='bullish' else 'neutral',
                    'scenarios': {'best_case': 'price moves favorably', 'worst_case': 'stop out'},
                    'invalidation_levels': ['below 4400', 'below 4380'],
                    'confidence': confidence,
                    'comment': f'Auto-generated based on vol={vol}'
                })
                return FakeResponse(content)

# Create analyzer with fake client
fake = FakeLLM()
config = {'AI_MODEL':'gpt-test','AI_MAX_TOKENS':300}
analyzer = ManualAIAnalyzer(fake, config)

# Example enriched context
context = {
    'symbol':'XAUUSD',
    'timeframe':'H1',
    'direction':'buy',
    'entry_price':4510.0,
    'stop_loss':4490.0,
    'take_profit':4550.0,
    'risk_amount':1.0,
    'bid':4509.5,
    'ask':4510.5,
    'spread':1.0,
    'volatility_est':0.22,
    'price_distance':0.5,
    'account_balance':124.5,
    'smc_structure':'uptrend pullback',
    'ml_bias':'bullish',
    'ml_confidence':0.8,
    'news_status':'No major events'
}

pred = analyzer.analyze_manual_trade(context)
if pred:
    print('Parsed prediction:')
    print(pred)
else:
    print('Prediction failed')
