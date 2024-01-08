
cp ./.env ./dist/qt_bullets/ 
cp -r ./prompts/ ./dist/qt_bullets/prompts
cp -r ./resources/ ./dist/qt_bullets/resources
pyinstaller -w -y ./qt_bullets.py
