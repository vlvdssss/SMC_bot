"""
BAZA Trading Bot - Version Information
Централизованное хранение версии приложения
"""

# Версия приложения
APP_VERSION = "2.0.0"

# URL для проверки обновлений
VERSION_CHECK_URL = "https://raw.githubusercontent.com/vlvdssss/SMC_bot/main/version.json"

# Примечания к версии
VERSION_NOTES = {
    "2.0.0": [
        "🚀 GPT Decision Engine v2.0 - Event-Driven Architecture",
        "⚡ TTL System: Signal expiration + auto-requery (60min default)",
        "🎯 Event Triggers: Position close → New analysis request",
        "🧹 Schedule Removed: Pure event-driven logic (no cron)",
        "💰 Live News Feed: Real-time high-impact events (TODAY'S NEWS)",
        "🔧 Settings: TTL controls (3 settings: minutes + 2 checkboxes)",
        "✅ Bugfixes: API key loading, config paths, imports",
        "📊 Stability: All settings verified functional"
    ],
    "1.3.2": [
        "🎨 Clean Logging System v2.0",
        "📊 Visual Schedule Tab",
        "🧹 Auto-cleanup старых сигналов и логов",
        "🔧 Bugfixes: API key, Settings dialog"
    ],
    "1.0.0": [
        "Первый релиз BAZA Trading Bot",
        "AI Market Analysis через GPT-4o Vision",
        "Pure AI Trading Mode",
        "Telegram интеграция",
        "Система автоматических обновлений"
    ]
}
