"""Render the real report locally without queuing or sending an email."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store
from founder_os.report_email import DailyReporter

if __name__=='__main__':
    s=Store(ROOT/'data/founder.sqlite')
    try:
        r=DailyReporter(s).render(sample=True)
        folder=ROOT/'reports/email-preview';folder.mkdir(parents=True,exist_ok=True)
        (folder/'index.html').write_text(r['body_html'],encoding='utf-8')
        print('Rendered',len(r['shortlist']),'opportunities;',len(r['body_html'].encode('utf-8')),'HTML bytes')
    finally:s.close()
