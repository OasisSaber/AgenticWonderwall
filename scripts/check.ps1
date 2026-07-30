#requires -Version 7.0

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repositoryDirectory = Split-Path -Parent $PSScriptRoot
$bashPath = $null

if ($IsWindows) {
    $programFilesDirectories = @(
        [Environment]::GetFolderPath("ProgramFiles"),
        [Environment]::GetFolderPath("ProgramFilesX86")
    ) | Where-Object { $_ }

    foreach ($directory in $programFilesDirectories) {
        $candidate = Join-Path $directory "Git\bin\bash.exe"
        if (Test-Path -LiteralPath $candidate) {
            $bashPath = $candidate
            break
        }
    }
}

if (-not $bashPath) {
    $bashCommand = Get-Command bash -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($bashCommand) {
        $bashPath = $bashCommand.Source
    }
}

if (-not $bashPath) {
    Write-Error "UNAVAILABLE: Git Bash or another compatible Bash is required."
    exit 1
}

Push-Location $repositoryDirectory
try {
    & $bashPath "scripts/check.sh"
    $validationExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

exit $validationExitCode
