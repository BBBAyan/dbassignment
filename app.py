"""Flask administrative interface, complete CRUD for four core resources."""
import json, os
from datetime import date,datetime,time
from flask import Flask,request,redirect,url_for,flash,render_template,abort
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError,SQLAlchemyError,DBAPIError
from sqlalchemy.orm import Session,selectinload
from models import *
from services import *

app=Flask(__name__);app.secret_key=os.getenv('SECRET_KEY','development-change-this-secret')
engine=make_engine()
KINDS={'users':AppUser,'papers':Paper,'reviews':Review,'sessions':ConferenceSession}
PK={'users':'user_id','papers':'paper_id','reviews':'review_id','sessions':'session_id'}
FIELDS={
'users':['given_name','surname','email','affiliation','country','phone_number','is_author','orcid','research_areas','is_reviewer','years_experience','expertise'],
'papers':['track_id','title','abstract','submission_date','status','session_id','authors_json','keywords','versions_json'],
'reviews':['paper_id','reviewer_id','overall_score','recommendation','comments_for_authors','confidential_comments','review_submission_date'],
'sessions':['conference_id','title','session_date','start_time','end_time','room_label','chair_id']}


def to_form(kind,obj):
    if not obj: return {}
    fields=FIELDS[kind];d={f:str(getattr(obj,f) or '') for f in fields if hasattr(obj,f)}
    if kind=='users':
        d.update(is_author=bool(obj.author),is_reviewer=bool(obj.reviewer),orcid=obj.author.orcid if obj.author else '',research_areas=', '.join(x.area_label for x in obj.author.areas) if obj.author else '',years_experience=obj.reviewer.years_experience if obj.reviewer else 0,expertise=', '.join(x.area_label for x in obj.reviewer.expertise) if obj.reviewer else '')
    elif kind=='papers':
        d['authors_json']=json.dumps([dict(author_id=a.author_id,author_position=a.author_position,is_corresponding=a.is_corresponding) for a in sorted(obj.authors,key=lambda x:x.author_position)],indent=2)
        d['keywords']=', '.join(x.keyword for x in obj.keywords)
        d['versions_json']=json.dumps([dict(version_no=v.version_no,file_location=v.file_location,uploaded_at=v.uploaded_at.isoformat(),change_note=v.change_note) for v in sorted(obj.versions,key=lambda x:x.version_no)],indent=2)
    return d

def parse_form(kind,form):
    d=form.to_dict()
    if kind=='users': d.update(is_author=('is_author' in form),is_reviewer=('is_reviewer' in form))
    if kind=='papers':
        try:
            d['authors']=json.loads(d.pop('authors_json') or '[]')
            d['versions']=json.loads(d.pop('versions_json') or '[]')
        except (json.JSONDecodeError,TypeError) as e: raise ValidationError('Authors and versions must be valid JSON: '+str(e))
        if not isinstance(d['authors'],list) or not isinstance(d['versions'],list): raise ValidationError('Authors and versions must be JSON arrays')
    return d

@app.route('/')
def home():
    with Session(engine) as db:
        counts={k:db.query(v).count() for k,v in KINDS.items()}
    return render_template('home.html',counts=counts)

@app.route('/<kind>')
def listing(kind):
    if kind not in KINDS: abort(404)
    with Session(engine) as db:
        rows=db.scalars(select(KINDS[kind]).order_by(getattr(KINDS[kind],PK[kind]))).all()
        data=[{'id':getattr(x,PK[kind]),'summary':(x.full_name+' · '+x.email if kind=='users' else x.title if kind in ('papers','sessions') else f'Paper {x.paper_id}, reviewer {x.reviewer_id}, score {x.overall_score}') } for x in rows]
    return render_template('list.html',kind=kind,rows=data)

@app.route('/<kind>/new',methods=['GET','POST'])
@app.route('/<kind>/<int:object_id>/edit',methods=['GET','POST'])
def edit(kind,object_id=None):
    if kind not in KINDS: abort(404)
    with Session(engine) as db:
        obj=db.get(KINDS[kind],object_id) if object_id else None
        if object_id and obj is None: abort(404)
        options={'tracks':[(t.track_id,f'{t.name} ({t.conference_id})') for t in db.scalars(select(Track))],
                 'conferences':[(c.conference_id,c.acronym) for c in db.scalars(select(Conference))],
                 'sessions':[(s.session_id,f'{s.title} ({s.conference_id})') for s in db.scalars(select(ConferenceSession))],
                 'reviewers':[(r.reviewer_id,r.user.full_name) for r in db.scalars(select(Reviewer))],
                 'authors':[(a.author_id,a.user.full_name) for a in db.scalars(select(Author))],
                 'papers':[(p.paper_id,p.title) for p in db.scalars(select(Paper))]}
        values=to_form(kind,obj)
        if request.method=='POST':
            values=request.form.to_dict()
            try:
                data=parse_form(kind,request.form)
                if kind=='users': save_user(db,data,obj)
                elif kind=='papers': save_paper(db,data,obj)
                elif kind=='reviews': save_review(db,data,obj)
                elif kind=='sessions': save_session(db,data,obj)
                db.commit(); flash('Saved successfully','success');return redirect(url_for('listing',kind=kind))
            except (ValidationError,SQLAlchemyError,ValueError,KeyError) as exc:
                db.rollback();flash(f'Could not save: {str(exc.orig) if isinstance(exc,DBAPIError) else exc}','error')
        return render_template('form.html',kind=kind,fields=FIELDS[kind],values=values,object_id=object_id,options=options)

@app.route('/<kind>/<int:object_id>/delete',methods=['POST'])
def remove(kind,object_id):
    if kind not in KINDS: abort(404)
    with Session(engine) as db:
        obj=db.get(KINDS[kind],object_id)
        if obj is None: abort(404)
        try:
            delete_entity(db,kind,obj);db.commit();flash('Deleted successfully','success')
        except (SQLAlchemyError,ValidationError) as exc:
            db.rollback();flash(f'Deletion rejected: {str(exc.orig) if isinstance(exc,DBAPIError) else exc}','error')
    return redirect(url_for('listing',kind=kind))

@app.route('/schedule')
def schedule():
    from sqlalchemy import text
    with engine.connect() as conn:
        result=conn.execute(text('SELECT * FROM accepted_paper_schedule ORDER BY conference_id, session_date, start_time, session_id, paper_id'))
        cols=list(result.keys());rows=result.fetchall()
    return render_template('schedule.html',columns=cols,rows=rows)

@app.route('/health')
def health():
    from sqlalchemy import text
    with engine.connect() as c: c.execute(text('SELECT 1'))
    return {'status':'ok'}

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')),debug=os.getenv('FLASK_DEBUG')=='1')
