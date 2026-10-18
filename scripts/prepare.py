#!/usr/bin/env python3
"""Install a pinned Trivy release under this checkout, checking its archive hash."""
import hashlib,json,platform,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if platform.system()!='Linux' or platform.machine()!='x86_64':raise SystemExit('Automatic setup supports Linux x86_64 / WSL.')
config=json.loads((ROOT/'config/tool.json').read_text())
local=ROOT/'.local';local.mkdir(exist_ok=True)
archive=local/config['asset']
if not archive.exists():
    url=f"https://github.com/aquasecurity/trivy/releases/download/v{config['version']}/{config['asset']}"
    subprocess.run(['curl','--fail','--location','--connect-timeout','15','--max-time','240','--retry','2',url,'--output',str(archive)],check=True)
if hashlib.sha256(archive.read_bytes()).hexdigest()!=config['sha256']:raise SystemExit('Trivy archive checksum mismatch; refusing to execute it.')
with tarfile.open(archive) as source:
    binary=source.extractfile('trivy').read()
folder=local/'bin';folder.mkdir(exist_ok=True)
target=folder/'trivy'
if not target.exists() or target.read_bytes()!=binary:target.write_bytes(binary)
target.chmod(0o755)
subprocess.run([str(target),'--version'],check=True)
