# -*- coding: utf-8 -*-

from gevent import monkey

monkey.patch_all()

import time
from sqlite3 import dbapi2 as sqlite3
from threading import Thread
from flask import Flask, render_template, session, request, flash, redirect, url_for
from flask.ext.socketio import SocketIO, emit, join_room, leave_room

# configuration
USERNAME = 'admin'
PASSWORD = 'default'
TITLE = 'SugiChat'
SECRET_KEY = 'secret!'
NAMESPACE = '/test'

app = Flask(__name__)
app.debug = True
# これで設定(configuration)の変数を突っ込める
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
socketio = SocketIO(app)
thread = None

# 新・旧に対応できている
try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        time.sleep(10)
        count += 1
        socketio.emit('my response',
                      {'data': 'Server generated event', 'count': count},
                      namespace=app.config['NAMESPACE'])


def get_default_context():
    title = app.config['TITLE']
    dic = {'title': title}
    return dic


@app.route('/')
def index():
    global thread
    if thread is None:
        thread = Thread(target=background_thread)
        thread.start()

    context = get_default_context()
    return render_template('index.html', **context)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))

    context = get_default_context()
    context.update(error=error)
    return render_template('login.html', **context)


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    top = stack.top
    if not hasattr(top, 'sqlite_db'):
        sqlite_db = sqlite3.connect(app.config['DATABASE'])
        sqlite_db.row_factory = sqlite3.Row
        top.sqlite_db = sqlite_db

    return top.sqlite_db


def show_entries():
    db = get_db()
    cur = db.execute('select title, text from entries order by id desc')
    entries = cur.fetchall()
    return render_template('show_entries.html', entries=entries)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


@app.route('/room/<roomname>')
def room(roomname):
    return redirect(url_for('show_entries'))


@socketio.on('my event', namespace=app.config['NAMESPACE'])
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my response',
         {'data': message['data'], 'count': session['receive_count']})


@socketio.on('my broadcast event', namespace=app.config['NAMESPACE'])
def test_broadcast_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@socketio.on('join', namespace=app.config['NAMESPACE'])
def join(message):
    join_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my response',
         {'data': 'In rooms: ' + ', '.join(request.namespace.rooms),
          'count': session['receive_count']})


@socketio.on('leave', namespace=app.config['NAMESPACE'])
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my response',
         {'data': 'In rooms: ' + ', '.join(request.namespace.rooms),
          'count': session['receive_count']})


@socketio.on('my room event', namespace=app.config['NAMESPACE'])
def send_room_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my response',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])


@socketio.on('connect', namespace=app.config['NAMESPACE'])
def test_connect():
    emit('my response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace=app.config['NAMESPACE'])
def test_disconnect():
    print('Client disconnected')


if __name__ == '__main__':
    socketio.run(app)
