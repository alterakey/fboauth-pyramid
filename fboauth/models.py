import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extensions=ZopeTransactionExtension))
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = sa.Column(sa.Text, nullable=False, primary_key=True)
    created = sa.Column(sa.DateTime, server_default='now')
    updated = sa.Column(sa.DateTime, server_default='now')
    name = sa.Column(sa.Text, nullable=False)
    profile_url = sa.Column(sa.Text, nullable=False)
    access_token = sa.Column(sa.Text, nullable=False)
