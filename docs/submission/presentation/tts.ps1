param(
  [Parameter(Mandatory=$true)][string]$Json,
  [Parameter(Mandatory=$true)][string]$OutDir,
  [string]$Voice = "Microsoft David Desktop",
  [int]$Rate = 1
)
# Synthesizes one WAV per sentence with the Windows speech engine (System.Speech).
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice($Voice)
$synth.Rate = $Rate
$items = Get-Content -LiteralPath $Json -Raw -Encoding UTF8 | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
foreach ($it in $items) {
  $synth.SetOutputToWaveFile((Join-Path $OutDir ($it.id + ".wav")))
  $synth.Speak($it.text)
}
$synth.SetOutputToNull()
$synth.Dispose()
