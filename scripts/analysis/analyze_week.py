"""
Weekly ML Analysis Runner

Запускает анализ торговых данных за неделю и создает рекомендации.

Usage:
    python analyze_week.py

Результат будет сохранен в data/ml_training/recommendations_YYYYMMDD_HHMMSS.json
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в Python path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from src.ml.weekly_analyzer import WeeklyAnalyzer

def main():
    print("="*80)
    print("📊 BAZA Trading Bot - Weekly Performance Analysis")
    print("="*80)
    print()
    
    # Создаем анализатор
    print("Initializing analyzer...")
    analyzer = WeeklyAnalyzer()
    
    # Запускаем полный анализ
    print("Running analysis...")
    print()
    
    try:
        recommendations = analyzer.run_full_analysis()
        
        if recommendations:
            print()
            print("="*80)
            print("✅ Analysis Complete!")
            print("="*80)
            print()
            print(f"Recommendations saved to: {recommendations}")
            print()
            print("Review the JSON file for detailed insights on:")
            print("  - Best trading hours")
            print("  - Hours to avoid")
            print("  - Optimal market conditions (ATR, RSI, Trend)")
            print("  - Best trading session (ASIA/EUROPE/US)")
            print("  - AI signal quality metrics")
            print()
        else:
            print()
            print("="*80)
            print("⚠️ Analysis Failed")
            print("="*80)
            print()
            print("Check the logs for errors.")
            print("Make sure data files exist in data/ml_training/")
            print()
    
    except Exception as e:
        print()
        print("="*80)
        print("❌ Error During Analysis")
        print("="*80)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    
    # Ждем нажатия Enter перед закрытием (чтобы увидеть результат)
    print()
    input("Press Enter to exit...")
    
    sys.exit(exit_code)
