# Push Update System to GitHub
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Pushing BAZA Updates to GitHub" -ForegroundColor Cyan  
Write-Host "========================================`n" -ForegroundColor Cyan

# Check current status
Write-Host "Current branch status:" -ForegroundColor Yellow
git branch -vv

Write-Host "`nLast commits:" -ForegroundColor Yellow
git log --oneline -n 3

Write-Host "`nAttempting to push..." -ForegroundColor Yellow

# Try to push (if behind, will show error)
$pushResult = git push origin main 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Successfully pushed to GitHub!" -ForegroundColor Green
    Write-Host "`n📋 Next steps:" -ForegroundColor Cyan
    Write-Host "1. Go to: https://github.com/vlvdssss/SMC_bot/releases"
    Write-Host "2. Click 'Create a new release'"
    Write-Host "3. Tag: v1.0.0"
    Write-Host "4. Title: BAZA Trading Bot v1.0.0"
    Write-Host "5. Upload file: dist\BAZA_TradingBot.exe"
    Write-Host "6. Click 'Publish release'"
    Write-Host "`n🔄 After that, update system will work!"
} else {
    Write-Host "`n⚠️ Push failed. Trying to pull first..." -ForegroundColor Yellow
    
    # Pull with merge strategy
    git pull origin main --no-rebase
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Pull successful, pushing again..." -ForegroundColor Green
        git push origin main
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✅ Successfully pushed!" -ForegroundColor Green
        } else {
            Write-Host "`n❌ Push still failed. Check for conflicts." -ForegroundColor Red
            Write-Host "Error output:" -ForegroundColor Red
            Write-Host $pushResult
        }
    } else {
        Write-Host "`n❌ Pull failed with conflicts." -ForegroundColor Red
        Write-Host "Run: git status" -ForegroundColor Yellow
    }
}

Write-Host "`nDone!" -ForegroundColor Cyan
