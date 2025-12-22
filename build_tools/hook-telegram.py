# PyInstaller hook for python-telegram-bot
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all telegram modules
datas, binaries, hiddenimports = collect_all('telegram')

# Explicitly add all telegram submodules
hiddenimports += collect_submodules('telegram')
hiddenimports += collect_submodules('telegram.ext')
hiddenimports += [
    'telegram',
    'telegram.ext',
    'telegram._bot',
    'telegram._update',
    'telegram.ext._application',
    'telegram.ext._commandhandler',
    'telegram.ext._contexttypes',
    'telegram.ext._utils',
    'telegram.request',
    'telegram.request._httpxrequest',
    'httpx',
    'httpcore',
    'h11',
    'certifi',
    'anyio',
]
