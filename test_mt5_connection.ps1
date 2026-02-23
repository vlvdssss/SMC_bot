# MT5 Connection Test Script
# Быстрая проверка подключения MetaTrader 5

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  🔍 MT5 CONNECTION DIAGNOSTIC" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan

# Activate virtual environment
$venvPath = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "✓ Activating virtual environment..." -ForegroundColor Green
    & $venvPath
} else {
    Write-Host "⚠ Virtual environment not found, using system Python" -ForegroundColor Yellow
}

# Run Python diagnostic
Write-Host "`nRunning MT5 diagnostic...`n" -ForegroundColor Cyan

python -c @"
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path.cwd()))

try:
    import MetaTrader5 as mt5
    print('✓ MetaTrader5 package installed')
except ImportError:
    print('❌ MetaTrader5 package NOT installed')
    print('   Run: pip install MetaTrader5')
    sys.exit(1)

# Load config
try:
    import yaml
    config_path = Path('config/mt5.yaml')
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        mt5_config = config.get('mt5', {}).get('connection', {})
        print(f'\n📋 MT5 CONFIG:')
        print(f'   Login: {mt5_config.get(\"login\", \"NOT SET\")}')
        print(f'   Server: {mt5_config.get(\"server\", \"NOT SET\")}')
        print(f'   Path: {mt5_config.get(\"path\", \"NOT SET\")}')
    else:
        print('❌ config/mt5.yaml not found')
        sys.exit(1)
except Exception as e:
    print(f'❌ Failed to read config: {e}')
    sys.exit(1)

# Try to initialize MT5
print(f'\n🔌 CONNECTING TO MT5...')

try:
    # Initialize
    if not mt5.initialize():
        error = mt5.last_error()
        print(f'❌ MT5 initialization failed')
        print(f'   Error code: {error[0]}')
        print(f'   Description: {error[1]}')
        print(f'\n💡 SOLUTIONS:')
        print(f'   1. Make sure MetaTrader 5 terminal is RUNNING')
        print(f'   2. Make sure terminal is CONNECTED to server (green status)')
        print(f'   3. Check path in config/mt5.yaml')
        print(f'   4. Try closing and reopening MT5 terminal')
        sys.exit(1)
    
    print('✓ MT5 initialized successfully')
    
    # Get terminal info
    terminal_info = mt5.terminal_info()
    if terminal_info:
        print(f'\n📊 TERMINAL INFO:')
        print(f'   Company: {terminal_info.company}')
        print(f'   Name: {terminal_info.name}')
        print(f'   Path: {terminal_info.path}')
        print(f'   Connected: {\"✓ YES\" if terminal_info.connected else \"❌ NO\"}')
        
        if not terminal_info.connected:
            print(f'\n⚠️  TERMINAL NOT CONNECTED TO SERVER!')
            print(f'   Open MT5 → File → Login to Trade Account')
            print(f'   Or check internet connection')
            mt5.shutdown()
            sys.exit(1)
    
    # Get account info
    account_info = mt5.account_info()
    if account_info:
        print(f'\n💰 ACCOUNT INFO:')
        print(f'   Login: {account_info.login}')
        print(f'   Server: {account_info.server}')
        print(f'   Balance: ${account_info.balance:.2f}')
        print(f'   Leverage: 1:{account_info.leverage}')
        print(f'   Trade Allowed: {\"✓ YES\" if account_info.trade_allowed else \"❌ NO\"}')
        
        if not account_info.trade_allowed:
            print(f'\n⚠️  TRADING NOT ALLOWED!')
            print(f'   Check account settings in MT5')
    
    # Test symbol access
    print(f'\n📈 TESTING SYMBOLS:')
    test_symbols = ['XAUUSD', 'EURUSD', 'GBPUSD']
    
    for symbol in test_symbols:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info:
            if symbol_info.visible:
                print(f'   ✓ {symbol} - available')
            else:
                print(f'   ⚠ {symbol} - exists but not visible (enable in Market Watch)')
        else:
            print(f'   ❌ {symbol} - not available')
    
    # Success!
    print(f'\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    print(f'✅ MT5 CONNECTION SUCCESSFUL!')
    print(f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    
    mt5.shutdown()
    sys.exit(0)

except Exception as e:
    print(f'❌ Unexpected error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan

if ($LASTEXITCODE -eq 0) {
    Write-Host "Press any key to continue..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} else {
    Write-Host "MT5 connection check failed. Press any key to exit..." -ForegroundColor Red
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}
