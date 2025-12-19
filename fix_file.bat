@echo off
setlocal enabledelayedexpansion

set "file=src\components\PersonalInfoEditScreen.tsx"
set "temp=src\components\PersonalInfoEditScreen_temp.tsx"

(
    set "skip=0"
    for /f "delims=" %%a in ('type "%file%"') do (
        set "line=%%a"
        
        REM Fix 1: Change handleSearchAddress
        echo !line! | findstr /C:"}).open();" >nul
        if !errorlevel!==0 (
            echo         setIsAddressModalOpen(true);
            set "skip=3"
        ) else if !skip! gtr 0 (
            set /a skip-=1
        ) else (
            REM Fix 2: Remove disabled line
            echo !line! | findstr /C:"disabled={isEmailVerified" >nul
            if !errorlevel! neq 0 (
                REM Fix 3: Simplify style
                set "line=!line:, backgroundColor: (isEmailVerified && !emailChanged) ? '#f5f5f5' : 'white'=!"
                echo !line!
            )
        )
    )
) > "%temp%"

move /y "%temp%" "%file%"
echo Fixed!
