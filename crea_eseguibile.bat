@echo off
REM ============================================================
REM  Crea l'eseguibile Windows del Gestionale Magazzino
REM  Da eseguire su un PC Windows con Python 3.10+ installato,
REM  dentro la cartella del programma (dove si trova main.py)
REM ============================================================

echo Installazione librerie necessarie...
pip install -r requirements.txt

echo.
echo Creazione dell'eseguibile in corso...
pyinstaller --noconfirm --onefile --windowed --name "GestionaleMagazzino" main.py

echo.
echo ============================================================
echo Fatto! Trovi il programma pronto in: dist\GestionaleMagazzino.exe
echo Puoi copiare quel file dove preferisci (es. Desktop) e avviarlo
echo con un doppio click. Il file magazzino.db verra' creato accanto
echo all'eseguibile alla prima esecuzione.
echo ============================================================
pause
