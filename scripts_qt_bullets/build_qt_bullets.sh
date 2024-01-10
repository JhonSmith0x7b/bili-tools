#! /usr/bin/bash

# check os type windows or linux or mac
if [ "$(uname)" == "Darwin" ]; then
    echo "Mac OS X"
    pyinstaller --onefile -y ./qt_bullets.py
    cp ./.env ./dist/ && cp -r ./prompts/ ./dist/prompts && cp -r ./resources/ ./dist/resources
    echo "Done, Good Luck!"
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
    echo "Linux"
elif [ "$(expr substr $(uname -s) 1 10)" == "MINGW32_NT" ]; then
    echo "Windows"
    pyinstaller -w -y ./qt_bullets.py
    cp ./.env ./dist/qt_bullets/ && cp -r ./prompts/ ./dist/qt_bullets/prompts && cp -r ./resources/ ./dist/qt_bullets/resources
fi
