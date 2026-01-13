"""
Update Window - UI для обновления приложения
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import sys
import subprocess
import logging
from typing import Dict, Any

from .downloader import UpdateDownloader

logger = logging.getLogger(__name__)


class UpdateWindow:
    """Окно обновления приложения"""
    
    def __init__(self, parent: tk.Tk, current_version: str, update_info: Dict[str, Any]):
        """
        Args:
            parent: Родительское окно
            current_version: Текущая версия приложения
            update_info: Информация об обновлении из version.json
        """
        self.parent = parent
        self.current_version = current_version
        self.update_info = update_info
        self.downloader = None
        
        # Создаем модальное окно
        self.window = tk.Toplevel(parent)
        self.window.title("Обновление доступно")
        self.window.geometry("500x450")
        self.window.resizable(False, False)
        
        # Делаем окно модальным
        self.window.transient(parent)
        self.window.grab_set()
        
        # Центрируем окно
        self._center_window()
        
        # Создаем интерфейс
        self._create_ui()
        
    def _center_window(self):
        """Центрировать окно относительно родителя"""
        self.window.update_idletasks()
        
        # Получаем размеры
        window_width = self.window.winfo_width()
        window_height = self.window.winfo_height()
        
        # Позиция родителя
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Вычисляем центр
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2
        
        self.window.geometry(f"+{x}+{y}")
    
    def _create_ui(self):
        """Создать интерфейс окна обновления"""
        # Основной контейнер
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Иконка и заголовок
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = ttk.Label(
            title_frame,
            text="🎉 Доступно обновление!",
            font=("Segoe UI", 14, "bold")
        )
        title_label.pack()
        
        # Информация о версиях
        version_frame = ttk.LabelFrame(main_frame, text="Версии", padding="10")
        version_frame.pack(fill=tk.X, pady=(0, 15))
        
        current_label = ttk.Label(
            version_frame,
            text=f"Текущая версия: {self.current_version}",
            font=("Segoe UI", 10)
        )
        current_label.pack(anchor=tk.W)
        
        new_label = ttk.Label(
            version_frame,
            text=f"Новая версия: {self.update_info['latest_version']}",
            font=("Segoe UI", 10, "bold"),
            foreground="green"
        )
        new_label.pack(anchor=tk.W, pady=(5, 0))
        
        size_label = ttk.Label(
            version_frame,
            text=f"Размер файла: {self.update_info.get('size_mb', 'N/A')} MB",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        size_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Список изменений
        changelog_frame = ttk.LabelFrame(main_frame, text="Что нового", padding="10")
        changelog_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Создаем scrollable text для changelog
        changelog_text = tk.Text(
            changelog_frame,
            height=10,
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            bg="white",
            relief=tk.FLAT,
            borderwidth=1
        )
        changelog_text.pack(fill=tk.BOTH, expand=True)
        
        # Заполняем changelog
        for i, change in enumerate(self.update_info.get('changelog', []), 1):
            changelog_text.insert(tk.END, f"• {change}\n")
        
        changelog_text.config(state=tk.DISABLED)
        
        # Прогресс-бар (скрыт по умолчанию)
        self.progress_frame = ttk.Frame(main_frame)
        
        self.progress_label = ttk.Label(
            self.progress_frame,
            text="Загрузка обновления...",
            font=("Segoe UI", 9)
        )
        self.progress_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=450
        )
        self.progress_bar.pack(fill=tk.X)
        
        self.progress_percent = ttk.Label(
            self.progress_frame,
            text="0%",
            font=("Segoe UI", 9)
        )
        self.progress_percent.pack(anchor=tk.E, pady=(5, 0))
        
        # Кнопки
        self.button_frame = ttk.Frame(main_frame)
        self.button_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.cancel_button = ttk.Button(
            self.button_frame,
            text="Отмена",
            command=self._on_cancel,
            width=15
        )
        self.cancel_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.update_button = ttk.Button(
            self.button_frame,
            text="Обновить",
            command=self._start_update,
            width=15
        )
        self.update_button.pack(side=tk.RIGHT)
        
    def _start_update(self):
        """Начать загрузку обновления"""
        logger.info("User initiated update")
        
        # Скрываем кнопку обновления и показываем прогресс
        self.update_button.config(state=tk.DISABLED)
        self.progress_frame.pack(fill=tk.X, pady=(15, 0), before=self.button_frame)
        
        # Запускаем загрузку в отдельном потоке
        download_url = self.update_info['download_url']
        
        # Определяем путь для сохранения обновления
        if getattr(sys, 'frozen', False):
            # Если запущен как EXE
            current_exe = sys.executable
            exe_dir = os.path.dirname(current_exe)
            update_path = os.path.join(exe_dir, "BAZA_TradingBot_update.exe")
        else:
            # Если запущен как скрипт (для разработки)
            update_path = os.path.join(os.getcwd(), "dist", "BAZA_TradingBot_update.exe")
        
        logger.info(f"Update will be saved to: {update_path}")
        
        self.downloader = UpdateDownloader(download_url, update_path)
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self._download_update, daemon=True)
        thread.start()
    
    def _download_update(self):
        """Загрузить обновление (выполняется в отдельном потоке)"""
        try:
            success = self.downloader.download(progress_callback=self._update_progress)
            
            if success:
                # Загрузка завершена
                self.window.after(0, self._download_complete)
            else:
                # Загрузка отменена
                self.window.after(0, lambda: self._download_failed("Загрузка отменена"))
                
        except Exception as e:
            logger.error(f"Download failed: {e}")
            self.window.after(0, lambda: self._download_failed(str(e)))
    
    def _update_progress(self, downloaded: int, total: int):
        """
        Обновить прогресс-бар
        
        Args:
            downloaded: Загружено байт
            total: Всего байт
        """
        if total > 0:
            percent = (downloaded / total) * 100
            
            # Обновляем UI в главном потоке
            self.window.after(0, lambda: self._set_progress(percent, downloaded, total))
    
    def _set_progress(self, percent: float, downloaded: int, total: int):
        """Установить значение прогресса (в главном потоке)"""
        self.progress_bar['value'] = percent
        self.progress_percent.config(text=f"{percent:.1f}%")
        
        # Показываем размер
        downloaded_mb = downloaded / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        self.progress_label.config(
            text=f"Загружено {downloaded_mb:.1f} MB из {total_mb:.1f} MB"
        )
    
    def _download_complete(self):
        """Загрузка завершена успешно"""
        logger.info("Download completed successfully")
        
        # Меняем интерфейс
        self.progress_label.config(
            text="✅ Обновление загружено успешно!",
            foreground="green"
        )
        
        # Меняем кнопки
        self.update_button.config(
            text="Перезапустить",
            state=tk.NORMAL,
            command=self._restart_application
        )
        
        self.cancel_button.config(text="Позже", state=tk.NORMAL)
        
        messagebox.showinfo(
            "Обновление готово",
            "Обновление загружено.\nНажмите 'Перезапустить' для применения обновления.",
            parent=self.window
        )
    
    def _download_failed(self, error_message: str):
        """Загрузка не удалась"""
        logger.error(f"Download failed: {error_message}")
        
        self.progress_label.config(
            text=f"❌ Ошибка загрузки",
            foreground="red"
        )
        
        self.update_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.NORMAL)
        
        messagebox.showerror(
            "Ошибка обновления",
            f"Не удалось загрузить обновление:\n{error_message}",
            parent=self.window
        )
    
    def _restart_application(self):
        """Перезапустить приложение с обновленной версией"""
        logger.info("Restarting application with update")
        
        try:
            if getattr(sys, 'frozen', False):
                # Запущен как EXE
                current_exe = sys.executable
                exe_dir = os.path.dirname(current_exe)
                update_exe = os.path.join(exe_dir, "BAZA_TradingBot_update.exe")
                
                if not os.path.exists(update_exe):
                    raise FileNotFoundError(f"Update file not found: {update_exe}")
                
                # Запускаем обновленную версию
                logger.info(f"Launching update: {update_exe}")
                subprocess.Popen([update_exe], cwd=exe_dir)
                
                # Закрываем текущее приложение
                logger.info("Closing current application")
                self.parent.quit()
                
            else:
                # Режим разработки
                messagebox.showinfo(
                    "Режим разработки",
                    "В режиме разработки перезапуск недоступен.\n"
                    "Обновленный EXE находится в dist/BAZA_TradingBot_update.exe",
                    parent=self.window
                )
                self.window.destroy()
                
        except Exception as e:
            logger.error(f"Failed to restart: {e}")
            messagebox.showerror(
                "Ошибка перезапуска",
                f"Не удалось перезапустить приложение:\n{e}\n\n"
                f"Запустите BAZA_TradingBot_update.exe вручную.",
                parent=self.window
            )
    
    def _on_cancel(self):
        """Отменить обновление"""
        if self.downloader:
            # Если идет загрузка - отменяем
            self.downloader.cancel()
        
        self.window.destroy()
