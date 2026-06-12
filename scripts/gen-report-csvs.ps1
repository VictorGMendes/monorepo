$monitoringDir="\\brsppsfpipm001.io.ad.gmfinancial.com\Shared\INBITAT\Monitoring"
$db_dirs=Get-ChildItem -Path $monitoringDir -Directory | ForEach-Object { if($_.Name -ne ".csvs"){Join-Path $monitoringDir $_.Name | Join-Path -ChildPath 'runs'}}
$argsList = @('-db') + $db_dirs + @('-o', "$monitoringDir\.csvs")

echo "Generating report CSVs"
build_rpa_report $argsList