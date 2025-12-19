$filePath = "c:\Users\Admin\AIX\localy\src\components\PersonalInfoEditScreen.tsx"
$content = Get-Content $filePath -Raw

# Fix 1: Replace the handleSearchAddress body to use modal
$pattern1 = '(?s)(const handleSearchAddress = \(\) => \{)\s+if \(window\.daum && window\.daum\.Postcode\) \{[^}]+\}\.open\(\);\s+\} else \{[^}]+\}\s+(\};)'
$replacement1 = '$1' + "`r`n        setIsAddressModalOpen(true);`r`n    " + '$2'
$content = $content -replace $pattern1, $replacement1

# Fix 2: Remove disabled attribute from email input
$content = $content -replace 'disabled=\{isEmailVerified && !emailChanged\}\s+', ''

# Fix 3: Simplify email input style
$content = $content -replace 'style=\{\{ \.\.\.inputStyle, backgroundColor: \(isEmailVerified && !emailChanged\) \? ''#f5f5f5'' : ''white'' \}\}', 'style={inputStyle}'

Set-Content $filePath -Value $content -NoNewline
Write-Host "File updated successfully!"
