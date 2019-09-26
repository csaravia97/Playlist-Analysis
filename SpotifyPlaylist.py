def get_playlists(playlist_type, country_code, limit):
    
    '''
    Returns a dictionary of containing the given amount of playlists of the provided type from the 
    country matching the country code provided.
    '''
    
    playlists = (requests.get(url=f"https://api.spotify.com/v1/browse/categories/{playlist_type}/playlists?country={country_code}&limit={limit}",
                              headers = headers)).json()
    
    return playlists


def extract_playlist_ids(playlists):
    
    ''' Extract the ids of the playlists to be able to query the tracks contained in the playlist using Spotify API. '''
    
    ids = []
    playlist_info = playlists['playlists']['items']
    for i in range(len(playlist_info)):
        ids.append(playlist_info[i]['id'])
    
    return ids


def extract_track_info(playlist_ids):
    
    ''' Extract all of the relevant information about the tracks in a playlist, given a list a playlist ids. '''
    
    track_info = []

    for playlist in playlist_ids:
        tracks = (requests.get(url=f"https://api.spotify.com/v1/playlists/{playlist}/tracks",
                               headers = headers)).json()            
  
        fields = {"id", "name", "artists", "album", "duration_ms", "popularity"}
        for i in range(len(tracks['items'])):
            if tracks['items'][i]['track']:
                info = { key:value for key,value in tracks['items'][i]['track'].items() if key in fields}
                track_info.append(info)
            else:
                print('BARK BARK BARK >:(')
    
    return track_info

def get_tracks(playlist_type, country_code, limit):
    
    '''
    Returns a list containing the information for various tracks.
    playlist_type: The type of playlists where you want to query songs
    country_code: The country code of the country where you want to find the playlists
    limit: The amount of playlists you want to extract tracks from
    '''
    
    playlists = get_playlists(playlist_type, country_code, limit)
    playlist_ids = extract_playlist_ids(playlists)
    track_info = pd.DataFrame(extract_track_info(playlist_ids))
    track_info = track_info[['id', 'name', 'artists', 'album','duration_ms', 'popularity']]
    
    return track_info

def get_track_features(track_ids, df):
    '''
    Given an array of track ids extract the audio features of the track.
    '''
    track_features = []
    lower_bound = 0
    upper_bound = 60
    while lower_bound < len(track_ids):
        track_string = ','.join(df['id'][lower_bound:upper_bound])
        features = requests.get(url=f"https://api.spotify.com/v1/audio-features",
                                params={'ids':track_string},
                                headers=headers).json()
        lower_bound += 60
        upper_bound += 60
        if features['audio_features']:
            track_features.extend(features['audio_features'])
    return track_features


def extract_artist_name(track_data):
    '''Given a dataframe of track_data extract the artist names from the artists column'''
    artist_names = []
    for i in range(len(track_data)):
        artist_names.append(track_data['artists'][i][0]['name'])
    
    return artist_names


def extract_album_name(track_data):
    '''Given a dataframe of track_data extract the album names from the album column'''
    album_names = []
    for i in range(len(track_data)):
        album_names.append(track_data['album'][i]['name'])
    
    return album_names


def popularity_transform(column, tracks):
    star_rating = []
    for popularity_rating in tracks.popularity:
        if popularity_rating <= 20:
            star_rating.append(1)
        elif popularity_rating <= 40:
            star_rating.append(2)
        elif popularity_rating <= 60:
            star_rating.append(3)
        elif popularity_rating <= 80:
            star_rating.append(4)
        else:
            star_rating.append(5)
    return star_rating


class SpotifyPlaylist:

    def __init__(self, playlist_type, country_code, limit):
        self.playlist_type = playlist_type
        self.country_code = country_code
        self.limit = limit
        self.Extract()
        self.Transform()

    def Extract(self):
        '''
        Returns tracks of all the playlists of the specified type with their corresponding track features
        '''
        self.tracks = get_tracks(self.playlist_type, self.country_code, self.limit)
        track_features = pd.DataFrame(get_track_features(self.tracks['id'], self.tracks))
        track_features = track_features[['id', 'acousticness', 'danceability','energy', 'instrumentalness', 'key', 'liveness', 'loudness', 'mode',
           'speechiness', 'tempo', 'time_signature', 'valence']]
        self.tracks = pd.merge(self.tracks, track_features, on="id", how="inner").set_index('id')
    
    
    def Transform(self):
        self.tracks['artists'] = extract_artist_name(self.tracks)
        self.tracks['album'] = extract_album_name(self.tracks)

        self.tracks.drop_duplicates(inplace=True)
        self.tracks = self.tracks.sort_values(by=['name', 'popularity'], ascending = False)
        self.tracks.drop_duplicates(subset=['name', 'artists'], inplace=True)

        self.tracks['rating'] = popularity_transform(self.tracks['popularity'], self.tracks)

        self.tracks[['time_signature', 'key', 'mode', 'rating']] = self.tracks[['time_signature', 'key', 'mode', 'rating']].astype('category')

