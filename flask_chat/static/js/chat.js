$(function() {

    //var WEB_SOCKET_SWF_LOCATION = '/static/js/socketio/WebSocketMain.swf',
    //    socket = io.connect('/chat');
    var socket = io.connect('/chat');

    socket.on('connect', function () {
        $('#chat').addClass('connected');
        socket.emit('join', window.room);

        // chat.py on_nickname()
        socket.emit('nickname', $('#nick').val(), function (set) {
            console.log("my nick: " + $('#nick').val());
            if (set) {
                return $('#chat').addClass('nickname-set');
            }
        });
        return false;
    });

    socket.on('announcement', function (msg) {
        $('#lines').append($('<p>').append($('<em>').text(msg)));
    });

    socket.on('nicknames', function (nicknames) {
        $('#nicknames').empty().append($('<span>Online: </span>'));

        // 重複を削除したリスト
        var nicknames = nicknames.filter(function (x, i, self) {
            return self.indexOf(x) === i;
        });

        for (var i in nicknames) {
            $('#nicknames').append($('<b>').text(nicknames[i]));
        }
    });

    socket.on('msg_to_room', message);

    socket.on('reconnect', function () {
        $('#lines').remove();
        message('System', 'Reconnected to the server');
    });

    socket.on('reconnecting', function () {
        message('System', 'Attempting to re-connect to the server');
    });

    socket.on('error', function (e) {
        message('System', e ? e : 'A unknown error occurred');
    });

    function message (from, msg) {
        $('#lines').append($('<p>').append($('<b>').text(from), msg));
    }

    // DOM manipulation
    $(function () {
        $('#set-nickname').submit(function (ev) {
            socket.emit('nickname', $('#nick').val(), function (set) {
                if (set) {
                    clear();
                    return $('#chat').addClass('nickname-set');
                }
                $('#nickname-err').css('visibility', 'visible');
            });
            return false;
        });

        $('#send-message').submit(function () {
            message('me', $('#message').val());
            socket.emit('user message', $('#message').val());
            clear();
            $('#lines').get(0).scrollTop = 10000000;
            return false;
        });

        function clear () {
            $('#message').val('').focus();
        }
    });

});