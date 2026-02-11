"""
Weekly ML Analyzer - Анализ недельных данных и рекомендации
Запускается в конце недели для анализа собранных данных
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import sys

def get_data_path(filename):
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent.parent
    return base_path / 'data' / filename

class WeeklyAnalyzer:
    """Анализирует недельные данные и выдаёт рекомендации"""
    
    def __init__(self):
        self.ml_folder = get_data_path('ml_training')
        self.snapshots_file = self.ml_folder / 'market_snapshots.csv'
        self.decisions_file = self.ml_folder / 'ai_decisions.csv'
        self.trades_file = self.ml_folder / 'trade_outcomes.csv'
        
        self.snapshots_df = None
        self.decisions_df = None
        self.trades_df = None
    
    def load_data(self):
        """Загружаем все собранные данные"""
        print("📊 Loading collected data...")
        
        try:
            self.snapshots_df = pd.read_csv(self.snapshots_file)
            print(f"✅ Market snapshots: {len(self.snapshots_df)}")
        except Exception as e:
            print(f"❌ No market snapshots: {e}")
            self.snapshots_df = pd.DataFrame()
        
        try:
            self.decisions_df = pd.read_csv(self.decisions_file)
            print(f"✅ AI decisions: {len(self.decisions_df)}")
        except Exception as e:
            print(f"❌ No AI decisions: {e}")
            self.decisions_df = pd.DataFrame()
        
        try:
            self.trades_df = pd.read_csv(self.trades_file)
            print(f"✅ Trade outcomes: {len(self.trades_df)}")
        except Exception as e:
            print(f"❌ No trades: {e}")
            self.trades_df = pd.DataFrame()
    
    def analyze_best_hours(self):
        """Анализ: в какие часы лучше торговать"""
        print("\n" + "="*80)
        print("📈 HOURLY PERFORMANCE ANALYSIS")
        print("="*80)
        
        if self.trades_df.empty:
            print("❌ No trade data")
            return {}
        
        hourly_stats = self.trades_df.groupby('open_hour').agg({
            'trade_id': 'count',
            'win': ['sum', 'mean'],
            'pnl': ['sum', 'mean']
        }).round(2)
        
        hourly_stats.columns = ['trades', 'wins', 'winrate', 'total_pnl', 'avg_pnl']
        hourly_stats['winrate'] = (hourly_stats['winrate'] * 100).round(1)
        
        # Фильтруем часы с минимум 5 сделками
        hourly_stats_filtered = hourly_stats[hourly_stats['trades'] >= 5]
        
        if not hourly_stats_filtered.empty:
            best_hours = hourly_stats_filtered.nlargest(5, 'winrate')
            worst_hours = hourly_stats_filtered.nsmallest(5, 'winrate')
            
            print("\n🟢 BEST HOURS (Top 5):")
            print(best_hours.to_string())
            
            print("\n🔴 WORST HOURS (Bottom 5):")
            print(worst_hours.to_string())
            
            # Рекомендации
            good_hours = best_hours[best_hours['winrate'] > 55].index.tolist()
            bad_hours = worst_hours[worst_hours['winrate'] < 45].index.tolist()
            
            print(f"\n✅ RECOMMENDED HOURS: {good_hours}")
            print(f"❌ AVOID HOURS: {bad_hours}")
            
            return {'good_hours': good_hours, 'bad_hours': bad_hours}
        else:
            print("⚠️ Not enough data (need 5+ trades per hour)")
            return {}
    
    def analyze_market_conditions(self):
        """Анализ: при каких условиях рынка лучше торговать"""
        print("\n" + "="*80)
        print("🌊 MARKET CONDITIONS ANALYSIS")
        print("="*80)
        
        if self.trades_df.empty:
            print("❌ No trade data")
            return {}
        
        # ATR Analysis
        print("\n📊 ATR (Volatility) Performance:")
        self.trades_df['atr_bucket'] = pd.cut(
            self.trades_df['open_atr'], 
            bins=[0, 5, 10, 15, 20, 100],
            labels=['Very Low', 'Low', 'Medium', 'High', 'Very High']
        )
        
        atr_stats = self.trades_df.groupby('atr_bucket').agg({
            'trade_id': 'count',
            'win': 'mean',
            'pnl': 'mean'
        }).round(2)
        
        atr_stats.columns = ['trades', 'winrate', 'avg_pnl']
        atr_stats['winrate'] = (atr_stats['winrate'] * 100).round(1)
        print(atr_stats.to_string())
        
        # RSI Analysis
        print("\n📊 RSI (Momentum) Performance:")
        self.trades_df['rsi_bucket'] = pd.cut(
            self.trades_df['open_rsi'],
            bins=[0, 30, 40, 60, 70, 100],
            labels=['Oversold', 'Weak', 'Neutral', 'Strong', 'Overbought']
        )
        
        rsi_stats = self.trades_df.groupby('rsi_bucket').agg({
            'trade_id': 'count',
            'win': 'mean',
            'pnl': 'mean'
        }).round(2)
        
        rsi_stats.columns = ['trades', 'winrate', 'avg_pnl']
        rsi_stats['winrate'] = (rsi_stats['winrate'] * 100).round(1)
        print(rsi_stats.to_string())
        
        # Trend Analysis
        print("\n📊 TREND State Performance:")
        trend_stats = self.trades_df.groupby('open_ema_trend').agg({
            'trade_id': 'count',
            'win': 'mean',
            'pnl': 'mean'
        }).round(2)
        
        trend_stats.columns = ['trades', 'winrate', 'avg_pnl']
        trend_stats['winrate'] = (trend_stats['winrate'] * 100).round(1)
        print(trend_stats.to_string())
        
        recommendations = {}
        
        # Best ATR range
        best_atr = atr_stats[atr_stats['trades'] >= 3].nlargest(1, 'winrate')
        if not best_atr.empty:
            recommendations['best_atr'] = best_atr.index[0]
        
        # Best RSI range
        best_rsi = rsi_stats[rsi_stats['trades'] >= 3].nlargest(1, 'winrate')
        if not best_rsi.empty:
            recommendations['best_rsi'] = best_rsi.index[0]
        
        # Best trend
        best_trend = trend_stats[trend_stats['trades'] >= 3].nlargest(1, 'winrate')
        if not best_trend.empty:
            recommendations['best_trend'] = best_trend.index[0]
        
        print(f"\n✅ OPTIMAL CONDITIONS:")
        print(f"   ATR: {recommendations.get('best_atr', 'N/A')}")
        print(f"   RSI: {recommendations.get('best_rsi', 'N/A')}")
        print(f"   Trend: {recommendations.get('best_trend', 'N/A')}")
        
        return recommendations
    
    def analyze_session_performance(self):
        """Анализ: какая сессия лучше"""
        print("\n" + "="*80)
        print("🌍 TRADING SESSION ANALYSIS")
        print("="*80)
        
        if self.trades_df.empty:
            print("❌ No trade data")
            return {}
        
        session_stats = self.trades_df.groupby('session').agg({
            'trade_id': 'count',
            'win': ['sum', 'mean'],
            'pnl': ['sum', 'mean']
        }).round(2)
        
        session_stats.columns = ['trades', 'wins', 'winrate', 'total_pnl', 'avg_pnl']
        session_stats['winrate'] = (session_stats['winrate'] * 100).round(1)
        
        print(session_stats.to_string())
        
        best_session = session_stats.nlargest(1, 'winrate').index[0] if not session_stats.empty else None
        worst_session = session_stats.nsmallest(1, 'winrate').index[0] if not session_stats.empty else None
        
        print(f"\n✅ BEST SESSION: {best_session}")
        print(f"❌ WORST SESSION: {worst_session}")
        
        return {'best_session': best_session, 'worst_session': worst_session}
    
    def analyze_ai_quality(self):
        """Анализ: насколько хорошо работает AI"""
        print("\n" + "="*80)
        print("🤖 AI DECISION QUALITY ANALYSIS")
        print("="*80)
        
        if self.decisions_df.empty:
            print("❌ No AI decision data")
            return {}
        
        # Сколько сигналов AI дал
        total_signals = len(self.decisions_df[self.decisions_df['action'] != 'NONE'])
        buy_signals = len(self.decisions_df[self.decisions_df['action'] == 'BUY'])
        sell_signals = len(self.decisions_df[self.decisions_df['action'] == 'SELL'])
        
        print(f"\n📊 AI Signal Distribution:")
        print(f"   Total signals: {total_signals}")
        print(f"   BUY:  {buy_signals} ({buy_signals/total_signals*100:.1f}%)")
        print(f"   SELL: {sell_signals} ({sell_signals/total_signals*100:.1f}%)")
        
        # Сколько триггерились
        triggered = len(self.decisions_df[self.decisions_df['triggered'] == True])
        executed = len(self.decisions_df[self.decisions_df['executed'] == True])
        
        print(f"\n📊 Signal Execution:")
        print(f"   Triggered: {triggered}/{total_signals} ({triggered/total_signals*100:.1f}%)")
        print(f"   Executed:  {executed}/{total_signals} ({executed/total_signals*100:.1f}%)")
        
        # Причины пропуска
        if 'skip_reason' in self.decisions_df.columns:
            skip_reasons = self.decisions_df[self.decisions_df['skip_reason'] != '']['skip_reason'].value_counts()
            if not skip_reasons.empty:
                print(f"\n📊 Skip Reasons:")
                print(skip_reasons.to_string())
        
        return {
            'total_signals': total_signals,
            'execution_rate': executed/total_signals*100 if total_signals > 0 else 0
        }
    
    def generate_recommendations(self):
        """Генерируем финальные рекомендации"""
        print("\n" + "="*80)
        print("💡 FINAL RECOMMENDATIONS")
        print("="*80)
        
        recommendations = {
            'generated_at': datetime.now().isoformat(),
            'data_period': {
                'snapshots': len(self.snapshots_df) if not self.snapshots_df.empty else 0,
                'decisions': len(self.decisions_df) if not self.decisions_df.empty else 0,
                'trades': len(self.trades_df) if not self.trades_df.empty else 0
            }
        }
        
        # Собираем все анализы
        hour_analysis = self.analyze_best_hours()
        condition_analysis = self.analyze_market_conditions()
        session_analysis = self.analyze_session_performance()
        ai_analysis = self.analyze_ai_quality()
        
        recommendations.update({
            'best_hours': hour_analysis.get('good_hours', []),
            'avoid_hours': hour_analysis.get('bad_hours', []),
            'best_session': session_analysis.get('best_session', 'UNKNOWN'),
            'optimal_atr': condition_analysis.get('best_atr', 'UNKNOWN'),
            'optimal_rsi': condition_analysis.get('best_rsi', 'UNKNOWN'),
            'optimal_trend': condition_analysis.get('best_trend', 'UNKNOWN'),
            'ai_execution_rate': ai_analysis.get('execution_rate', 0)
        })
        
        # Сохраняем в JSON
        output_file = self.ml_folder / f"recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(recommendations, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Recommendations saved to: {output_file}")
        
        return recommendations
    
    def run_full_analysis(self):
        """Запустить полный анализ"""
        print("\n" + "="*80)
        print("🚀 WEEKLY ML ANALYSIS STARTING")
        print("="*80)
        
        self.load_data()
        
        if self.trades_df.empty and self.decisions_df.empty:
            print("\n❌ No data collected yet!")
            print("   Bot needs to run for at least a few days to collect data.")
            return None
        
        recommendations = self.generate_recommendations()
        
        print("\n" + "="*80)
        print("✅ ANALYSIS COMPLETE!")
        print("="*80)
        
        return recommendations

# Для прямого запуска
if __name__ == '__main__':
    analyzer = WeeklyAnalyzer()
    analyzer.run_full_analysis()
