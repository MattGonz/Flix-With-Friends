import * as React from 'react';

import { Socket } from './Socket';

import YoutubePlayer from './youtube/youtube-player.js';


const EVENT_YT_LOAD = 'yt-load';
const EVENT_YT_STATE_CHANGE = 'yt-state-change';


export function YoutubeContainer() {
	const [ytPlayer, setYtPlayer] = React.useState(null);
	const [ytComponent, setYtComponent] = React.useState(null);

	const ytPlayerRef = React.useRef();
	ytPlayerRef.current = ytPlayer;

	React.useEffect(() => {
		let [player, component] = YoutubePlayer.createYoutubePlayer('dQw4w9WgXcQ', {
			playerVars: {
				autoplay: 1,
				controls: 1,
				disablekb: 1
			}
		}, onYtReady, onYtStateChange, onYtPlaybackRateChange);

		setYtPlayer(player);
		setYtComponent(component);

		ytPlayerRef.current = ytPlayer;

		Socket.on(EVENT_YT_LOAD, (data) => {
			ytPlayerRef.current.player.loadVideoById(data.videoId);
		});

		Socket.on(EVENT_YT_STATE_CHANGE, (data) => {
			function doState(data)
			{
				console.log(data);

				let ts = (new Date()).getTime();
				let tsdiff = Math.max(0, ts - data.timestamp);
				let adjustedOffset = data.offset + (tsdiff / 1000);

				console.log(data.offset, adjustedOffset, tsdiff / 1000);

				switch(data.state)
				{
					case YoutubePlayer.prototype.PLAYER_PLAYING_STR:
						ytPlayerRef.current.player.play(adjustedOffset);
						break;
					case YoutubePlayer.prototype.PLAYER_PAUSED_STR:
						ytPlayerRef.current.player.pause(adjustedOffset);
						break;
					case YoutubePlayer.prototype.PLAYER_PLAYBACK_STR:
						ytPlayerRef.current.player.setPlayback(adjustedOffset, data.rate);
						break;
				}
			}

			doState(data);

			/*
			let secdiff = Math.max(0, data.runAt - Math.floor((new Date()).getTime() / 1000));
			if(secdiff > 0)
			{
				setTimeout(() => {
					doState(data);
				}, secdiff * 1000);
			}else
			{
				doState(data);
			}
			*/
		});
	}, []);

	function onYtReady(event)
	{
		console.log('ready', event);

		ytPlayerRef.current.player.pauseVideo();

		emitStateChange(ytPlayerRef.current.player, 'ready', 0, 1);
	}

	function onYtStateChange(event)
	{
		console.log('state change', event);

		emitStateChange(ytPlayerRef.current.player, YoutubePlayer.playerStateToStr(event.data));
	}

	function onYtPlaybackRateChange(event)
	{
		console.log('playback change', event);

		emitStateChange(ytPlayerRef.current.player, 'playback');
	}

	function emitStateChange(player, state, offset, rate, timestamp)
	{
		offset = offset || player.getCurrentTime();
		rate = rate || player.getPlaybackRate();
		timestamp = timestamp || (new Date()).getTime();

		Socket.emit(EVENT_YT_STATE_CHANGE, {
			'state': state,
			'offset': offset,
			'rate': rate,
			'timestamp': timestamp
		});
	}

	return (
		<div>
			{ytComponent}
		</div>
	);
}
