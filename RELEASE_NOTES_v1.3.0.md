# 🚀 BAZA Trading Bot v1.3.0 - Schedule UI & Stability

**Дата релиза:** 19 января 2026  
**Размер:** ~206 MB  
**Платформа:** Windows 10/11 x64

---

## 🎯 Основные улучшения

### ⏰ NEW: Visual Schedule Tab
Полностью переработанный интерфейс управления расписанием AI анализа:

- **🎨 Time Picker** - визуальный выбор времени с HH:MM spinboxes (00-23 часы, 00-59 минуты)
- **📋 Список времён** - отображение всех запланированных анализов с кнопками удаления
- **⚡ Quick Presets** - быстрые шаблоны:
  * Every Hour - 24 анализа в день (каждый час)
  * Every 2h - 12 анализов в день (каждые 2 часа)
  * Clear All - очистка всего расписания
- **📊 Live Statistics**:
  * Счётчик запланированных времён
  * Следующий анализ (реальное время)
  * Оценка стоимости (~$0.30 за анализ)

**Преимущества:**
- ✅ Нет ошибок ввода (spinboxes вместо текста)
- ✅ Визуальный контроль всех времён
- ✅ Быстрая настройка через presets
- ✅ Прозрачность затрат на API

---

## 🐛 Исправленные баги

### 1. ✅ Settings Dialog Config Loading
**Проблема:** `'SettingsDialog' object has no attribute '_load_ai_config'`  
**Решение:** Использование `self.configs.get('ai.yaml', {})` вместо несуществующего метода  
**Файл:** `src/gui/settings_dialog.py:498`  
**Коммит:** `6412f2c`

### 2. ✅ Color Constants Fix
**Проблема:** `type object 'Colors' has no attribute 'DANGER'`  
**Решение:** Замена `Colors.DANGER` на `Colors.ERROR` (красный `#f85149`)  
**Файлы:** `src/gui/settings_dialog.py:597, 716`  
**Коммит:** `dd9b484`

### 3. ✅ Signal State Format Migration
**Проблема:** `'list' object has no attribute 'get'` при загрузке AI сигналов  
**Решение:** Автоконвертация старого формата (list) в новый (dict) при загрузке  
**Файл:** `src/ai/signal_manager.py:808-818`  
**Коммит:** `dd9b484`

```python
# Backward compatibility: если state это список (старый формат), создаём новый формат
if isinstance(state, list):
    logger.info(f"[AI-Signal] Converting old format (list) to new format (dict)")
    state = {
        "active_signals": state,
        "block_type": "none",
        "signal_history": []
    }
```

### 4. ✅ Unknown Fields Filtering
**Проблема:** `AISignal.__init__() got an unexpected keyword argument 'direction'`  
**Решение:** Фильтрация неизвестных полей при создании сигналов из старых данных  
**Файл:** `src/ai/signal_manager.py:830-843`  
**Коммит:** `919ce4b`

```python
# Список допустимых полей AISignal
valid_fields = {
    'id', 'symbol', 'type', 'entry_price', 'stop_loss', 'take_profit',
    'trigger_time', 'reasoning', 'confidence', 'risk_reward', 
    'created_at', 'expires_at', 'analysis_version', 'status', 
    'triggered_at', 'priority'
}

# Фильтруем только допустимые поля
filtered_data = {k: v for k, v in signal_data.items() if k in valid_fields}
signal = AISignal(**filtered_data)
```

---

## 📊 Статистика тестирования

### Комплексный тест системы (test_all_components.py)
```
Всего тестов: 11
✅ Пройдено: 10 (90.9%)
❌ Провалено: 1 (Telegram disabled - это норма)

Детальные результаты:
✅ config_MT5          - OK (812 bytes)
✅ config_AI           - OK (1283 bytes)
✅ config_Portfolio    - OK (1161 bytes)
✅ config_Telegram     - OK (225 bytes)
✅ config_Instruments  - OK (1026 bytes)
✅ mt5_manager         - OK (подключение успешно)
✅ bot_manager         - OK (70 сделок, 30% win rate)
✅ live_trader         - OK (все компоненты на месте)
❌ telegram            - DISABLED (нет токена/chat_id)
✅ gui_components      - OK (все диалоги найдены)
✅ ai_components       - OK (market analyst, signal manager)
```

### Проверка критических узлов
- ✅ **risk_manager.py** - validate_signal(), can_open_position()
- ✅ **executor.py** - execute_signal(), position lifecycle
- ✅ **signal_manager.py** - process_analysis(), get_active_signals()
- ✅ **live_trader.py** - check_signals(), process_signal(), execute_trade()

**Все основные функции работают корректно!**

---

## 🔧 Технические детали

### Изменённые файлы
```
src/gui/settings_dialog.py    - Schedule Tab UI (257 новых строк)
src/ai/signal_manager.py       - Backward compatibility + filtering
version.py                     - APP_VERSION = "1.3.0"
version.json                   - Changelog v1.3.0
```

### Git коммиты
```
919ce4b - fix: Filter unknown fields when loading old signals
dd9b484 - fix: Add backward compatibility for old signal format + Colors.ERROR
6412f2c - fix: Use self.configs instead of non-existent _load_ai_config method
12747e7 - feat: Add visual Schedule Tab to Settings dialog
```

---

## 📥 Установка и обновление

### Новая установка
1. Скачать `BAZA_TradingBot.exe` (206 MB)
2. Создать папку (например, `C:\BAZA`)
3. Запустить EXE - автоматически создаст config/, data/, logs/
4. Настроить MT5 credentials (Settings → MT5)
5. Добавить OpenAI API key (Settings → AI → API Key)

### Обновление с v1.2.8
**ВАЖНО:** При первом запуске v1.3.0 автоматически произойдёт:
1. Миграция формата AI сигналов (list → dict)
2. Фильтрация старых полей (direction и др.)
3. Сохранение в новом формате

Ваши настройки и история сохранятся!

---

## 🎯 Что дальше?

### v1.3.1 (планируется)
- 📊 Live график в Analysis Tab
- 🔔 Настройка Telegram уведомлений в GUI
- 📈 Расширенная статистика AI сигналов

---

## 📝 Полный Changelog

```
v1.3.0 (2026-01-19)
⏰ NEW: Visual Schedule Tab - графический интерфейс управления расписанием AI анализа
🎯 UI: Time Picker с HH:MM spinboxes для точного выбора времени
⚡ QUICK PRESETS: Every Hour (24 раза), Every 2h (12 раз), Clear All
📊 LIVE STATS: Счётчик времён, следующий анализ, оценка стоимости (~$0.30/анализ)
🐛 BUGFIX: Исправлена загрузка конфигурации в Schedule Tab
🎨 BUGFIX: Исправлены цветовые константы кнопок (Colors.ERROR)
🔄 BUGFIX: Автоконвертация старого формата AI сигналов (list → dict)
🧹 BUGFIX: Фильтрация старых полей при загрузке сигналов (direction и др.)

v1.2.8 (2026-01-19)
🧹 NEW: Автоматическая очистка старых AI сигналов (>36 часов)
🗑️ NEW: Автоматическая очистка старых логов (>7д 20ч)
🐛 BUGFIX: API ключ теперь загружается из .env в Settings
```

---

## 💬 Поддержка

**Telegram:** @your_support  
**GitHub Issues:** https://github.com/vlvdssss/SMC_bot/issues  
**Email:** support@bazabot.com

---

**Made with ❤️ by BAZA Team**
