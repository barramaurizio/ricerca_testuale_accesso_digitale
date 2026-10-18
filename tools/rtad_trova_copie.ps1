# RTAD - trova copie Standalone (di default SOLO elenca).
# Amico, non demone: elenca e spiega; cancella solo se chiedi -RimuoviSicuri
# e confermi digitando SI. Mai tocca le chiavi API in Roaming.
#
# Dalla 1.7.5 la stessa funzione è anche nel programma:
#   Strumenti → Trova altre copie sul PC…
# Usa questo script se il programma non parte o vuoi un controllo da console.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File rtad_trova_copie.ps1
# Opzionale:
#   ... -RimuoviSicuri
#
# NON tocca: AppData\Roaming\RTAD_Standalone (chiavi API).

param([switch]$RimuoviSicuri)

$ErrorActionPreference = "Continue"
$desktop = [Environment]::GetFolderPath("Desktop")
if (-not $desktop) { $desktop = Join-Path $env:USERPROFILE "Desktop" }
$reportPath = Join-Path $desktop "RTAD_copie_trovate.txt"

function Out-Report([string]$t) {
    Add-Content -LiteralPath $script:reportPath -Value $t -Encoding UTF8
    Write-Host $t
}

# Ricomincia sempre da zero
Set-Content -LiteralPath $reportPath -Value "RTAD - rapporto copie Standalone" -Encoding UTF8
Out-Report ("Data: {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Out-Report ("Utente: {0}" -f $env:USERNAME)
Out-Report ("PC: {0}" -f $env:COMPUTERNAME)
Out-Report ""

Out-Report "=== 1) Installazioni nel Registro (Installer) ==="
$regHits = 0
$uninstRoots = @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*"
)
foreach ($root in $uninstRoots) {
    Get-ItemProperty $root -ErrorAction SilentlyContinue | Where-Object {
        $_.DisplayName -and ($_.DisplayName -match "Ricerca Testuale|Accesso Digitale")
    } | ForEach-Object {
        $regHits++
        Out-Report ("- {0}  (v{1})" -f $_.DisplayName, $_.DisplayVersion)
        if ($_.InstallLocation) { Out-Report ("    Cartella: {0}" -f $_.InstallLocation) }
        if ($_.UninstallString) { Out-Report ("    Disinstalla: {0}" -f $_.UninstallString) }
    }
}
if ($regHits -eq 0) { Out-Report "(nessuna voce Installer nel Registro)" }

Out-Report ""
Out-Report "=== 2) File .exe tipici ==="
$roots = @(
    (Join-Path $env:USERPROFILE "Downloads"),
    (Join-Path $env:USERPROFILE "Desktop"),
    (Join-Path $env:USERPROFILE "Documents"),
    (Join-Path $env:USERPROFILE "OneDrive\Downloads"),
    (Join-Path $env:USERPROFILE "OneDrive\Desktop"),
    (Join-Path $env:LOCALAPPDATA "Programs"),
    $env:ProgramFiles,
    ${env:ProgramFiles(x86)}
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

$patterns = @(
    "Ricerca Testuale Accesso Digitale.exe",
    "RicercaTestualeAccessoDigitale_Portable*.exe",
    "Ricerca_Testuale_v*.exe",
    "Setup_RicercaTestualeAccessoDigitale*.exe"
)

$found = @()
foreach ($root in $roots) {
    foreach ($pat in $patterns) {
        try {
            Get-ChildItem -Path $root -Filter $pat -File -Recurse -Depth 4 -Force -ErrorAction SilentlyContinue |
                ForEach-Object { $found += $_ }
        } catch {}
    }
}
$found = $found | Sort-Object FullName -Unique
if (-not $found -or $found.Count -eq 0) {
    Out-Report "(nessun exe tipico trovato)"
} else {
    foreach ($f in $found) {
        Out-Report ("- {0}" -f $f.FullName)
        Out-Report ("    Modificato: {0}  Byte: {1}" -f $f.LastWriteTime, $f.Length)
    }
}

Out-Report ""
Out-Report "=== 3) Scorciatoie .lnk sul Desktop ==="
try {
    $sh = New-Object -ComObject WScript.Shell
    foreach ($desk in @($desktop, (Join-Path $env:USERPROFILE "OneDrive\Desktop")) | Select-Object -Unique) {
        if (-not (Test-Path $desk)) { continue }
        Get-ChildItem -LiteralPath $desk -Filter "*.lnk" -Force -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $t = $sh.CreateShortcut($_.FullName).TargetPath
                if ($t -and ($t -match "Ricerca Testuale|RicercaTestuale|Ricerca_Testuale")) {
                    Out-Report ("- {0}" -f $_.FullName)
                    Out-Report ("    Punta a: {0}" -f $t)
                }
            } catch {}
        }
    }
} catch {
    Out-Report "(impossibile leggere scorciatoie)"
}

Out-Report ""
Out-Report "=== Note ==="
Out-Report "- NON cancellare: %AppData%\Roaming\RTAD_Standalone (chiavi API)."
Out-Report "- Installer: Impostazioni Windows -> App -> disinstalla, oppure unins000.exe."
Out-Report "- Portable/Download/Desktop: si possono cancellare."
Out-Report ""
Out-Report ("FINE RAPPORTO. File: {0}" -f $reportPath)
Write-Host ""
Write-Host "OK. Apri il file sul Desktop: RTAD_copie_trovate.txt"
Write-Host "Deve iniziare con: RTAD - rapporto copie Standalone"
Write-Host "e finire con: FINE RAPPORTO."

if ($RimuoviSicuri) {
    Write-Host ""
    Write-Host "Modalita RimuoviSicuri: solo Download/Desktop/Portable (NON Installer)."
    $safeRoots = @(
        (Join-Path $env:USERPROFILE "Downloads"),
        (Join-Path $env:USERPROFILE "Desktop"),
        (Join-Path $env:USERPROFILE "OneDrive\Downloads"),
        (Join-Path $env:USERPROFILE "OneDrive\Desktop")
    ) | Where-Object { $_ -and (Test-Path $_) }

    $toDelete = @()
    foreach ($f in $found) {
        $inSafe = $false
        foreach ($sr in $safeRoots) {
            if ($f.FullName.StartsWith($sr, [StringComparison]::OrdinalIgnoreCase)) { $inSafe = $true; break }
        }
        $name = $f.Name
        $looksPortable = ($name -match "Portable" -or $name -match "^Ricerca_Testuale_v" -or $name -match "^Setup_Ricerca")
        if (($inSafe -or $looksPortable) -and ($f.FullName -notmatch "\\Local\\Programs\\|\\Program Files")) {
            $toDelete += $f
        }
    }
    if (-not $toDelete) {
        Write-Host "Nessun file sicuro da rimuovere automaticamente."
        exit 0
    }
    Write-Host "Proposti:"
    $toDelete | ForEach-Object { Write-Host ("  {0}" -f $_.FullName) }
    $ans = Read-Host "Confermi cancellazione? Digita SI e Invio"
    if ($ans -ne "SI") { Write-Host "Annullato."; exit 0 }
    foreach ($f in $toDelete) {
        try {
            Remove-Item -LiteralPath $f.FullName -Force
            Write-Host ("Cancellato: {0}" -f $f.FullName)
        } catch {
            Write-Host ("NON cancellato: {0}" -f $f.FullName)
        }
    }
}
