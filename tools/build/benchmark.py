"""Three separate real Windows EXE boots per ZIP, with an actual Start action."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import tempfile
import zipfile
from tools.build.verify_package import run_native_tests, validate_native_report
from tools.compile_tests import WINDOWED_ACCEPTANCE_INIT

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous',type=Path,required=True)
    parser.add_argument('--current',type=Path,required=True)
    args=parser.parse_args()
    if os.name!='nt': raise SystemExit('Real Windows EXE required')
    evidence=Path('reports/native-startup'); evidence.mkdir(parents=True,exist_ok=True)
    suites=[]
    for name,package in [('previous',args.previous),('current',args.current)]:
        package_sha=hashlib.sha256(package.read_bytes()).hexdigest()
        results=[]
        for iteration in range(1,4):
            with tempfile.TemporaryDirectory(prefix='rain-startup-') as temp:
                target=Path(temp)
                with zipfile.ZipFile(package) as archive:
                    if archive.testzip(): raise ValueError('Package CRC failure')
                    if any('..' in Path(path).parts or ':' in path or path.startswith(('/', '\\')) for path in archive.namelist()):
                        raise ValueError('Unsafe ZIP path')
                    archive.extractall(target)
                exe=next(target.rglob('BeforeTheRainStops.exe'))
                plan='\n'.join(WINDOWED_ACCEPTANCE_INIT)+'''
testsuite global:
    setup:
        $ _test.timeout = 30.0
        $ preferences.text_cps = 0
        run Preference("display", "window")
        run Function(renpy.set_physical_size, (1280, 720))
        pause until screen "main_menu"
    teardown:
        exit
testcase real_boot_and_start:
    assert screen "main_menu"
    click id "menu_start"
    advance
    assert eval current_scene == "p00_entry"
'''
                (exe.parent/'game/testcases.rpy').write_text(plan,encoding='utf-8')
                entry=evidence/f'{name}-{iteration}'
                result=run_native_tests([str(exe),str(exe.parent),'test','global','--report-detailed','--savedir',str(target/'saves')],cwd=exe.parent,evidence=entry,timeout=45)
                if result.returncode: raise ValueError('Startup process failed')
                validate_native_report(result.stdout,plan)
                process=json.loads((entry/'process.json').read_text())
                results.append(process['elapsed_seconds'])
        if hashlib.sha256(package.read_bytes()).hexdigest()!=package_sha: raise ValueError('Original package changed')
        suites.append({'scope':name,'zip':package.name,'sha256':package_sha,'seconds':results,'median_seconds':statistics.median(results)})
    ratio=suites[1]['median_seconds']/suites[0]['median_seconds']
    report={'status':'passed','samples_per_package':3,'packages':suites,'median_ratio':round(ratio,3),
        'scope':'Separate Windows processes, main menu assertion, actual Start and first-scene assertion. Wall time includes test startup/exit; not pure first-frame latency.',
        'hardware':'Same local Windows host; process-level DPI awareness; 1280x720 window; dummy audio',
        'original_zips_unmodified':True,'budget_seconds':45,'timing_warning':ratio>1.25}
    (evidence/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
