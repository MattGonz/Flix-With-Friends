import flask
import flask_socketio

from db_models.message import Message
from db_models.room import Room
from db_models.user import User
from db_models.video import Video
from db_models.room_video_playlist import RoomVideoPlaylist
from db_models.room_allowed_users import RoomAllowedUsers

import socketns
import socketns.base
import socketns.chat
import socketns.login
import socketns.youtube
import socketns.room

MESSAGES_EMIT_CHANNEL = 'messages_received'


class FlaskServer:
    def __init__(self, app, db):
        self.app = app
        self.app.add_url_rule('/', 'index', self.index)
        self.socketio = flask_socketio.SocketIO(self.app)
        self.socketio.init_app(self.app, cors_allowed_origins='*')

        self.db = db

        self.base_ns = socketns.base.BaseNamespace('/', self)
        self.chat_ns = socketns.chat.ChatNamespace('/', self)
        self.youtube_ns = socketns.youtube.YoutubeNamespace('/', self)
        self.login_ns = socketns.login.LoginNamespace('/', self)
        self.room_ns = socketns.room.RoomNamespace('/', self)
        
        self.socketio.on_namespace(socketns.CustomCombinedNamespace('/', self, [
            self.base_ns,
            self.chat_ns,
            self.youtube_ns,
            self.room_ns,
            self.login_ns
        ]))

        self.rooms = {}
        self.users = {}

    def run(self, host, port, debug=False):
        self.socketio.run(
            self.app,
            host=host,
            port=port,
            debug=debug
        )

    def index(self):
        return flask.render_template('index.html')

    def emit_all_messages(self):
        if not self.db_enabled():
            return

        all_users = self.db.session.query(User).all()
        all_messages = [
            (db_message.id, db_message.text, str(db_message.timestamp), \
            db_message.user_id, self.get_facebook_tuple(db_message.user_id, all_users))
            for db_message in self.db.session.query(Message).all()
        ]
        self.socketio.emit(MESSAGES_EMIT_CHANNEL, all_messages)

    def get_facebook_tuple(self, user_id, all_users):
        for fb_user in all_users:
            if fb_user.oauth_id == str(user_id):
                return (fb_user.name, fb_user.image_url)

    def create_user_from_request(self, request):
        user = User.from_request(request)
        self.users[user.id] = user

        return user

    def delete_user(self, user):
        del self.users[user.id]

    def get_user_by_request(self, request):
        return self.users[request.sid]

    def create_room(self, room_id=None):
        room = Room(room_id)
        self.rooms[room.id] = room

        return room

    def delete_room(self, room):
        for user in list(room.users.values()):
            room.remove_user(user)

        del self.rooms[room.id]

    def db_enabled(self):
        return self.db is not None
