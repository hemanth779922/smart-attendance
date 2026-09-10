@echo off
setlocal
echo ========================================================
echo  Smart Attendance System 2.0 - GitHub Push Utility
echo ========================================================
echo Repository: https://github.com/hemanth779922/smart-attendance.git
echo.

if "%~1"=="" goto prompt_or_push

:: If token provided as argument: push_to_github.bat <YOUR_GITHUB_TOKEN>
echo Pushing using provided Personal Access Token...
git push https://%~1@github.com/hemanth779922/smart-attendance.git main
goto end

:prompt_or_push
echo Choose an option:
echo  [1] Push using current Git credentials (git push origin main)
echo  [2] Clear cached credential (fixes 403 for K-24-dec) and push
echo  [3] Push with a GitHub Personal Access Token (PAT)
echo.
set /p choice="Enter option [1-3]: "

if "%choice%"=="1" (
    git push origin main
) else if "%choice%"=="2" (
    echo Deleting cached GitHub credential...
    cmdkey /delete:git:https://github.com
    echo Pushing... (a browser sign-in window may appear)
    git push origin main
) else if "%choice%"=="3" (
    set /p token="Enter your GitHub Personal Access Token (PAT): "
    git push https://!token!@github.com/hemanth779922/smart-attendance.git main
) else (
    echo Invalid selection.
)

:end
echo.
pause
