"""Calculate runtime dependencies from built ELF binaries in the extracted dpkg database."""
from pathlib import Path
import re
import subprocess
from build_runtimes import ROOT, BUILD, sandbox


def dependencies(stage):
    workspace=BUILD/'dependency-check'/stage.name
    control=workspace/'debian/control'
    control.parent.mkdir(parents=True,exist_ok=True)
    control.write_text('Source: larsana-local\nSection: devel\nPriority: optional\nMaintainer: LARSANA Contributors <maintainers@larsana.invalid>\n\nPackage: larsana-local\nArchitecture: any\nDescription: Dependency scanner\n')
    files=[]
    for file in (stage/'usr/lib/larsana/runtimes').rglob('*'):
        if file.is_file() and not file.is_symlink():
            with file.open('rb') as stream:
                if stream.read(4)==b'\x7fELF':files.append(file)
    args=['dpkg-shlibdeps','--ignore-missing-info','-O','-l/usr/lib/x86_64-linux-gnu','-l/usr/lib']
    for file in files:args+=['-e'+str(file).replace(str(ROOT),'/work',1)]
    for directory in (stage/'usr/lib/larsana/runtimes').glob('*/*/lib*'):
        args+=['-l'+str(directory).replace(str(ROOT),'/work',1)]
        for private in directory.glob('private'):
            args+=['-l'+str(private).replace(str(ROOT),'/work',1)]
    log=workspace/'shlibdeps.log'
    with log.open('w') as stream:
        sandbox(args,cwd=str(workspace).replace(str(ROOT),'/work',1),log=stream)
    text=log.read_text()
    match=re.search(r'^shlibs:Depends=(.*)$',text,re.M)
    if not match:raise RuntimeError('No ELF dependency result: '+str(log))
    return match[1]

if __name__=='__main__':
    import sys
    print(dependencies(Path(sys.argv[1]).resolve()))
