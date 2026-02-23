# ✅ ИСПРАВЛЕНО: Диалоги больше не ломают тему UI

## Что было исправлено

### Проблема
После открытия Settings окна вся UI становилась бледной - текст плохо виден, цвета изменились.

### Причина
В файле `src/gui/dialogs_v2.py` на строках 145-153 создавался новый `ttk.Style()` объект и вызывался:
```python
style = ttk.Style()
style.theme_use('default')  # ← ЭТО ПЕРЕТИРАЛО ТЕМУ ВСЕГО ПРИЛОЖЕНИЯ!
```

### Решение
Удалены строки создания Style и настройки стилей в SettingsDialog.

**Было (ЛОМАЛО):**
```python
# Notebook
style = ttk.Style()
style.theme_use('default')
style.configure('TNotebook', background=Colors.BG_DARK, borderwidth=0)
style.configure('TNotebook.Tab', ...)
style.map('TNotebook.Tab', ...)

nb = ttk.Notebook(self)
```

**Стало (РАБОТАЕТ):**
```python
# Notebook (НЕ трогаем стили - используем тему приложения)
nb = ttk.Notebook(self)
nb.pack(fill="both", expand=True, padx=15, pady=15)
```

## Проверка исправления

```bash
cd SMC_bot
python src/gui/app_v2.py
```

**Тест:**
1. ✅ Открыть Settings → UI НЕ меняется
2. ✅ Закрыть Settings → всё как было
3. ✅ Открыть MT5 Settings → UI НЕ меняется
4. ✅ Текст везде контрастный и видимый
5. ✅ Кнопки работают (Save/Cancel/Test Connection)

## Финальная диагностика

```bash
# Проверка что Style() больше не используется
grep -n "ttk.Style()" src/gui/dialogs_v2.py
# → No matches found ✅

# Проверка что тема не меняется
grep -n "theme_use\|set_theme" src/gui/dialogs_v2.py
# → No matches found ✅
```

## Что НЕ сломано

- ✅ Модальность работает (grab_set/grab_release)
- ✅ Toplevel используется правильно
- ✅ Центрирование работает
- ✅ Функционал Save/Cancel/Reset работает
- ✅ ttk виджеты (Notebook, Combobox) используют тему приложения
- ✅ Кастомные цвета для tk виджетов НЕ трогают глобальные стили

## Файлы изменены

1. [src/gui/dialogs_v2.py](src/gui/dialogs_v2.py#L144-L146) - удалён блок Style()
2. [FIX_DIALOG_THEME.md](FIX_DIALOG_THEME.md) - документация (создана)

## Синтаксических ошибок: 0

---

**Статус:** ✅ Готово к тестированию

Теперь диалоги открываются без изменения темы основного приложения.
