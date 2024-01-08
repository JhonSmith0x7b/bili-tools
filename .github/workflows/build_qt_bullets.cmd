

xcopy ./prompt/ ./dist/qt_bullets/prompt/
xcopy ./resources/ ./dist/qt_bullets/resources/
copy ./.env ./dist/qt_bullets/

pyinstaller -w -y ./qt_bullets.py

