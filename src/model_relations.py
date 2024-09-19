from sqlalchemy import Column, Integer, Table, ForeignKey
from src.database.core import Base

user_repo = Table('user_repo', Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('repo_id', Integer, ForeignKey('repos.id'), primary_key=True)
)

