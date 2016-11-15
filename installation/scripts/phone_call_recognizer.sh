#! /bin/bash

HOME_DIR=/home/yurburo
APP_DIR=/home/yurburo/service

export GOOGLE_APPLICATION_CREDENTIALS=$HOME_DIR/google_speech_api_key.json

cd $APP_DIR/srv/speech_recognition &&
$APP_DIR/bin/python ./phone_call_recognizer.py



