#!/usr/bin/env python3
"""Mirror exact Ubuntu sources for privately redistributed compatibility libraries."""
from pathlib import Path
import concurrent.futures,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'.build/compat-apt';(base/'lists/partial').mkdir(parents=True,exist_ok=True)
folder=ROOT/'.build/compat-sources';folder.mkdir(exist_ok=True)
sources=base/'sources.list';sources.write_text('deb-src http://archive.ubuntu.com/ubuntu noble main universe\ndeb-src http://archive.ubuntu.com/ubuntu noble-updates main universe\ndeb-src http://security.ubuntu.com/ubuntu noble-security main universe\n')
status=base/'status';status.write_text('')
opts=['-o',f'Dir::Etc::sourcelist={sources}','-o','Dir::Etc::sourceparts=-','-o',f'Dir::State::lists={base}/lists','-o',f'Dir::State::status={status}','-o','Debug::NoLocking=true']
subprocess.run(['apt-get']+opts+['update'],check=True)
packages={}
for para in (ROOT/'.build/rootfs/var/lib/dpkg/status').read_text().split('\n\n'):
 fields={line.split(': ',1)[0]:line.split(': ',1)[1] for line in para.splitlines() if ': ' in line and not line.startswith(' ')}
 if 'Package' in fields:packages[fields['Package']]=fields
origins=json.loads((ROOT/'.build/unified-stage/usr/share/doc/larsana/compat-libraries.json').read_text())
requested=set()
for entry in origins.values():
 record=packages[entry['package']];source=record.get('Source',record['Package'])
 match=re.fullmatch(r'(\S+)(?: \((.*)\))?',source)
 requested.add((match[1],match[2] or record['Version']))
def fetch(item):
 name,version=item;log=folder/(name+'.log')
 with log.open('w') as stream:
  subprocess.run(['apt-get']+opts+['source','--download-only','--only-source',name+'='+version],cwd=folder,stdout=stream,stderr=subprocess.STDOUT,check=True)
 print('SOURCE',name,version,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(fetch,sorted(requested)))
files=[p for p in folder.iterdir() if p.is_file() and not p.name.endswith('.log') and p.name!='manifest.json']
manifest={'sources':[{'name':n,'version':v} for n,v in sorted(requested)],'files':[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]}
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS exact compatibility-library source mirror',len(requested),flush=True)
