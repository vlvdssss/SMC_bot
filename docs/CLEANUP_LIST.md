# 🗑️ Файлы для удаления

## Старые/Бэкап файлы (можно удалить)

### В корне проекта:
- `test_trader.py` - старый тестовый файл
- `test_livetrader_gpt.py` - старый тестовый файл
- `test_gui.py` - старый тестовый файл
- `test_gpt_filter.py` - старый тестовый файл
- `final_test.py` - старый тестовый файл

### В src/:
- `src/live/live_trader_old.py` - старая версия (есть актуальная live_trader.py)
- `src/backtest/backtester_backup.py` - бэкап (есть актуальная backtester.py)

### В scripts/:
- `scripts/test_ai_dynamic.py` - тестовый
- `scripts/test_ai_init.py` - тестовый
- `scripts/test_display_ai_ui.py` - тестовый
- `scripts/test_manual_predict.py` - тестовый

## Команды для удаления

```powershell
# Удалить тестовые файлы из корня
Remove-Item test_trader.py, test_livetrader_gpt.py, test_gui.py, test_gpt_filter.py, final_test.py

# Удалить старые версии
Remove-Item src\live\live_trader_old.py
Remove-Item src\backtest\backtester_backup.py

# Удалить тестовые скрипты
Remove-Item scripts\test_*.py
```

## ⚠️ НЕ УДАЛЯТЬ (важные файлы):

- `train_ml_model.py` - для обучения ML модели
- `build_exe.py` - для сборки exe
- `generate_key.py` - для генерации лицензий
- Все файлы в `src/` кроме упомянутых выше
