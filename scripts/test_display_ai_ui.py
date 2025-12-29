import sys, os
sys.path.insert(0, os.path.abspath(os.getcwd()))

from datetime import datetime
from src.gui.app import BazaApp
from src.models import AIPrediction

app = BazaApp()

pred = AIPrediction(
    market_bias='bullish',
    trade_alignment='aligned',
    scenarios={'best_case': 'Price rallies to 4520', 'worst_case': 'Retrace to 4480'},
    invalidation_levels=['below 4480', 'close below 4470'],
    confidence='high',
    comment='Momentum and ML indicators support bullish continuation.',
    timestamp=datetime.now(),
    context={'ml_bias': 'bullish', 'ml_confidence': 0.87, 'news_status': 'No major events', 'smc_structure': 'uptrend pullback'}
)

# Call display method (will update GUI widgets)
app.display_ai_prediction(pred)
print('Display called successfully')
