"""Build the pinned official Ren'Py WASM runtime with atomic offline delivery."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile
from PIL import Image
from tools.story_model import ROOT
from tools.build import sdk as sdk_tools

WEB_SHA256 = '954db897e65f51ea63cb2fb7b203d02be0447f4e22069514020bbe6c6691fdfc'
WEB_VERSION = '8.5.3'
TEMPLATES = Path(__file__).with_name('pwa')

def ensure_web(sdk: Path, runtime: Path) -> Path:
    archive = runtime / f'renpy-{WEB_VERSION}-web.zip'
    if not sdk_tools.archive_is_valid(archive, WEB_SHA256):
        sdk_tools._download_atomic(f'https://www.renpy.org/dl/{WEB_VERSION}/{archive.name}', archive, WEB_SHA256)
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or any('..' in Path(name).parts or not name.startswith('web/') for name in names):
            raise ValueError('Unsafe official web archive')
        with tempfile.TemporaryDirectory(prefix='web-extract-', dir=runtime) as temp:
            bundle.extractall(temp)
            candidate = Path(temp) / 'web'
            for name in ('renpy.wasm', 'renpy.js', 'renpy.data', 'index.html', 'renpy-pre.js'):
                if not (candidate / name).is_file(): raise ValueError(f'Incomplete web SDK: {name}')
            shutil.copytree(candidate, sdk / 'web', dirs_exist_ok=True)
    return sdk / 'web'

def add_pwa(destination: Path, version: str) -> dict:
    html_path = destination / 'index.html'
    html = html_path.read_text(encoding='utf-8')
    html = html.replace('<html lang="en-us">', '<html lang="zh-CN">')
    html = html.replace('content="#000"', 'content="#112b36"')
    html = html.replace('Import Saves', '导入存档').replace('Export Saves', '导出存档').replace('Download Log', '下载日志')
    # Replace only the official registration block. The engine scripts and APIs stay intact.
    registration = re.compile(r'      // Register the service worker\..*?(?=  </script>)', re.DOTALL)
    if len(registration.findall(html)) != 1: raise ValueError('Official HTML registration layout changed')
    html = registration.sub('', html)
    controls = '''<aside id="pwaControls" aria-label="离线与安装">
      <span id="offlineStatus" role="status">正在保存完整离线内容…</span>
      <button id="installPwa" hidden>安装到设备</button>
    </aside>
    <p id="orientationHint" role="status">请横屏阅读，画面与文字会更清晰</p>
    <style>#pwaControls{position:fixed;right:8px;top:8px;z-index:30;font:12px sans-serif;color:#d9eff4;background:#112b36dd;padding:6px 9px;border-radius:6px;max-width:70vw}#installPwa{margin-left:8px;border:1px solid #91d4e0;border-radius:4px;color:#fff;background:#234552;cursor:pointer}#pwaControls:focus-within{outline:2px solid #91d4e0}#orientationHint{display:none}@media(max-width:760px) and (orientation:portrait){#orientationHint{display:block;position:fixed;bottom:24px;left:16px;right:16px;margin:0;text-align:center;z-index:30;font:14px sans-serif;color:#d9eff4}}</style>
    <script src="pwa-client.js" defer></script>'''
    html_path.write_text(html.replace('</body>', controls + '\n</body>'), encoding='utf-8', newline='\n')
    shutil.copy2(TEMPLATES / 'client.js', destination / 'pwa-client.js')
    manifest_path = destination / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest.update({'id':'./', 'name':'雨停之前', 'short_name':'雨停之前', 'lang':'zh-CN',
        'description':'六章离线中文视觉小说；17句配音、两个结局与鉴赏室。',
        'start_url':'./index.html', 'scope':'./', 'display':'standalone',
        'background_color':'#112b36', 'theme_color':'#112b36', 'orientation':'landscape', 'version':version})
    manifest.pop('display_override', None)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # Symbols are developer debugging data and not needed for gameplay or offline caching.
    (destination / 'index.html.symbols').unlink(missing_ok=True)
    (destination / 'pwa_catalog.json').unlink(missing_ok=True)
    (destination / '.nojekyll').touch()
    # Retain the native "download for offline" API: the catalog is already cached
    # as part of this complete build, so Ren'Py's loadCache sees equal versions.
    native_catalog = {'version':version, 'files':[path.relative_to(destination).as_posix()
        for path in sorted(destination.rglob('*')) if path.is_file() and path.name != 'service-worker.js']}
    (destination / 'pwa_catalog.json').write_text(json.dumps(native_catalog)+'\n', encoding='utf-8')
    files = []
    for path in sorted(destination.rglob('*')):
        if not path.is_file() or path.name == 'service-worker.js': continue
        raw = path.read_bytes()
        if len(raw) >= 50_000_000: raise ValueError(f'Web file exceeds 50 MB cache budget: {path.name}')
        files.append({'path':path.relative_to(destination).as_posix(), 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()})
    revision = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:24]
    catalog = {'revision':revision, 'version':version, 'files':files}
    sw = (TEMPLATES / 'service-worker.js').read_text().replace('/* BUILD_CONFIG */', json.dumps(catalog, ensure_ascii=False))
    (destination / 'service-worker.js').write_text(sw, encoding='utf-8')
    return catalog

def stage_project(destination: Path) -> None:
    """Keep Ren'Py dump/compile and local persistent writes away from authors."""
    shutil.copytree(ROOT / 'game', destination / 'game', ignore=shutil.ignore_patterns('saves'))
    for name in ('old-game', 'licenses'):
        if (ROOT / name).is_dir(): shutil.copytree(ROOT / name, destination / name)
    for name in ('PLAYER_README.txt', 'CREDITS.md', 'LICENSE', 'VERSION', 'progressive_download.txt'):
        if (ROOT / name).is_file(): shutil.copy2(ROOT / name, destination / name)
    # Reuse the authored icon/background without modifying the source project.
    with Image.open(ROOT / 'game/gui/window_icon.png') as icon:
        icon.convert('RGBA').resize((512,512), Image.Resampling.LANCZOS).save(destination / 'web-icon.png')
    assets = json.loads((ROOT / 'game/data/asset_manifest.json').read_text())['assets']
    background = next(asset for asset in assets if asset['id'] == 'station')
    shutil.copy2(ROOT / 'game' / background['file'], destination / 'web-presplash.png')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, default=ROOT / '.runtime/renpy-8.5.3-sdk')
    parser.add_argument('--destination', type=Path, default=ROOT / 'dist/web')
    args = parser.parse_args()
    sdk, destination = args.sdk.resolve(), args.destination.resolve()
    if not destination.is_relative_to(ROOT / 'dist') or destination == ROOT / 'dist':
        raise SystemExit('Web output must be a child of this project dist directory')
    runtime = ROOT / '.runtime'; runtime.mkdir(exist_ok=True)
    if not sdk_tools.sdk_is_usable(sdk): raise SystemExit('Run python -m tools.build.sdk first')
    ensure_web(sdk, runtime)
    interpreter = sdk / 'lib' / ('py3-windows-x86_64/python.exe' if os.name == 'nt' else 'py3-linux-x86_64/python')
    with tempfile.TemporaryDirectory(prefix='rain-web-stage-') as temp:
        project = Path(temp) / 'project'
        stage_project(project)
        environment = {**os.environ, 'RENPY_PATH_TO_SAVES': str(Path(temp) / 'user-saves')}
        subprocess.run([str(interpreter), str(sdk/'renpy.py'), str(sdk/'launcher'), 'web_build', str(project), '--destination', str(destination)], check=True, env=environment)
    version = (ROOT/'VERSION').read_text().strip()
    catalog = add_pwa(destination, version)
    # Repack the postprocessed artifact; the official web_build ZIP predates PWA customization.
    destination.with_suffix('.zip').unlink(missing_ok=True)
    archive_path = ROOT / 'dist' / f'BeforeTheRainStops-{version}-web.zip'
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(destination.rglob('*')):
            if path.is_file(): archive.write(path, path.relative_to(destination).as_posix())
    report = {'status':'built', 'engine':'RenPy 8.5.3 official WASM', 'web_sdk_sha256':WEB_SHA256,
        'runtime_files':len(catalog['files']), 'offline_bytes':sum(file['bytes'] for file in catalog['files']),
        'revision':catalog['revision'], 'version':version, 'web_zip_sha256':sdk_tools._sha256_file(archive_path),
        'scope':'relative; supports /Rain/ and local test subpaths', 'browser_execution':'requires actual smoke test'}
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports/web-build.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
