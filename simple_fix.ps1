$file = "c:\Users\Admin\AIX\localy\src\components\PersonalInfoEdit Screen.tsx"
$lines = Get-Content $file

for ($i = 0; $i -lt $lines.Count; $i++) {
    # Fix line 282: replace }).open(); with setIsAddressModalOpen(true);
    if ($lines[$i] -match '^\s+\}\)\.open\(\);') {
        $lines[$i] = '        setIsAddressModalOpen(true);'
        # Remove lines 273-281 and 283-285
        $lines[272] = ''
        for ($j = 273; $j -le 280; $j++) { $lines[$j] = '' }
        for ($j = 282; $j -le 284; $j++) { $lines[$j] = '' }
    }
    
    # Fix line 458: remove disabled attribute
    if ($i -eq 457 -and $lines[$i] -match 'disabled=') {
        $lines[$i] = ''
    }
    
    # Fix line 459: simplify style attribute
    if ($i -eq 458 -and $lines[$i] -match 'backgroundColor:') {
        $lines[$i] = $lines[$i] -replace ', backgroundColor: \(isEmailVerified && !emailChanged\) \? ''#f5f5f5'' : ''white''', ''
    }
}

$lines | Where-Object { $_ -ne '' } | Set-Content $file -NoNewline
Write-Host "Fixed!"
