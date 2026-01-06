"""
BAZA Trading Bot Dashboard

Веб-интерфейс для мониторинга торгового бота в реальном времени.
Запуск: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import json
from datetime import datetime, timedelta
import sys

# Добавляем путь к модулям проекта (родительская директория)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Кэширование для оптимизации загрузки
@st.cache_data(ttl=5)  # Кэш на 5 секунд
def load_cached_stats():
    """Загрузить статистику с кэшированием"""
    stats_file = Path("data/bot_stats.json")
    if stats_file.exists():
        with open(stats_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

@st.cache_data(ttl=5)  # Кэш на 5 секунд
def load_cached_trades():
    """Загрузить торги с кэшированием"""
    trades_file = Path("data/trades_history.json")
    if trades_file.exists():
        with open(trades_file, 'r', encoding='utf-8') as f:
            trades = json.load(f)
            if trades:
                return pd.DataFrame(trades)
    return pd.DataFrame()


class BAZADashboard:
    """Главный класс дашборда BAZA"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.results_dir = Path("results")
        
    def load_bot_stats(self):
        """Загрузить статистику бота"""
        return load_cached_stats()
    
    def load_trades_history(self):
        """Загрузить историю торгов"""
        return load_cached_trades()
    
    def load_backtest_results(self, symbol: str, year: str):
        """Загрузить результаты бэктеста"""
        import glob
        
        # Поддержка Portfolio
        if symbol == "Portfolio":
            folder_name = f"portfolio/{year}"
            file_prefix = "portfolio"
        else:
            folder_name = symbol.lower()
            file_prefix = "backtest"
        
        # Ищем файлы по паттерну (может быть разная конечная дата)
        equity_pattern = str(self.results_dir / folder_name / f"{file_prefix}_{year}-01-01_{year}-*_equity.csv")
        trades_pattern = str(self.results_dir / folder_name / f"{file_prefix}_{year}-01-01_{year}-*_trades.csv")
        
        equity_files = glob.glob(equity_pattern)
        trades_files = glob.glob(trades_pattern)
        
        equity_df = None
        trades_df = None
        
        # Берем последний файл (самый свежий)
        if equity_files:
            equity_file = sorted(equity_files)[-1]
            equity_df = pd.read_csv(equity_file)
            # Поддержка разных названий колонок времени
            if 'time' in equity_df.columns and 'timestamp' not in equity_df.columns:
                equity_df['timestamp'] = pd.to_datetime(equity_df['time'])
            elif 'timestamp' in equity_df.columns:
                equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
        
        if trades_files:
            trades_file = sorted(trades_files)[-1]
            trades_df = pd.read_csv(trades_file)
            if 'open_time' in trades_df.columns:
                trades_df['open_time'] = pd.to_datetime(trades_df['open_time'])
            elif 'entry_time' in trades_df.columns:
                trades_df['open_time'] = pd.to_datetime(trades_df['entry_time'])
            
            if 'close_time' in trades_df.columns:
                trades_df['close_time'] = pd.to_datetime(trades_df['close_time'])
            elif 'exit_time' in trades_df.columns:
                trades_df['close_time'] = pd.to_datetime(trades_df['exit_time'])
        
        return equity_df, trades_df
    
    def calculate_metrics(self, trades_df):
        """Рассчитать торговые метрики"""
        if trades_df is None or trades_df.empty:
            return {}
        
        total_trades = len(trades_df)
        
        # Поддержка разных названий колонки прибыли
        profit_col = 'profit' if 'profit' in trades_df.columns else 'pnl' if 'pnl' in trades_df.columns else None
        
        if profit_col:
            winning_trades = len(trades_df[trades_df[profit_col] > 0])
            losing_trades = len(trades_df[trades_df[profit_col] < 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            total_profit = trades_df[profit_col].sum()
            avg_profit = trades_df[trades_df[profit_col] > 0][profit_col].mean() if winning_trades > 0 else 0
            avg_loss = trades_df[trades_df[profit_col] < 0][profit_col].mean() if losing_trades > 0 else 0
            
            profit_factor = abs(avg_profit * winning_trades / (avg_loss * losing_trades)) if losing_trades > 0 and avg_loss != 0 else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor
            }
        
        return {'total_trades': total_trades}
    
    def plot_equity_curve(self, equity_df):
        """График эквити"""
        if equity_df is None or equity_df.empty:
            return None
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=equity_df['timestamp'],
            y=equity_df['equity'],
            mode='lines',
            name='Эквити',
            line=dict(color='#00d4ff', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 212, 255, 0.1)'
        ))
        
        fig.update_layout(
            title='График эквити',
            xaxis_title='Дата',
            yaxis_title='Эквити ($)',
            hovermode='x unified',
            template='plotly_dark',
            height=500
        )
        
        return fig
    
    def plot_trades_distribution(self, trades_df):
        """График распределения торгов"""
        if trades_df is None or trades_df.empty:
            return None
        
        # Поддержка разных названий колонки прибыли
        profit_col = 'profit' if 'profit' in trades_df.columns else 'pnl' if 'pnl' in trades_df.columns else None
        if not profit_col:
            return None
        
        fig = go.Figure()
        
        # Разделяем прибыльные и убыточные сделки
        winning = trades_df[trades_df[profit_col] > 0][profit_col]
        losing = trades_df[trades_df[profit_col] < 0][profit_col]
        
        fig.add_trace(go.Histogram(
            x=winning,
            name='Прибыльные',
            marker_color='#00ff00',
            opacity=0.7
        ))
        
        fig.add_trace(go.Histogram(
            x=losing,
            name='Убыточные',
            marker_color='#ff0000',
            opacity=0.7
        ))
        
        fig.update_layout(
            title='Распределение прибыли/убытка',
            xaxis_title='Прибыль/Убыток ($)',
            yaxis_title='Количество сделок',
            barmode='overlay',
            template='plotly_dark',
            height=400
        )
        
        return fig
    
    def plot_monthly_performance(self, trades_df):
        """График месячной производительности"""
        if trades_df is None or trades_df.empty:
            return None
        
        # Поддержка разных названий колонок
        time_col = 'close_time' if 'close_time' in trades_df.columns else 'exit_time' if 'exit_time' in trades_df.columns else None
        profit_col = 'profit' if 'profit' in trades_df.columns else 'pnl' if 'pnl' in trades_df.columns else None
        
        if not time_col or not profit_col:
            return None
        
        # Группируем по месяцам
        trades_df['month'] = trades_df[time_col].dt.to_period('M')
        monthly = trades_df.groupby('month')[profit_col].sum().reset_index()
        monthly['month'] = monthly['month'].astype(str)
        
        fig = go.Figure()
        
        colors = ['#00ff00' if p > 0 else '#ff0000' for p in monthly[profit_col]]
        
        fig.add_trace(go.Bar(
            x=monthly['month'],
            y=monthly[profit_col],
            marker_color=colors,
            name='Месячная прибыль'
        ))
        
        fig.update_layout(
            title='Месячная производительность',
            xaxis_title='Месяц',
            yaxis_title='Прибыль ($)',
            template='plotly_dark',
            height=400
        )
        
        return fig


def main():
    """Главная функция дашборда"""
    
    # Настройка страницы
    st.set_page_config(
        page_title="BAZA Trading Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Заголовок
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📊 BAZA Trading Dashboard")
    with col2:
        # Индикатор последнего обновления
        current_time = datetime.now().strftime('%H:%M:%S')
        st.markdown(f"🕐 **{current_time}**")
    
    st.markdown("---")
    
    # Создаем экземпляр дашборда
    dashboard = BAZADashboard()
    
    # Боковая панель
    st.sidebar.title("⚙️ Настройки")
    
    # Выбор режима
    mode = st.sidebar.radio(
        "Режим просмотра",
        ["📈 Live Trading", "🔙 Backtest Results"]
    )
    
    if mode == "📈 Live Trading":
        st.header("Live Trading Stats")
        
        # Добавить индикатор живых обновлений
        col_status1, col_status2, col_status3 = st.columns([2, 1, 1])
        with col_status1:
            st.markdown("### 🟢 Live Trading Mode")
        with col_status2:
            current_time = datetime.now().strftime("%H:%M:%S")
            st.markdown(f"**⏰ {current_time}**")
        with col_status3:
            # Показать статус автообновления
            if 'auto_refresh_enabled' in st.session_state and st.session_state.auto_refresh_enabled:
                st.markdown("**🔄 Auto-refresh ON**")
            else:
                st.markdown("**⏸️ Auto-refresh OFF**")
        
        st.markdown("---")
        
        # Загружаем статистику
        stats = dashboard.load_bot_stats()
        trades_df = dashboard.load_trades_history()
        
        # Метрики в верхней части с отслеживанием изменений
        if 'prev_metrics' not in st.session_state:
            st.session_state.prev_metrics = {}
        
        prev_metrics = st.session_state.prev_metrics
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_trades = len(trades_df) if not trades_df.empty else 0
            prev_trades = prev_metrics.get('total_trades', total_trades)
            delta_trades = total_trades - prev_trades if prev_trades != total_trades else None
            
            st.metric(
                "Всего торгов", 
                total_trades,
                delta=delta_trades if delta_trades else None,
                delta_color="off"
            )
        
        with col2:
            if not trades_df.empty:
                profit_col = 'profit' if 'profit' in trades_df.columns else 'pnl' if 'pnl' in trades_df.columns else None
                if profit_col:
                    total_profit = trades_df[profit_col].sum()
                    prev_profit = prev_metrics.get('total_profit', total_profit)
                    delta_profit = total_profit - prev_profit if prev_profit != total_profit else None
                    
                    st.metric(
                        "Общая прибыль", 
                        f"${total_profit:.2f}",
                        delta=f"${delta_profit:.2f}" if delta_profit else None,
                        delta_color="normal"
                    )
                else:
                    st.metric("Общая прибыль", "$0.00")
            else:
                st.metric("Общая прибыль", "$0.00")
        
        with col3:
            if not trades_df.empty:
                profit_col = 'profit' if 'profit' in trades_df.columns else 'pnl' if 'pnl' in trades_df.columns else None
                if profit_col:
                    winning = len(trades_df[trades_df[profit_col] > 0])
                    win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
                    prev_wr = prev_metrics.get('win_rate', win_rate)
                    delta_wr = win_rate - prev_wr if prev_wr != win_rate else None
                    
                    st.metric(
                        "Винрейт", 
                        f"{win_rate:.1f}%",
                        delta=f"{delta_wr:.1f}%" if delta_wr else None,
                        delta_color="normal"
                    )
                else:
                    st.metric("Винрейт", "0%")
            else:
                st.metric("Винрейт", "0%")
        
        with col4:
            if stats:
                balance = stats.get('balance', 0)
                prev_balance = prev_metrics.get('balance', balance)
                delta_balance = balance - prev_balance if prev_balance != balance else None
                
                st.metric(
                    "Баланс", 
                    f"${balance:.2f}",
                    delta=f"${delta_balance:.2f}" if delta_balance else None,
                    delta_color="normal"
                )
            else:
                st.metric("Баланс", "$0.00")
        
        # Обновить предыдущие метрики
        st.session_state.prev_metrics = {
            'total_trades': total_trades,
            'total_profit': total_profit if not trades_df.empty and profit_col else 0,
            'win_rate': win_rate if not trades_df.empty and profit_col else 0,
            'balance': balance if stats else 0
        }
        
        st.markdown("---")
        
        # Таблица торгов
        if not trades_df.empty:
            st.subheader("История торгов")
            
            # Отслеживание новых торгов
            if 'last_trade_count' not in st.session_state:
                st.session_state.last_trade_count = len(trades_df)
            
            current_trade_count = len(trades_df)
            if current_trade_count > st.session_state.last_trade_count:
                new_trades = current_trade_count - st.session_state.last_trade_count
                st.success(f"🆕 Новых торгов: {new_trades}")
                st.session_state.last_trade_count = current_trade_count
            
            # Выбираем только нужные колонки
            display_cols = []
            for col in ['symbol', 'direction', 'open_time', 'close_time', 'profit', 'pips', 'lot']:
                if col in trades_df.columns:
                    display_cols.append(col)
            
            if display_cols:
                # Сортировка по времени (последние сверху)
                display_df = trades_df[display_cols].copy()
                if 'close_time' in display_df.columns:
                    display_df = display_df.sort_values(by='close_time', ascending=False)
                
                st.dataframe(
                    display_df.head(20),
                    use_container_width=True,
                    height=400
                )
        else:
            st.info("Нет данных о торгах. Запустите бота для начала торговли.")
    
    else:  # Backtest Results
        st.header("Backtest Results")
        
        # Выбор параметров
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            symbol = st.selectbox(
                "Символ",
                ["Portfolio", "XAUUSD", "EURUSD"]
            )
        
        with col2:
            year = st.selectbox(
                "Год",
                ["2025", "2024", "2023"]
            )
        
        # Загружаем данные бэктеста
        equity_df, trades_df = dashboard.load_backtest_results(symbol, year)
        
        if equity_df is not None or trades_df is not None:
            # Рассчитываем метрики
            metrics = dashboard.calculate_metrics(trades_df)
            
            # Отображаем метрики
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Всего торгов", metrics.get('total_trades', 0))
            
            with col2:
                st.metric("Винрейт", f"{metrics.get('win_rate', 0):.1f}%")
            
            with col3:
                st.metric("Общая прибыль", f"${metrics.get('total_profit', 0):.2f}")
            
            with col4:
                st.metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
            
            with col5:
                st.metric("Сред. прибыль", f"${metrics.get('avg_profit', 0):.2f}")
            
            st.markdown("---")
            
            # График эквити
            if equity_df is not None:
                fig_equity = dashboard.plot_equity_curve(equity_df)
                if fig_equity:
                    st.plotly_chart(fig_equity, use_container_width=True)
            
            # Дополнительные графики
            col1, col2 = st.columns(2)
            
            with col1:
                if trades_df is not None:
                    fig_dist = dashboard.plot_trades_distribution(trades_df)
                    if fig_dist:
                        st.plotly_chart(fig_dist, use_container_width=True)
            
            with col2:
                if trades_df is not None:
                    fig_monthly = dashboard.plot_monthly_performance(trades_df)
                    if fig_monthly:
                        st.plotly_chart(fig_monthly, use_container_width=True)
            
            # Таблица торгов
            if trades_df is not None and not trades_df.empty:
                st.subheader("Детали торгов")
                st.dataframe(trades_df, use_container_width=True, height=400)
        
        else:
            st.warning(f"Нет данных бэктеста для {symbol} за {year} год.")
            st.info("Запустите бэктест для получения данных.")
    
    # Real-time автообновление
    if mode == "📈 Live Trading":
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚡ Real-Time Updates")
        
        # Выбор интервала обновления
        refresh_interval = st.sidebar.selectbox(
            "Интервал обновления",
            options=[5, 10, 15, 30, 60],
            index=3,  # 30 сек по умолчанию
            format_func=lambda x: f"{x} секунд"
        )
        
        auto_refresh = st.sidebar.checkbox("Включить автообновление", value=False)
        
        # Сохранить состояние в session_state
        st.session_state.auto_refresh_enabled = auto_refresh
        
        # Кнопка ручного обновления
        if st.sidebar.button("🔄 Обновить сейчас"):
            # Очистить кэш перед обновлением
            st.cache_data.clear()
            st.rerun()
        
        # Прогресс-бар для визуализации следующего обновления
        if auto_refresh:
            import time
            
            # Показать статистику обновлений
            if 'refresh_count' not in st.session_state:
                st.session_state.refresh_count = 0
            if 'last_refresh_time' not in st.session_state:
                st.session_state.last_refresh_time = datetime.now()
            
            st.sidebar.markdown("---")
            st.sidebar.markdown("**📊 Статистика обновлений**")
            st.sidebar.text(f"Обновлений: {st.session_state.refresh_count}")
            
            time_since_last = (datetime.now() - st.session_state.last_refresh_time).seconds
            st.sidebar.text(f"Последнее: {time_since_last}с назад")
            st.sidebar.markdown("---")
            
            progress_bar = st.sidebar.progress(0)
            status_text = st.sidebar.empty()
            
            for i in range(refresh_interval):
                progress = (i + 1) / refresh_interval
                progress_bar.progress(progress)
                remaining = refresh_interval - i - 1
                status_text.text(f"⏱️ Обновление через {remaining} сек")
                time.sleep(1)
            
            # Обновить статистику
            st.session_state.refresh_count += 1
            st.session_state.last_refresh_time = datetime.now()
            
            # Очистить кэш перед обновлением
            st.cache_data.clear()
            st.rerun()


if __name__ == "__main__":
    main()
