import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.gui.app import BazaApp
from src.manual_trading.ai_analyzer import ManualAIAnalyzer

app = BazaApp()
if app.manual_controller:
    app.manual_controller.llm_client = object()
    app.manual_controller.ai_analyzer = ManualAIAnalyzer(app.manual_controller.llm_client, app.manual_controller.config)
    print('AI analyzer attached:', bool(app.manual_controller.ai_analyzer))
else:
    print('No manual_controller')
