"""Deterministic fictional seed. Run: python seed.py --reset"""
import argparse
from datetime import date, datetime, time
from sqlalchemy import text
from sqlalchemy.orm import Session
from models import *

USERS=[
(1,'Arman','Armanov','arman.armanov@example.com','NU','Kazakhstan','+77001112233','both',5),
(2,'Amina','Aminova','amina.aminova@example.com','NU','Kazakhstan',None,'author',0),
(3,'Dana','Sadykova','dana@example.com','KBTU','Kazakhstan',None,'both',6),
(4,'Timur','Ospanov','timur@example.com','NU','Kazakhstan',None,'reviewer',8),
(5,'Leila','Karim','leila@example.com','MIT','USA',None,'both',4),
(6,'Maksat','Nurlan','maksat@example.com','AITU','Kazakhstan',None,'author',0),
(7,'Sofia','Chen','sofia@example.com','Oxford','UK',None,'reviewer',9),
(8,'Ali','Bek','ali@example.com','NU','Kazakhstan',None,'author',0),
(9,'Noor','Patel','noor@example.com','Stanford','USA',None,'both',3),
(10,'Elena','Smith','elena@example.com','ETH','Switzerland',None,'reviewer',2),
(11,'Boris','Lee','boris@example.com','KU','Kazakhstan',None,'author',0),
(12,'Sara','Kim','sara@example.com','Cambridge','UK',None,'reviewer',5)]
CONFERENCES=[(1,'International Computing Summit','ICS26','Data and AI','Astana','Kazakhstan',date(2026,12,10),date(2026,12,12),date(2026,10,10),date(2026,11,10)),
(2,'Global Data Research Forum','GDR26','Databases and systems','Prague','Czechia',date(2027,1,15),date(2027,1,17),date(2026,10,20),date(2026,11,20)),
(3,'Central Asia Future Tech','CAFT27','Research planning','Astana','Kazakhstan',date(2027,2,10),date(2027,2,11),date(2026,12,1),date(2027,1,5))]
PAPERS=[
(1,1,'Learning for Sustainable Cities','We use machine learning for climate risk.',date(2026,9,3),'accepted',1,[2,6],2,['AI','climate'],2),
(2,1,'Efficient Query Planning','Cost based indexing in relational engines.',date(2026,9,4),'accepted',None,[3,8],3,['Databases'],1),
(3,2,'Ethical Research Data','Privacy and governance in research.',date(2026,9,5),'rejected',None,[5],5,['Ethics'],1),
(4,2,'Graph Analysis','Graph algorithms in networks.',date(2026,9,6),'under review',None,[1,11],1,['graphs'],1),
(5,3,'Federated ML Security','Machine Learning in sensitive data.',date(2026,9,7),'submitted',None,[6,8],6,['privacy','AI'],1),
(6,3,'Adaptive Systems','Optimization for scheduling.',date(2026,9,8),'accepted',2,[2,5],5,['optimization'],2),
(7,4,'Ocean Data Platforms','A cloud-native data pipeline.',date(2026,9,9),'accepted',3,[3,11],3,['cloud'],1),
(8,4,'Human Factors in AI','Trust and usability studies.',date(2026,9,10),'withdrawn',None,[2,8],2,['HCI'],1),
(9,1,'A Second Withdrawn Study','A replication of older models.',date(2026,9,11),'withdrawn',None,[2,6],2,['replication'],1),
(10,4,'Reliable Transactions','Concurrency control and serializability.',date(2026,9,12),'rejected',None,[1,6],1,['transactions'],1),
(11,2,'Computational Linguistics','Language modelling using transformers.',date(2026,9,13),'accepted',None,[5,11],5,['NLP'],1),
(12,3,'Distributed Monitoring','Scalable system telemetry.',date(2026,9,14),'under review',None,[8],8,['systems'],1)]
REVIEWS=[(1,1,4,5,'accept'),(2,1,7,4,'accept'),(3,2,4,4,'accept'),(4,2,7,5,'accept'),
(5,3,4,2,'reject'),(6,3,9,3,'reject'),(7,4,7,3,'reject'),(8,5,3,4,'accept'),
(9,6,4,5,'accept'),(10,6,9,4,'accept'),(11,7,4,5,'accept'),(12,8,7,2,'reject'),
(13,9,4,2,'reject'),(14,10,7,2,'reject'),(15,11,9,4,'accept'),(16,12,4,3,'accept')]

def populate(session):
    for uid,first,last,email,aff,country,phone,role,years in USERS:
        session.add(AppUser(user_id=uid,given_name=first,surname=last,email=email,affiliation=aff,country=country,phone_number=phone));
        if role in ('both','author'):
            session.add(Author(author_id=uid,orcid=f'0000-0002-0000-{uid:04d}'))
            session.add(AuthorResearchArea(author_id=uid,area_label='Computer Science'))
        if role in ('both','reviewer'):
            session.add(Reviewer(reviewer_id=uid,years_experience=years))
            session.add(ReviewerExpertise(reviewer_id=uid,area_label='Databases' if uid in (1,3,4,7,9) else 'Artificial Intelligence'))
    session.flush()
    for id_,name,acronym,desc,city,country,start,end,submit,review in CONFERENCES:
        session.add(Conference(conference_id=id_,name=name,acronym=acronym,description=desc,city=city,country=country,start_date=start,end_date=end,submission_deadline=submit,review_deadline=review))
        session.add(ConferenceHost(conference_id=id_,host_name=f'{city} Research Institute'))
    session.flush()
    for cid, ids in [(1,[1,3,4,7,9,10,12]),(2,[1,3,4,7,9,12]),(3,[1,4,7])]:
        for uid in ids: session.add(ConferenceReviewer(conference_id=cid,reviewer_id=uid))
    for vals in [(1,1,'AI & ML','Machine learning','AI',4),(2,1,'Responsible Tech','Privacy and ethics','Ethics',7),(3,1,'Systems','Distributed systems','Systems',1),(4,2,'Database Engineering','Database applications','Databases',3),(5,2,'Empty Track','No assigned papers','Theory',7),(6,3,'Future Computing','Exploratory track','Computing',1)]:
        session.add(Track(track_id=vals[0],conference_id=vals[1],name=vals[2],description=vals[3],research_area=vals[4],coordinator_id=vals[5]))
    session.flush()
    for id_,cid,name,day,start,end,room,chair in [(1,1,'AI Keynotes',date(2026,12,10),time(10),time(12),'A101',4),
        (2,1,'Advanced Systems',date(2026,12,11),time(13),time(15),'B202',7),
        (3,2,'Data Practice',date(2027,1,15),time(11),time(13),'P1',3),
        (4,1,'Empty Astana Session',date(2026,12,12),time(9),time(10),'C303',1),
        (5,3,'Empty Future Session',date(2027,2,10),time(9),time(11),'D4',1)]:
        session.add(ConferenceSession(session_id=id_,conference_id=cid,title=name,session_date=day,start_time=start,end_time=end,room_label=room,chair_id=chair))
    session.flush()
    for pid,tid,title,abstract,submit,status,sid,authors,corr,keywords,nver in PAPERS:
        session.add(Paper(paper_id=pid,track_id=tid,title=title,abstract=abstract,submission_date=submit,status=status,session_id=sid)); session.flush()
        for pos,aid in enumerate(authors,1): session.add(PaperAuthor(paper_id=pid,author_id=aid,author_position=pos,is_corresponding=(aid==corr)))
        for kw in keywords: session.add(PaperKeyword(paper_id=pid,keyword=kw))
        for ver in range(1,nver+1):
            session.add(PaperVersion(paper_id=pid,version_no=ver,file_location=f'/files/paper_{pid}_v{ver}.pdf',uploaded_at=datetime(2026,9,submit.day,10,ver),change_note='Revised' if ver>1 else 'Initial submission'))
    session.flush()
    for rid,pid,uid,score,rec in REVIEWS:
        session.add(Review(review_id=rid,paper_id=pid,reviewer_id=uid,overall_score=score,recommendation=rec,comments_for_authors=f'Completed assessment for paper {pid}.',review_submission_date=date(2026,10,15)))
    session.flush()

SEQUENCES=[('app_user','user_id'),('conference','conference_id'),('track','track_id'),
           ('conference_session','session_id'),('paper','paper_id'),('review','review_id')]

def sync_sequences(session):
    """Seed rows use explicit IDs, so PostgreSQL's SERIAL sequences still start at 1.
    Without this, the first web-form INSERT fails with a duplicate primary key."""
    if session.get_bind().dialect.name!='postgresql': return
    for table,col in SEQUENCES:
        session.execute(text(f"SELECT setval(pg_get_serial_sequence('{table}','{col}'), (SELECT MAX({col}) FROM {table}))"))

def reset_database(engine):
    from sqlalchemy import text
    with engine.begin() as c: c.execute(text('DROP VIEW IF EXISTS accepted_paper_schedule'))
    Base.metadata.drop_all(engine)
    create_schema(engine)
    with Session(engine) as session:
        populate(session); sync_sequences(session); session.commit()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--reset',action='store_true');args=parser.parse_args()
    if not args.reset: parser.error('Specify --reset to acknowledge replacing the existing database')
    engine=make_engine();reset_database(engine)
    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            print(table.name,conn.execute(text(f'SELECT COUNT(*) FROM {table.name}')).scalar_one())
