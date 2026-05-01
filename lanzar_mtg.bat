@echo off
TITLE Lanzador MTG Forge Lab
echo 🃏 Iniciando el Laboratorio de Cartas...
echo.

:: Navegar a la carpeta del proyecto
cd /d "d:\Drive Profe Dani Diaz\IA VS\Proyectos GaiteroDade\01_MTG"

:: Ejecutar la aplicación usando el módulo de python para evitar errores de PATH
python -m streamlit run streamlit_app.py --server.port 8501 --server.address localhost

pause