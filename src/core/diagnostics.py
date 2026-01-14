"""
System Diagnostics - проверка подключений и конфигурации
"""

import os
from pathlib import Path
from typing import Dict, List
from src.core.logger import logger


class SystemDiagnostics:
    """Диагностика системы перед запуском."""
    
    @staticmethod
    def check_all() -> Dict[str, any]:
        """
        Проверить все компоненты системы.
        
        Returns:
            Dict с результатами проверок
        """
        results = {
            "openai_api": SystemDiagnostics.check_openai_api(),
            "config_files": SystemDiagnostics.check_config_files(),
            "data_folders": SystemDiagnostics.check_data_folders(),
            "all_ok": True
        }
        
        # Проверяем есть ли критические ошибки
        for key, value in results.items():
            if key != "all_ok" and isinstance(value, dict):
                if not value.get("status"):
                    results["all_ok"] = False
        
        return results
    
    @staticmethod
    def check_openai_api() -> Dict[str, any]:
        """Проверка OpenAI API ключа."""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            
            if not api_key:
                return {
                    "status": False,
                    "message": "❌ OpenAI API key not found in environment",
                    "solution": "Set OPENAI_API_KEY in config/.env or Settings"
                }
            
            if not api_key.startswith('sk-'):
                return {
                    "status": False,
                    "message": "⚠️ OpenAI API key format invalid",
                    "solution": "API key should start with 'sk-'"
                }
            
            logger.info(f"[Diagnostics] ✅ OpenAI API key found: {api_key[:15]}...{api_key[-4:]}")
            return {
                "status": True,
                "message": f"✅ OpenAI API key configured ({api_key[:15]}...{api_key[-4:]})"
            }
            
        except Exception as e:
            logger.error(f"[Diagnostics] Error checking OpenAI API: {e}")
            return {
                "status": False,
                "message": f"❌ Error: {e}",
                "solution": "Check config/.env file"
            }
    
    @staticmethod
    def check_config_files() -> Dict[str, any]:
        """Проверка конфигурационных файлов."""
        try:
            config_dir = Path('config')
            required_files = {
                'ai.yaml': 'AI configuration',
                'portfolio.yaml': 'Portfolio and risk settings',
                'trading.yaml': 'Trading parameters'
            }
            
            missing = []
            found = []
            
            for filename, description in required_files.items():
                filepath = config_dir / filename
                if filepath.exists():
                    found.append(f"✅ {filename}")
                else:
                    missing.append(f"❌ {filename} ({description})")
            
            if missing:
                logger.warning(f"[Diagnostics] Missing config files: {', '.join(missing)}")
                return {
                    "status": False,
                    "message": f"Missing config files: {len(missing)}",
                    "details": missing,
                    "solution": "Create missing YAML files from examples"
                }
            
            logger.info(f"[Diagnostics] ✅ All config files present")
            return {
                "status": True,
                "message": f"✅ All config files present ({len(found)})",
                "details": found
            }
            
        except Exception as e:
            logger.error(f"[Diagnostics] Error checking config files: {e}")
            return {
                "status": False,
                "message": f"❌ Error: {e}"
            }
    
    @staticmethod
    def check_data_folders() -> Dict[str, any]:
        """Проверка папок с данными."""
        try:
            data_dir = Path('data')
            required_folders = ['ai_analysis', 'ai_signals', 'screenshots']
            
            missing = []
            found = []
            
            for folder in required_folders:
                folderpath = data_dir / folder
                if folderpath.exists():
                    found.append(f"✅ {folder}/")
                else:
                    # Создаём отсутствующие папки
                    folderpath.mkdir(parents=True, exist_ok=True)
                    missing.append(f"Created: {folder}/")
            
            logger.info(f"[Diagnostics] ✅ Data folders ready")
            return {
                "status": True,
                "message": f"✅ Data folders ready ({len(found) + len(missing)})",
                "details": found + missing
            }
            
        except Exception as e:
            logger.error(f"[Diagnostics] Error checking data folders: {e}")
            return {
                "status": False,
                "message": f"❌ Error: {e}"
            }
    
    @staticmethod
    def get_diagnostic_report() -> str:
        """Получить текстовый отчёт диагностики."""
        results = SystemDiagnostics.check_all()
        
        lines = [
            "=== SYSTEM DIAGNOSTICS ===",
            ""
        ]
        
        # OpenAI API
        openai = results["openai_api"]
        lines.append(f"OpenAI API: {openai['message']}")
        if not openai["status"] and "solution" in openai:
            lines.append(f"  → {openai['solution']}")
        lines.append("")
        
        # Config Files
        config = results["config_files"]
        lines.append(f"Config Files: {config['message']}")
        if "details" in config:
            for detail in config["details"]:
                lines.append(f"  {detail}")
        lines.append("")
        
        # Data Folders
        data = results["data_folders"]
        lines.append(f"Data Folders: {data['message']}")
        if "details" in data:
            for detail in data["details"]:
                lines.append(f"  {detail}")
        lines.append("")
        
        # Summary
        if results["all_ok"]:
            lines.append("✅ All systems operational")
        else:
            lines.append("⚠️ Some issues detected - see details above")
        
        lines.append("==========================")
        
        return "\n".join(lines)
