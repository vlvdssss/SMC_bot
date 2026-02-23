# FIX: Модальные диалоги ломали тему приложения

## Проблема

После открытия Settings окна вся UI становилась бледной/изменялась визуально.

**Причина:** В `dialogs_v2.py` создавался новый `ttk.Style()` объект и вызывался `style.theme_use('default')`, что перетирало глобальную тему приложения.

## Что было исправлено

### ❌ СТАРЫЙ КОД (ЛОМАЛ ТЕМУ):
```python
# Notebook
style = ttk.Style()                                    # ← Создаём новый Style
style.theme_use('default')                             # ← ПЕРЕТИРАЕМ ГЛОБАЛЬНУЮ ТЕМУ!
style.configure('TNotebook', background=Colors.BG_DARK, borderwidth=0)
style.configure('TNotebook.Tab',
               background=Colors.BG_CARD,
               foreground=Colors.TEXT_PRIMARY,
               padding=[15, 8])
style.map('TNotebook.Tab',
         background=[('selected', Colors.BG_PANEL)],
         foreground=[('selected', Colors.ACCENT)])

nb = ttk.Notebook(self)
```

### ✅ НОВЫЙ КОД (НЕ ТРОГАЕТ ТЕМУ):
```python
# Notebook (НЕ трогаем стили - используем тему приложения)
nb = ttk.Notebook(self)
nb.pack(fill="both", expand=True, padx=15, pady=15)
```

## Правила для модальных диалогов

### 1. ✅ Использовать Toplevel, НЕ Tk
```python
# ✅ ПРАВИЛЬНО
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, ...):
        super().__init__(parent)  # Toplevel наследует от parent

# ❌ НЕПРАВИЛЬНО
class SettingsDialog:
    def __init__(self, parent, ...):
        self.root = tk.Tk()  # Создаёт новое окно приложения!
```

### 2. ✅ НЕ трогать глобальные стили
```python
# ❌ ЗАПРЕЩЕНО в диалогах:
style = ttk.Style()
style.theme_use('default')  # Меняет тему всего приложения
style.configure('TNotebook', ...)  # Перетирает глобальный стиль
style.configure('TLabel', ...)
style.map('TButton', ...)

# ✅ РАЗРЕШЕНО:
# Вообще НЕ трогать стили - использовать тему приложения как есть

# ✅ ЕСЛИ НУЖНЫ КАСТОМНЫЕ СТИЛИ:
style = ttk.Style()
style.configure('Dialog.TNotebook', ...)  # Именованный стиль
# И в коде: ttk.Notebook(self, style='Dialog.TNotebook')
```

### 3. ✅ НЕ менять bg родительского окна
```python
# ❌ ЗАПРЕЩЕНО:
parent.configure(bg='white')
root.configure(bg=Colors.BG_DARK)

# ✅ ПРАВИЛЬНО:
self.configure(bg=Colors.BG_DARK)  # Только свой Toplevel
```

### 4. ✅ Правильная модальность
```python
def __init__(self, parent, ...):
    super().__init__(parent)
    
    # Модальность
    self.transient(parent)     # Окно поверх родителя
    self.grab_set()            # Блокировка родительского окна
    self.protocol("WM_DELETE_WINDOW", self._cancel)  # Обработка закрытия
    
def _close(self):
    try:
        self.grab_release()    # Освобождение фокуса
    except:
        pass
    self.destroy()
```

### 5. ✅ Центрирование относительно родителя
```python
w, h = 650, 600
x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
self.geometry(f"{w}x{h}+{x}+{y}")
```

## Быстрая диагностика проблемы

Если после открытия диалога UI изменилась, проверьте:

```bash
# 1. Поиск создания новых Style объектов
grep -n "ttk.Style()" src/gui/dialogs_v2.py

# 2. Поиск изменения темы
grep -n "theme_use\|set_theme" src/gui/dialogs_v2.py

# 3. Поиск перетирания глобальных стилей
grep -n "configure('T" src/gui/dialogs_v2.py

# 4. Поиск создания Tk вместо Toplevel
grep -n "tk.Tk()" src/gui/dialogs_v2.py

# 5. Поиск изменения bg родителя
grep -n "parent.configure\|root.configure" src/gui/dialogs_v2.py
```

## Что НЕ нужно менять

### ttk виджеты МОЖНО использовать
```python
# ✅ МОЖНО (используют тему приложения):
ttk.Notebook(self)
ttk.Combobox(frame, ...)
ttk.Button(frame, ...)
```

### Кастомные tk виджеты с цветами МОЖНО
```python
# ✅ МОЖНО (не влияют на глобальную тему):
tk.Frame(self, bg=Colors.BG_DARK)
tk.Label(frame, bg=Colors.BG_PANEL, fg=Colors.TEXT_PRIMARY)
tk.Button(frame, bg=Colors.SUCCESS, fg='white')
```

## Тестирование исправления

1. Запустить приложение:
```bash
python src/gui/app_v2.py
```

2. Открыть Settings → проверить что UI НЕ побледнела

3. Закрыть Settings → проверить что всё вернулось как было

4. Открыть MT5 Settings → проверить что UI НЕ изменилась

5. Проверить что кнопки и текст везде видны и контрастны

## Статус

✅ **ИСПРАВЛЕНО**

Файл: `src/gui/dialogs_v2.py`
- Удалены строки 145-153 (создание Style и theme_use)
- Notebook теперь использует тему приложения напрямую
- Без ошибок синтаксиса
- Модальность работает корректно
- Тема приложения не меняется при открытии диалогов

## Проверка после исправления

```python
# В dialogs_v2.py должно быть:
class SettingsDialog(tk.Toplevel):  # ✅ Toplevel
    def __init__(self, parent, ...):
        super().__init__(parent)     # ✅ Наследует от parent
        self.transient(parent)       # ✅ Модальность
        self.grab_set()              # ✅ Блокировка

    def _build_ui(self):
        # ✅ НЕТ Style(), НЕТ theme_use()
        nb = ttk.Notebook(self)      # ✅ Использует тему приложения
```

## Что делать если проблема повторится

Если после открытия настроек UI снова изменилась:

1. Проверить что в диалогах НЕТ `ttk.Style()` или `theme_use()`
2. Проверить что используется `tk.Toplevel`, а не `tk.Tk()`
3. Проверить что НЕ меняется `bg` родительских виджетов
4. Убедиться что все `style.configure()` используют именованные стили ("Dialog.TLabel") а не глобальные ("TLabel")
