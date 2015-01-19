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

    // 他から来たメッセージ message()メソッドに送る
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

    // messageを削除(TODO: でたらめなのであとで直す)
    $(".message-delete-link").on("click", function() {
        var delete_url = $(this).attr('data-delete-url');

        $.ajax({
            url: delete_url,
            type: 'DELETE',
            success: function(response) {
                if (response.status == 'OK') {
                    // window.location = '{{ url_for('message') }}';
                } else {
                    alert('Delete failed.')
                }
            }
        });

        return false;
    });

    // messageを編集(TODO: でたらめなのであとで直す)
    $(".message-delete-link").on("click", function() {
        var edit_url = $(this).attr('data-delete-url');

        $.ajax({
            url: edit_url,
            type: 'DELETE',
            success: function(response) {
                if (response.status == 'OK') {
                    // window.location = '{{ url_for('message') }}';
                } else {
                    alert('Delete failed.')
                }
            }
        });

        return false;
    });

    // 他から来たメッセージを処理
    //function message (from, msg) {
    var message = function(from, msg) {
        //$('#lines').append($('<p>').append($('<b>').text(from), msg));
        var other_text = msg;

        // 自分の時
        if (from == 'me') {
            // TDOO: 今後削除や他の処理も入れる
            var button = '<button class="message-delete-link">edit</button>' + ' ' +
                         '<button class="message-edit-link">delete</button>';
            other_text += ' ' + button;
        }
        // TODO: 自分以外の時もボタンを作りたい
        else
        {
        }

        $('#lines').append($('<p>').append($('<b>').text(from), other_text));
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

        //function clear () {
        var clear = function() {
            $('#message').val('').focus();
        }
    });
});