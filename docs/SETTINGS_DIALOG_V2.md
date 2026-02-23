# Settings Dialog V2 - Документация

## Обзор

Модальные диалоги настроек для GUI V2 BAZA Trading Bot.

**Ключевые изменения:**
- ✅ Модальные Toplevel окна (transient + grab_set)
- ✅ Без открытия редакторов (subprocess.run/os.startfile убраны)
- ✅ Автозагрузка значений из YAML
- ✅ Автосохранение в YAML файлы
- ✅ Кнопки Save/Cancel/Reset работают

## Структура

### 1. SettingsDialog
Главное окно настроек с 5 вкладками:

#### Trading Tab
- Trading Enabled (bool)
- Trading Mode (auto/semi-auto/manual)
- Fixed Lot Size (0.01-10.0)
- Default SL/TP (pips)
- Trailing Stop settings (enabled, activation %, step %)

#### Risk Tab
- Risk % per Trade (0.1-5.0)
- Max Daily Loss/Profit ($)
- Max Open Positions (1-10)
- Max Trades per Hour/Day
- Max Losses in Row (0=off)
- Max Spread (pips)
- Stop Loss Protection (consecutive stops, cooldown)
- Profit Protection (consecutive wins, cooldown)

#### AI Tab
- AI Enabled (bool)
- GPT Model (gpt-4o/gpt-4-turbo/gpt-4/gpt-3.5-turbo)
- Temperature (0.0-1.0)
- Min Confidence % (50-95)
- Analysis Interval (15-240 min)
- API Timeout (10-120 sec)
- Force JSON Response (bool)
- Block Night Trading (bool)
- Block Weekend Trading (bool)
- Signal TTL (5-120 min)
- Auto Re-query on Expire (bool)

#### Logging Tab
- Log Level (DEBUG/INFO/WARNING/ERROR)
- Auto-save Logs (bool)
- Export Path (str)

#### Advanced Tab
- Adaptive Lot Size (bool)
- Base Lot (0.01-1.0)
- Max Lot (0.01-5.0)
- Lookback Trades (5-50)

### 2. MT5SettingsDialog
Окно настроек MT5:

**Поля:**
- Login (int/str)
- Password (str, show='*')
- Server (str)
- Terminal Path (optional, str)

**Кнопки:**
- Test Connection - проверяет подключение к MT5
- Save - сохраняет в config/mt5.yaml и .env
- Cancel - закрывает без сохранения

## Использование

### Открыть Settings
```python
from src.gui.dialogs_v2 import SettingsDialog

def on_save(data):
    print("Settings saved:", data)
    # Reload configs

SettingsDialog(root, title="Settings", on_save=on_save)
```

### Открыть MT5 Settings
```python
from src.gui.dialogs_v2 import MT5SettingsDialog

def on_save(data):
    print("MT5 settings saved:", data)

def on_test():
    print("Testing connection...")

MT5SettingsDialog(root, title="MT5 Settings", 
                  on_save=on_save, on_test=on_test)
```

## CONFIG_SCHEMA

Схема всех настроек с типами, дефолтами, табами, лимитами:

```python
CONFIG_SCHEMA = {
    "key": {
        "type": bool|int|float|str,
        "default": value,
        "tab": "Trading|Risk|AI|Logging|Advanced",
        "label": "Display Name",
        "min": min_value,      # optional
        "max": max_value,      # optional
        "options": [...]       # для dropdown (str type)
    }
}
```

## Формат данных

### Save callback получает dict:
```python
{
    "trading_enabled": True,
    "fixed_lot_size": 0.01,
    "default_sl_pips": 40,
    "ai_enabled": True,
    "ai_model": "gpt-4o",
    ...
}
```

### Сохранение в YAML:
- `config/trading.yaml` - trading, risk, trailing_stop, protections, v5
- `config/ai.yaml` - ai_enabled, market_analyst settings
- `config/mt5.yaml` - MT5 connection credentials
- `.env` - MT5_LOGIN, MT5_PASSWORD, MT5_SERVER

## Модальность

Окна модальные - блокируют основное окно:

```python
self.transient(parent)      # Окно поверх родителя
self.grab_set()             # Захват фокуса (modal)
self.protocol("WM_DELETE_WINDOW", self._cancel)  # Обработка закрытия
```

При закрытии:
```python
def _close(self):
    try:
        self.grab_release()  # Освободить фокус
    except:
        pass
    self.destroy()
```

## Центрирование

Окно автоматически центрируется относительно родителя:

```python
w, h = 650, 600  # размер окна
x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
self.geometry(f"{w}x{h}+{x}+{y}")
```

## Тестирование

### Checklist:
1. ✅ Settings открывается модально
2. ✅ MT5 Settings НЕ открывает редактор/файлы
3. ✅ Все поля из GUI v1 присутствуют (основные ~80%)
4. ✅ Save реально записывает в YAML
5. ✅ Cancel ничего не меняет
6. ✅ Reset устанавливает дефолты
7. ✅ Пароль MT5 скрыт (show='*')
8. ✅ Test Connection работает
9. ✅ После закрытия фокус возвращается (grab_release)
10. ✅ Current Settings обновляется после Save

## Что не включено

**Специфические настройки инструментов** (редактируются вручную в YAML):
- Manual Overrides для XAUUSD (sl_dollars, tp_dollars, fixed_lot)
- Manual Overrides для EURUSD (sl_pips, tp_pips, fixed_lot)
- Instruments config (XAUUSD/EURUSD enabled, trading_enabled, analysis_enabled)
- Trading Hours (start/end времена)
- Max trades per symbol
- Commission per lot

**Причина:** Эти настройки редко меняются и требуют точной настройки для каждого инструмента. Проще редактировать в `config/ai.yaml` вручную.

## Известные ограничения

1. **Не все поля проверяются на валидность** - можно ввести некорректные значения
2. **Нет предпросмотра изменений** - только Save/Cancel
3. **Требуется перезапуск бота** после изменения некоторых настроек (AI model, trading hours)

## Будущие улучшения

- [ ] Validation для всех полей (min/max/regex)
- [ ] Preview изменений перед Save
- [ ] Hot reload конфигов без перезапуска
- [ ] Tooltips с подсказками для каждого поля
- [ ] History изменений настроек
- [ ] Export/Import конфигов
