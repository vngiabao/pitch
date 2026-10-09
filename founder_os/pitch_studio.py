"""Editable, versioned pitches anchored to the original Pitch OS records."""
import json,re,uuid
from .store import now,js,digest

LENGTHS=[30,60,180,300,420,600,900,1200]
AUDIENCES=['General','Competition judges','Investors','Families & customers','Older storytellers','University & community partners','AI & technology partners']
SCENARIOS=['Quick introduction','Networking','Competition stage','Application video','Investor meeting','Customer conversation','Partnership meeting','Product demonstration']
SCHEMA='''
CREATE TABLE IF NOT EXISTS pitch_documents(
 pitch_id TEXT PRIMARY KEY REFERENCES pitches(id),current_version_id TEXT NOT NULL REFERENCES pitch_versions(id),updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pitch_versions(
 id TEXT PRIMARY KEY,pitch_id TEXT NOT NULL REFERENCES pitches(id),title TEXT NOT NULL,
 duration_seconds INTEGER NOT NULL,audience TEXT NOT NULL,scenario TEXT NOT NULL,speaker TEXT NOT NULL,
 body TEXT NOT NULL,notes TEXT NOT NULL,format TEXT NOT NULL,status TEXT NOT NULL,
 sources_json TEXT NOT NULL,claim_versions_json TEXT NOT NULL,created_at TEXT NOT NULL,
 parent_version_id TEXT REFERENCES pitch_versions(id),change_note TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS pitch_version_history ON pitch_versions(pitch_id,created_at);
CREATE TABLE IF NOT EXISTS pitch_seed_keys(seed_key TEXT PRIMARY KEY,pitch_id TEXT NOT NULL REFERENCES pitches(id));
CREATE TRIGGER IF NOT EXISTS pitch_version_immutable BEFORE UPDATE ON pitch_versions BEGIN SELECT RAISE(ABORT,'Pitch versions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS pitch_version_retain BEFORE DELETE ON pitch_versions BEGIN SELECT RAISE(ABORT,'Pitch history is retained'); END;
'''

class PitchConflict(ValueError):pass

class PitchStudio:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.db.executescript(SCHEMA)
    def _fields(self,p):
        result={}
        for name,limit in [('title',160),('audience',100),('scenario',100),('speaker',100),('body',40000),('notes',10000),('change_note',300)]:
            value=p.get(name,'')
            if not isinstance(value,str) or len(value)>limit:raise ValueError(name+' must be text of at most '+str(limit)+' characters')
            result[name]=value.strip()
        if not result['title'] or not result['body']:raise ValueError('A title and pitch text are required')
        result['audience']=result['audience'] or 'General';result['scenario']=result['scenario'] or 'Quick introduction'
        duration=p.get('duration_seconds',60)
        if isinstance(duration,bool) or not isinstance(duration,int) or not 10<=duration<=7200:raise ValueError('Pitch length must be 10 to 7200 seconds')
        result['duration_seconds']=duration
        result['format']=p.get('format','script');result['status']=p.get('status','draft')
        if result['format'] not in ('script','outline'):raise ValueError('Choose a spoken script or working outline')
        if result['status'] not in ('draft','rehearsal_ready','archived'):raise ValueError('Unknown pitch status')
        for field,table in [('sources','source_versions'),('claim_versions','claim_versions')]:
            values=p.get(field,[])
            if not isinstance(values,list) or len(values)>30 or any(not isinstance(v,str) for v in values):raise ValueError('Invalid '+field)
            values=list(dict.fromkeys(values))
            for value in values:self.s.one('SELECT id FROM '+table+' WHERE id=?',(value,))
            result[field]=values
        return result
    def _version(self,pid,f,parent=None):
        vid='pitch-version-'+uuid.uuid4().hex;stamp=now()
        self.db.execute('INSERT INTO pitch_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (vid,pid,f['title'],f['duration_seconds'],f['audience'],f['scenario'],f['speaker'],f['body'],f['notes'],f['format'],f['status'],js(f['sources']),js(f['claim_versions']),stamp,parent,f['change_note']))
        self.db.execute('INSERT INTO pitch_documents VALUES(?,?,?) ON CONFLICT(pitch_id) DO UPDATE SET current_version_id=excluded.current_version_id,updated_at=excluded.updated_at',(pid,vid,stamp))
        for source in f['sources']:self.s.import_receipt(source,'pitch_version',vid,'working pitch adaptation','Draft wording; source preserved; not promoted to company truth')
        self.s.log('pitch.version_saved','pitch_studio',{'pitch_id':pid,'version_id':vid,'parent_version_id':parent,'status':f['status']})
        return vid
    def sync_legacy(self):
        with self.s.transaction():
            for p in self.s.rows('SELECT p.* FROM pitches p LEFT JOIN pitch_documents d ON d.pitch_id=p.id WHERE d.pitch_id IS NULL'):
                f=self._fields({'title':'Original '+str(p['duration_seconds'])+'-second pitch','duration_seconds':p['duration_seconds'],'audience':p['audience'],
                    'body':p['body'],'notes':'Preserved original Pitch OS draft. Review current product details before using.','sources':[p['source_version_id']] if p['source_version_id'] else [],'claim_versions':json.loads(p['claim_versions_json']),'change_note':'Registered original pitch'})
                self._version(p['id'],f)
    def create(self,p,seed_key=None):
        f=self._fields(p);pid='pitch-'+uuid.uuid4().hex
        with self.s.transaction():
            if seed_key:
                old=self.db.execute('SELECT pitch_id FROM pitch_seed_keys WHERE seed_key=?',(seed_key,)).fetchone()
                if old:return self.detail(old['pitch_id'])
            self.db.execute('INSERT INTO pitches VALUES(?,?,?,?,?,?,?,?)',(pid,f['duration_seconds'],f['audience'],f['body'],js(f['claim_versions']),'draft',now(),f['sources'][0] if f['sources'] else None))
            self._version(pid,f)
            if seed_key:self.db.execute('INSERT INTO pitch_seed_keys VALUES(?,?)',(seed_key,pid))
        return self.detail(pid)
    def save(self,pid,p):
        f=self._fields(p)
        with self.s.transaction():
            old=self.s.one('SELECT current_version_id FROM pitch_documents WHERE pitch_id=?',(pid,))
            if p.get('expected_version_id')!=old['current_version_id']:raise PitchConflict('This pitch changed in another tab. Your edits are still here. Copy them, then reload the latest version.')
            self._version(pid,f,old['current_version_id'])
        return self.detail(pid)
    def restore(self,pid,vid,expected):
        v=self.s.one('SELECT * FROM pitch_versions WHERE id=? AND pitch_id=?',(vid,pid))
        f=self._decoded(v);f.update(expected_version_id=expected,change_note='Restored a copy of '+vid)
        return self.save(pid,f)
    def _decoded(self,v):
        v=dict(v);v['sources']=json.loads(v.pop('sources_json'));v['claim_versions']=json.loads(v.pop('claim_versions_json'))
        v['word_count']=len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b",v['body']));v['estimated_seconds']=round(v['word_count']/130*60)
        v['target_words']=round(v['duration_seconds']/60*130)
        v['placeholders']=list(dict.fromkeys(re.findall(r'\[[^\]\n]{1,250}\]',v['body'])))
        return v
    def detail(self,pid):
        v=self.s.one('SELECT v.* FROM pitch_documents d JOIN pitch_versions v ON v.id=d.current_version_id WHERE d.pitch_id=?',(pid,))
        result=self._decoded(v)
        result['history']=self.s.rows('SELECT id,title,created_at,change_note,format,status FROM pitch_versions WHERE pitch_id=? ORDER BY rowid DESC',(pid,))
        result['source_details']=[self.s.one('SELECT v.id,v.captured_at,s.original_path,s.kind,(SELECT m.id FROM material_library m WHERE m.source_version_id=v.id LIMIT 1) material_id FROM source_versions v JOIN sources s ON s.id=v.source_id WHERE v.id=?',(key,)) for key in result['sources']] if self.db.execute("SELECT 1 FROM sqlite_master WHERE name='material_library'").fetchone() else [self.s.one('SELECT v.id,v.captured_at,s.original_path,s.kind,NULL material_id FROM source_versions v JOIN sources s ON s.id=v.source_id WHERE v.id=?',(key,)) for key in result['sources']]
        result['claim_details']=[self.s.one('SELECT v.id,c.label,v.body,r.status,c.canonical_version_id FROM claim_versions v JOIN claims c ON c.id=v.claim_id LEFT JOIN claim_reviews r ON r.version_id=v.id WHERE v.id=?',(key,)) for key in result['claim_versions']]
        return result
    def list(self,q='',audience='',scenario='',duration='',archived=False):
        self.sync_legacy();where=["v.status!='archived'"] if not archived else [];args=[]
        if q:where.append('(instr(lower(v.title),lower(?))>0 OR instr(lower(v.body),lower(?))>0)');args+=[q[:300]]*2
        for name,value in [('audience',audience),('scenario',scenario),('duration_seconds',duration)]:
            if value:where.append('v.'+name+'=?');args.append(value)
        rows=self.s.rows('SELECT v.* FROM pitch_documents d JOIN pitch_versions v ON v.id=d.current_version_id'+(' WHERE '+' AND '.join(where) if where else '')+' ORDER BY v.duration_seconds,v.title',args)
        items=[]
        for row in rows:
            d=self._decoded(row);d['preview']=d.pop('body')[:220];items.append(d)
        choices=self.s.rows('SELECT DISTINCT v.audience,v.scenario,v.duration_seconds FROM pitch_documents d JOIN pitch_versions v ON v.id=d.current_version_id')
        return {'items':items,'lengths':sorted(set(LENGTHS+[r['duration_seconds'] for r in choices])),
            'audiences':list(dict.fromkeys(AUDIENCES+[r['audience'] for r in choices])),
            'scenarios':list(dict.fromkeys(SCENARIOS+[r['scenario'] for r in choices]))}
    def export(self,pid,vid=None):
        r=self._decoded(self.s.one('SELECT * FROM pitch_versions WHERE pitch_id=? AND id=?',(pid,vid))) if vid else self.detail(pid)
        return '\n'.join([r['title'],'','Audience: '+r['audience'],'Scenario: '+r['scenario'],'Speaker: '+(r['speaker'] or 'Not assigned'),
            'Target: '+str(r['duration_seconds'])+' seconds | '+str(r['word_count'])+' words | estimated '+str(r['estimated_seconds'])+' seconds at 130 words/minute',
            'Format: '+r['format']+' | '+r['status'],'Version: '+r['id'],'','PITCH',r['body'],'','SPEAKER NOTES',r['notes'],'',
            'Working draft; historical sources are not current company truth. No external submission or canonical fact change.','Source versions: '+', '.join(r['sources']),'Claim versions: '+', '.join(r['claim_versions'])])
