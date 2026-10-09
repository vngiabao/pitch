"""Owner-only secure Gmail setup; secret arrives on stdin, never in arguments."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from founder_os.report_email import store_credential
if __name__=='__main__':
    try:store_credential(sys.stdin.read().strip());print('Gmail connection saved in Windows Credential Manager. No password is saved in the project.');raise SystemExit(0)
    except Exception:print('Gmail connection could not be saved. Use a Google app password for the report account.',file=sys.stderr);raise SystemExit(1)
