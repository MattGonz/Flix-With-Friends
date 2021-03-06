import re

import flask
import flask_socketio

import utils
from utils import clamp, unix_timestamp
from db_models.video import Video

EVENT_YT_STATE_CHANGE = 'yt_state_change'
EVENT_YT_LOAD = 'yt_load'
EVENT_YT_SPHERE_UPDATE = 'yt_sphere_update'


class YoutubeNamespace(flask_socketio.Namespace):
    def __init__(self, namespace, server):
        super().__init__(namespace)
        self.namespace = namespace
        self.flaskserver = server

    def on_yt_load(self, data):
        self.handle_yt_load(flask.request, flask.session, data)

    def get_youtube_video_id(self, url):
        match = re.match(
            r'^(?:https?://)?(?:www\.)?youtu(?:\.be/|be\.com/(?:embed/|watch\?v=))([A-Za-z0-9_-]+)',
            url
        )
        if match is not None:
            return match[1]

        match = re.match(r'^([A-Za-z0-9_-]+)$', url)
        if match is not None:
            return match[1]

        return None

    def handle_yt_load(self, request, session, data):
        user = self.flaskserver.get_user_by_request(request, session)
        if user.room is None:
            return

        if user.room.get_host_mode() and not user.room.is_creator(user):
            return

        url = data.get('url')
        if url is None:
            return

        video_id = self.get_youtube_video_id(url)
        if video_id is None:
            return

        user.room.current_video_code = video_id

        user.room.emit(EVENT_YT_LOAD, {
            'videoId': video_id
        })

    def on_yt_state_change(self, data):
        self.handle_yt_state_change(flask.request, flask.session, data)

    def handle_yt_state_change(self, request, session, data):
        user = self.flaskserver.get_user_by_request(request, session)
        if user.room is None:
            return

        if user.room.get_host_mode() and not user.room.is_creator(user):
            return

        offset = self.getval(data, 'offset',
            lambda x: isinstance(x, float),
            lambda x: abs(float(x)),
            0
        )
        rate = self.getval(data, 'rate',
            lambda x: isinstance(x, float),
            lambda x: abs(float(x)),
            1
        )
        run_at = self.getval(data, 'runAt',
            lambda x: isinstance(x, int),
            lambda x: max(0, int(x)),
            0
        )
        timestamp = self.getval(data, 'timestamp',
            lambda x: isinstance(x, int),
            lambda x: int(x),
            unix_timestamp()
        )

        if data.get('state') not in [
                'ready',
                'unstarted',
                'ended',
                'playing',
                'paused',
                'buffering',
                'cued',
                'playback'

        ]:
            return

        user.room.emit(EVENT_YT_STATE_CHANGE, {
            'state': data['state'],
            'sender': user.username,
            'offset': offset,
            'rate': rate,
            'runAt': run_at,
            'timestamp': timestamp
        })

    def on_yt_sphere_update(self, data):
        self.handle_yt_sphere_update(flask.request, flask.session, data)

    def handle_yt_sphere_update(self, request, session, data):
        user = self.flaskserver.get_user_by_request(request, session)
        if user.room is None:
            return

        # does not work well with peer-sync mode, only allow in host-sync mode
        if not user.room.is_creator(user):
            return

        yaw = self.getval(data, 'properties.yaw',
            lambda x: isinstance(x, float) and x >= 0 and x < 360,
            lambda x: clamp(float(x), 0, 360),
            0
        )
        pitch = self.getval(data, 'properties.pitch',
            lambda x: isinstance(x, float) and x >= -90 and x <= 90,
            lambda x: clamp(float(x), -90, 90),
            0
        )
        roll = self.getval(data, 'properties.roll',
            lambda x: isinstance(x, float) and x >= -180 and x <= 180,
            lambda x: clamp(float(x), -180, 180),
            0
        )
        fov = self.getval(data, 'properties.fov',
            lambda x: isinstance(x, float) and x >= 30 and x <= 120,
            lambda x: clamp(float(x), 30, 120),
            100
        )

        user.room.emit(EVENT_YT_SPHERE_UPDATE, {
            'properties': {
                'yaw': yaw,
                'pitch': pitch,
                'roll': roll,
                'fov': fov
            }
        }, sender=user)

    def getval(self, data, key, fnc_chk, fnc_fix, default=None):
        val = utils.getval(data, key, default)
        if not fnc_chk(val):
            try:
                val = fnc_fix(val)
            except Exception:
                val = default
        return val

    def on_yt_enqueue(self, data):
        room_id = data['roomId']
        url = data['url']
        video_id = self.get_youtube_video_id(url)

        print('\nNew Enqueue Data:')
        print('room_id: %s' % room_id)
        print('video_url: %s' % url)
        print('video_id: %s' % video_id)

        if self.flaskserver.db_connected():
            cur = self.flaskserver.db.cursor()
            playlist = self.flaskserver.get_playlist_from_room_id(cur, room_id)
            video = Video(video_id, url, playlist['playlist_id'])

            video.insert_to_db(cur)
            self.flaskserver.db.commit()
            cur.close()

        self.flaskserver.emit_playlist(room_id)

    def on_yt_dequeue(self, data):
        room_id = data['roomId']
        url = data['url']
        video_id = self.get_youtube_video_id(url)

        print('\nNew Dequeue Data:')
        print('room_id: %s' % room_id)
        print('video_url: %s' % url)
        print('video_id: %s' % video_id)

        if self.flaskserver.db_connected():
            cur = self.flaskserver.db.cursor()
            playlist = self.flaskserver.get_playlist_from_room_id(cur, room_id)
            video = Video(video_id, url, playlist['playlist_id'])

            video.delete_from_db(cur)
            self.flaskserver.db.commit()
            cur.close()

        self.flaskserver.emit_playlist(room_id)
