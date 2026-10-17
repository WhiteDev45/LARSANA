"""Build a prepared private payload through the standard debhelper pipeline."""
from pathlib import Path
import shutil
import subprocess
from build_runtimes import ROOT, BUILD, sandbox


def build_deb(stage, output):
    control=(stage/'DEBIAN/control').read_text()
    fields={line.split(': ',1)[0]:line.split(': ',1)[1] for line in control.splitlines() if ': ' in line and not line.startswith(' ')}
    name,version=fields['Package'],fields['Version']
    workspace=BUILD/'debian-packages'/name
    if workspace.exists():shutil.rmtree(workspace)
    debian=workspace/'debian';debian.mkdir(parents=True)
    payload=workspace/'payload';payload.mkdir()
    for directory in stage.iterdir():
        if directory.name=='DEBIAN':continue
        if directory.is_dir():shutil.copytree(directory,payload/directory.name,symlinks=True)
        else:shutil.copy2(directory,payload/directory.name)
    binary='\n'.join(line for line in control.splitlines() if not line.startswith(('Version:','Maintainer:','Section:','Priority:')))
    # External ABI dependencies have already been calculated for runtimes. Qt is
    # private to the desktop and uses explicit platform dependencies + GUI tests.
    binary=binary.replace('Depends: ', 'Depends: ${misc:Depends}, ',1)
    (debian/'control').write_text(f'''Source: {name}
Section: {fields.get('Section','devel')}
Priority: optional
Maintainer: LARSANA Contributors <maintainers@larsana.invalid>
Build-Depends: debhelper-compat (= 13)
Rules-Requires-Root: no
Standards-Version: 4.7.0

{binary}
''')
    (debian/'changelog').write_text(f'''{name} ({version}) unstable; urgency=low

  * Build isolated LARSANA payload for this distribution.

 -- LARSANA Contributors <maintainers@larsana.invalid>  Sat, 17 Oct 2026 12:00:00 +0700
''')
    (debian/'rules').write_text(f'''#!/usr/bin/make -f
%:
\tdh $@ --buildsystem=none

override_dh_auto_install:
\tmkdir -p debian/{name}
\tcp -a payload/. debian/{name}/

# Sources are compiled and ABI dependencies verified by the runtime builder.
# Libraries are private, pre-stripped payloads; do not publish global shlibs.
override_dh_shlibdeps:
override_dh_makeshlibs:
override_dh_strip:
override_dh_dwz:
''')
    (debian/'rules').chmod(0o755)
    for script in ('preinst','postinst','prerm','postrm'):
        source=stage/'DEBIAN'/script
        if source.exists():
            text=source.read_text()
            if '#DEBHELPER#' not in text:text=text.replace('exit 0\n','#DEBHELPER#\nexit 0\n')
            (debian/script).write_text(text);(debian/script).chmod(0o755)
    log=BUILD/'logs'/(name+'-debhelper.log');log.parent.mkdir(exist_ok=True)
    with log.open('w') as stream:
        sandbox(['dpkg-buildpackage','-b','-us','-uc'],cwd=str(workspace).replace(str(ROOT),'/work',1),log=stream)
    built=workspace.parent/output.name
    if not built.exists():
        matches=list(workspace.parent.glob(f'{name}_{version}_*.deb'))
        if len(matches)!=1:raise RuntimeError('Cannot locate debhelper output for '+name)
        built=matches[0]
    shutil.copy2(built,output)
    for suffix in ['.changes','.buildinfo']:
        for metadata in workspace.parent.glob(f'{name}_{version}_*'+suffix):
            shutil.copy2(metadata,output.parent/metadata.name)
    print('DEBHELPER',output.name,flush=True)
