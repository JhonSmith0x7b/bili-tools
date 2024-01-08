
cp -f ./.env ./dist/qt_bullets/ 
cp -rf ./prompts/ ./dist/qt_bullets/prompts
cp -rf ./resources/ ./dist/qt_bullets/resources
pyinstaller -w -y ./qt_bullets.py
