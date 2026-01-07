# Исправление: Баланс в Telegram уведомлениях

## 🐛 Проблема

При запуске и остановке бота в Telegram уведомлениях отображался баланс **100.00**, хотя реальный баланс на MT5 счете был **122.95**.

## 🔍 Причина

`BotManager` инициализировал статистику с дефолтным значением:
```python
self.stats = {
    'balance': 100.0,  # Статическое значение
    'total_pnl': 0.0,
    ...
}
```

Это значение никогда не обновлялось из реального MT5 счета, поэтому при отправке уведомлений использовались неверные данные.

## ✅ Решение

### 1. Добавлен метод получения реального баланса

**Файл:** `src/core/bot_manager.py`

```python
def set_mt5_manager(self, mt5_manager):
    """Установка MT5 Manager для получения реальной статистики."""
    self.mt5_manager = mt5_manager
    logger.info("MT5 Manager connected to BotManager")

def _update_stats_from_mt5(self):
    """Обновление статистики из MT5."""
    if self.mt5_manager and self.mt5_manager.is_connected():
        try:
            account_info = self.mt5_manager.get_account_info()
            if account_info:
                self.stats['balance'] = account_info.get('balance', self.stats['balance'])
                self.stats['equity'] = account_info.get('equity', account_info.get('balance', 0))
                logger.info(f"Stats updated from MT5: balance=${self.stats['balance']:.2f}")
                return True
        except Exception as e:
            logger.error(f"Failed to update stats from MT5: {e}")
    return False
```

### 2. Обновление статистики перед отправкой уведомлений

**При запуске бота:**
```python
# Обновляем статистику из MT5 перед отправкой уведомления
self._update_stats_from_mt5()

# Telegram уведомление
if self.telegram and self.notify_config.get('startup', True):
    instruments = list(self.stats.get('instruments', ['XAUUSD', 'EURUSD']))
    self.telegram.send_startup(mode=mode.upper(), instruments=instruments)
```

**При остановке бота:**
```python
# Обновляем статистику из MT5 перед отправкой уведомления
self._update_stats_from_mt5()

# Telegram уведомление
if self.telegram and self.notify_config.get('shutdown', True):
    self.telegram.send_shutdown(stats=self.stats)
```

### 3. Передача MT5Manager в BotManager

**Файл:** `src/gui/app.py`

При инициализации MT5:
```python
# Передаем MT5 Manager в BotManager для получения реальной статистики
if self.app_state.mt5_manager and self.bot_manager:
    self.bot_manager.set_mt5_manager(self.app_state.mt5_manager)
    app_logger.info("[OK] MT5 Manager connected to BotManager")
```

При подключении к MT5:
```python
if success:
    # Обновляем связь с BotManager после подключения
    if self.bot_manager:
        self.bot_manager.set_mt5_manager(self.app_state.mt5_manager)
        self.log("[OK] MT5 Manager reconnected to BotManager")
```

## 📊 Теперь работает корректно

### До исправления:
```
🚀 BAZA BOT запущен
💰 Баланс: $100.00  ❌
```

### После исправления:
```
🚀 BAZA BOT запущен
💰 Баланс: $122.95  ✅
```

## 🔄 Процесс работы

1. **Инициализация**: GUI создает `MT5Manager` и передает его в `BotManager`
2. **Подключение**: При подключении к MT5 обновляется связь с `BotManager`
3. **Запуск бота**: Перед отправкой уведомления вызывается `_update_stats_from_mt5()`
4. **Получение баланса**: Метод запрашивает `account_info` из MT5 через `mt5_manager.get_account_info()`
5. **Обновление статистики**: Реальный баланс и equity записываются в `self.stats`
6. **Отправка уведомления**: Telegram получает актуальные данные

## 🧪 Тестирование

1. Подключиться к MT5 счету
2. Проверить реальный баланс (например, 122.95)
3. Запустить бота
4. Проверить Telegram уведомление - должен быть правильный баланс
5. Остановить бота
6. Проверить Telegram уведомление - должен быть актуальный баланс

## 📝 Дополнительно

Этот же механизм можно использовать для:
- Периодических отчетов (каждые 3 часа)
- Дневных отчетов
- Обновления статистики сделок
- Отображения актуального equity

## ✅ Файлы изменены

- `src/core/bot_manager.py` - добавлены методы для работы с MT5Manager
- `src/gui/app.py` - передача MT5Manager в BotManager при инициализации и подключении

## 🚀 Следующие шаги

1. Протестировать на реальном счете
2. Проверить все типы уведомлений (startup, shutdown, reports)
3. Пересобрать EXE с исправлениями
