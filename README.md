SugiChat
====

Overview

## Description

Chat Application

flaskrは公式のチュートリアルのもの。
socketiochatはSocketIOのサイトから。
flask_chatはから持ってきた。

## Demo

N/A

## VS. 

ChatWork
Slack

## Requirement

Python 2.7.x
Flask

## Usage

### DB初期化

```
init_db.py
```

### DB初期化(Heroku用)

```
heroku addons:add heroku-postgresql:dev
heroku config | grep HEROKU_POSTGRESQL
```

### アプリケーションを起動

```
python app.py
```

## Install

```
pip install slugify
pip install sqlalchemy
pip install flask.ext.sqlalchemy
pip install socketio
pip install gevent
pip install gevent-socketio
pip install Flask-Security 
```

## Contribution

shinriyo

## Licence

MIT.

## Author

[shinriyo](https://github.com/shinriyo/)

