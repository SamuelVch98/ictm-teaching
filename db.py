from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, query

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    organization_code = Column(String, nullable=True)
    admin = Column(Boolean, default=False)

class Course(Base):
    __tablename__ = 'course'
    id = Column(Integer, primary_key=True)
    code = Column(String)
    organization_code = Column(String)
    title = Column(String)
    quadri = Column(Integer)
    year = Column(String)
    load_needed = Column(Integer)


# Création de la base de données
engine = create_engine('sqlite:///ictm-teaching.db', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Ajouter le premier admin dans la base de données
def add_first_admin():
    session = Session()
    admin_exists = session.query(User).filter_by(admin=True).first()
    if admin_exists is None:
        first_admin = User(name='Admin', first_name='Admin', email='admin@example.com', organization_code="", admin=True)
        session.add(first_admin)
        session.commit()

add_first_admin()
