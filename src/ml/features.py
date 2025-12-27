"""
Feature Engineering для ML модели

Собирает признаки для предсказания успешности сделки.
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime


class FeatureExtractor:
    """Извлечение признаков из рыночных данных."""

    def __init__(self):
        self.feature_names = []

    def extract_features(self, h1_data: pd.DataFrame, m15_data: pd.DataFrame,
                         m15_idx: int, signal: Dict) -> Dict[str, float]:
        """
        Извлекает все фичи для одного сигнала.

        Args:
            h1_data: H1 данные
            m15_data: M15 данные
            m15_idx: Индекс текущей M15 свечи
            signal: Сигнал от стратегии

        Returns:
            Dict с фичами
        """
        features = {}

        current_bar = m15_data.iloc[m15_idx]
        current_time = pd.to_datetime(current_bar['time'])
        current_price = current_bar['close']

        # ========== ВРЕМЕННЫЕ ФИЧИ ==========
        features['hour'] = current_time.hour
        features['day_of_week'] = current_time.dayofweek
        features['is_london_session'] = 1 if 7 <= current_time.hour <= 16 else 0
        features['is_ny_session'] = 1 if 13 <= current_time.hour <= 22 else 0
        features['is_overlap'] = 1 if 13 <= current_time.hour <= 16 else 0
        features['is_friday'] = 1 if current_time.dayofweek == 4 else 0
        features['is_monday'] = 1 if current_time.dayofweek == 0 else 0

        # ========== ВОЛАТИЛЬНОСТЬ ==========
        features['atr_14'] = self._calculate_atr(m15_data, m15_idx, 14)
        features['atr_50'] = self._calculate_atr(m15_data, m15_idx, 50)
        features['atr_ratio'] = features['atr_14'] / features['atr_50'] if features['atr_50'] > 0 else 1

        # Волатильность последних N свечей
        if m15_idx >= 20:
            recent_highs = m15_data.iloc[m15_idx-20:m15_idx]['high']
            recent_lows = m15_data.iloc[m15_idx-20:m15_idx]['low']
            features['recent_range'] = (recent_highs.max() - recent_lows.min()) / current_price
        else:
            features['recent_range'] = 0

        # ========== ТРЕНД ==========
        features['ema_20'] = self._calculate_ema(m15_data, m15_idx, 20)
        features['ema_50'] = self._calculate_ema(m15_data, m15_idx, 50)
        features['ema_200'] = self._calculate_ema(m15_data, m15_idx, 200)

        # Позиция цены относительно EMA
        features['price_vs_ema20'] = (current_price - features['ema_20']) / features['ema_20'] if features['ema_20'] > 0 else 0
        features['price_vs_ema50'] = (current_price - features['ema_50']) / features['ema_50'] if features['ema_50'] > 0 else 0
        features['price_vs_ema200'] = (current_price - features['ema_200']) / features['ema_200'] if features['ema_200'] > 0 else 0

        # Наклон EMA (тренд)
        if m15_idx >= 10:
            ema20_prev = self._calculate_ema(m15_data, m15_idx - 10, 20)
            features['ema20_slope'] = (features['ema_20'] - ema20_prev) / ema20_prev if ema20_prev > 0 else 0
        else:
            features['ema20_slope'] = 0

        # ========== МОМЕНТУМ ==========
        features['rsi_14'] = self._calculate_rsi(m15_data, m15_idx, 14)
        features['rsi_7'] = self._calculate_rsi(m15_data, m15_idx, 7)

        # RSI зоны
        features['rsi_oversold'] = 1 if features['rsi_14'] < 30 else 0
        features['rsi_overbought'] = 1 if features['rsi_14'] > 70 else 0

        # ========== СВЕЧНЫЕ ПАТТЕРНЫ ==========
        if m15_idx >= 3:
            # Размер последних свечей
            for i in range(1, 4):
                bar = m15_data.iloc[m15_idx - i]
                body = abs(bar['close'] - bar['open'])
                full_range = bar['high'] - bar['low']
                features[f'body_ratio_{i}'] = body / full_range if full_range > 0 else 0
                features[f'is_bullish_{i}'] = 1 if bar['close'] > bar['open'] else 0

        # ========== СИГНАЛ ==========
        features['signal_direction'] = 1 if signal.get('direction') == 'BUY' else -1

        # RR сигнала
        entry = signal.get('entry', current_price)
        sl = signal.get('sl', entry)
        tp = signal.get('tp', entry)

        risk = abs(entry - sl)
        reward = abs(tp - entry)
        features['signal_rr'] = reward / risk if risk > 0 else 0

        # ========== H1 КОНТЕКСТ ==========
        if len(h1_data) > 20:
            h1_idx = len(h1_data) - 1
            features['h1_atr'] = self._calculate_atr(h1_data, h1_idx, 14)
            features['h1_ema20'] = self._calculate_ema(h1_data, h1_idx, 20)
            features['h1_trend'] = 1 if h1_data.iloc[h1_idx]['close'] > features['h1_ema20'] else -1
        else:
            features['h1_atr'] = 0
            features['h1_ema20'] = 0
            features['h1_trend'] = 0

        self.feature_names = list(features.keys())
        return features

    def _calculate_atr(self, df: pd.DataFrame, idx: int, period: int) -> float:
        """Расчёт ATR."""
        if idx < period:
            return 0.0

        tr_list = []
        for i in range(idx - period + 1, idx + 1):
            high = df.iloc[i]['high']
            low = df.iloc[i]['low']
            prev_close = df.iloc[i-1]['close'] if i > 0 else df.iloc[i]['close']
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)

        return np.mean(tr_list)

    def _calculate_ema(self, df: pd.DataFrame, idx: int, period: int) -> float:
        """Расчёт EMA."""
        if idx < period:
            return df.iloc[idx]['close']

        closes = df.iloc[idx - period + 1:idx + 1]['close'].values
        weights = np.exp(np.linspace(-1., 0., period))
        weights /= weights.sum()
        return np.sum(closes * weights)

    def _calculate_rsi(self, df: pd.DataFrame, idx: int, period: int) -> float:
        """Расчёт RSI."""
        if idx < period + 1:
            return 50.0

        closes = df.iloc[idx - period:idx + 1]['close'].values
        deltas = np.diff(closes)

        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))