#!/usr/bin/env python3
"""Mirror matching source modules for the private Qt/PySide/ICU desktop libraries."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'.build/desktop-sources';CACHE.mkdir(parents=True,exist_ok=True)
QT='https://download.qt.io/archive/qt/6.8/6.8.3/submodules/'
modules=['qtbase','qtdeclarative','qttools','qtsvg','qtwayland','qtimageformats','qtquicktimeline','qttranslations','qtlanguageserver','qtshadertools']
items=[{'id':m,'version':'6.8.3','url':QT+m+'-everywhere-src-6.8.3.tar.xz'} for m in modules]
items.append({'id':'pyside-shiboken','version':'6.8.3','url':'https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.8.3-src/pyside-setup-everywhere-src-6.8.3.tar.xz'})
items.append({'id':'icu','version':'73.2','url':'https://github.com/unicode-org/icu/releases/download/release-73-2/icu4c-73_2-src.tgz'})

def metadata(item):
    if item['id']!='icu':
        xml=urllib.request.urlopen(item['url']+'.meta4',timeout=45).read()
        tree=ET.fromstring(xml)
        item['sha256']=next(h.text.strip() for h in tree.findall('.//{*}hash') if h.get('type')=='sha-256')
        item['verification']='SHA256 from official Qt Metalink metadata over HTTPS'
    return item

def download(item):
    item=metadata(item)
    file=CACHE/item['url'].split('/')[-1]
    if not file.exists():
        partial=file.with_name(file.name+'.part')
        with (CACHE/(item['id']+'.log')).open('a') as log:
            subprocess.run(['curl','-L','--fail','--retry','4','--retry-all-errors','--connect-timeout','20','--max-time','600','-C','-',item['url'],'-o',str(partial)],stdout=log,stderr=log,check=True)
        partial.replace(file)
    digest=hashlib.sha256(file.read_bytes()).hexdigest()
    if item.get('sha256') and item['sha256']!=digest:raise RuntimeError('Desktop source hash mismatch: '+item['id'])
    item['sha256']=digest
    item.setdefault('verification','Official Unicode ICU release over HTTPS; SHA256 pinned on retrieval')
    print('SOURCE READY',item['id'],item['version'],flush=True)
    return item
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:locked=list(pool.map(download,items))
(ROOT/'packaging/desktop-sources.lock.json').write_text(json.dumps({'schema':1,'sources':locked},indent=2)+'\n')
print('Matching desktop source modules mirrored and locked.',flush=True)
