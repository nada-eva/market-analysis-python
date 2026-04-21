@echo off
echo ============================================
echo   Lancement Spark Consumer - Job Market
echo ============================================

:: Variables d'environnement
set SPARK_HOME=C:\spark-3.5.8-bin-hadoop3
set JAVA_HOME=C:\Program Files\Java\jdk-21
set HADOOP_HOME=C:\hadoop
set PYSPARK_PYTHON=C:\projet_emploi\venv\Scripts\python.exe
set PYSPARK_DRIVER_PYTHON=C:\projet_emploi\venv\Scripts\python.exe
set PATH=%SPARK_HOME%\bin;%JAVA_HOME%\bin;%HADOOP_HOME%\bin;%PATH%

:: Aller dans le dossier projet
cd C:\projet_emploi

:: Activer le venv
call venv\Scripts\activate.bat

:: Vérification
echo.
echo SPARK_HOME = %SPARK_HOME%
echo JAVA_HOME  = %JAVA_HOME%
echo PYTHON     = %PYSPARK_PYTHON%
echo.

:: Lancer Spark Consumer
echo Lancement de spark_consumer.py...
echo.

spark-submit ^
  --master local[*] ^
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 ^
  spark_consumer.py

pause