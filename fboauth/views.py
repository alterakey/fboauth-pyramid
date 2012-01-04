import cgi
import urllib
import urllib.parse
import datetime
import json

import sqlalchemy as sa
import transaction
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPFound

from .models import DBSession, User

@view_config(route_name='home', renderer='oauth.jinja2')
def home(request):
    user = None
    try:
        username = request.session['fb_user']
        not_after = request.session['fb_user_not_after']
        if not_after > datetime.datetime.today():
            user = DBSession.query(User).filter_by(name=username).one()
    except (KeyError, sa.orm.exc.NoResultFound):
        pass
    return dict(current_user=user)

@view_config(route_name='login')
def login(request):
    verification_code = request.GET.get("code")
    args = dict(client_id=request.registry.settings['facebook.id'], redirect_uri=request.path_url)
    if verification_code:
        args["client_secret"] = request.registry.settings['facebook.secret']
        args["code"] = verification_code
        response = cgi.parse_qs(urllib.urlopen(
            "https://graph.facebook.com/oauth/access_token?" +
            urllib.parse.urlencode(args)).read())
        access_token = response["access_token"][-1]

        # Download the user profile and cache a local instance of the
        # basic profile info
        profile = json.load(urllib.urlopen(
            "https://graph.facebook.com/me?" +
            urllib.parse.urlencode(dict(access_token=access_token))))

        with transaction.manager:
            user = User(id=profile["id"],
                        name=profile["name"], access_token=access_token,
                        profile_url=profile["link"])
            DBSession.add(user)

        request.session['fb_user'] = bytes(profile["id"])
        request.session['fb_user_not_after'] = datetime.datetime.today() + datetime.timedelta(days=30)
        return HTTPFound(location="/")
    else:
        return HTTPFound(location=
            "https://graph.facebook.com/oauth/authorize?" +
            urllib.parse.urlencode(args))

@view_config(route_name='logout')
def logout(request):
    del request.session['fb_user']
    del request.session['fb_user_not_after']
    return HTTPFound(location="/")
