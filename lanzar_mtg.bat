@echo off
TITLE Lanzador MTG Forge Lab
echo 🃏 Iniciando el Laboratorio de Cartas...
echo.

:: Navegar a la carpeta del proyecto (ruta relativa al .bat)
cd /d "%~dp0"

:: Ejecutar la aplicación usando el módulo de python para evitar errores de PATH
python -m streamlit run streamlit_app.py --server.port 8501 --server.address localhost

pause