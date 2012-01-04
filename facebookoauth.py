#!/usr/bin/env python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A barebones AppEngine application that uses Facebook for login.

This application uses OAuth 2.0 directly rather than relying on Facebook's
JavaScript SDK for login. It also accesses the Facebook Graph API directly
rather than using the Python SDK. It is designed to illustrate how easy
it is to use the Facebook Platform without any third party code.

See the "appengine" directory for an example using the JavaScript SDK.
Using JavaScript is recommended if it is feasible for your application,
as it handles some complex authentication states that can only be detected
in client-side code.
"""

FACEBOOK_APP_ID = "your app id"
FACEBOOK_APP_SECRET = "your app secret"

import base64
import cgi
import hashlib
import hmac
import logging
import time
import urllib

import datetime
import json
import eventlet
import pyramid
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPFound
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

DBSession = scoped_session(sessionmaker(autoflush=True, autocommit=True))
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = sa.Column(sa.Text, nullable=False, primary_key=True)
    created = sa.Column(sa.DateTime, server_default='now')
    updated = sa.Column(sa.DateTime, server_default='now')
    name = sa.Column(sa.Text, nullable=False)
    profile_url = sa.Column(sa.Text, nullable=False)
    access_token = sa.Column(sa.Text, nullable=False)

_current_user = None

def get_current_user(request):
    """Returns the logged in Facebook user, or None if unconnected."""
    global _current_user
    if _current_user is None:
        try:
            user_id = parse_cookie(request.cookies["fb_user"])
            if user_id:
                _current_user = DBSession.query(User).filter_by(name=user_id).one()
        except (KeyError, sa.orm.NoResultFound):
            pass
    return _current_user

@view_config(route_name='home', renderer='oauth.jinja2')
def home(request):
    return dict(current_user=get_current_user(request))

@view_config(route_name='login')
def login(request):
    verification_code = request.GET.get("code")
    args = dict(client_id=FACEBOOK_APP_ID, redirect_uri=request.path_url)
    if request.GET.get("code"):
        args["client_secret"] = FACEBOOK_APP_SECRET
        args["code"] = request.GET.get("code")
        response = cgi.parse_qs(urllib.urlopen(
            "https://graph.facebook.com/oauth/access_token?" +
            urllib.urlencode(args)).read())
        access_token = response["access_token"][-1]

        # Download the user profile and cache a local instance of the
        # basic profile info
        profile = json.load(urllib.urlopen(
            "https://graph.facebook.com/me?" +
            urllib.urlencode(dict(access_token=access_token))))

        user = User(id=str(profile["id"]),
                    name=profile["name"], access_token=access_token,
                    profile_url=profile["link"])
        DBSession.add(user)
        DBSession.flush()
        resp = Response()
        resp.status = 302
        resp.location = "/"
        set_cookie(resp, "fb_user", str(profile["id"]),
                        expires=datetime.datetime.today() + datetime.timedelta(days=30))
        return resp
    else:
        return HTTPFound(location=
            "https://graph.facebook.com/oauth/authorize?" +
            urllib.urlencode(args))

@view_config(route_name='logout')
def logout(request):
    resp = Response()
    resp.status = 302
    resp.location = "/"
    set_cookie(resp, 'fb_user', '', expires=datetime.datetime.today())
    return resp

def set_cookie(response, name, value, domain=None, path="/", expires=None):
    """Generates and signs a cookie for the give name/value"""
    timestamp = str(int(time.time()))
    value = base64.b64encode(value)
    signature = cookie_signature(value, timestamp)
    response.set_cookie(name, "|".join([value, timestamp, signature]), path=path, domain=domain, expires=expires)

def parse_cookie(value):
    """Parses and verifies a cookie value from set_cookie"""
    if not value: return None
    parts = value.split("|")
    if len(parts) != 3: return None
    if cookie_signature(parts[0], parts[1]) != parts[2]:
        logging.warning("Invalid cookie signature %r", value)
        return None
    timestamp = int(parts[1])
    if timestamp < time.time() - 30 * 86400:
        logging.warning("Expired cookie %r", value)
        return None
    try:
        return base64.b64decode(parts[0]).strip()
    except:
        return None

def cookie_signature(*parts):
    """Generates a cookie signature.

    We use the Facebook app secret since it is different for every app (so
    people using this example don't accidentally all use the same secret).
    """
    hash = hmac.new(FACEBOOK_APP_SECRET, digestmod=hashlib.sha1)
    for part in parts: hash.update(part)
    return hash.hexdigest()

if __name__ == "__main__":
    import eventlet
    from eventlet import wsgi

    from pyramid.config import Configurator
    from sqlalchemy import engine_from_config
    engine = sa.create_engine('sqlite:///fbo.db')
    DBSession.configure(bind=engine)
    config = Configurator()
    config.include('pyramid_jinja2')
    config.add_jinja2_search_path(".")
    config.add_route('home', '/')
    config.add_route('login', '/auth/login')
    config.add_route('logout', '/auth/logout')
    config.scan()
    app = config.make_wsgi_app()

    wsgi.server(eventlet.listen(('127.0.0.1', 9999)), app)
