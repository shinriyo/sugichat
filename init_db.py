# -*- coding: utf-8 -*-

def init():
    # これがないとエラーが出る
    import sys
    if 'threading' in sys.modules:
        del sys.modules['threading']
    import gevent
    import gevent.socket
    import gevent.monkey
    gevent.monkey.patch_all()

    # DBの初期化(dbファイルが有れば先に消して行う)
    import chat
    chat.init_db()

    # admin追加
    from chat import User
    user = User(name='Admin', password='default', email='shinriyo@gmail.com')
    user.save()


if __name__ == '__main__':
    # rm /tmp/chat.db
    # をしたあと
    init()
