"""SQLAlchemy schema for CSCI 341 Assignment 3 (PostgreSQL)."""
from datetime import datetime
from sqlalchemy import (create_engine, Column, Integer, String, Text, Date, Time, DateTime,
                        Boolean, ForeignKey, UniqueConstraint, CheckConstraint, ForeignKeyConstraint,
                        event)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from sqlalchemy.sql import func
import os

class Base(DeclarativeBase): pass

class AppUser(Base):
    __tablename__='app_user'
    user_id=Column(Integer,primary_key=True)
    given_name=Column(String(100),nullable=False)
    surname=Column(String(100),nullable=False)
    email=Column(String(255),nullable=False,unique=True)
    affiliation=Column(String(200),nullable=False)
    country=Column(String(100),nullable=False)
    phone_number=Column(String(32))
    author=relationship('Author',uselist=False,cascade='all, delete-orphan',back_populates='user')
    reviewer=relationship('Reviewer',uselist=False,cascade='all, delete-orphan',back_populates='user')
    @property
    def full_name(self): return f'{self.given_name} {self.surname}'

class Author(Base):
    __tablename__='author'
    author_id=Column(Integer,ForeignKey('app_user.user_id',ondelete='CASCADE'),primary_key=True)
    orcid=Column(String(25))
    user=relationship('AppUser',back_populates='author')
    areas=relationship('AuthorResearchArea',cascade='all, delete-orphan')

class AuthorResearchArea(Base):
    __tablename__='author_research_area'
    author_id=Column(Integer,ForeignKey('author.author_id',ondelete='CASCADE'),primary_key=True)
    area_label=Column(String(120),primary_key=True)

class Reviewer(Base):
    __tablename__='reviewer'
    reviewer_id=Column(Integer,ForeignKey('app_user.user_id',ondelete='CASCADE'),primary_key=True)
    years_experience=Column(Integer,nullable=False,default=0)
    __table_args__=(CheckConstraint('years_experience >= 0',name='ck_reviewer_experience'),)
    user=relationship('AppUser',back_populates='reviewer')
    expertise=relationship('ReviewerExpertise',cascade='all, delete-orphan')

class ReviewerExpertise(Base):
    __tablename__='reviewer_expertise'
    reviewer_id=Column(Integer,ForeignKey('reviewer.reviewer_id',ondelete='CASCADE'),primary_key=True)
    area_label=Column(String(120),primary_key=True)

class Conference(Base):
    __tablename__='conference'
    conference_id=Column(Integer,primary_key=True)
    name=Column(String(200),nullable=False)
    acronym=Column(String(40),nullable=False)
    description=Column(Text,nullable=False)
    city=Column(String(100),nullable=False)
    country=Column(String(100),nullable=False)
    start_date=Column(Date,nullable=False)
    end_date=Column(Date,nullable=False)
    submission_deadline=Column(Date,nullable=False)
    review_deadline=Column(Date,nullable=False)
    __table_args__=(CheckConstraint('end_date >= start_date',name='ck_conference_dates'),)
    hosts=relationship('ConferenceHost',cascade='all, delete-orphan')

class ConferenceHost(Base):
    __tablename__='conference_host'
    conference_id=Column(Integer,ForeignKey('conference.conference_id',ondelete='CASCADE'),primary_key=True)
    host_name=Column(String(200),primary_key=True)

class ConferenceReviewer(Base):
    __tablename__='conference_reviewer'
    conference_id=Column(Integer,ForeignKey('conference.conference_id',ondelete='CASCADE'),primary_key=True)
    reviewer_id=Column(Integer,ForeignKey('reviewer.reviewer_id'),primary_key=True)

class Track(Base):
    __tablename__='track'
    track_id=Column(Integer,primary_key=True)
    conference_id=Column(Integer,ForeignKey('conference.conference_id'),nullable=False)
    name=Column(String(200),nullable=False)
    description=Column(Text,nullable=False)
    research_area=Column(String(120),nullable=False)
    coordinator_id=Column(Integer,ForeignKey('reviewer.reviewer_id'),nullable=False)
    conference=relationship('Conference')

class ConferenceSession(Base):
    __tablename__='conference_session'
    session_id=Column(Integer,primary_key=True)
    conference_id=Column(Integer,ForeignKey('conference.conference_id'),nullable=False)
    title=Column(String(200),nullable=False)
    session_date=Column(Date,nullable=False)
    start_time=Column(Time,nullable=False)
    end_time=Column(Time,nullable=False)
    room_label=Column(String(100),nullable=False)
    chair_id=Column(Integer,ForeignKey('reviewer.reviewer_id'),nullable=False)
    __table_args__=(CheckConstraint('end_time > start_time',name='ck_session_times'),)
    conference=relationship('Conference')

class Paper(Base):
    __tablename__='paper'
    paper_id=Column(Integer,primary_key=True)
    track_id=Column(Integer,ForeignKey('track.track_id'),nullable=False)
    title=Column(String(250),nullable=False)
    abstract=Column(Text,nullable=False)
    submission_date=Column(Date,nullable=False)
    status=Column(String(30),nullable=False)
    session_id=Column(Integer,ForeignKey('conference_session.session_id',ondelete='SET NULL'))
    __table_args__=(CheckConstraint("status IN ('submitted','under review','accepted','rejected','withdrawn')",name='ck_paper_status'),)
    track=relationship('Track')
    session=relationship('ConferenceSession')
    authors=relationship('PaperAuthor',cascade='all, delete-orphan',back_populates='paper')
    keywords=relationship('PaperKeyword',cascade='all, delete-orphan')
    versions=relationship('PaperVersion',cascade='all, delete-orphan',back_populates='paper')
    reviews=relationship('Review',cascade='all, delete-orphan',back_populates='paper')

class PaperKeyword(Base):
    __tablename__='paper_keyword'
    paper_id=Column(Integer,ForeignKey('paper.paper_id',ondelete='CASCADE'),primary_key=True)
    keyword=Column(String(120),primary_key=True)

class PaperAuthor(Base):
    __tablename__='paper_author'
    paper_id=Column(Integer,ForeignKey('paper.paper_id',ondelete='CASCADE'),primary_key=True)
    author_id=Column(Integer,ForeignKey('author.author_id'),primary_key=True)
    author_position=Column(Integer,nullable=False)
    is_corresponding=Column(Boolean,nullable=False,default=False)
    __table_args__=(UniqueConstraint('paper_id','author_position',name='uq_paper_author_position'),
                    CheckConstraint('author_position > 0',name='ck_author_position'))
    paper=relationship('Paper',back_populates='authors')

class PaperVersion(Base):
    __tablename__='paper_version'
    paper_id=Column(Integer,ForeignKey('paper.paper_id',ondelete='CASCADE'),primary_key=True)
    version_no=Column(Integer,primary_key=True)
    file_location=Column(String(500),nullable=False)
    uploaded_at=Column(DateTime,nullable=False)
    change_note=Column(Text)
    __table_args__=(CheckConstraint('version_no > 0',name='ck_version_no'),)
    paper=relationship('Paper',back_populates='versions')

class Review(Base):
    __tablename__='review'
    review_id=Column(Integer,primary_key=True)
    paper_id=Column(Integer,ForeignKey('paper.paper_id',ondelete='CASCADE'),nullable=False)
    reviewer_id=Column(Integer,ForeignKey('reviewer.reviewer_id'),nullable=False)
    overall_score=Column(Integer,nullable=False)
    recommendation=Column(String(10),nullable=False)
    comments_for_authors=Column(Text,nullable=False)
    confidential_comments=Column(Text)
    review_submission_date=Column(Date,nullable=False)
    __table_args__=(UniqueConstraint('paper_id','reviewer_id',name='uq_review_paper_reviewer'),
                   CheckConstraint('overall_score BETWEEN 1 AND 5',name='ck_review_score'),
                   CheckConstraint("recommendation IN ('accept','reject')",name='ck_recommendation'))
    paper=relationship('Paper',back_populates='reviews')

VIEW_SQL="""CREATE VIEW accepted_paper_schedule AS
SELECT p.paper_id, p.title AS paper_title, c.conference_id, c.acronym,
       t.name AS track_name, s.session_id, s.title AS session_title,
       s.session_date, s.start_time, s.end_time, s.room_label,
       chair.given_name || ' ' || chair.surname AS chair_full_name,
       au.given_name || ' ' || au.surname AS corresponding_author_name,
       au.email AS corresponding_author_email
FROM paper p JOIN track t ON t.track_id=p.track_id
JOIN conference c ON c.conference_id=t.conference_id
JOIN conference_session s ON s.session_id=p.session_id
JOIN app_user chair ON chair.user_id=s.chair_id
JOIN paper_author pa ON pa.paper_id=p.paper_id AND pa.is_corresponding=TRUE
JOIN app_user au ON au.user_id=pa.author_id
WHERE p.status='accepted'"""

def database_url():
    return os.getenv('DATABASE_URL','postgresql+psycopg2://conference:conference@localhost:5432/conference_db').replace('postgres://','postgresql://',1)

def make_engine(url=None, echo=False):
    return create_engine(url or database_url(),echo=echo,pool_pre_ping=True)

def create_schema(engine):
    from sqlalchemy import text
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text('DROP VIEW IF EXISTS accepted_paper_schedule'))
        conn.execute(text(VIEW_SQL))
