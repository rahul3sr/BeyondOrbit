"""Official API protocol exercised only through an injected mock transport.
No account authorization or default HTTP client is connected.
"""
import json
from urllib.parse import urlencode,urlsplit

class YouTubeProtocol:
    mode='protocol-mock'
    def __init__(self,transport):self.transport=transport

    def private_upload(self,video_bytes,metadata,access_token):
        if metadata['destination']['platform']!='youtube' or metadata['destination']['privacy']!='private':
            raise ValueError('Initial protocol supports private YouTube uploads only')
        body={'snippet':{'title':metadata['title'],'description':metadata['description']},
              'status':{'privacyStatus':'private'}}
        initial=self.transport('POST',
            'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
            {'Authorization':'Bearer '+access_token,'Content-Type':'application/json',
             'X-Upload-Content-Type':'video/mp4','X-Upload-Content-Length':str(len(video_bytes))},json.dumps(body).encode())
        location=initial['location'];url=urlsplit(location)
        if url.scheme!='https' or url.hostname!='www.googleapis.com' or url.username or url.password or url.port not in (None,443):
            raise ValueError('Unexpected upload session host')
        return self.transport('PUT',location,{'Authorization':'Bearer '+access_token,
                            'Content-Type':'video/mp4','Content-Length':str(len(video_bytes))},video_bytes)

    def analytics(self,access_token,start,end):
        from datetime import date
        if date.fromisoformat(start)>date.fromisoformat(end):raise ValueError('Invalid reporting date range')
        return self.transport('GET','https://youtubeanalytics.googleapis.com/v2/reports?'+urlencode({
            'ids':'channel==MINE','startDate':start,'endDate':end,
            'metrics':'views,estimatedMinutesWatched,subscribersGained','dimensions':'video'}),
            {'Authorization':'Bearer '+access_token},None)
