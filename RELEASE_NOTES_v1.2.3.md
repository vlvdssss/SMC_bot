# BAZA Trading Bot v1.2.3 - Финальное исправление Settings Dialog

## 🐛 Критические исправления

### Settings Dialog
- **ИСПРАВЛЕНО**: AttributeError при сохранении настроек (trading_mode, max_positions)
- **ИСПРАВЛЕНО**: AttributeError при использовании полей (default_lot)
- Удалены несуществующие поля, которые вызывали крэши при нажатии "Apply & Restart"
- Теперь Settings Dialog работает полностью стабильно

### AI Market Analyst
- **ИСПРАВЛЕНО**: AttributeError 'direction' → исправлено на 'type'
- Теперь AI сигналы отображаются корректно

### Пути к файлам в EXE
- **ИСПРАВЛЕНО**: Добавлены get_data_path() хелперы в 4 файлах
- Исправлена работа с файлами bot_stats.json, trades_history.json, config.json
- EXE теперь корректно работает с путями к данным

### Форматирование дат в EXE
- **ИСПРАВЛЕНО**: datetime.strftime() на строках
- Добавлен format_datetime() helper для совместимости с EXE

## 📋 Полный список изменений

### v1.2.3 (16.01.2026)
- 🐛 Удалены несуществующие поля trading_mode и max_positions из Settings Dialog
- 🐛 Исправлена ошибка AttributeError при сохранении настроек
- ✅ Финальная стабильная версия Settings Dialog

### v1.2.2 (16.01.2026)
- 🐛 Исправлена критическая ошибка Settings Dialog (AttributeError: default_lot)
- 🐛 Исправлены field names: max_lot_size → max_lot, stop_loss → default_sl, take_profit → default_tp

### v1.2.1 (16.01.2026)
- 🐛 Исправлена ошибка AI Market Analyst (signal.direction → signal.type)
- 🐛 Исправлены datetime ошибки в EXE (format_datetime helper)
- 🐛 Исправлены пути к файлам в EXE (get_data_path helpers)

### v1.2.0
- 📈 Новая вкладка Instruments - раздельные настройки для EURUSD и XAUUSD
- 💶 Добавлена полная поддержка EURUSD (анализ + торговля)
- 🎛️ Раздельный контроль анализа и торговли для каждого инструмента
- 🔄 Apply & Restart - автоматический перезапуск бота после изменения настроек
- 📊 Синхронизация P&L с MT5 при запуске бота
- 💰 Total P&L и Today P&L из единого источника (bot_stats.json)
- 🌙 Автоматический сброс Today P&L в полночь
- 🔧 Исправлены ошибки Colors в настройках
- ⚡ Автоматическая загрузка пропущенных сделок из MT5

## 📦 Установка

1. Скачайте `BAZA_TradingBot.exe` (206 MB)
2. Запустите файл
3. Настройте MT5 credentials в Settings
4. Начните торговлю!

## ⚙️ Системные требования

- Windows 10/11
- MetaTrader 5
- 512 MB свободного места
- Интернет-соединение

## 🔒 Безопасность

- EXE подписан и безопасен
- Все учётные данные шифруются
- Исходный код доступен в репозитории

## 📝 Примечания

Это финальная стабильная версия с полностью рабочим Settings Dialog. Все известные критические баги исправлены.

## 🐛 Известные проблемы

- P&L display может показывать $0.00 в некоторых случаях (будет исправлено в v1.3.0)

---

**Full Changelog**: https://github.com/vlvdssss/SMC_bot/compare/v1.2.0...v1.2.3
