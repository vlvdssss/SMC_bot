"""
Скрипт обучения ML модели на исторических сделках.

Использует результаты бэктеста для обучения.
"""

import pandas as pd
import numpy as np
import sys
import os
from typing import Tuple

sys.path.insert(0, os.path.dirname(__file__))

from src.ml.features import FeatureExtractor
from src.ml.predictor import TradePredictor
from src.core.data_loader import DataLoader
from src.strategies.xauusd_strategy import StrategyXAUUSD
from src.strategies.eurusd_strategy import StrategyEURUSD_SMC_Retracement


def collect_training_data(instrument: str, year: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Собирает данные для обучения из бэктеста.

    Returns:
        trades_df: DataFrame со сделками
        features_df: DataFrame с фичами
    """
    print(f"[*] Collecting {instrument} data for {year}...")

    # Загружаем данные
    loader = DataLoader(
        instrument=instrument.lower(),
        start_date=f'{year}-01-01',
        end_date=f'{year}-12-31'
    )
    h1_data, m15_data = loader.load()

    # Инициализируем стратегию
    if instrument == 'XAUUSD':
        strategy = StrategyXAUUSD()
    else:
        strategy = StrategyEURUSD_SMC_Retracement()

    strategy.load_data(h1_data, m15_data)

    # Собираем сделки и фичи
    feature_extractor = FeatureExtractor()
    trades = []
    features_list = []

    h1_idx = 0

    for m15_idx in range(100, len(m15_data) - 50):
        current_time = m15_data.iloc[m15_idx]['time']

        # Обновляем H1 индекс
        while h1_idx < len(h1_data) - 1 and h1_data.iloc[h1_idx + 1]['time'] <= current_time:
            h1_idx += 1

        if h1_idx < 2:
            continue

        # Строим контекст
        strategy.build_context(h1_idx)

        # Генерируем сигнал
        analysis_price = m15_data.iloc[m15_idx]['close']
        entry_price = m15_data.iloc[m15_idx + 1]['open']

        if instrument == 'XAUUSD':
            signal = strategy.generate_signal(m15_idx, analysis_price, entry_price)
        else:
            signal = strategy.generate_signal(m15_idx, analysis_price, entry_price, current_time)

        if not signal.get('valid'):
            continue

        # Извлекаем фичи
        features = feature_extractor.extract_features(h1_data, m15_data, m15_idx, signal)

        # Симулируем результат сделки
        entry = signal['entry']
        sl = signal['sl']
        tp = signal['tp']
        direction = signal['direction']

        # Проверяем что было раньше - SL или TP
        result = simulate_trade_result(m15_data, m15_idx + 1, entry, sl, tp, direction)

        trades.append({
            'time': current_time,
            'instrument': instrument,
            'direction': direction,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'result': result  # 1 = win, 0 = loss
        })

        features_list.append(features)

    trades_df = pd.DataFrame(trades)
    features_df = pd.DataFrame(features_list)

    print(f"[*] Collected {len(trades_df)} trades")
    if len(trades_df) > 0:
        print(f"    Win rate: {trades_df['result'].mean():.2%}")

    return trades_df, features_df


def simulate_trade_result(m15_data: pd.DataFrame, start_idx: int,
                          entry: float, sl: float, tp: float, direction: str,
                          max_bars: int = 100) -> int:
    """Симулирует результат сделки."""

    for i in range(start_idx, min(start_idx + max_bars, len(m15_data))):
        bar = m15_data.iloc[i]

        if direction == 'BUY':
            if bar['low'] <= sl:
                return 0  # Loss
            if bar['high'] >= tp:
                return 1  # Win
        else:  # SELL
            if bar['high'] >= sl:
                return 0  # Loss
            if bar['low'] <= tp:
                return 1  # Win

    # Таймаут - считаем как loss
    return 0


def main():
    print("=" * 60)
    print("ML MODEL TRAINING")
    print("=" * 60)

    all_trades = []
    all_features = []

    # Собираем данные за 2023-2024 (2025 оставляем для теста)
    for year in [2023, 2024]:
        for instrument in ['XAUUSD', 'EURUSD']:
            trades_df, features_df = collect_training_data(instrument, year)
            all_trades.append(trades_df)
            all_features.append(features_df)

    # Объединяем
    trades_combined = pd.concat(all_trades, ignore_index=True)
    features_combined = pd.concat(all_features, ignore_index=True)

    print(f"\n[*] Total training samples: {len(trades_combined)}")
    if len(trades_combined) > 0:
        print(f"    Overall win rate: {trades_combined['result'].mean():.2%}")

    # Обучаем модель
    predictor = TradePredictor()
    results = predictor.train(trades_combined, features_combined)

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Model saved to: models/trade_predictor.pkl")
    print(f"Train accuracy: {results['train_acc']:.2%}")
    print(f"Test accuracy: {results['test_acc']:.2%}")


if __name__ == "__main__":
    main()