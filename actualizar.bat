@echo off
REM Doble clic para descargar los datos mas recientes de la SCVS y regenerar el dashboard.
cd /d "%~dp0"
python scripts\actualizar_datos.py || goto error
python scripts\generar_dashboard.py || goto error
del /q datos\_descarga_scvs.zip 2>nul
echo.
echo Listo. Datos en la carpeta "datos" y dashboard en "dashboard\Panorama_Fondos.html".
pause
exit /b 0
:error
echo.
echo Hubo un error. Revisa tu conexion a internet o si la pagina de la Superintendencia esta caida.
pause
exit /b 1
