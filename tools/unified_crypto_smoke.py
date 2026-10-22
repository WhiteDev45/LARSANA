#!/usr/bin/env python3
"""Check relocated ICU/JPEG/OpenSSL/cURL functionality across both host ABIs."""
import http.server,json,ssl,subprocess,sys,threading,tempfile
from pathlib import Path
sys.path.insert(0,'/work/src')
from larsana.core import Manager
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.end_headers();self.wfile.write(b'tls-ok')
 def log_message(self,*args):pass
tls=tempfile.TemporaryDirectory()
cert=Path(tls.name)/'cert.pem';key=Path(tls.name)/'key.pem'
subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(key),'-out',str(cert)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
server=http.server.HTTPServer(('127.0.0.1',0),Handler)
context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(cert,key)
server.socket=context.wrap_socket(server.socket,server_side=True)
threading.Thread(target=server.serve_forever,daemon=True).start()
m=Manager()
try:
 for item in m.catalog.installed('php'):
  ini,_,_=m.php_config(item['series'])
  code=r'''if (transliterator_transliterate('Any-Latin; Latin-ASCII','é')!=='e')exit(2);
$im=imagecreatetruecolor(2,2);ob_start();imagejpeg($im);$bytes=ob_get_clean();if(substr($bytes,0,2)!="\xFF\xD8")exit(3);
$c=curl_init('https://localhost:PORT');curl_setopt($c,CURLOPT_CAINFO,'CERTFILE');curl_setopt($c,CURLOPT_RETURNTRANSFER,true);
if(curl_exec($c)!=='tls-ok'){fwrite(STDERR,curl_error($c));exit(4);}
echo 'ok';'''.replace('PORT',str(server.server_port)).replace('CERTFILE',str(cert))
  output=m._run([m.catalog.executable('php',item['series'],'cli'),'-c',str(ini),'-r',code])
  assert output=='ok',output
  print('PASS private ICU/JPEG/cURL TLS',item['version'],flush=True)
finally:server.shutdown();m.close();tls.cleanup()
