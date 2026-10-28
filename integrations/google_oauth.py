"""Official Google OAuth PKCE primitives. No default network transport or login."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
from urllib.parse import urlencode,urlsplit

UPLOAD_SCOPE='https://www.googleapis.com/auth/youtube.upload'
ANALYTICS_SCOPE='https://www.googleapis.com/auth/yt-analytics.readonly'

class GoogleOAuth:
    def __init__(self,client_id,redirect_uri,scope=UPLOAD_SCOPE):
        uri=urlsplit(redirect_uri)
        if uri.scheme!='http' or uri.hostname!='127.0.0.1' or not uri.port:
            raise ValueError('Desktop development OAuth requires a registered loopback callback')
        if scope not in {UPLOAD_SCOPE,ANALYTICS_SCOPE}:raise ValueError('Request only one minimum-purpose scope')
        self.client_id=client_id;self.redirect_uri=redirect_uri;self.scope=scope
        self.state=secrets.token_urlsafe(32);self.verifier=secrets.token_urlsafe(64);self.used=False

    def authorization_url(self):
        challenge=base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b'=').decode()
        return 'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({
            'client_id':self.client_id,'redirect_uri':self.redirect_uri,'response_type':'code',
            'scope':self.scope,'state':self.state,'code_challenge':challenge,'code_challenge_method':'S256',
            'access_type':'offline','prompt':'consent'})

    def exchange(self,code,state,transport):
        if self.used or not hmac.compare_digest(state,self.state):raise ValueError('OAuth callback state invalid or already used')
        if not code:raise ValueError('Missing authorization code')
        self.used=True
        # Transport must be supplied explicitly after account authorization; tests inject mocks.
        response=transport('POST','https://oauth2.googleapis.com/token',
            {'Content-Type':'application/x-www-form-urlencoded'},urlencode({
            'client_id':self.client_id,'redirect_uri':self.redirect_uri,'code':code,
            'code_verifier':self.verifier,'grant_type':'authorization_code'}).encode())
        if not response.get('access_token'):raise ValueError('Google token response missing access token')
        return response


def save_tokens(path,tokens):
    path=Path(path)
    if path.parent.name!='credentials':raise ValueError('Use an ignored credentials directory')
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    # Refuse existing paths and symlinks rather than overwrite another person's credentials.
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,'w') as f:json.dump(tokens,f)
