from threading import Thread
from gmusicapi import Mobileclient
import time
from ruse.aural.vlc.manager import VlcManager
from ruse.aural.vlc import vlc
from ruse.etc.config import config


class MusicManager(object):
    def __init__(self):

        self.api = Mobileclient(validate=False, debug_logging=False)
        self.api.login(config.GOOGLE_USERNAME, config.GOOGLE_PASSWORD)

        self.queue = []
        self.current_index = len(self.queue) - 1

        self.vlc = VlcManager()

        self.state_thread = Thread(target=self.check_state)
        self.state_thread.daemon = True
        self.state_thread.start()

    def play_song(self, id):
        song = self.queue_song(id)
        self.current_index = len(self.queue) - 1
        self.load_song()
        return song

    def queue_song(self, id):
        self.queue.append(self.getSongInfo(id))

    def play_radio_station(self, id):
        results = self.api.get_station_tracks(id, num_tracks=40)

        for song in results:
            song['albumArtRef'] = song['albumArtRef'][0]['url']
            if 'artistId' in song:
                song['artistId'] = song['artistId'][0]

        self.current_index = len(self.queue) - 1
        self.queue.append(results)
        self.load_song()

    def play_album(self, args):
        album = self.get_album_details(args)
        songs = []
        for index in range(len(album['tracks'])):
            song = album['tracks'][index]
            if index == 0:
                songs.append(self.play_song(song['nid']))
            else:
                songs.append(self.queue_song(song['nid']))
        return songs

    def queue_album(self, args):
        album = self.get_album_details(args)
        songs = []
        for song in album['tracks']:
            songs.append(self.queue_song(song['nid']))
        return songs

    def next(self):
        self.current_index += 1
        self.load_song()

    def prev(self):
        self.current_index -= 1
        self.load_song()

    def pause(self):
        self.vlc.vlc_pause()

    def resume(self):
        self.vlc.vlc_resume()

    def volume(self, val):
        self.vlc.vlc_volume(val)

    def delete(self, id):
        if id > self.current_index:
            del self.queue[id]
        elif id < self.current_index:
            del self.queue[id]
            self.current_index -= 1
        else:
            del self.queue[id]
            self.load_song()

    def go_to(self, id):
        self.current_index = id
        self.load_song()

    def load_song(self):
        if self.current_index < len(self.queue):
            song = self.queue[self.current_index]
            url = self.api.get_stream_url(song['nid'], config.GOOGLE_STREAMKEY)
            self.vlc.vlc_play(url)

    def check_state(self):
        while True:
            status = self.vlc.player.get_state()
            if status == vlc.State.Ended:
                if self.current_index != len(self.queue) - 1:
                    self.next()

            time.sleep(1)

    def get_status(self):

        status = self.vlc.vlc_status()

        # status['queue'] = self.queue[:]
        # for i in range(len(status['queue'])):
        #     status['queue'][i]['vlcid'] = i
        #     if i == self.current_index:
        #         status['queue'][i]['current'] = True
        #         status['current'] = status['queue'][i]
        if len(self.queue) > 0:
            status['current'] = self.queue[self.current_index]
        return status

    def get_queue(self):
        queue = self.queue[:]
        for i in range(len(queue)):
            queue[i]['vlcid'] = i

        return queue


    def search(self, query):
        results = self.api.search_all_access(query, max_results=50)

        results['artist_hits'] = [artist['artist'] for artist in results['artist_hits']]

        results['album_hits'] = [album['album'] for album in results['album_hits']]
        for album in results['album_hits']:
            album['artistId'] = album['artistId'][0]

        results['song_hits'] = [song['track'] for song in results['song_hits']]
        for song in results['song_hits']:
            song['albumArtRef'] = song['albumArtRef'][0]['url']
            if 'artistId' in song:
                song['artistId'] = song['artistId'][0]
        return results

    def get_album_details(self, id):
        results = self.api.get_album_info(album_id=id, include_tracks=True)
        results['artistId'] = results['artistId'][0]
        for song in results['tracks']:
            song['albumArtRef'] = song['albumArtRef'][0]['url']
            if 'artistId' in song:
                song['artistId'] = song['artistId'][0]
        return results

    def get_artist_details(self, id):
        results = self.api.get_artist_info(artist_id=id)
        for album in results['albums']:
            album['artistId'] = album['artistId'][0]

        for song in results['topTracks']:
            song['albumArtRef'] = song['albumArtRef'][0]['url']
            if 'artistId' in song:
                song['artistId'] = song['artistId'][0]
        return results


    def create_radio_station(self, name, id):
        if id[0] == 'A':
            station_id = self.api.create_station(name, artist_id=id)

        elif id[0] == 'B':
            station_id = self.api.create_station(name, album_id=id)

        else:
            station_id = self.api.create_station(name, track_id=id)

        return station_id

    def get_radio_stations(self):
        return self.api.get_all_stations()

    def flush(self):
        self.vlc.vlc_stop()
        self.queue = []

    def getSongInfo(self, id):
        song = self.api.get_track_info(id)
        song['albumArtRef'] = song['albumArtRef'][0]['url']
        if 'artistId' in song:
            song['artistId'] = song['artistId'][0]
        return song
