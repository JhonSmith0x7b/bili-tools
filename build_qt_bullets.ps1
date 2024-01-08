
pyinstaller -w -y ./qt_bullets.py

Copy-Item ./.env -Destination ./dist/qt_bullets -Force
Copy-Item -Path ./prompts/ -Destination ./dist/qt_bullets/prompts -Force
Copy-Item -Path ./resources/ -Destination ./dist/qt_bullets/resources/ -Force
