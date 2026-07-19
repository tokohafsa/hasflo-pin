@echo off
title HASflo Pinterest Tool

:: Baris conda di bawah ini dihapus atau diberi tanda "rem" (komentar)
call conda activate env_main

:: Pindah ke folder project
cd /d G:\HASFLO_PINTEREST

:: Buka Chrome setelah 3 detik
powershell -Command "Start-Sleep -Seconds 3; Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' 'http://localhost:8501'" &

:: Jalankan Streamlit
streamlit run app.py --server.headless true

pause