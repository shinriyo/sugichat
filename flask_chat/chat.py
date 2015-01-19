# -*- coding: utf-8 -*-

import re
import unicodedata
from slugify import slugify
from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from socketio.mixins import RoomsMixin, BroadcastMixin
from werkzeug.exceptions import NotFound
from werkzeug import check_password_hash, generate_password_hash
from gevent import monkey
from sqlalchemy.orm import synonym
from flask import Flask, Response, request, render_template, url_for, redirect, session, flash, jsonify, abort
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


"""

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default='', nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    _password = db.Column('password', db.String(100), nullable=False)

    def _get_password(self):
        return self._password

    def _set_password(self, password):
        if password:
            password = password.strip()
        self._password = generate_password_hash(password)

    password_descriptor = property(_get_password, _set_password)
    password = synonym('_password', descriptor=password_descriptor)

    def check_password(self, password):
        password = password.strip()
        if not password:
            return False
        return check_password_hash(self.password, password)

    @classmethod
    def authenticate(cls, query, email, password):
        user = query(cls).filter(cls.email == email).first()
        if user is None:
            return None, False
        return user, user.check_password(password)

    def __repr__(self):
        return u'<User id={self.id} email={self.email!r}>'.format(
            self=self)
"""


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


def get_or_create_room(klass, **kwargs):
    """
    部屋を取得、なければ作る
    """
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
    # TODO: user name
    name = session['name']
    context.update({'name': name})

    return render_template('room.html', **context)


@app.route('/admin', methods=['POST'])
def admin():
    """
    Adminページ
    """
    return redirect(url_for('rooms'))


@app.route('/create_user', methods=['POST'])
def create_user():
    """
    ユーザの追加
    """
    return redirect(url_for('rooms'))


# http://study-flask.readthedocs.org/ja/latest/04.html
@app.route('/remove_room/<int:remove_room_id>/delete/', methods=['DELETE'])
def remove_room(remove_room_id):
    """
    部屋の削除
    """
    chat_room = ChatRoom.query.get(remove_room_id)
    if chat_room is None:
        response = jsonify({'status': 'Not Found'})
        response.status_code = 404
        return response
    db.session.delete(chat_room)
    db.session.commit()
    return jsonify({'status': 'OK'})


@app.route('/create_room', methods=['POST'])
def create_room():
    """
    Handles post from the "Add room" form on the homepage, and
    redirects to the new room.
    """
    name = request.form.get("name")
    if name:
        room, created = get_or_create_room(ChatRoom, name=name)
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

# これ使いたい
"""
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user, authenticated = User.authenticate(db.session.query,
                request.form['email'], request.form['password'])
        if authenticated:
            session['user_id'] = user.id
            flash('You were logged in')
            return redirect(url_for('show_entries'))
        else:
            flash('Invalid email or password')
    return render_template('login.html')
"""

# ログアウト
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('rooms'))


# TODO: メッセージのedit, delete
# 多分メッセージ自体のDB登録が先と思う
@app.route('/<int:user_id>/<int:message_id>/edit/', methods=['GET', 'POST'])
# @login_required
def edit_message(user_id):
    return render_template('hoge.html')


@app.route('/<int:user_id>/<int:message_id>/delete/', methods=['GET', 'POST'])
# @login_required
def delete_message(user_id):
    return render_template('hoge.html')


@app.route('/<int:user_id>/edit/', methods=['GET', 'POST'])
# @login_required
def user_detail(user_id):
    user = User.query.get(user_id)
    return render_template('user/detail.html', user=user)


@app.route('/<int:user_id>/edit/', methods=['GET', 'POST'])
# @login_required
def user_edit(user_id):
    user = User.query.get(user_id)
    if user is None:
        abort(404)
    if request.method == 'POST':
        user.name = request.form['name']
        user.email = request.form['email']
        if request.form['password']:
            user.password = request.form['password']
        # db.session.add(user)
        db.session.commit()
        return redirect(url_for('.user_detail', user_id=user_id))
    return render_template('user/edit.html', user=user)


@app.route('/create/', methods=['GET', 'POST'])
# @login_required
def user_create():
    if request.method == 'POST':
        user = User(name=request.form['name'],
                    email=request.form['email'],
                    password=request.form['password'])
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('.user_list'))
    return render_template('user/edit.html')


@app.route('/<int:user_id>/delete/', methods=['DELETE'])
# @login_required
def user_delete(user_id):
    user = User.query.get(user_id)
    if user is None:
        response = jsonify({'status': 'Not Found'})
        response.status_code = 404
        return response
    db.session.delete(user)
    db.session.commit()
    return jsonify({'status': 'OK'})


class ChatNamespace(BaseNamespace, RoomsMixin, BroadcastMixin):
    """
    チャットルーム内で使われる
    """
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
        """
        チャットルーム接続時のメッセージ
        """
        # nicknameはチャットルームに入った人の名前
        self.log(u'Nickname: {0}'.format(nickname))
        if nickname in self.nicknames:
            self.log(u"すでにいる。")

        self.nicknames.append(nickname)
        self.session['nickname'] = nickname
        # jsに送る
        self.broadcast_event('announcement', '%s has connected' % nickname)
        self.broadcast_event('nicknames', self.nicknames)
        return True, nickname

    def recv_disconnect(self):
        """
        チャットルーム切断時のメッセージ
        """
        # Remove nickname from the list.
        self.log('Disconnected')
        nickname = self.session['nickname']
        # 居る時だけ外す
        if nickname in self.nicknames:
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
