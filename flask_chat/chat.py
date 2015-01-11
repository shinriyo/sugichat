# -*- coding: utf-8 -*-

import re
import unicodedata
from slugify import slugify
from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from socketio.mixins import RoomsMixin, BroadcastMixin
from werkzeug.exceptions import NotFound
from gevent import monkey

from flask import Flask, Response, request, render_template, url_for, redirect, session, flash
from flask.ext.sqlalchemy import SQLAlchemy

monkey.patch_all()

app = Flask(__name__)
app.debug = True

# configuration
TITLE = 'SugiChat'
# これ入れないとloginできない
SECRET_KEY = 'development key'
SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/chat.db'

app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

db = SQLAlchemy(app)


# models
class ChatRoom(db.Model):
    __tablename__ = 'chatrooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    slug = db.Column(db.String(50))
    users = db.relationship('ChatUser', backref='chatroom', lazy='dynamic')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return url_for('room', slug=self.slug)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        db.session.add(self)
        db.session.commit()


class ChatUser(db.Model):
    """
    チャットルーム内のユーザ
    """
    __tablename__ = 'chatusers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    # TODO: nameの代わりにする？
    # user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    session = db.Column(db.String(20), nullable=False)
    chatroom_id = db.Column(db.Integer, db.ForeignKey('chatrooms.id'))

    def __unicode__(self):
        return self.name


# TODO: 後で使う
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(20), nullable=False)
    # こちらは実際の名前
    name = db.Column(db.String(20), nullable=False)

    def save(self, *args, **kwargs):
        db.session.add(self)
        db.session.commit()

    def __unicode__(self):
        return self.username


def get_default_context():
    title = app.config['TITLE']
    dic = {'title': title}
    return dic


import six
# Extra characters outside of alphanumerics that we'll allow.
SLUG_OK = '-_~'


def smart_text(s, encoding='utf-8', errors='strict'):
    if isinstance(s, six.text_type):
        return s

    if not isinstance(s, six.string_types):
        if six.PY3:
            if isinstance(s, bytes):
                s = six.text_type(s, encoding, errors)
            else:
                s = six.text_type(s)
        elif hasattr(s, '__unicode__'):
            s = six.text_type(s)
        else:
            s = six.text_type(bytes(s), encoding, errors)
    else:
        s = six.text_type(s)
    return s


def get_object_or_404(klass, **query):
    instance = klass.query.filter_by(**query).first()
    if not instance:
        raise NotFound()
    return instance


def get_or_create(klass, **kwargs):
    try:
        return get_object_or_404(klass, **kwargs), False
    except NotFound:
        instance = klass(**kwargs)
        instance.save()
        return instance, True


def init_db():
    db.create_all(app=app)


# views
@app.route('/')
def rooms():
    """
    Homepage - lists all rooms.
    """
    context = {"rooms": ChatRoom.query.all()}
    default_context = get_default_context()
    context.update(default_context)
    return render_template('rooms.html', **context)


import os
from flask import send_from_directory


@app.route('/<path:slug>')
def room(slug):
    """
    Show a room.
    """
    context = {"room": get_object_or_404(ChatRoom, slug=slug)}
    default_context = get_default_context()
    context.update(default_context)
    return render_template('room.html', **context)


@app.route('/create', methods=['POST'])
def create():
    """
    Handles post from the "Add room" form on the homepage, and
    redirects to the new room.
    """
    name = request.form.get("name")
    if name:
        room, created = get_or_create(ChatRoom, name=name)
        return redirect(url_for('room', slug=room.slug))
    return redirect(url_for('rooms'))


# ログイン
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # DBでやる
        username = request.form['username']
        password = request.form['password']
        where = User.username == username
        # ユーザ名だけでまず検索
        res = db.session.query(User).filter(where)
        print "-"*100
        print (res.count())

        # ユーザ調べる
        if res.count() > 0:
            where = User.password == password
            res = res.filter(where)
            # パスワード調べる
            if res.count() > 0:
                session['logged_in'] = True
                # ユーザの名前入れておく
                session['name'] = res[0].name
                flash('You were logged in')
                return redirect(url_for('rooms'))
            else:
                error = 'Invalid password'
        else:
            error = 'Invalid username'

    context = get_default_context()
    context.update(error=error)
    return render_template('login.html', **context)


# ログアウト
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('rooms'))


class ChatNamespace(BaseNamespace, RoomsMixin, BroadcastMixin):
    nicknames = []

    def initialize(self):
        self.logger = app.logger
        self.log("Socketio session started")

    def log(self, message):
        self.logger.info(u"[{0}] {1}".format(self.socket.sessid, message))

    def on_join(self, room):
        self.room = room
        self.join(room)
        return True

    def on_nickname(self, nickname):
        self.log(u'Nickname: {0}'.format(nickname))
        self.nicknames.append(nickname)
        self.session['nickname'] = nickname
        self.broadcast_event('announcement', '%s has connected' % nickname)
        self.broadcast_event('nicknames', self.nicknames)
        return True, nickname

    def recv_disconnect(self):
        # Remove nickname from the list.
        self.log('Disconnected')
        nickname = self.session['nickname']
        self.nicknames.remove(nickname)
        self.broadcast_event('announcement', '%s has disconnected' % nickname)
        self.broadcast_event('nicknames', self.nicknames)
        self.disconnect(silent=True)
        return True

    def on_user_message(self, msg):
        self.log(u'User message: {0}'.format(msg))
        self.emit_to_room(self.room, 'msg_to_room',
                          self.session['nickname'], msg)
        return True


@app.route('/socket.io/<path:remaining>')
def socketio(remaining):
    try:
        socketio_manage(request.environ, {'/chat': ChatNamespace}, request)
    except:
        app.logger.error("Exception while handling socketio connection",
                         exc_info=True)
    return Response()


if __name__ == '__main__':
    app.run()
