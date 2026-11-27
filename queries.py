"""Assignment Part 2: labelled operations on independent original seed snapshots.

Usage: python queries.py > query_results.txt
Mutations are shown before/after and rolled back. Engine echo logs SQL and bind values.
"""
from sqlalchemy import text
from models import make_engine,Base
from seed import reset_database

engine=make_engine(echo=True)

def exercise(number,description,sql,params=None,pre=None,after=None):
    print('\n'+'='*90+'\nTASK '+number+' — '+description+'\n'+'='*90,flush=True)
    print('SQL:',sql, '\nPARAMETERS:',params or {},flush=True)
    with engine.connect() as c:
        tx=c.begin()
        try:
            if pre:
                print('BEFORE:',[dict(r) for r in c.execute(text(pre),params or {}).mappings().all()],flush=True)
            result=c.execute(text(sql),params or {})
            if result.returns_rows:
                print('RESULT:',[dict(r) for r in result.mappings().all()],flush=True)
            else: print('ROWS AFFECTED:',result.rowcount,flush=True)
            if after:
                print('AFTER:',[dict(r) for r in c.execute(text(after),params or {}).mappings().all()],flush=True)
        finally:
            tx.rollback();print('ROLLBACK: independent original seed restored',flush=True)


def run():
    print('TASK 1 — CREATE: Base.metadata.create_all and CREATE VIEW are invoked in reset_database.')
    print('TASK 2 — INSERT: deterministic data populated in reset_database via SQLAlchemy Session.add.')
    reset_database(engine)
    with engine.connect() as c:
        for table in Base.metadata.sorted_tables:
            print('TASK 2 ROW COUNT:',table.name,c.execute(text(f'SELECT COUNT(*) FROM {table.name}')).scalar_one())

    exercise('3.1','Update Arman phone',
        "UPDATE app_user SET phone_number=:phone WHERE email=:email",
        {'phone':'+77773414141','email':'arman.armanov@example.com'},
        'SELECT user_id,email,phone_number FROM app_user WHERE email=:email',
        'SELECT user_id,email,phone_number FROM app_user WHERE email=:email')
    exercise('3.2','Conditional deadline extension (both city branches)',
        "UPDATE conference SET review_deadline=review_deadline + CASE WHEN city='Astana' THEN 7 ELSE 3 END",
        pre='SELECT conference_id,city,review_deadline FROM conference ORDER BY conference_id',
        after='SELECT conference_id,city,review_deadline FROM conference ORDER BY conference_id')
    exercise('4.1','Delete withdrawn Amina corresponding papers (children cascade)',
        """DELETE FROM paper WHERE status='withdrawn' AND paper_id IN (
            SELECT pa.paper_id FROM paper_author pa JOIN app_user u ON u.user_id=pa.author_id
            WHERE pa.is_corresponding=TRUE AND u.email=:email)""",
        {'email':'amina.aminova@example.com'},
        """SELECT p.paper_id,p.title FROM paper p JOIN paper_author pa ON pa.paper_id=p.paper_id
           JOIN app_user u ON u.user_id=pa.author_id
           WHERE p.status='withdrawn' AND pa.is_corresponding=TRUE AND u.email=:email ORDER BY p.paper_id""",
        """SELECT (SELECT COUNT(*) FROM paper WHERE paper_id IN (8,9)) AS papers,
           (SELECT COUNT(*) FROM paper_author WHERE paper_id IN (8,9)) AS authorships,
           (SELECT COUNT(*) FROM paper_keyword WHERE paper_id IN (8,9)) AS keywords,
           (SELECT COUNT(*) FROM paper_version WHERE paper_id IN (8,9)) AS versions,
           (SELECT COUNT(*) FROM review WHERE paper_id IN (8,9)) AS reviews,
           (SELECT COUNT(*) FROM app_user WHERE email='amina.aminova@example.com') AS amina_user_kept""")
    exercise('4.2','Delete empty sessions of Astana conferences',
        """DELETE FROM conference_session s WHERE NOT EXISTS
          (SELECT 1 FROM paper p WHERE p.session_id=s.session_id)
          AND EXISTS (SELECT 1 FROM conference c WHERE c.conference_id=s.conference_id AND c.city=:city)""",
        {'city':'Astana'},
        """SELECT s.session_id,s.title FROM conference_session s JOIN conference c ON c.conference_id=s.conference_id
        WHERE c.city=:city ORDER BY s.session_id""",
        """SELECT s.session_id,s.title FROM conference_session s JOIN conference c ON c.conference_id=s.conference_id
        WHERE c.city=:city ORDER BY s.session_id""")
    exercise('5.1','Accepted papers and corresponding authors',
        """SELECT p.paper_id,p.title,u.given_name || ' ' || u.surname AS corresponding_author,
          u.email,t.name AS track_name,c.conference_id,c.acronym FROM paper p
          JOIN paper_author pa ON pa.paper_id=p.paper_id AND pa.is_corresponding=TRUE
          JOIN app_user u ON u.user_id=pa.author_id
          JOIN track t ON t.track_id=p.track_id JOIN conference c ON c.conference_id=t.conference_id
          WHERE p.status='accepted' ORDER BY p.paper_id""")
    exercise('5.2','Abstract phrase case-insensitive',
        'SELECT paper_id,title FROM paper WHERE abstract ILIKE :pattern ORDER BY paper_id',
        {'pattern':'%machine learning%'})
    exercise('5.3','Version history descending',
        """SELECT paper_id,version_no,file_location,uploaded_at FROM paper_version
          WHERE paper_id=:paper_id ORDER BY version_no DESC""",{'paper_id':1})
    exercise('5.4','Conference database experts with experience >= 3',
        """SELECT DISTINCT u.user_id,u.given_name || ' ' || u.surname AS full_name,u.email
          FROM conference_reviewer cr JOIN reviewer r ON r.reviewer_id=cr.reviewer_id
          JOIN reviewer_expertise e ON e.reviewer_id=r.reviewer_id
          JOIN app_user u ON u.user_id=r.reviewer_id
          WHERE cr.conference_id=:conference_id AND e.area_label=:expertise
          AND r.years_experience>=:years ORDER BY u.user_id""",
        {'conference_id':1,'expertise':'Databases','years':3})
    exercise('6.1','Track paper and distinct author counts including empty track',
        """SELECT t.track_id,t.name,t.conference_id,COUNT(DISTINCT p.paper_id) AS paper_count,
          COUNT(DISTINCT pa.author_id) AS distinct_author_count
          FROM track t LEFT JOIN paper p ON p.track_id=t.track_id
          LEFT JOIN paper_author pa ON pa.paper_id=p.paper_id
          GROUP BY t.track_id,t.name,t.conference_id ORDER BY t.track_id""")
    exercise('6.2','Reviewer review counts and average including zero reviews',
        """SELECT r.reviewer_id,u.given_name || ' ' || u.surname AS full_name,
          COUNT(v.review_id) AS review_count,ROUND(AVG(v.overall_score)::numeric,2) AS avg_score
          FROM reviewer r JOIN app_user u ON u.user_id=r.reviewer_id
          LEFT JOIN review v ON v.reviewer_id=r.reviewer_id
          GROUP BY r.reviewer_id,u.given_name,u.surname ORDER BY r.reviewer_id""")
    exercise('6.3','Conference counts and average of each review exactly once',
        """WITH paper_stats AS (
          SELECT t.conference_id,COUNT(p.paper_id) AS total_papers,
          COUNT(p.paper_id) FILTER(WHERE p.status='accepted') AS accepted_papers
          FROM track t LEFT JOIN paper p ON p.track_id=t.track_id GROUP BY t.conference_id),
          review_stats AS (
          SELECT t.conference_id,ROUND(AVG(r.overall_score)::numeric,2) AS avg_overall_score
          FROM track t JOIN paper p ON p.track_id=t.track_id
          JOIN review r ON r.paper_id=p.paper_id GROUP BY t.conference_id)
          SELECT c.conference_id,c.acronym,COALESCE(ps.total_papers,0) AS total_papers,
          COALESCE(ps.accepted_papers,0) AS accepted_papers,rs.avg_overall_score
          FROM conference c LEFT JOIN paper_stats ps ON ps.conference_id=c.conference_id
          LEFT JOIN review_stats rs ON rs.conference_id=c.conference_id ORDER BY c.conference_id""")
    exercise('6.4','Reviewers above overall reviewer average incl zero reviewers',
        """WITH counts AS (
          SELECT r.reviewer_id,COUNT(v.review_id) AS review_count
          FROM reviewer r LEFT JOIN review v ON v.reviewer_id=r.reviewer_id
          GROUP BY r.reviewer_id),
          overall AS (SELECT AVG(review_count::numeric) AS overall_average FROM counts)
          SELECT c.reviewer_id,u.given_name || ' ' || u.surname AS full_name,
          c.review_count,ROUND(o.overall_average,2) AS overall_average
          FROM counts c CROSS JOIN overall o JOIN app_user u ON u.user_id=c.reviewer_id
          WHERE c.review_count>o.overall_average ORDER BY c.reviewer_id""")
    exercise('7','Acceptance rate among decisions only',
        """SELECT c.conference_id,c.acronym,
          COUNT(p.paper_id) FILTER(WHERE p.status='accepted') AS accepted_count,
          COUNT(p.paper_id) FILTER(WHERE p.status='rejected') AS rejected_count,
          ROUND(100.0*COUNT(p.paper_id) FILTER(WHERE p.status='accepted') /
          NULLIF(COUNT(p.paper_id) FILTER(WHERE p.status IN ('accepted','rejected')),0),2) AS acceptance_rate
          FROM conference c LEFT JOIN track t ON t.conference_id=c.conference_id
          LEFT JOIN paper p ON p.track_id=t.track_id
          GROUP BY c.conference_id,c.acronym ORDER BY c.conference_id""")
    exercise('8','Query real database view accepted_paper_schedule',
        """SELECT * FROM accepted_paper_schedule
          ORDER BY conference_id,session_date,start_time,session_id,paper_id""")
    print('\nAll independent operations completed; initial seed database remains unchanged.')

if __name__=='__main__':run()
