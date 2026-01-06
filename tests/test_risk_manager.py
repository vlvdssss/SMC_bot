"""
Тесты для RiskManager - управление рисками портфеля.
"""

import pytest
from datetime import datetime
from src.core.risk_manager import RiskManager


class TestRiskManager:
    """Тесты для RiskManager."""
    
    @pytest.fixture
    def risk_manager(self):
        """Создает RiskManager с тестовой конфигурацией."""
        config = {
            'max_daily_loss_percent': 5.0,
            'max_open_positions': 4,
            'max_lot_size': 1.0,
            'max_daily_trades': 10
        }
        return RiskManager(config)
    
    def test_initialization(self, risk_manager):
        """Тест инициализации RiskManager."""
        assert risk_manager.max_daily_loss_percent == 5.0
        assert risk_manager.max_open_positions == 4
        assert risk_manager.max_lot_size == 1.0
        assert risk_manager.max_daily_trades == 10
        assert risk_manager.open_positions == 0
    
    def test_can_open_position_success(self, risk_manager):
        """Тест успешной проверки возможности открытия позиции."""
        result = risk_manager.can_open_position('EURUSD', 0.5, 10000.0)
        assert result is True
    
    def test_can_open_position_max_positions_exceeded(self, risk_manager):
        """Тест блокировки при превышении максимального количества позиций."""
        risk_manager.open_positions = 4
        result = risk_manager.can_open_position('EURUSD', 0.5, 10000.0)
        assert result is False
    
    def test_can_open_position_lot_size_exceeded(self, risk_manager):
        """Тест блокировки при превышении максимального размера лота."""
        result = risk_manager.can_open_position('EURUSD', 1.5, 10000.0)
        assert result is False
    
    def test_can_open_position_daily_trades_limit(self, risk_manager):
        """Тест блокировки при достижении дневного лимита сделок."""
        today = datetime.now().date()
        risk_manager.daily_trades[today] = 10
        result = risk_manager.can_open_position('EURUSD', 0.5, 10000.0)
        assert result is False
    
    def test_can_open_position_daily_loss_limit(self, risk_manager):
        """Тест блокировки при достижении дневного лимита убытков."""
        today = datetime.now().date()
        risk_manager.daily_pnl[today] = -600.0  # 6% от 10000
        result = risk_manager.can_open_position('EURUSD', 0.5, 10000.0)
        assert result is False
    
    def test_validate_signal_buy_success(self, risk_manager):
        """Тест валидации BUY сигнала."""
        signal = {
            'direction': 'BUY',
            'sl': 2030.0,
            'tp': 2080.0,
            'risk_percent': 1.0,
            'instrument': 'XAUUSD'
        }
        result = risk_manager.validate_signal(signal, 2050.0, 10000.0)
        assert result is True
    
    def test_validate_signal_sell_success(self, risk_manager):
        """Тест валидации SELL сигнала."""
        signal = {
            'direction': 'SELL',
            'sl': 2080.0,
            'tp': 2020.0,
            'risk_percent': 1.0,
            'instrument': 'XAUUSD'
        }
        result = risk_manager.validate_signal(signal, 2050.0, 10000.0)
        assert result is True
    
    def test_validate_signal_invalid_buy_levels(self, risk_manager):
        """Тест отклонения BUY сигнала с неверными уровнями."""
        signal = {
            'direction': 'BUY',
            'sl': 2070.0,  # SL выше entry - неверно
            'tp': 2080.0,
            'risk_percent': 1.0,
            'instrument': 'XAUUSD'
        }
        result = risk_manager.validate_signal(signal, 2050.0, 10000.0)
        assert result is False
    
    def test_validate_signal_invalid_sell_levels(self, risk_manager):
        """Тест отклонения SELL сигнала с неверными уровнями."""
        signal = {
            'direction': 'SELL',
            'sl': 2030.0,  # SL ниже entry - неверно
            'tp': 2020.0,
            'risk_percent': 1.0,
            'instrument': 'XAUUSD'
        }
        result = risk_manager.validate_signal(signal, 2050.0, 10000.0)
        assert result is False
    
    def test_validate_signal_missing_sl_tp(self, risk_manager):
        """Тест отклонения сигнала без SL или TP."""
        signal = {
            'direction': 'BUY',
            'risk_percent': 1.0,
            'instrument': 'XAUUSD'
        }
        result = risk_manager.validate_signal(signal, 2050.0, 10000.0)
        assert result is False
    
    def test_validate_signal_zero_stop_distance(self, risk_manager):
        """Тест отклонения сигнала с нулевым расстоянием до стопа."""
        signal = {
            'direction': 'BUY',
            'sl': 2050.0,  # SL == entry
            'tp': 2080.0,
            'risk_percent': 1.0,
            'instrument': 'XAUUSD'
        }
        result = risk_manager.validate_signal(signal, 2050.0, 10000.0)
        assert result is False
    
    def test_update_daily_stats(self, risk_manager):
        """Тест обновления дневной статистики."""
        today = datetime.now().date()
        
        risk_manager.update_daily_stats(100.0)
        assert risk_manager.daily_trades[today] == 1
        assert risk_manager.daily_pnl[today] == 100.0
        
        risk_manager.update_daily_stats(-50.0)
        assert risk_manager.daily_trades[today] == 2
        assert risk_manager.daily_pnl[today] == 50.0
    
    def test_position_opened(self, risk_manager):
        """Тест уведомления об открытии позиции."""
        initial = risk_manager.open_positions
        risk_manager.position_opened()
        assert risk_manager.open_positions == initial + 1
    
    def test_position_closed(self, risk_manager):
        """Тест уведомления о закрытии позиции."""
        risk_manager.open_positions = 3
        risk_manager.position_closed()
        assert risk_manager.open_positions == 2
    
    def test_multiple_positions_workflow(self, risk_manager):
        """Тест рабочего процесса с несколькими позициями."""
        # Открываем 3 позиции
        assert risk_manager.can_open_position('EURUSD', 0.1, 10000.0) is True
        risk_manager.position_opened()
        
        assert risk_manager.can_open_position('XAUUSD', 0.1, 10000.0) is True
        risk_manager.position_opened()
        
        assert risk_manager.can_open_position('GBPUSD', 0.1, 10000.0) is True
        risk_manager.position_opened()
        
        assert risk_manager.open_positions == 3
        
        # Пытаемся открыть 4-ю (должна пройти)
        assert risk_manager.can_open_position('USDJPY', 0.1, 10000.0) is True
        risk_manager.position_opened()
        
        # Пытаемся открыть 5-ю (должна заблокироваться)
        assert risk_manager.can_open_position('EURJPY', 0.1, 10000.0) is False
        
        # Закрываем одну позицию
        risk_manager.position_closed()
        
        # Теперь можем открыть ещё одну
        assert risk_manager.can_open_position('EURJPY', 0.1, 10000.0) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
