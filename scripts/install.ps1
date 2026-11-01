[CmdletBinding()]
param(
    [string]$Source = '',
    [string[]]$Clients = @('codex', 'claude'),
    [string]$Bank = '',
    [string]$Python = '3.12',
    [switch]$Semantic,
    [switch]$Help
)
$ErrorActionPreference = 'Stop'
if ($Help) {
    Write-Output 'Install Maverick Bank: -Source PATH_OR_WHEEL -Clients codex,claude [-Bank PATH] [-Python 3.12] [-Semantic]'
    exit 0
}
if (-not $Source) { $Source = Split-Path -Parent $PSScriptRoot }
$selectedClients = @($Clients | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($selectedClients.Count -eq 0 -or @($selectedClients | Where-Object { $_ -notin @('codex','claude') }).Count -gt 0) {
    throw 'Select codex, claude, or both with -Clients.'
}
if (-not (Get-Command git -CommandType Application -ErrorAction SilentlyContinue)) {
    throw 'Git is required for local history. Install Git, reopen the terminal, and run this command again.'
}
if (Test-Path -LiteralPath $Source) { $Source = (Resolve-Path -LiteralPath $Source).Path }
$uvCommand = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue
if (-not $uvCommand) {
    $uvDirectory = if ($env:UV_UNMANAGED_INSTALL) { $env:UV_UNMANAGED_INSTALL } else { Join-Path ([Environment]::GetFolderPath('UserProfile')) '.local\bin' }
    New-Item -ItemType Directory -Path $uvDirectory -Force | Out-Null
    $uvInstaller = Join-Path $uvDirectory ('uv-install-' + [Guid]::NewGuid().ToString('N') + '.ps1')
    $previousInstall = $env:UV_UNMANAGED_INSTALL
    $previousModulePath = $env:PSModulePath
    try {
        Write-Host 'Installing uv from the official Astral distribution...'
        Invoke-WebRequest -Uri 'https://astral.sh/uv/0.12.23/install.ps1' -OutFile $uvInstaller -UseBasicParsing
        $env:UV_UNMANAGED_INSTALL = $uvDirectory
        # PowerShell 7 parents may export incompatible modules to a Windows PowerShell 5 child.
        $env:PSModulePath = (Join-Path $PSHOME 'Modules') + [IO.Path]::PathSeparator + $previousModulePath
        $shellExecutable = if ($PSVersionTable.PSEdition -eq 'Core') { Join-Path $PSHOME 'pwsh.exe' } else { Join-Path $PSHOME 'powershell.exe' }
        & $shellExecutable -NoProfile -ExecutionPolicy Bypass -File $uvInstaller
        if ($LASTEXITCODE -ne 0) { throw 'uv provisioning failed.' }
    } finally {
        $env:UV_UNMANAGED_INSTALL = $previousInstall
        $env:PSModulePath = $previousModulePath
        if (Test-Path -LiteralPath $uvInstaller) { Remove-Item -LiteralPath $uvInstaller }
    }
    $uvExecutable = Join-Path $uvDirectory 'uv.exe'
} else { $uvExecutable = $uvCommand.Source }
if (-not (Test-Path -LiteralPath $uvExecutable)) { throw 'uv executable was not installed.' }
$installArguments = @('tool', 'install', '--python', $Python, '--force')
if ($Semantic) { $installArguments += @('--with', 'fastembed>=0.7,<1') }
$installArguments += $Source
Write-Host 'Installing the isolated Maverick Bank runtime...'
& $uvExecutable @installArguments
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed. Existing memory has not been removed.' }
$binDirectory = (& $uvExecutable tool dir --bin | Select-Object -Last 1).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not locate the installed executable directory.' }
$application = Join-Path $binDirectory 'maverick-bank.exe'
if (-not (Test-Path -LiteralPath $application)) { throw "Installed executable missing: $application" }
$bankArguments = @()
if ($Bank) { $bankArguments = @('--bank', $Bank) }
& $application init @bankArguments
if ($LASTEXITCODE -ne 0) { throw 'Bank initialization failed.' }
& $application install @bankArguments --clients @selectedClients --scope user
if ($LASTEXITCODE -ne 0) { throw 'Client registration failed. Conflicting settings were preserved; inspect the message above.' }
if ($Semantic) {
    Write-Host 'Explicitly downloading and validating the local semantic model...'
    & $application semantic install @bankArguments
    if ($LASTEXITCODE -ne 0) { throw 'Semantic provisioning failed. Base memory remains installed; retry semantic install.' }
}
& $application doctor @bankArguments --mcp
if ($LASTEXITCODE -ne 0) { throw 'Installation requires attention; see the doctor report above.' }
Write-Host "Installed: $application"
Write-Host 'Start a new Claude Code or Codex session. Follow the README first-memory check; no API key is needed for the bank.'
