param([parameter(ValueFromRemainingArguments=$true)] [string[]] $bots )

$currentDir=$pwd.Path
$buildScript="$currentDir\scripts\build.py"

$wheelhouse="\\brsppsfpipm001.io.ad.gmfinancial.com\Shared\INBITAT\Releases\wheelhouse"
$templateDir="\\brsppsfpipm001.io.ad.gmfinancial.com\Shared\INBITAT\Releases\config_templates"

# $wheelhouse="$currentDir\dist"
# $templateDir="$currentDir\dist\config_templates"

foreach ($bot in $bots) {
    $botPyprojectToml="$currentDir\packages\bots\$bot\pyproject.toml"
    if (-not (Test-Path $botPyprojectToml -PathType Leaf)) {
        throw [System.IO.FileNotFoundException] "Invalid path for bot '$bot': $botPyprojectToml not found."
    }
}

python $buildScript $bots --output $wheelhouse

foreach ($bot in $bots) {
    $writeTemplateCmd="write_$bot" + "_config_template"
    $templatePath="$templateDir\$bot" + "_config.yaml"
    & $writeTemplateCmd -o $templatePath
}