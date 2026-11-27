"""Unit tests runnable locally with pytest, using an FK-enabled SQLite test database.
Production and required assignment queries run on PostgreSQL, not SQLite.
"""
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from models import Base, AppUser, Author, Reviewer, Track, ConferenceSession, Paper, Review, PaperAuthor
from seed import populate
from services import save_review, save_paper, save_session, ValidationError

@pytest.fixture
def db():
    engine=create_engine('sqlite+pysqlite:///:memory:')
    @event.listens_for(engine,'connect')
    def foreign_keys(conn,record): conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        populate(s);s.commit()
        yield s

def test_seed_counts(db):
    assert db.query(AppUser).count()>=10
    assert db.query(Paper).count()>=10
    assert db.query(Review).count()>=10

def test_self_review_rejected(db):
    with pytest.raises(ValidationError,match='Self-review'):
        save_review(db,dict(paper_id=1,reviewer_id=2,overall_score=4,recommendation='accept',comments_for_authors='No',review_submission_date='2026-10-20'))
    db.rollback()

def test_bad_schedule_rejected(db):
    paper=db.get(Paper,3)
    with pytest.raises(ValidationError,match='Only accepted'):
        save_paper(db,dict(track_id=2,title=paper.title,abstract=paper.abstract,submission_date='2026-09-05',status='rejected',session_id=1),paper)
    db.rollback()

def test_cross_conference_schedule_rejected(db):
    p=db.get(Paper,2)
    with pytest.raises(ValidationError,match='different conferences'):
        save_paper(db,dict(track_id=1,title=p.title,abstract=p.abstract,submission_date='2026-09-04',status='accepted',session_id=3),p)
    db.rollback()

def test_author_change_self_review_rejected(db):
    p=db.get(Paper,6)
    with pytest.raises(ValidationError,match='self-review'):
        save_paper(db,dict(track_id=3,title=p.title,abstract=p.abstract,submission_date='2026-09-08',status='accepted',session_id=2,authors=[dict(author_id=9,author_position=1,is_corresponding=True)]),p)
    db.rollback()

def test_valid_review_insert_and_delete(db):
    review=save_review(db,dict(paper_id=11,reviewer_id=4,overall_score=5,recommendation='accept',comments_for_authors='Good',review_submission_date='2026-10-23'))
    assert review.review_id is not None
    db.delete(review);db.flush();db.rollback()

def test_cascade_paper_versions(db):
    p=db.get(Paper,8)
    assert len(p.versions)>=1
    db.delete(p);db.flush()
    assert db.get(Paper,8) is None
    db.rollback()


def test_feedback_multiple_reviewers_per_paper(db):
    from sqlalchemy import func
    counts=db.execute(select(Review.paper_id,func.count(Review.review_id)).group_by(Review.paper_id)).all()
    assert any(count>=2 for _,count in counts)
    from sqlalchemy.exc import IntegrityError
    # Repeating the same reviewer/paper pair is forbidden, not multiple reviews in general.
    db.add(Review(paper_id=1,reviewer_id=4,overall_score=3,recommendation='reject',
                  comments_for_authors='Duplicate review',review_submission_date=__import__('datetime').date(2026,10,20)))
    with pytest.raises(IntegrityError): db.flush()
    db.rollback()

def test_feedback_reviewer_pool_many_to_many(db):
    from sqlalchemy import func
    from models import ConferenceReviewer,Conference
    counts=db.execute(select(ConferenceReviewer.conference_id,func.count(ConferenceReviewer.reviewer_id)).group_by(ConferenceReviewer.conference_id)).all()
    assert len(counts)==db.query(Conference).count()
    assert all(n>=1 for _,n in counts)
    assert db.scalar(select(func.count()).select_from(ConferenceReviewer).where(ConferenceReviewer.reviewer_id==4))>=2
