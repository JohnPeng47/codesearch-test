from src.database.core import engine
from src.auth.service import get_by_email

from sqlalchemy.orm import sessionmaker
from src.repo.models import Repo

Session = sessionmaker(bind=engine)
session = Session()

curr_user = get_by_email(db_session=session, email="JKmNvYPRAE@hotmail.com")
print(curr_user)
user_repo = session.query(Repo).filter(Repo.users.contains(curr_user)).all()
print(user_repo)
