# BAZA Trading Bot V2 - Modern Professional UI

## 🚀 Что нового

### Полная переработка интерфейса
- ✅ **ttkbootstrap** - современная темная тема в стиле TradingView/MT5
- ✅ **Grid Layout** - правильная структура (Status Bar + Left Panel + Tabs)
- ✅ **Live Updates** - все данные обновляются в реальном времени
- ✅ **Non-blocking** - GUI не замораживается во время операций
- ✅ **Secret Sanitizer** - автоматическое скрытие API keys, tokens, passwords
- ✅ **Professional Design** - 8px spacing, цветовая схема, hover states

---

## 📋 Структура интерфейса

### **Status Bar (верхняя панель)**
- 🟢/🔴 MT5 Connection Status (обновление каждую 1 сек)
- 💰 XAUUSD Live Price
- 📊 Trading Status (ON/OFF)
- 🤖 AI Model (GPT-4o)
- 🔴 LIVE Indicator
- ⏰ Current Time

### **Left Control Panel (360px)**

#### 1. Control Section
- ▶️ **START BOT** - запуск бота через bot_manager
- ⏸️ **PAUSE** - пауза торговли
- 🚀 **Force AI Analysis** - принудительный анализ
- 🔓 **Reset Protection** - сброс защиты

#### 2. Account Statistics
- 💰 **Balance** (live обновление каждые 3 сек)
- 📈 **Today P&L** (цветной: зелёный/красный)
- 📊 **Total P&L** (цветной: зелёный/красный)
- 📈 **Trades Today**
- 🎯 **Winrate %**

#### 3. Current Settings
- Risk %
- Trading Status
- AI Model
- Mode

#### 4. Quick Navigation
- ⚙️ **Settings** - открывает полный SettingsDialog
- 🔧 **MT5 Settings** - открывает mt5.yaml
- 🧪 **Test GPT** - тест подключения к GPT

### **Main Tabs (центральная область)**

---

## 📝 Tab 1: Logs

### Features:
- ✅ **5 фильтров**: System / Trading / GPT / Risk / MT5
- ✅ **Цветная подсветка**: INFO (белый), WARN (жёлтый), ERROR (красный), GPT (синий), TRADE (зелёный)
- ✅ **Secret Sanitizer**: Автоматически скрывает:
  - API keys (sk-...)
  - Telegram tokens
  - MT5 passwords/logins
- ✅ **Поиск**: Search with highlighting (Next/Prev)
- ✅ **Export**: Save logs to .txt file
- ✅ **Copy**: Copy to clipboard
- ✅ **Autoscroll**: Toggle auto-scroll
- ✅ **Auto-limit**: 500 lines visible, 1000 in memory
- ✅ **Live capture**: Все логи бота автоматически попадают в GUI

### Shortcuts:
- Фильтры работают в реальном времени
- Поиск подсвечивает все совпадения
- Экспорт сохраняет даже скрытые логи

---

## 🤖 Tab 2: AI Decision

### Features:
- 📊 **Last Signal Card**: BUY/SELL/HOLD с цветной индикацией
- 🎯 **Confidence Level**: Уверенность GPT в сигнале (%)
- 💬 **Recommendation**: Текстовая рекомендация от AI
- 📜 **Recent Analysis**: Скроллируемая история анализов
- 🔄 **Refresh Button**: Принудительный запуск анализа

### Update Frequency:
- Обновление каждые 10 секунд
- Показывает последний анализ от scheduler
- Timestamp последнего сигнала

---

## 📊 Tab 3: Positions (Live)

### Features:
- 📋 **Treeview Table** с колонками:
  - Ticket
  - Symbol
  - Type (BUY/SELL)
  - Lots
  - Entry Price
  - Current Price
  - Stop Loss
  - Take Profit
  - P&L $ (цветной: зелёный/красный)
  - Open Time

### Actions:
- 🔄 **Refresh** - ручное обновление
- ❌ **Close All** - закрыть все позиции
- **Right-click menu**:
  - Close Position
  - Modify SL/TP

### Update Frequency:
- Автообновление каждые 5 секунд
- Цветная индикация P&L
- Показывает позиции из MT5 в реальном времени

---

## 📈 Tab 4: Orders (History)

### Features:
- 📋 **Treeview Table** с колонками:
  - Ticket
  - Time
  - Symbol
  - Type
  - Lots
  - Entry Price
  - Exit Price
  - SL
  - TP
  - P&L $
  - Duration

### Filters:
- **Period**: Today / Last 7 days / Last 30 days / All
- **Result**: All / Wins / Losses
- **Symbol**: All / XAUUSD / EURUSD / GBPUSD

### Statistics:
- Total Trades
- Wins / Losses
- Winrate %
- Цветная индикация (зелёный - win, красный - loss)

### Update Frequency:
- Автообновление каждые 5 секунд
- Фильтры применяются мгновенно

---

## 🛡️ Tab 5: Risk Management

### Sections:

#### 1. Daily Limits
- Max Daily Loss: $100 (конфигурируемо)
- Current Loss: $X (live)
- Progress Bar (визуализация)
- Max Daily Profit: $200 (конфигурируемо)
- Current Profit: $X (live)
- Progress Bar

#### 2. Position Limits
- Max Open Positions: 3
- Current Open: X (live)
- Max Duration: 24h

#### 3. Session Limits
- Max Trades/Day: 10
- Trades Today: X (live)
- Max Trades/Hour: 3
- Trades This Hour: X (live)
- Max Losses in Row: 3
- Current Streak: X (live)

#### 4. Cooldowns & Risk
- Cooldown After Loss: 5 min
- Cooldown After Win: 2 min
- Max Risk per Trade: 2.0%
- Max Total Risk: 6.0%
- Max Lot Size: 0.50
- Min Balance Protection: $50

### Actions:
- 🔄 **Refresh** - обновить лимиты
- 🔓 **Reset Limits** - сбросить защиту

### Data Source:
- Читает из `config/trading.yaml`
- Live значения из `bot_manager.stats`
- Обновление вместе со статистикой (каждые 3 сек)

---

## ⚙️ Технические детали

### Архитектура:
- **Status Bar**: Fixed height 50px, grid row 0
- **Left Panel**: Fixed width 360px, grid column 0
- **Main Tabs**: Expandable, grid column 1
- **Layout**: 100% grid, no pack() mixing

### Update Loops:
1. **Queue Processing**: 100ms (логи, события)
2. **MT5 Data**: 1 sec (connection, price)
3. **Statistics**: 3 sec (balance, P&L, trades)
4. **Positions/Orders**: 5 sec (открытые позиции, история)
5. **AI Data**: 10 sec (последний анализ)

### Threading:
- Все обновления через `Queue` → `after()`
- Нет прямых вызовов GUI из worker threads
- Non-blocking UI

### Color Scheme:
```python
BG_DARK = '#0d1117'       # Main background
BG_PANEL = '#161b22'      # Panels
BG_CARD = '#21262d'       # Cards
BG_HOVER = '#30363d'      # Hover state
BORDER = '#30363d'
TEXT_PRIMARY = '#c9d1d9'
TEXT_SECONDARY = '#8b949e'
TEXT_MUTED = '#6e7681'
SUCCESS = '#3fb950'       # Green
ERROR = '#f85149'         # Red
WARNING = '#d29922'       # Yellow
INFO = '#58a6ff'          # Blue
ACCENT = '#1f6feb'        # Primary blue
BUY = '#26a69a'          # Teal
SELL = '#ef5350'         # Red
```

---

## 🚀 Запуск

### Способ 1: PowerShell скрипт
```powershell
.\run_gui_v2.ps1
```

### Способ 2: Прямой запуск
```powershell
& "C:\Users\kamsa\OneDrive\Рабочий стол\bobi\.venv\Scripts\python.exe" src\gui\app_v2.py
```

### Способ 3: Из активированного venv
```powershell
& ..\\.venv\Scripts\Activate.ps1
python src\gui\app_v2.py
```

---

## 📦 Требования

### Python пакеты:
- `ttkbootstrap` - современные виджеты (установлен ✅)
- `MetaTrader5` - подключение к MT5
- `openai` - GPT API
- `pyyaml` - конфигурация
- Все остальные из `requirements.txt`

### Конфигурация:
- `config/trading.yaml` - риск-менеджмент
- `config/ai.yaml` - настройки GPT
- `config/mt5.yaml` - подключение к MT5
- `credentials.yaml` - API keys (не в git)

---

## 🎨 Сравнение с V1

| Feature | Old GUI (app.py) | New GUI V2 (app_v2.py) |
|---------|------------------|------------------------|
| Theme | CustomTkinter | ttkbootstrap darkly |
| Layout | pack() | grid() |
| Update | Blocking | Non-blocking (Queue) |
| Positions | Text logs only | Treeview table |
| Orders | No history | Full history + filters |
| Risk | Basic display | 4 sections with limits |
| AI | Minimal | Full decision tab |
| Logs | Basic | 5 filters + sanitizer |
| Secret Safety | No | Full sanitizer |
| Live Updates | Partial | All data live |
| Performance | Can freeze | Always responsive |

---

## 🐛 Troubleshooting

### GUI не запускается:
1. Проверь установку ttkbootstrap: `pip list | grep ttkbootstrap`
2. Проверь виртуальное окружение активно
3. Проверь логи в `logs/baza_YYYYMMDD.log`

### Не обновляются данные:
1. Проверь MT5 подключение (статус бар)
2. Проверь bot_manager запущен (START BOT)
3. Проверь логи в Logs tab

### Тормозит:
1. Уменьши частоту обновлений в коде (after() значения)
2. Проверь антивирус не блокирует
3. Закрой другие MT5 окна

---

## 🔮 Future Features (Optional)

- [ ] Charts Tab с matplotlib (Equity, P&L)
- [ ] Dark/Light theme toggle
- [ ] Multi-monitor support
- [ ] Customizable update frequencies
- [ ] Trade notifications (desktop)
- [ ] Export reports (PDF/Excel)
- [ ] Position notes/tags
- [ ] Trade replay mode
- [ ] Performance analytics

---

## 👨‍💻 Development

### Код структурирован:
- `StatusBar` class - верхняя панель
- `ControlPanel` class - левая панель
- `BazaAppV2` class - основное приложение
- `Theme` class - цветовая схема

### Добавление нового таба:
1. Создай метод `_create_xxx_tab(self)`
2. Добавь в `_create_tabs()`
3. Верни `ttk.Frame`
4. Добавь обновление в `_update_xxx_loop()` если нужно

---

## ✅ TODO List Status

- [x] Интеграция с bot_manager + live обновления
- [x] Этап 2: Фильтры логов + Secret sanitizer
- [x] Settings dialog integration
- [x] Этап 3: Positions tab с Treeview
- [x] Этап 3: Orders history tab
- [x] Этап 3: Risk tab (limits, counters)
- [x] AI Decision tab (signals, recommendations)
- [ ] Charts (optional - not critical)

**Все критические функции реализованы! 🎉**

---

## 📞 Support

При проблемах:
1. Проверь `logs/baza_YYYYMMDD.log`
2. Проверь Logs tab в GUI
3. Проверь MT5 терминал запущен
4. Проверь интернет соединение (GPT API)

---

**Made with ❤️ by BAZA Team**
**Version: 2.0.0**
**Date: 2026-02-17**
