"""
ML Predictor для оценки вероятности успеха сделки.

Использует LightGBM для предсказания.
"""

import os
import pickle
import numpy as np
import pandas as pd
from typing import Tuple, Optional
from datetime import datetime

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("[!] LightGBM not installed. ML predictions disabled.")

from .features import FeatureExtractor


class TradePredictor:
    """ML модель для предсказания успеха сделки."""

    def __init__(self, model_path: str = 'models/trade_predictor.pkl'):
        self.model_path = model_path
        self.model = None
        self.feature_extractor = FeatureExtractor()
        self.is_trained = False
        self.feature_names = []

        # Загружаем модель если есть
        self.load_model()

    def predict_success(self, h1_data: pd.DataFrame, m15_data: pd.DataFrame,
                        m15_idx: int, signal: dict) -> Tuple[float, str]:
        """
        Предсказывает вероятность успеха сделки.

        Returns:
            Tuple[probability: float, confidence: str]
            - probability: 0.0 - 1.0
            - confidence: 'LOW', 'MEDIUM', 'HIGH'
        """
        if not self.is_trained or not LIGHTGBM_AVAILABLE:
            return (0.5, 'UNKNOWN')

        # Извлекаем фичи
        features = self.feature_extractor.extract_features(
            h1_data, m15_data, m15_idx, signal
        )

        # Создаём DataFrame с правильным порядком колонок
        X = pd.DataFrame([features])[self.feature_names]

        # Предсказываем
        try:
            proba = self.model.predict_proba(X)[0][1]  # Вероятность класса 1 (win)

            # Определяем уверенность
            if proba > 0.7 or proba < 0.3:
                confidence = 'HIGH'
            elif proba > 0.6 or proba < 0.4:
                confidence = 'MEDIUM'
            else:
                confidence = 'LOW'

            return (proba, confidence)

        except Exception as e:
            print(f"[ML] Prediction error: {e}")
            return (0.5, 'ERROR')

    def should_take_trade(self, probability: float, min_probability: float = 0.55) -> bool:
        """Решение брать ли сделку."""
        return probability >= min_probability

    def train(self, trades_data: pd.DataFrame, features_data: pd.DataFrame):
        """
        Обучает модель на исторических данных.

        Args:
            trades_data: DataFrame со сделками (должен содержать 'result': 1=win, 0=loss)
            features_data: DataFrame с фичами для каждой сделки
        """
        if not LIGHTGBM_AVAILABLE:
            print("[!] Cannot train: LightGBM not installed")
            return

        print("[ML] Training model...")

        # Подготовка данных
        X = features_data
        y = trades_data['result'].values

        self.feature_names = list(X.columns)

        # Разделение на train/test
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Обучение
        self.model = lgb.LGBMClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            num_leaves=31,
            random_state=42,
            verbose=-1
        )

        self.model.fit(X_train, y_train)

        # Оценка
        train_acc = self.model.score(X_train, y_train)
        test_acc = self.model.score(X_test, y_test)

        print(f"[ML] Training accuracy: {train_acc:.2%}")
        print(f"[ML] Test accuracy: {test_acc:.2%}")

        # Feature importance
        importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        print("\n[ML] Top 10 features:")
        print(importance.head(10).to_string(index=False))

        self.is_trained = True
        self.save_model()

        return {'train_acc': train_acc, 'test_acc': test_acc}

    def save_model(self):
        """Сохраняет модель."""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names,
                'is_trained': self.is_trained
            }, f)

        print(f"[ML] Model saved to {self.model_path}")

    def load_model(self):
        """Загружает модель."""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)

                self.model = data['model']
                self.feature_names = data['feature_names']
                self.is_trained = data['is_trained']

                print(f"[ML] Model loaded from {self.model_path}")
            except Exception as e:
                print(f"[ML] Failed to load model: {e}")