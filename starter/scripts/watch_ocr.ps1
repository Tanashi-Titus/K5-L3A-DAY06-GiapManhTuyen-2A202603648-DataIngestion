$ErrorActionPreference = 'SilentlyContinue'
$ocrPath = Join-Path (Split-Path $PSScriptRoot -Parent) '..\results\ocr.json'
$ocrPath = [System.IO.Path]::GetFullPath($ocrPath)

while ($true) {
    Clear-Host
    Write-Host 'DAY 06 - OCR PROGRESS' -ForegroundColor Cyan
    Write-Host ('Updated: {0}' -f (Get-Date -Format 'HH:mm:ss dd/MM/yyyy'))
    Write-Host ('File:    {0}' -f $ocrPath)
    Write-Host ''

    if (Test-Path -LiteralPath $ocrPath) {
        try {
            $data = Get-Content -LiteralPath $ocrPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $completed = @($data.pages).Count
            $total = [int]$data.page_count
            $latest = if ($completed -gt 0) { $data.pages[-1].page } else { '-' }
            $lines = (@($data.pages) | ForEach-Object { @($_.lines).Count } | Measure-Object -Sum).Sum
            $percent = if ($total -gt 0) { [math]::Round(100 * $completed / $total, 1) } else { 0 }
            $barWidth = 40
            $filled = [math]::Floor($barWidth * $completed / [math]::Max($total, 1))
            $bar = ('#' * $filled).PadRight($barWidth, '-')

            Write-Host ('[{0}] {1}%  ({2}/{3} pages)' -f $bar, $percent, $completed, $total) -ForegroundColor Green
            Write-Host ('Latest page: {0}' -f $latest)
            Write-Host ('OCR lines:   {0}' -f $lines)

            if ($completed -ge $total) {
                Write-Host ''
                Write-Host 'OCR COMPLETE. You may close this window.' -ForegroundColor Green
                break
            }
        }
        catch {
            Write-Host 'OCR output is currently being updated; retrying...' -ForegroundColor Yellow
        }
    }
    else {
        Write-Host 'Waiting for results\ocr.json...' -ForegroundColor Yellow
    }

    $ocrProcess = Get-Process python -ErrorAction SilentlyContinue
    Write-Host ''
    Write-Host ('Python OCR process: {0}' -f $(if ($ocrProcess) { 'RUNNING' } else { 'NOT FOUND' }))
    Write-Host 'Press Ctrl+C to stop this monitor only (OCR keeps running).'
    Start-Sleep -Seconds 3
}

Read-Host 'Press Enter to close'
