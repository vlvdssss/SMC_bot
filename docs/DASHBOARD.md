# 📊 BAZA Trading Dashboard

## Описание

Веб-интерфейс для мониторинга торгового бота BAZA в реальном времени. Построен на Streamlit с интерактивными графиками Plotly.

## Возможности

### 📈 Live Trading Mode
- **Реалтайм метрики**: общее количество торгов, прибыль, винрейт, баланс
- **История торгов**: таблица с последними 20 сделками
- **Автообновление**: обновление данных каждые 30 секунд
- **Детали сделок**: символ, направление, время открытия/закрытия, прибыль, пипсы

### 🔙 Backtest Mode
- **Выбор данных**: выбор символа (XAUUSD/EURUSD) и года (2023-2025)
- **Детальные метрики**: 
  - Общее количество торгов
  - Винрейт (%)
  - Общая прибыль
  - Profit Factor
  - Средняя прибыль/убыток
- **Интерактивные графики**:
  - График эквити с заливкой
  - Распределение прибыли/убытка (гистограмма)
  - Месячная производительность (барчарт)
- **Таблица торгов**: полная история всех сделок бэктеста

## Установка

```bash
# Зависимости уже установлены в pyproject.toml
pip install streamlit plotly
```

## Запуск

```bash
streamlit run dashboard.py
```

Dashboard откроется автоматически в браузере по адресу `http://localhost:8501`

## Структура

```python
class BAZADashboard:
    """Главный класс дашборда"""
    
    def load_bot_stats() -> dict
        """Загрузить статистику бота из data/bot_stats.json"""
    
    def load_trades_history() -> pd.DataFrame
        """Загрузить историю торгов из data/trades_history.json"""
    
    def load_backtest_results(symbol: str, year: str) -> tuple
        """Загрузить результаты бэктеста (equity_df, trades_df)"""
    
    def calculate_metrics(trades_df: pd.DataFrame) -> dict
        """Рассчитать торговые метрики"""
    
    def plot_equity_curve(equity_df: pd.DataFrame) -> go.Figure
        """Построить график эквити"""
    
    def plot_trades_distribution(trades_df: pd.DataFrame) -> go.Figure
        """Построить распределение прибыли/убытка"""
    
    def plot_monthly_performance(trades_df: pd.DataFrame) -> go.Figure
        """Построить месячную производительность"""
```

## Используемые данные

### Live Trading
- `data/bot_stats.json` - статистика бота (баланс, equity и т.д.)
- `data/trades_history.json` - история торгов

### Backtest Results
- `results/{symbol}/backtest_{year}-01-01_{year}-12-31_equity.csv` - эквити
- `results/{symbol}/backtest_{year}-01-01_{year}-12-31_trades.csv` - торги

## Метрики

### Базовые метрики
- **Total Trades** - общее количество сделок
- **Win Rate** - процент прибыльных сделок
- **Total Profit** - общая прибыль в $
- **Balance** - текущий баланс счета

### Продвинутые метрики (Backtest)
- **Profit Factor** - отношение прибыли к убыткам
- **Average Win** - средняя прибыль на сделку
- **Average Loss** - средний убыток на сделку

## Графики

### 1. Equity Curve (График эквити)
- Линейный график с заливкой
- Показывает рост/падение капитала во времени
- Интерактивный hover с точными значениями

### 2. Trades Distribution (Распределение торгов)
- Гистограмма прибыльных (зеленые) и убыточных (красные) сделок
- Overlay mode для наглядности
- Показывает частоту прибылей/убытков

### 3. Monthly Performance (Месячная производительность)
- Барчарт с цветом по прибыли (зеленый/красный)
- Группировка по месяцам
- Быстрая оценка динамики

## Настройки

### Боковая панель
- **Режим просмотра**: Live Trading / Backtest Results
- **Символ** (backtest): XAUUSD / EURUSD
- **Год** (backtest): 2023 / 2024 / 2025
- **Автообновление** (live): чекбокс для включения

### Layout
- **Wide mode**: растянутый на весь экран
- **Dark theme**: темная тема Plotly
- **Responsive**: адаптивная сетка колонок

## Примеры использования

### Запуск для мониторинга live торговли

```bash
# 1. Запустите бота
python main.py

# 2. В другом терминале запустите dashboard
streamlit run dashboard.py

# 3. Включите автообновление в sidebar
```

### Анализ результатов бэктеста

```bash
# 1. Запустите бэктест
python main.py --mode backtest --symbol XAUUSD --timeframe H1

# 2. Запустите dashboard
streamlit run dashboard.py

# 3. Выберите "Backtest Results", символ и год
```

## Горячие клавиши

- `R` - перезагрузить приложение
- `C` - открыть настройки
- `S` - скриншот
- `?` - помощь

## Кастомизация

### Изменить тему

Создайте `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#00d4ff"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#262730"
textColor = "#fafafa"
font = "sans serif"
```

### Добавить свои графики

```python
def plot_custom_chart(self, data):
    """Ваш кастомный график"""
    fig = go.Figure()
    # ... ваш код ...
    return fig

# В main():
custom_fig = dashboard.plot_custom_chart(data)
st.plotly_chart(custom_fig, use_container_width=True)
```

### Добавить новые метрики

```python
def calculate_custom_metrics(self, trades_df):
    """Ваши кастомные метрики"""
    sharpe_ratio = ...
    max_drawdown = ...
    
    return {
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown
    }
```

## Troubleshooting

### Dashboard не запускается
```bash
# Убедитесь что streamlit установлен
pip install streamlit plotly

# Проверьте версию Python (требуется 3.9+)
python --version
```

### Нет данных
```bash
# Убедитесь что бот запущен и создает файлы
ls data/bot_stats.json
ls data/trades_history.json

# Или запустите бэктест
python main.py --mode backtest
```

### Графики не отображаются
```bash
# Проверьте формат данных
python -c "import pandas as pd; print(pd.read_csv('results/xauusd/backtest_2023-01-01_2023-12-31_equity.csv').head())"

# Убедитесь что есть колонки timestamp и equity
```

## Performance

- **Скорость загрузки**: ~1-2 секунды
- **Потребление RAM**: ~150-200 MB
- **Автообновление**: каждые 30 секунд
- **Рекомендуемый браузер**: Chrome, Firefox

## Roadmap

- [ ] Real-time WebSocket обновления
- [ ] Сравнение нескольких бэктестов
- [ ] Экспорт отчетов в PDF
- [ ] Уведомления о важных событиях
- [ ] Интеграция с Telegram
- [ ] Dark/Light тема toggle
- [ ] Mobile responsive дизайн

## См. также

- [API Documentation](API.md)
- [Monitoring System](MONITORING.md)
- [Telegram Setup](TELEGRAM_SETUP.md)
