@echo off
REM ============================
REM LEVELS LIVING PROJECT SETUP SCRIPT
REM ============================

echo ========================================
echo LEVELS LIVING PROJECT SETUP
echo ========================================
echo.

REM Check if Python is installed
echo 1. Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
) else (
    echo ✅ Python is installed
    python --version
)
echo.

REM Check if pip is installed
echo 2. Checking pip installation...
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip is not installed
    echo Please install pip or reinstall Python
    pause
    exit /b 1
) else (
    echo ✅ pip is installed
    pip --version
)
echo.

REM Create virtual environment
echo 3. Creating virtual environment...
if exist venv (
    echo Virtual environment already exists
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    ) else (
        echo ✅ Virtual environment created successfully
    )
)
echo.

REM Activate virtual environment
echo 4. Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
) else (
    echo ✅ Virtual environment activated
)
echo.

REM Upgrade pip
echo 5. Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install dependencies
echo 6. Installing Flask dependencies...
pip install Flask==2.3.3
pip install Flask-JWT-Extended==4.5.2
pip install Flask-CORS==4.0.0
pip install mysql-connector-python==8.1.0
pip install PyMySQL==1.1.0
pip install redis==4.6.0
pip install Werkzeug==2.3.7
pip install requests==2.31.0
pip install python-dotenv==1.0.0
pip install marshmallow==3.20.1
pip install webargs==8.3.0
pip install python-dateutil==2.8.2
pip install gunicorn==21.2.0
pip install flask-restx==1.1.0
pip install Flask-Limiter==3.5.0
pip install PyJWT==2.8.0
pip install cryptography==41.0.4
pip install email-validator==2.0.0
pip install phonenumbers==8.13.19

if errorlevel 1 (
    echo ❌ Failed to install some dependencies
    echo Trying to install from requirements.txt...
    pip install -r requirements.txt
)
echo.

REM Test imports
echo 7. Testing Python imports...
python -c "import flask; print('✅ Flask imported successfully')" 2>nul
python -c "import mysql.connector; print('✅ MySQL connector imported successfully')" 2>nul
python -c "import redis; print('✅ Redis imported successfully')" 2>nul
python -c "import jwt; print('✅ PyJWT imported successfully')" 2>nul
echo.

REM Create .env file if it doesn't exist
echo 8. Creating environment file...
if not exist .env (
    echo Creating .env file...
    (
        echo DB_HOST=localhost
        echo DB_NAME=levels_living_db
        echo DB_USER=root
        echo DB_PASSWORD=your_mysql_password_here
        echo DB_PORT=3306
        echo REDIS_HOST=localhost
        echo REDIS_PORT=6379
        echo REDIS_DB=0
        echo JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
        echo SECRET_KEY=your-flask-secret-key-change-in-production
        echo FLASK_ENV=development
        echo FLASK_DEBUG=1
    ) > .env
    echo ✅ .env file created
    echo ⚠️  Please edit .env file to set your MySQL password
) else (
    echo ✅ .env file already exists
)
echo.

REM Create VS Code folders if they don't exist
echo 9. Setting up VS Code configuration...
if not exist .vscode mkdir .vscode
echo ✅ VS Code folder ready
echo.

echo ========================================
echo ✅ SETUP COMPLETE!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env file to set your MySQL password
echo 2. Install MySQL and Redis if running locally
echo 3. Run: python UserMS/app.py (in one terminal)
echo 4. Run: python CustomerMS/app.py (in another terminal)
echo 5. Test with: python test_api.py
echo.
echo Or use Docker: docker-compose up -d
echo.
pause