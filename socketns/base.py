import datetime

import flask
import flask_socketio


class BaseNamespace(flask_socketio.Namespace):
    def __init__(self, namespace, server):
        super().__init__(namespace)
        self.namespace = namespace
        self.flaskserver = server

    def on_connect(self):
        self.connect_user(flask.request)

    def connect_user(self, request):
        user = self.flaskserver.create_user_from_request(request)
        user.socket_connected = True
        user.last_socket_connect = None

    def on_disconnect(self):
        self.disconnect_user(flask.request)

    def disconnect_user(self, request):
        user = self.flaskserver.get_user_by_request(request)
        if user is None or user == False:
            return

        user.socket_connected = False
        user.last_socket_connect = datetime.datetime.utcnow()

<<<<<<< HEAD
        if user.room is not None:
=======
        if user.room is None:
            pass
        else:
>>>>>>> 8d7ed36a03af33ab6351afb5a820f128ab7ebb1c
            user.room.remove_user(user)
