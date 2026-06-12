param([parameter(Mandatory=$true)] [string] $botName )

$currentDir=$pwd.Path
$botTemplateDir="$currentDir\scripts\bot_template"
$botNameLower=$botName.ToLower()

mkdir "$currentDir\packages\bots\$botNameLower" -Force
mkdir "$currentDir\packages\bots\$botNameLower\src" -Force
mkdir "$currentDir\packages\bots\$botNameLower\src\bsc_rpa_$botNameLower" -Force
mkdir "$currentDir\packages\bots\$botNameLower\tests" -Force
mkdir "$currentDir\packages\bots\$botNameLower\tests\logs" -Force
mkdir "$currentDir\packages\bots\$botNameLower\tests\local_dbs" -Force
mkdir "$currentDir\packages\bots\$botNameLower\tests\shared_dbs" -Force

New-Item -Path "$currentDir\packages\bots\$botNameLower\src\bsc_rpa_$botNameLower\__init__.py" -ItemType File

foreach ($fileName in @(
    "pyproject.toml",
    "README.md",
    "tests\.gitignore",
    "tests\config.yaml"
)) {
    $templatePath="$botTemplateDir\$fileName"
    $destinationPath="$currentDir\packages\bots\$botNameLower\$fileName"
    if (-not (Test-Path $destinationPath -PathType Leaf)) {
        $content = (
            (Get-Content -Path $templatePath -Raw) -Replace "{botName}", $botName
        ) -Replace "{botNameLower}", $botNameLower
        New-Item -Path $destinationPath -Value $content -ItemType File 
    }
}

foreach ($fileName in @(
    "config.py",
    "main.py",
    "tasks.py"
)) {
    $templatePath="$botTemplateDir\src\bsc_rpa_example\$fileName"
    $destinationPath="$currentDir\packages\bots\$botNameLower\src\bsc_rpa_$botNameLower\$fileName"
    if (-not (Test-Path $destinationPath -PathType Leaf)) {
        $content = (
            (Get-Content -Path $templatePath -Raw) -Replace "{botName}", $botName
        ) -Replace "{botNameLower}", $botNameLower
        New-Item -Path $destinationPath -Value $content -ItemType File 
    }
}