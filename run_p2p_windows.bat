@echo off
:: ============================================================================
:: P2P File Sharing - Script de lancement Windows
:: Téléchargez et exécutez ce script pour démarrer votre peer
:: ============================================================================

title P2P File Sharing - Installation

color 0B
echo.
echo ========================================================================
echo          P2P File Sharing - Installation et Demarrage
echo ========================================================================
echo.

:: Vérifier les privilèges admin (optionnel)
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Execute en tant qu'administrateur
) else (
    echo [INFO] Non execute en tant qu'administrateur
    echo        Certaines fonctionnalites peuvent etre limitees
)
echo.

:: Vérifier Python
echo [INFO] Verification de Python...
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Python est installe
    set PYTHON_CMD=python
    goto :python_ok
)

python3 --version >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Python3 est installe
    set PYTHON_CMD=python3
    goto :python_ok
)

echo [ERREUR] Python n'est pas installe !
echo.
echo Telechargez Python depuis : https://www.python.org/downloads/
echo.
echo IMPORTANT: Cochez "Add Python to PATH" lors de l'installation !
echo.
pause
exit /b 1

:python_ok
echo.

:: Demander le mode d'installation
echo ========================================================================
echo                      Mode d'Installation
echo ========================================================================
echo.
echo 1) Installation complete (Tracker + Peer)
echo    Pour heberger votre propre reseau P2P
echo.
echo 2) Peer uniquement
echo    Pour rejoindre un reseau P2P existant
echo.
set /p INSTALL_MODE="Votre choix [1-2] : "

if "%INSTALL_MODE%"=="1" (
    set MODE=full
    echo [INFO] Installation complete selectionnee
) else if "%INSTALL_MODE%"=="2" (
    set MODE=peer
    echo [INFO] Installation Peer uniquement
) else (
    echo [ERREUR] Choix invalide
    pause
    exit /b 1
)
echo.

:: Créer le répertoire d'installation
set INSTALL_DIR=%USERPROFILE%\.p2p_file_sharing
echo [INFO] Installation dans : %INSTALL_DIR%

if exist "%INSTALL_DIR%" (
    echo [ATTENTION] Le repertoire existe deja
    set /p REINSTALL="Voulez-vous reinstaller ? [o/N] : "
    if /i "%REINSTALL%"=="o" (
        rmdir /s /q "%INSTALL_DIR%"
        echo [OK] Ancien repertoire supprime
    ) else (
        echo [INFO] Utilisation de l'installation existante
    )
)

mkdir "%INSTALL_DIR%" 2>nul
cd /d "%INSTALL_DIR%"

:: Télécharger les fichiers (si nécessaire)
if not exist "requirements.txt" (
    echo [INFO] Telechargement des fichiers...
    echo.
    echo [ERREUR] Veuillez telecharger manuellement les fichiers depuis GitHub :
    echo    git clone https://github.com/VOTRE-REPO/p2p-file-sharing.git "%INSTALL_DIR%"
    echo.
    echo Ou telechargez le ZIP et extrayez-le dans :
    echo    %INSTALL_DIR%
    echo.
    pause
    exit /b 1
)

:: Créer un environnement virtuel
echo [INFO] Creation de l'environnement virtuel...
if not exist "venv" (
    %PYTHON_CMD% -m venv venv
    echo [OK] Environnement virtuel cree
) else (
    echo [OK] Environnement virtuel existe deja
)

:: Activer l'environnement virtuel
call venv\Scripts\activate.bat

:: Installer les dépendances
echo [INFO] Installation des dependances...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1
echo [OK] Dependances installees
echo.

:: Configuration
echo [INFO] Configuration...

if "%MODE%"=="full" (
    set /p TRACKER_PORT="Port du Tracker [5000] : "
    if "%TRACKER_PORT%"=="" set TRACKER_PORT=5000
    
    set /p PEER_PORT="Port du Peer [8001] : "
    if "%PEER_PORT%"=="" set PEER_PORT=8001
    
    set TRACKER_URL=http://localhost:%TRACKER_PORT%
) else (
    set /p TRACKER_URL="URL du Tracker [http://localhost:5000] : "
    if "%TRACKER_URL%"=="" set TRACKER_URL=http://localhost:5000
    
    set /p PEER_PORT="Port du Peer [8001] : "
    if "%PEER_PORT%"=="" set PEER_PORT=8001
)
echo.

:: Créer les répertoires nécessaires
mkdir data\shared_files 2>nul
mkdir data\downloads 2>nul
mkdir logs 2>nul

:: Démarrer les services
echo ========================================================================
echo                           Demarrage
echo ========================================================================
echo.

if "%MODE%"=="full" (
    echo [INFO] Demarrage du Tracker...
    start "P2P Tracker" /min cmd /c "python -m tracker.app > logs\tracker.log 2>&1"
    timeout /t 3 /nobreak >nul
    echo [OK] Tracker demarre
)

echo [INFO] Demarrage du Peer...
start "P2P Peer" /min cmd /c "python -m peer.app > logs\peer.log 2>&1"
timeout /t 3 /nobreak >nul
echo [OK] Peer demarre

echo.
echo ========================================================================
echo                    Installation Reussie !
echo ========================================================================
echo.
echo [OK] Votre peer P2P est maintenant actif !
echo.
echo Interfaces Web :
if "%MODE%"=="full" (
    echo    - Tracker Dashboard : http://localhost:%TRACKER_PORT%
)
echo    - Peer Interface    : http://localhost:%PEER_PORT%
echo.
echo Repertoires :
echo    - Fichiers partages : %INSTALL_DIR%\data\shared_files
echo    - Telechargements   : %INSTALL_DIR%\data\downloads
echo    - Logs              : %INSTALL_DIR%\logs
echo.
echo Commandes utiles :
echo    - Voir les logs      : type %INSTALL_DIR%\logs\peer.log
echo    - Arreter le peer    : %INSTALL_DIR%\stop_p2p.bat
echo    - Redemarrer         : %INSTALL_DIR%\restart_p2p.bat
echo.

:: Créer le script d'arrêt
echo @echo off > stop_p2p.bat
echo taskkill /FI "WINDOWTITLE eq P2P Peer*" /F ^>nul 2^>^&1 >> stop_p2p.bat
echo if "%%MODE%%"=="full" taskkill /FI "WINDOWTITLE eq P2P Tracker*" /F ^>nul 2^>^&1 >> stop_p2p.bat
echo echo [OK] Services arretes >> stop_p2p.bat
echo pause >> stop_p2p.bat

:: Créer le script de redémarrage
echo @echo off > restart_p2p.bat
echo call stop_p2p.bat >> restart_p2p.bat
echo timeout /t 2 /nobreak ^>nul >> restart_p2p.bat
echo call run_p2p_windows.bat >> restart_p2p.bat

echo [OK] Scripts de gestion crees
echo.
echo Appuyez sur une touche pour ouvrir l'interface web...
pause >nul

:: Ouvrir le navigateur
if "%MODE%"=="full" (
    start http://localhost:%TRACKER_PORT%
) else (
    start http://localhost:%PEER_PORT%
)

echo.
echo [INFO] Interface web ouverte dans votre navigateur
echo.
pause
