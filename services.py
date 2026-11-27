"""Atomic CRUD operations and application-level business validations."""
from datetime import date,datetime,time
from sqlalchemy import select
from models import *

class ValidationError(ValueError): pass

def integer(value,field):
    try: return int(value)
    except (TypeError,ValueError): raise ValidationError(f'{field} must be an integer')

def split_labels(s): return sorted(set(x.strip() for x in (s or '').split(',') if x.strip()))
def parse_date(s): return date.fromisoformat(s)
def parse_time(s): return time.fromisoformat(s)
def parse_datetime(s): return datetime.fromisoformat(s)
def boolean(s): return str(s).lower() in ('true','1','on','yes')

def validate_assignment(db,paper):
    if paper.session_id is None: return
    session=db.get(ConferenceSession,paper.session_id)
    track=db.get(Track,paper.track_id)
    if session is None or track is None: raise ValidationError('Unknown session or track')
    if paper.status!='accepted': raise ValidationError('Only accepted papers may be scheduled')
    if track.conference_id != session.conference_id: raise ValidationError('Track and session belong to different conferences')

def validate_self_review(db,paper_id,reviewer_id):
    authored=db.scalar(select(PaperAuthor).where(PaperAuthor.paper_id==paper_id,PaperAuthor.author_id==reviewer_id))
    if authored: raise ValidationError('Self-review prohibited: this reviewer authored the paper')

def validate_paper_authors(db,paper_id,authors):
    ids=[integer(x['author_id'],'author_id') for x in authors]
    positions=[integer(x['author_position'],'author_position') for x in authors]
    if not authors: raise ValidationError('A paper must have an author')
    if len(ids)!=len(set(ids)) or len(positions)!=len(set(positions)) or any(x<1 for x in positions):
        raise ValidationError('Author IDs and positive author positions must be unique')
    if sum(boolean(x.get('is_corresponding')) for x in authors)!=1:
        raise ValidationError('Exactly one corresponding author required')
    if any(db.get(Author,uid) is None for uid in ids):
        raise ValidationError('Author profile missing')
    reviewers=set(db.scalars(select(Review.reviewer_id).where(Review.paper_id==paper_id)))
    if reviewers.intersection(ids): raise ValidationError('Changing authors would create a self-review')

def save_user(db,data,user=None):
    if user is None:
        user=AppUser();db.add(user)
    for f in ('given_name','surname','email','affiliation','country','phone_number'):
        setattr(user,f,data.get(f) or None)
    db.flush()
    wants_author=boolean(data.get('is_author'))
    wants_reviewer=boolean(data.get('is_reviewer'))
    if not(wants_author or wants_reviewer): raise ValidationError('At least one author/reviewer role required')
    if wants_author:
        if not user.author: user.author=Author(orcid=data.get('orcid') or None)
        else: user.author.orcid=data.get('orcid') or None
        user.author.areas=[AuthorResearchArea(area_label=x) for x in split_labels(data.get('research_areas'))]
    elif user.author:
        if db.scalar(select(PaperAuthor).where(PaperAuthor.author_id==user.user_id)):
            raise ValidationError('Cannot remove author role: referenced by papers')
        db.delete(user.author)
    if wants_reviewer:
        if not user.reviewer: user.reviewer=Reviewer(years_experience=integer(data.get('years_experience',0),'years_experience'))
        else: user.reviewer.years_experience=integer(data.get('years_experience',0),'years_experience')
        user.reviewer.expertise=[ReviewerExpertise(area_label=x) for x in split_labels(data.get('expertise'))]
    elif user.reviewer:
        # Database FKs will also reject references by a coordinator, chair or review.
        db.delete(user.reviewer)
    db.flush()
    return user

def save_paper(db,data,paper=None):
    creating=paper is None
    if creating: paper=Paper();db.add(paper)
    for f in ('title','abstract','status'): setattr(paper,f,data[f])
    paper.track_id=integer(data['track_id'],'track_id')
    paper.submission_date=parse_date(data['submission_date'])
    paper.session_id=integer(data['session_id'],'session_id') if data.get('session_id') else None
    validate_assignment(db,paper)
    db.flush()
    authors=data.get('authors')
    if authors is not None:
        validate_paper_authors(db,paper.paper_id,authors)
        paper.authors.clear();db.flush()
        paper.authors=[PaperAuthor(author_id=integer(a['author_id'],'author_id'),author_position=integer(a['author_position'],'author_position'),is_corresponding=boolean(a.get('is_corresponding'))) for a in authors]
    elif creating: raise ValidationError('Authors are required')
    if 'keywords' in data:
        paper.keywords=[PaperKeyword(keyword=k) for k in split_labels(data['keywords'])]
    if 'versions' in data:
        versions=data['versions']
        nums=[integer(v['version_no'],'version_no') for v in versions]
        if len(nums)!=len(set(nums)): raise ValidationError('Version numbers must be unique')
        paper.versions=[PaperVersion(version_no=integer(v['version_no'],'version_no'),file_location=v['file_location'],uploaded_at=parse_datetime(v['uploaded_at']),change_note=v.get('change_note')) for v in versions]
    db.flush();return paper

def save_review(db,data,review=None):
    pid=integer(data['paper_id'],'paper_id');rid=integer(data['reviewer_id'],'reviewer_id')
    validate_self_review(db,pid,rid)
    for f in ('recommendation','comments_for_authors'):
        if not (data.get(f) or '').strip(): raise ValidationError(f'{f.replace("_"," ")} is required (completed reviews only)')
    if review is None: review=Review();db.add(review)
    for f,v in [('paper_id',pid),('reviewer_id',rid),('overall_score',integer(data['overall_score'],'overall_score'))]: setattr(review,f,v)
    for f in ('recommendation','comments_for_authors','confidential_comments'): setattr(review,f,data.get(f) or None)
    review.review_submission_date=parse_date(data['review_submission_date'])
    db.flush();return review

def save_session(db,data,session=None):
    if session is None: session=ConferenceSession();db.add(session)
    session.conference_id=integer(data['conference_id'],'conference_id')
    session.chair_id=integer(data['chair_id'],'chair_id')
    for f in ('title','room_label'): setattr(session,f,data[f])
    session.session_date=parse_date(data['session_date'])
    session.start_time=parse_time(data['start_time']);session.end_time=parse_time(data['end_time'])
    if session.end_time<=session.start_time: raise ValidationError('Session end time must be after start time')
    if session.session_id:
        for paper in db.scalars(select(Paper).where(Paper.session_id==session.session_id)):
            # check session conference updates
            if db.get(Track,paper.track_id).conference_id!=session.conference_id:
                raise ValidationError('Cannot move session: existing paper belongs to another conference')
    db.flush();return session

def delete_entity(db,kind,entity):
    if kind=='sessions':
        for paper in db.scalars(select(Paper).where(Paper.session_id==entity.session_id)):
            paper.session_id=None
        db.flush()
    db.delete(entity);db.flush()
