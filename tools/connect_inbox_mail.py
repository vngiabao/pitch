"""Owner-only inbox setup; the app password arrives on stdin, never in arguments.

Saves it in Windows Credential Manager, then checks a read-only IMAP login.
"""
import imaplib,ssl,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from founder_os.report_email import INBOX_ACCOUNTS,OWNER_ACCOUNT,store_credential,read_credential

def check(account):
    m=imaplib.IMAP4_SSL('imap.gmail.com',993,ssl_context=ssl.create_default_context(),timeout=30)
    try:
        secret=read_credential(account)
        try:m.login(account,secret)
        finally:del secret
        return m.select('INBOX',readonly=True)[0]=='OK'
    finally:
        try:m.logout()
        except (OSError,imaplib.IMAP4.error):pass

if __name__=='__main__':
    account=sys.argv[1] if len(sys.argv)>1 else ''
    if account not in INBOX_ACCOUNTS:print('Unknown inbox.',file=sys.stderr);raise SystemExit(2)
    try:store_credential(sys.stdin.read().strip(),account)
    except Exception:print('The connection could not be saved. Use a 16-letter Google app password for '+account+'.',file=sys.stderr);raise SystemExit(1)
    print('Saved in Windows Credential Manager. No password is saved in the project.')
    try:ok=check(account)
    except imaplib.IMAP4.error:ok=False;print('Google rejected the login. Check that IMAP is on for '+account+' and that this is its app password.',file=sys.stderr)
    except OSError:ok=False;print('Could not reach Gmail to test the login; the tracker will try again later.',file=sys.stderr)
    if ok:print('Read-only inbox access works for '+account+'.'+(' The same password also turns on the 9:30 daily-report fallback.' if account==OWNER_ACCOUNT else ''))
    raise SystemExit(0 if ok else 1)
