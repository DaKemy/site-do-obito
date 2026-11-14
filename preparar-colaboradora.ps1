[CmdletBinding()]
param(
    [string]$Destination = (Join-Path $HOME 'source\site-do-obito'),
    [switch]$SkipOpen
)

$ErrorActionPreference = 'Stop'
$repositoryUrl = 'https://github.com/DaKemy/site-do-obito.git'

function Get-GitExecutable {
    $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    if ($gitCommand) {
        return $gitCommand.Source
    }

    $wingetCommand = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wingetCommand) {
        throw 'Git nao esta instalado e winget nao esta disponivel. Instale Git for Windows em https://git-scm.com/download/win e execute o script novamente.'
    }

    $answer = Read-Host 'Git for Windows e necessario para baixar e sincronizar o projeto. Instalar com winget agora? (S/N)'
    if ($answer -notmatch '^(s|sim)$') {
        throw 'Instalacao cancelada. Instale Git for Windows e execute o script novamente.'
    }

    & $wingetCommand.Source install --id Git.Git --exact --source winget | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw 'O winget nao conseguiu instalar Git. Instale Git for Windows pelo site oficial e tente novamente.'
    }

    $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    if ($gitCommand) {
        return $gitCommand.Source
    }

    $knownGitPaths = @(
        (Join-Path $env:ProgramFiles 'Git\cmd\git.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Git\cmd\git.exe')
    )
    foreach ($gitPath in $knownGitPaths) {
        if (Test-Path -LiteralPath $gitPath) {
            return $gitPath
        }
    }

    throw 'Git foi instalado, mas este terminal ainda nao o encontrou. Feche e reabra o PowerShell e execute o script novamente.'
}

function Invoke-Git {
    param([string[]]$Arguments)

    & $script:gitExecutable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "O comando git falhou: git $($Arguments -join ' ')"
    }
}

$gitExecutable = Get-GitExecutable
$Destination = [System.IO.Path]::GetFullPath($Destination)
$script:gitExecutable = $gitExecutable

$scriptRepositoryRoot = Split-Path -Parent $PSScriptRoot
if (Test-Path -LiteralPath (Join-Path $scriptRepositoryRoot '.git')) {
    $repositoryPath = $scriptRepositoryRoot
}
else {
    $repositoryPath = $Destination
}

if (Test-Path -LiteralPath $repositoryPath) {
    if (-not (Test-Path -LiteralPath (Join-Path $repositoryPath '.git'))) {
        throw "A pasta de destino ja existe e nao e um clone Git. Nenhum arquivo foi alterado: $repositoryPath"
    }

    $originUrl = (& $gitExecutable -C $repositoryPath remote get-url origin).Trim().TrimEnd('/')
    $normalizedOrigin = $originUrl -replace '\.git$', ''
    $normalizedRepository = $repositoryUrl -replace '\.git$', ''
    if ($LASTEXITCODE -ne 0 -or $normalizedOrigin -ne $normalizedRepository) {
        throw "O clone existente nao aponta para o repositorio esperado. Nenhum remote foi alterado: $repositoryPath"
    }

    $workingChanges = @(& $gitExecutable -C $repositoryPath status --porcelain)
    if ($LASTEXITCODE -ne 0) {
        throw 'Nao foi possivel verificar o estado do clone Git.'
    }

    if ($workingChanges.Count -gt 0) {
        Write-Warning 'Ha alteracoes locais nao salvas. Para protege-las, nao atualizei a branch automaticamente.'
        Write-Host "Depois de salvar ou enviar suas alteracoes, rode: git -C `"$repositoryPath`" pull --ff-only origin main"
    }
    else {
        Invoke-Git -Arguments @('-C', $repositoryPath, 'fetch', 'origin', 'main')
        $currentBranch = (& $gitExecutable -C $repositoryPath branch --show-current).Trim()
        if ($LASTEXITCODE -ne 0) {
            throw 'Nao foi possivel identificar a branch atual.'
        }

        if ($currentBranch -eq 'main') {
            Invoke-Git -Arguments @('-C', $repositoryPath, 'pull', '--ff-only', 'origin', 'main')
        }
        else {
            Write-Host "Clone atualizado: origin/main foi buscada; sua branch atual e '$currentBranch' e nao foi alterada."
            Write-Host "Para incorporar atualizacoes de main sem reescrever seu historico: git -C `"$repositoryPath`" merge origin/main"
        }
    }
}
else {
    $parentDirectory = Split-Path -Parent $repositoryPath
    New-Item -ItemType Directory -Force -Path $parentDirectory | Out-Null
    Invoke-Git -Arguments @('clone', '--branch', 'main', '--single-branch', $repositoryUrl, $repositoryPath)
}

$workspacePath = Join-Path $repositoryPath 'versoes\0.0.2'
if (-not (Test-Path -LiteralPath (Join-Path $workspacePath 'mvp-tattoo\app.py'))) {
    throw "O clone nao contem os arquivos esperados da versao 0.0.2: $workspacePath"
}

Write-Host ''
Write-Host 'Projeto pronto para abrir no VS Code.'
Write-Host "Pasta atual do site: $workspacePath"
Write-Host 'O clone publico nao exige senha para baixar. Para enviar commits, entre no GitHub pelo VS Code ou Git Credential Manager.'
Write-Host 'As alteracoes nao sao enviadas automaticamente: crie uma branch, faca commit e envie um Pull Request.'
Write-Host 'Nao compartilhe nem envie arquivos .env, bancos locais ou uploads.'

if (-not $SkipOpen) {
    $codeCommand = Get-Command code -ErrorAction SilentlyContinue
    $codeExecutable = if ($codeCommand) { $codeCommand.Source } else { $null }
    if (-not $codeCommand) {
        $knownCodePaths = @(
            (Join-Path $env:LOCALAPPDATA 'Programs\Microsoft VS Code\bin\code.cmd'),
            (Join-Path $env:ProgramFiles 'Microsoft VS Code\bin\code.cmd')
        )
        foreach ($codePath in $knownCodePaths) {
            if (Test-Path -LiteralPath $codePath) {
                $codeExecutable = $codePath
                break
            }
        }
    }

    if ($codeExecutable) {
        & $codeExecutable --new-window $workspacePath
    }
    else {
        Write-Warning 'O comando code nao foi encontrado. Abra manualmente a pasta versoes\0.0.2 no VS Code.'
    }
}
