"""
Тесты для RiskCalculator - калькулятор риск-менеджмента.
"""

import pytest
from src.manual_trading.calculator import RiskCalculator


class TestRiskCalculator:
    """Тесты для RiskCalculator."""
    
    @pytest.fixture
    def calculator(self):
        """Создает RiskCalculator с тестовой конфигурацией."""
        config = {
            'PIP_VALUE': 0.0001,
            'CONTRACT_SIZE': 100000
        }
        return RiskCalculator(config)
    
    def test_initialization(self, calculator):
        """Тест инициализации калькулятора."""
        assert calculator.pip_value == 0.0001
        assert calculator.contract_size == 100000
    
    def test_calculate_lot_size_with_percent_risk(self, calculator):
        """Тест расчета размера лота с риском в процентах."""
        # Баланс $10000, риск 1%, SL 20 пипсов
        lot_size, explanation = calculator.calculate_lot_size(
            symbol='EURUSD',
            entry_price=1.1000,
            stop_loss=1.0980,  # 20 пипсов
            risk_amount=1.0,  # 1%
            account_balance=10000.0
        )
        
        # Ожидаемый размер: $100 риск / (20 пипсов * $10/пипс/лот) = 0.5 лота
        assert lot_size > 0
        assert isinstance(explanation, str)
    
    def test_calculate_lot_size_with_fixed_risk(self, calculator):
        """Тест расчета размера лота с фиксированным риском."""
        # Риск $100, SL 50 пипсов
        lot_size, explanation = calculator.calculate_lot_size(
            symbol='EURUSD',
            entry_price=1.1000,
            stop_loss=1.0950,  # 50 пипсов
            risk_amount=100.0,  # $100
            account_balance=10000.0
        )
        
        # Ожидаемый размер: $100 / (50 пипсов * $10/пипс/лот) = 0.2 лота
        assert lot_size > 0
        assert isinstance(explanation, str)
    
    def test_calculate_lot_size_zero_stop_distance(self, calculator):
        """Тест обработки нулевого расстояния до стопа."""
        lot_size, explanation = calculator.calculate_lot_size(
            symbol='EURUSD',
            entry_price=1.1000,
            stop_loss=1.1000,  # SL == entry
            risk_amount=1.0,
            account_balance=10000.0
        )
        
        # Должен вернуть минимальный лот и сообщение об ошибке
        assert lot_size == 0.01
        assert "Error" in explanation
    
    def test_calculate_rr_ratio_buy_signal(self, calculator):
        """Тест расчета RR для BUY сигнала."""
        rr_ratio = calculator.calculate_rr_ratio(
            entry_price=1.1000,
            stop_loss=1.0980,  # 20 пипсов риск
            take_profit=1.1030,  # 30 пипсов прибыль
            direction='BUY'
        )
        
        # RR = 30 / 20 = 1.5
        assert abs(rr_ratio - 1.5) < 0.01
    
    def test_calculate_rr_ratio_sell_signal(self, calculator):
        """Тест расчета RR для SELL сигнала."""
        rr_ratio = calculator.calculate_rr_ratio(
            entry_price=1.1000,
            stop_loss=1.1020,  # 20 пипсов риск
            take_profit=1.0960,  # 40 пипсов прибыль
            direction='SELL'
        )
        
        # RR = 40 / 20 = 2.0
        assert abs(rr_ratio - 2.0) < 0.01
    
    def test_calculate_rr_ratio_zero_reward(self, calculator):
        """Тест обработки нулевой прибыли."""
        rr_ratio = calculator.calculate_rr_ratio(
            entry_price=1.1000,
            stop_loss=1.0980,
            take_profit=1.1000,  # TP == entry
            direction='BUY'
        )
        
        assert rr_ratio == 0.0
    
    def test_validate_risk_parameters_success(self, calculator):
        """Тест успешной валидации параметров."""
        is_valid, message = calculator.validate_risk_parameters(
            lot_size=0.5,
            risk_amount=100.0,
            account_balance=10000.0
        )
        
        assert is_valid is True
    
    def test_validate_risk_parameters_lot_too_small(self, calculator):
        """Тест отклонения слишком маленького лота."""
        is_valid, message = calculator.validate_risk_parameters(
            lot_size=0.005,
            risk_amount=10.0,
            account_balance=10000.0
        )
        
        assert is_valid is False
        assert "too small" in message.lower()
    
    def test_validate_risk_parameters_lot_too_large(self, calculator):
        """Тест отклонения слишком большого лота."""
        is_valid, message = calculator.validate_risk_parameters(
            lot_size=150.0,
            risk_amount=1000.0,
            account_balance=10000.0
        )
        
        assert is_valid is False
        assert "too large" in message.lower()
    
    def test_validate_risk_parameters_risk_too_high(self, calculator):
        """Тест отклонения слишком большого риска."""
        is_valid, message = calculator.validate_risk_parameters(
            lot_size=1.0,
            risk_amount=1500.0,  # >10% от $10000
            account_balance=10000.0
        )
        
        assert is_valid is False
    
    def test_xauusd_calculation(self):
        """Тест расчета для XAUUSD (золото)."""
        # XAUUSD имеет другой pip value
        config = {
            'PIP_VALUE': 0.01,  # Для золота
            'CONTRACT_SIZE': 100
        }
        calculator = RiskCalculator(config)
        
        lot_size, explanation = calculator.calculate_lot_size(
            symbol='XAUUSD',
            entry_price=2050.00,
            stop_loss=2030.00,  # 20 долларов
            risk_amount=1.0,  # 1%
            account_balance=10000.0
        )
        
        assert lot_size > 0
        assert isinstance(explanation, str)
    
    def test_calculate_lot_size_edge_cases(self, calculator):
        """Тест граничных случаев."""
        # Очень маленький баланс
        lot_size, _ = calculator.calculate_lot_size(
            symbol='EURUSD',
            entry_price=1.1000,
            stop_loss=1.0950,
            risk_amount=1.0,
            account_balance=100.0
        )
        assert lot_size >= 0.01  # Минимальный лот
        
        # Очень большой стоп
        lot_size, _ = calculator.calculate_lot_size(
            symbol='EURUSD',
            entry_price=1.1000,
            stop_loss=1.0000,  # 1000 пипсов
            risk_amount=1.0,
            account_balance=10000.0
        )
        assert lot_size > 0
    
    def test_realistic_trading_scenario(self, calculator):
        """Тест реалистичного торгового сценария."""
        # Сценарий: Трейдер с балансом $5000 хочет рискнуть 2%
        account_balance = 5000.0
        risk_percent = 2.0
        entry = 1.0950
        stop_loss = 1.0920  # 30 пипсов
        take_profit = 1.1010  # 60 пипсов
        
        # Расчет размера лота
        lot_size, explanation = calculator.calculate_lot_size(
            symbol='EURUSD',
            entry_price=entry,
            stop_loss=stop_loss,
            risk_amount=risk_percent,
            account_balance=account_balance
        )
        
        # Расчет RR
        rr_ratio = calculator.calculate_rr_ratio(
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            direction='BUY'
        )
        
        # Валидация
        is_valid, message = calculator.validate_risk_parameters(
            lot_size=lot_size,
            risk_amount=account_balance * (risk_percent / 100),
            account_balance=account_balance
        )
        
        assert lot_size > 0
        assert abs(rr_ratio - 2.0) < 0.01  # 60/30 = 2 (с учетом погрешности)
        assert is_valid is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
