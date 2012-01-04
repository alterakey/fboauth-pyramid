from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from .models import DBSession

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    import fboauth.monkeypatch
    fboauth.monkeypatch.apply()

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    config = Configurator(settings=settings)
    config.add_route('home', '/')
    config.add_route('login', '/auth/login')
    config.add_route('logout', '/auth/logout')
    config.scan()
    return config.make_wsgi_app()
