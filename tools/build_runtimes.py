#!/usr/bin/env python3
"""Build pinned upstream sources in a rootless Bubblewrap builder; emit .deb.
Usage: python tools/build_runtimes.py [nginx apache-2.4 php-8.5 ...]
"""
import argparse
import hashlib
import gzip
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'.build'

def sandbox(args, cwd='/work', env=None, log=None):
    cmd=['bwrap','--die-with-parent','--unshare-pid','--unshare-ipc','--unshare-uts','--unshare-net',
         '--ro-bind',str(BUILD/'rootfs'),'/', '--bind',str(ROOT),'/work','--dev','/dev','--proc','/proc','--tmpfs','/tmp',
         '--setenv','PATH','/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
         '--setenv','HOME','/tmp', '--setenv','LC_ALL','C','--chdir',cwd]
    for key,value in (env or {}).items():
        cmd+=['--setenv',key,value]
    result=subprocess.run(cmd+list(args), stdout=log, stderr=subprocess.STDOUT if log else None)
    if result.returncode:
        raise RuntimeError(f'Build command exited {result.returncode}: {args}; see build log')


def package(item, stage):
    name='larsana-'+item['id']
    prefix=Path('usr/lib/larsana/runtimes')/item['kind']/item['series']
    # Only the private runtime prefix is distributable. Upstream install targets
    # may also emit systemd/PAM integration files, which LARSANA does not own.
    payload=stage/prefix
    clean=BUILD/'package-stage'/item['id']
    if clean.exists():
        shutil.rmtree(clean)
    installed=clean/prefix
    installed.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(payload,installed,symlinks=True)
    stage=clean
    if item['kind']=='nginx':
        import sys
        sys.path.insert(0,str(ROOT/'src'))
        from larsana.mime import nginx_mime_types
        mime=installed/'conf/mime.types'
        mime.write_text(nginx_mime_types(mime.read_text()))
    roles={
        'nginx':{'server':'sbin/nginx'},
        'apache':{'server':'bin/httpd'},
        'php':{'cli':'bin/php','fpm':'sbin/php-fpm'},
        'mariadb':{'server':'bin/mariadbd','client':'bin/mariadb','admin':'bin/mariadb-admin','install':'scripts/mariadb-install-db'},
    }[item['kind']]
    # MariaDB installs the initialization script in bin in some layouts.
    if item['kind']=='mariadb' and not (installed/roles['install']).exists():
        roles['install']='bin/mariadb-install-db'
    for role,file in roles.items():
        if not (installed/file).is_file():
            raise RuntimeError(f'Missing {role}: {installed/file}')
    manifest={key:item[key] for key in ('kind','series','version','channel','sha256','url','verification')}
    manifest['executables']=roles
    (installed/'runtime.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Remove development-only payloads; preserve server support files and licenses.
    for directory in ['mysql-test','mariadb-test','sql-bench','man','docs','include','manual']:
        shutil.rmtree(installed/directory,ignore_errors=True)
    for archive in installed.rglob('*.a'):
        archive.unlink()
    if item['kind']=='php':
        (installed/'bin/phpdbg').unlink(missing_ok=True)
        # Runtime packages do not expose an incomplete native-extension SDK.
        for tool in ['phpize','php-config']:
            (installed/'bin'/tool).unlink(missing_ok=True)
        shutil.rmtree(installed/'lib/php/build',ignore_errors=True)
        (installed/'php/php/fpm/status.html').unlink(missing_ok=True)
    overrides=[]
    if item['kind']=='php':
        overrides+=['# Private PHP runtimes intentionally retain the upstream libmagic/GD copies.',
                    '# Exact upstream sources and per-branch updates accompany the runtime.']
        for binary in ['bin/php','sbin/php-fpm']:
            path=str(prefix/binary)
            for library in ['file','libgd']:
                overrides.append(f'{name}: embedded-library {library} [{path}]')
        phar=str(prefix/'bin/phar.phar')
        interpreter='/'+str(prefix/'bin/php')
        overrides+=['# phar must use this package CLI, not the global system php-cli.',
            f'{name}: php-script-but-no-php-cli-dep {interpreter} (does not satisfy php-cli:any) [{phar}]',
            f'{name}: wrong-path-for-interpreter {interpreter} != /usr/bin/php [{phar}]']
    if item['kind']=='mariadb':
        overrides+=['# Upstream loadable provider/test plugins resolve symbols via mariadbd.',
                    '# --as-needed omits libc when there are no direct libc references.']
        for plugin in (installed/'lib/plugin').glob('*.so'):
            dynamic=subprocess.check_output(['readelf','-d',str(plugin)],text=True)
            path=str(prefix/plugin.relative_to(installed))
            if 'NEEDED' not in dynamic:
                overrides.append(f'{name}: shared-library-lacks-prerequisites [{path}]')
            elif 'libc.so.6' not in dynamic:
                overrides.append(f'{name}: library-not-linked-against-libc [{path}]')
    if overrides:
        file=stage/'usr/share/lintian/overrides'/name
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text('\n'.join(overrides)+'\n')
    from package_permissions import normalize
    normalize(installed)
    from elf_dependencies import dependencies
    generated=dependencies(stage)
    # Keep explicit non-ELF dependencies (Perl, coreutils) alongside computed ABI requirements.
    deps=generated + (', perl' if item['kind']=='mariadb' else '')
    control=stage/'DEBIAN'
    control.mkdir(exist_ok=True)
    (control/'control').write_text(f'''Package: {name}
Version: {item['version']}-1larsana1
Architecture: amd64
Maintainer: LARSANA Contributors <maintainers@larsana.invalid>
Section: devel
Priority: optional
Depends: {deps}
Description: Isolated {item['kind']} {item['version']} runtime for LARSANA
 Source-built runtime using a private prefix; does not start system services.
''')
    (control/'prerm').write_text("#!/bin/sh\nset -eu\ncase \"$1\" in remove|upgrade|deconfigure)\n  for entry in /proc/[0-9]*/exe; do\n    running=$(readlink \"$entry\" 2>/dev/null || true)\n    case \"$running\" in " + str('/'+str(prefix)) + "/*)\n      echo 'Stop LARSANA services before removing or upgrading this runtime.' >&2\n      exit 1;;\n    esac\n  done;;\nesac\nexit 0\n")
    (control/'prerm').chmod(0o755)
    doc=stage/'usr/share/doc'/name
    doc.mkdir(parents=True,exist_ok=True)
    shutil.copy(ROOT/'runtimes/sources.lock.json', doc/'sources.lock.json')
    source=BUILD/'src'/item['id']
    found=[]
    for pattern in ('LICENSE*','COPYING*','NOTICE*'):
        for file in source.glob(pattern):
            if file.is_file():
                shutil.copy(file,doc/file.name)
                found.append(file.name)
    for notice in source.rglob('*'):
        if not notice.is_file() or notice.is_symlink() or notice.stat().st_size>1024*1024:
            continue
        upper=notice.name.upper()
        if 'LICENSE' not in upper and not upper.startswith(('COPYING','COPYRIGHT','NOTICE')):
            continue
        target=doc/'third-party-notices'/notice.relative_to(source)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(notice,target)
    (doc/'copyright').write_text('Upstream: '+item['url']+'\nSource SHA256: '+item['sha256']+'\nUpstream licenses: '+', '.join(found)+'; embedded component notices in third-party-notices/.\nCopyright: respective upstream authors; see the upstream license files listed above.\nCopyright: 2026 LARSANA contributors (packaging).\nLARSANA packaging: GPL-3.0-or-later; text at /usr/share/common-licenses/GPL-3. Runtime retains upstream license.\n')
    (doc/'changelog.Debian.gz').write_bytes(gzip.compress(f"{name} ({item['version']}-1larsana1) noble; urgency=low\n\n  * Initial isolated runtime.\n\n -- LARSANA Contributors <maintainers@larsana.invalid>  Sat, 17 Oct 2026 12:00:00 +0700\n".encode(),mtime=0))
    out=ROOT/'dist'/f"{name}_{item['version']}-1larsana1_amd64.deb"
    from debian_package import build_deb
    build_deb(stage,out)
    destination=BUILD/'runtime-root'
    destination.mkdir(exist_ok=True)
    shutil.rmtree(destination/prefix,ignore_errors=True)
    subprocess.run(['dpkg-deb','-x',str(out),str(destination)],check=True)
    print('PACKAGED', out.name, flush=True)


def build(item, jobs):
    ident=item['id']
    source=BUILD/'src'/ident
    stage=BUILD/'stage'/ident
    log_path=BUILD/'logs'/f'{ident}.log'
    log_path.parent.mkdir(parents=True,exist_ok=True)
    src_tar=BUILD/'sources'/item['url'].split('/')[-1]
    if hashlib.sha256(src_tar.read_bytes()).hexdigest()!=item['sha256']:
        raise ValueError(f'Source checksum mismatch: {ident}')
    marker=source/'.source-sha256'
    if source.exists() and (not marker.exists() or marker.read_text().strip()!=item['sha256']):
        shutil.rmtree(source)
        shutil.rmtree(stage,ignore_errors=True)
    source.mkdir(parents=True,exist_ok=True)
    if not (source/'.extracted').exists():
        with tarfile.open(src_tar) as tar:
            # Upstream archives have one top-level directory. Reject unsafe members.
            for member in tar.getmembers():
                parts=Path(member.name).parts
                if len(parts)<2: continue
                member.name=str(Path(*parts[1:]))
                tar.extract(member,source,filter='data')
        (source/'.extracted').touch()
        marker.write_text(item['sha256']+'\n')
    stage.mkdir(parents=True,exist_ok=True)
    cwd='/work/.build/src/'+ident
    prefix='/usr/lib/larsana/runtimes/'+item['kind']+'/'+item['series']
    dest='/work/.build/stage/'+ident
    print('BUILD', ident, item['version'], flush=True)
    with log_path.open('a') as log:
        def run(args, env=None): sandbox(args,cwd=cwd,env=dict({'CFLAGS':'-O2 -g0','CXXFLAGS':'-O2 -g0'}, **(env or {})),log=log)
        if not (source/'.configured').exists():
            if item['kind']=='php':
                args=['./configure','--prefix='+prefix,'--enable-fpm','--disable-cgi','--disable-phpdbg','--without-pear',
                    '--with-openssl','--with-zlib','--with-curl','--with-zip','--with-mysqli=mysqlnd','--with-pdo-mysql=mysqlnd',
                    '--enable-mbstring','--enable-intl','--enable-bcmath','--enable-sockets','--enable-gd',
                    '--with-jpeg','--with-webp','--with-freetype','--with-libedit','--enable-pcntl','--enable-exif',
                    '--with-config-file-path='+prefix+'/etc','--with-config-file-scan-dir='+prefix+'/etc/conf.d']
                # OPcache is built in as of PHP 8.5; older branches build a shared extension.
                if item['series']!='8.5': args+=['--enable-opcache']
                run(args)
            elif item['kind']=='nginx':
                run(['./configure','--prefix='+prefix,'--with-http_ssl_module','--with-http_v2_module','--with-http_realip_module','--with-pcre-jit'])
            elif item['kind']=='apache':
                run(['./configure','--prefix='+prefix,'--with-mpm=event','--enable-so','--enable-mods-shared=most','--enable-ssl','--enable-proxy','--enable-proxy-fcgi','--enable-rewrite'])
            else:
                run(['cmake','-S','.','-B','build','-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_INSTALL_PREFIX='+prefix,'-DCMAKE_C_FLAGS_RELEASE=-O2 -DNDEBUG -g0','-DCMAKE_CXX_FLAGS_RELEASE=-O2 -DNDEBUG -g0',
                    '-DINSTALL_LAYOUT=STANDALONE','-DWITH_SSL=system','-DWITH_ZLIB=system',
                    '-DWITH_UNIT_TESTS=OFF','-DWITH_EMBEDDED_SERVER=OFF','-DWITH_WSREP=OFF',
                    '-DPLUGIN_ROCKSDB=NO','-DPLUGIN_TOKUDB=NO','-DPLUGIN_MROONGA=NO','-DPLUGIN_SPIDER=NO','-DPLUGIN_COLUMNSTORE=NO',
                    '-DPLUGIN_CONNECT=NO','-DPLUGIN_S3=NO','-DPLUGIN_DUCKDB=NO','-DWITH_INNODB_SNAPPY=OFF'])
            (source/'.configured').touch()
        if item['kind']=='mariadb':
            run(['cmake','--build','build','--parallel',str(min(jobs,4))])
            run(['cmake','--install','build','--strip'], env={'DESTDIR':dest})
        else:
            run(['make','-j'+str(jobs)])
            run(['make','install',('INSTALL_ROOT=' if item['kind']=='php' else 'DESTDIR=')+dest])
        # Strip only ELF files; preserve scripts and upstream configuration.
        sandbox(['sh','-c', 'find "$1" -type f -executable -exec strip --strip-unneeded {} + 2>/dev/null || true','strip',dest],log=log)
    package(item, stage)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('runtime',nargs='*')
    parser.add_argument('--jobs',type=int,default=6)
    parser.add_argument('--force',action='store_true',help='Reconfigure and rebuild selected runtimes')
    args=parser.parse_args()
    lock=json.loads((ROOT/'runtimes/sources.lock.json').read_text())
    items=lock['sources']
    # Deliver the first functioning stack before building the full version matrix.
    order=['nginx','apache-2.4','php-8.5','mariadb-10.11','php-8.1','php-8.2','php-8.3','php-8.4','mariadb-12.3','mariadb-13.0','mariadb-11.4','mariadb-11.8']
    for ident in (args.runtime or [i for i in order if i in {x['id'] for x in items}]):
        item=next(i for i in items if i['id']==ident)
        out=ROOT/'dist'/f"larsana-{ident}_{item['version']}-1larsana1_amd64.deb"
        (BUILD/'locks').mkdir(exist_ok=True)
        with (BUILD/'locks'/(ident+'.lock')).open('a+') as runtime_lock:
            try:
                fcntl.flock(runtime_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                raise SystemExit('Runtime is already being built: '+ident)
            if args.force:
                (BUILD/'src'/ident/'.configured').unlink(missing_ok=True)
            if not args.force and out.exists() and subprocess.run(['dpkg-deb','--info',str(out)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
                print('Already built',out.name,flush=True)
                continue
            jobs_file=BUILD/('jobs-'+item['kind'])
            if not jobs_file.exists(): jobs_file=BUILD/'jobs'
            effective_jobs=int(jobs_file.read_text()) if jobs_file.exists() else args.jobs
            build(item,max(1,min(effective_jobs,12)))
