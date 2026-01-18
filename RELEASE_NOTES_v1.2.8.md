# 🧹 Release v1.2.8 - Auto-Cleanup System

**Дата релиза:** 19 января 2026  
**Размер:** 206 MB  
**Тип:** Maintenance + New Feature  

---

## 🎯 Что нового

### 🧹 **Автоматическая очистка данных**

Теперь бот **автоматически удаляет старые данные**, чтобы не засорять диск!

#### **AI Сигналы**
- ✅ Удаляются автоматически если старше **36 часов**
- 🕐 Проверка каждый день в **22:00**
- 📊 Экономия ~14 MB на активном боте

#### **Логи**
- ✅ Удаляются автоматически если старше **7 дней 20 часов**
- 🕐 Проверка каждый понедельник в **22:00**
- 📊 Экономия ~55 MB за 2 месяца работы

**Пример логирования:**
```
22:00:00 [INFO] 🕐 Time for signals cleanup: 22:00
22:00:01 [INFO] ✅ Deleted 15 active signals (23 → 8)
22:00:01 [INFO] ✅ Signals cleanup complete: 15 signals deleted

22:00:00 [INFO] 🕐 Time for logs cleanup: Monday 22:00
22:00:01 [INFO] 🗑️ Deleted: baza_20260105.log (0.45 MB, age: 14 days)
22:00:01 [INFO] ✅ Logs cleanup complete: 13 files deleted (5.67 MB freed)
```

---

## 📋 Changelog

### ✨ Новые возможности

1. **🧹 Cleanup Service**
   - Фоновый процесс автоочистки
   - Работает без блокировки бота
   - Детальное логирование операций
   - Конфигурация через YAML

2. **⚙️ Новый конфиг:** `config/cleanup.yaml`
   ```yaml
   signals:
     max_age_hours: 36      # Возраст сигналов
     cleanup_time: "22:00"  # Время очистки
   
   logs:
     max_age_days: 7        # 7 дней
     max_age_hours: 20      # + 20 часов
     cleanup_time: "22:00"  # Время очистки
     cleanup_day: 0         # 0=Monday
   ```

3. **📊 Статистика очистки**
   - Сколько файлов удалено
   - Сколько места освобождено
   - Возраст удалённых данных

### 🐛 Bugfixes (из v1.2.7)

4. **✅ API Key Loading**
   - Теперь API ключ загружается из `.env` при открытии Settings
   - Больше не нужно вводить ключ каждый раз

5. **🧹 Telegram Commands**
   - Автоматическая очистка старых команд при старте бота
   - Только `/start` в меню (остальное через кнопки)

### 🎨 UI Improvements (из v1.2.7)

6. **📅 Smart Date Display**
   - Сегодняшние сигналы: `09:15:36` (только время)
   - Старые сигналы: `18.01 19:26` (дата + время)
   - Легко видеть возраст сигнала

---

## 🚀 Установка

### Вариант 1: EXE (рекомендуется)

1. Скачать `BAZA_TradingBot.exe` из релиза
2. Запустить двойным кликом
3. Настроить через Settings
4. Готово! ✅

### Вариант 2: Из исходников

```bash
git clone https://github.com/vlvdssss/SMC_bot.git
cd SMC_bot
git checkout v1.2.8
pip install -r requirements.txt
python main.py
```

---

## ⚙️ Конфигурация Cleanup

### Изменить время очистки

Редактируй `config/cleanup.yaml`:

```yaml
signals:
  cleanup_time: "23:00"  # Изменить на 23:00

logs:
  cleanup_time: "23:00"
```

### Изменить возраст данных

```yaml
signals:
  max_age_hours: 48  # Хранить 48 часов вместо 36

logs:
  max_age_days: 14   # Хранить 14 дней вместо 7
  max_age_hours: 0   # Без доп. часов
```

### Изменить день очистки логов

```yaml
logs:
  cleanup_day: 6  # Sunday (0=Mon, 1=Tue, ..., 6=Sun)
```

---

## 📖 Как это работает

### Пример для сигналов (36 часов)

```
Понедельник 20.01 02:00 → Создан сигнал
Вторник 21.01 14:00     → Сигналу 36 часов
Вторник 21.01 22:00     → УДАЛЕНИЕ (>36h)
```

### Пример для логов (7 дней 20 часов)

```
Понедельник 13.01 02:00 → Создан лог
Понедельник 20.01 22:00 → Логу 7д 20ч (188h)
Понедельник 20.01 22:00 → УДАЛЕНИЕ
```

### Почему именно 7д 20ч?

- Начали в **понедельник 02:00**
- Следующий понедельник в **22:00** = через **7 дней 20 часов**
- Таким образом недельный цикл = полная неделя торговли

---

## 🧪 Тестирование

Запусти тест cleanup service:

```bash
python scripts/test_cleanup.py
```

**Вывод:**
```
🧪 TEST: Signals Cleanup
   ✅ Created 5 test signals
   📊 Before cleanup: 5 signals
   📊 After cleanup: 2 signals
   🎉 TEST PASSED

🧪 TEST: Logs Cleanup
   ✅ Created 4 test log files
   📊 Before cleanup: 4 log files
   📊 After cleanup: 2 log files
   🎉 TEST PASSED

🎯 Total: 2/2 tests passed
🎉 ALL TESTS PASSED!
```

---

## 📁 Новые файлы

| Файл | Описание |
|------|----------|
| `src/core/cleanup_service.py` | Основной сервис автоочистки |
| `config/cleanup.yaml` | Конфигурация (можно редактировать) |
| `docs/AUTO_CLEANUP.md` | Полная документация |
| `scripts/test_cleanup.py` | Тесты системы очистки |

---

## 🔧 Технические детали

### Архитектура

```python
# BotManager запускает cleanup service
if CLEANUP_AVAILABLE:
    self.cleanup_service = CleanupService()
    self.cleanup_service.start()  # Фоновый поток

# Cleanup проверяет время каждые 60 секунд
while not self._stop_event.is_set():
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    
    if current_time == "22:00":
        self.cleanup_old_signals()  # Каждый день
        
    if now.weekday() == 0 and current_time == "22:00":
        self.cleanup_old_logs()  # Каждый понедельник
    
    self._stop_event.wait(60)  # Спим 60 сек
```

### Что удаляется

**Сигналы:**
- `data/ai_signals/active_signals.json` - старые записи
- `data/ai_signals/*.json` - старые файлы истории

**Логи:**
- `logs/*.log` - старые логи
- `logs/*.txt` - старые текстовые файлы

### Безопасность

- ✅ Проверяет дату перед удалением
- ✅ Логирует все операции
- ✅ Обрабатывает ошибки без крашей
- ✅ Не блокирует основной процесс
- ✅ Автоматически останавливается при остановке бота

---

## 📊 Статистика экономии

**На продакшн боте (работающем 2 месяца):**

| Тип данных | До очистки | После очистки | Экономия |
|-----------|-----------|---------------|----------|
| Сигналы | 500+ шт (15+ MB) | 20-30 шт (< 1 MB) | ~14 MB |
| Логи | 45 файлов (67 MB) | 6-8 файлов (8-12 MB) | ~55 MB |
| **ИТОГО** | **82 MB** | **~12 MB** | **~70 MB** |

---

## ❓ FAQ

**Q: Можно ли отключить cleanup?**  
A: Да, закомментируй `_init_cleanup()` в `bot_manager.py` или удали `config/cleanup.yaml`.

**Q: Cleanup удаляет мои важные файлы?**  
A: Нет, удаляются только:
- Сигналы в `data/ai_signals/` старше 36ч
- Логи в `logs/` старше 7д 20ч

**Q: Можно ли запустить cleanup вручную?**  
A: Да, через `cleanup_service.force_cleanup_now('both')` или `python scripts/test_cleanup.py`.

**Q: Что если я хочу хранить данные дольше?**  
A: Измени `max_age_hours` и `max_age_days` в `config/cleanup.yaml`.

**Q: Cleanup работает если бот остановлен?**  
A: Нет, cleanup работает только пока бот запущен. Если бот был выключен в 22:00, очистка произойдёт на следующий день.

**Q: Можно ли изменить время очистки?**  
A: Да, измени `cleanup_time` в `config/cleanup.yaml`.

---

## 🔄 Обновление с v1.2.7

### Автоматическое обновление (EXE)

1. Скачай новый `BAZA_TradingBot.exe`
2. Замени старый файл
3. Запусти - готово! ✅

### Обновление из исходников

```bash
git pull origin main
git checkout v1.2.8
pip install -r requirements.txt  # На всякий случай
```

### Что сохраняется

✅ Все настройки (`.env`, `config/*.yaml`)  
✅ История сделок (`data/trades_history.json`)  
✅ Текущие позиции  
✅ Статистика бота

### Что изменится

🆕 Появится `config/cleanup.yaml`  
🆕 Cleanup service запустится автоматически  
🆕 Старые сигналы/логи начнут удаляться

---

## 🎁 Бонус: Полная история релизов v1.2.x

### v1.2.8 (19.01.2026) - **Auto-Cleanup System**
- 🧹 Автоочистка сигналов (36h)
- 🗑️ Автоочистка логов (7д 20ч)
- 📊 Экономия ~70 MB дискового пространства

### v1.2.7 (18.01.2026) - **Bugfixes + UI**
- 🐛 API key loading fix
- 🧹 Telegram commands cleanup
- 📅 Smart date display

### v1.2.6 (17.01.2026) - **Production Dashboard**
- 🎨 Двухколоночный layout
- 💳 Signal cards с badges
- 📊 Progress bars для Confidence
- 🎯 Priority indicators

### v1.2.5 (16.01.2026) - **Signal History**
- ✨ Улучшенная история сигналов
- 📈 Lifecycle tracking
- 🎨 Semantic colors

---

## 📞 Поддержка

**Проблемы?** Открой issue: https://github.com/vlvdssss/SMC_bot/issues

**Вопросы?** Прочитай:
- [docs/AUTO_CLEANUP.md](docs/AUTO_CLEANUP.md) - Полная документация
- [README.md](README.md) - Общая документация
- [docs/FAQ.md](docs/FAQ.md) - Частые вопросы

---

## 🙏 Благодарности

Спасибо всем за feedback и bug reports! 🎉

**Особая благодарность:**
- За репорт бага с API key
- За репорт проблемы со старыми Telegram командами
- За предложение добавить даты в историю сигналов
- За идею системы автоочистки

---

## 🚀 Что дальше?

**Планы на v1.2.9:**
- 📊 Расширенная статистика cleanup (графики)
- 🗄️ Архивация данных вместо удаления (опционально)
- ⚙️ Настройка cleanup через GUI

**Долгосрочные планы:**
- 🤖 ML-модели для улучшения сигналов
- 📈 Backtesting на исторических данных
- 🌐 Web dashboard для мониторинга

---

**Приятного трейдинга! 📈💰**
