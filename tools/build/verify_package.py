"""Extract and execute the standalone Windows EXE; wait for all native tests."""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
import zipfile
from PIL import Image
from tools.compile_tests import render_persistence_tests
from tools.story_model import load_story

DEFAULT_TEST_TIMEOUT = 2400
READER_TEST_TIMEOUT = 120


def positive_timeout(value):
    seconds = int(value)
    if seconds <= 0:
        raise argparse.ArgumentTypeError('Timeout must be a positive number of seconds')
    return seconds


def output_text(value):
    return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else (value or '')


def run_native_tests(command, *, cwd, evidence, timeout):
    """Keep process output and timing even when the native suite times out."""
    evidence.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    timed_out = False
    returncode = None
    stdout = stderr = ''
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, encoding='utf-8',
                                errors='replace', timeout=timeout)
        stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
        return result
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout, stderr = output_text(exc.stdout), output_text(exc.stderr)
        raise
    finally:
        (evidence / 'stdout.txt').write_text(stdout, encoding='utf-8')
        (evidence / 'stderr.txt').write_text(stderr, encoding='utf-8')
        (evidence / 'process.json').write_text(json.dumps({
            'timeout_seconds': timeout, 'elapsed_seconds': round(time.monotonic()-started, 3),
            'timed_out': timed_out, 'returncode': returncode,
            'scope': 'native process only; required screenshots are checked separately'
        }, indent=2)+'\n', encoding='utf-8')


def run_source_tests(command, *, cwd, evidence, timeout):
    """Bound the source process and retain its report on failure or timeout."""
    process_evidence = evidence / 'source-process'
    try:
        return run_native_tests(command, cwd=cwd, evidence=process_evidence, timeout=timeout)
    finally:
        stdout = (process_evidence / 'stdout.txt').read_text(encoding='utf-8')
        stderr = (process_evidence / 'stderr.txt').read_text(encoding='utf-8')
        (evidence / 'source-tests.txt').write_text(stdout + '\n' + stderr, encoding='utf-8')
        print(stdout, flush=True)
        print(stderr, flush=True)


def collect_runtime_evidence(exe, evidence, screenshot_directory='reports/screenshots'):
    for log in ['log.txt', 'errors.txt', 'traceback.txt']:
        if (exe.parent / log).is_file():
            shutil.copy2(exe.parent / log, evidence / log)
    screenshots = exe.parent / screenshot_directory
    if screenshots.exists():
        shutil.copytree(screenshots, evidence / 'screenshots', dirs_exist_ok=True)
    return screenshots


def validate_native_report(output, test_source):
    """A zero exit alone cannot establish that every authored test ran."""
    cases = re.findall(r'^testcase ([a-zA-Z0-9_]+):', test_source, re.MULTILINE)
    assertions = len(re.findall(r'^\s+assert ', test_source, re.MULTILINE))
    if not cases or not assertions:
        raise ValueError('Native test plan is empty')
    for label, expected, tail in [('Test cases', len(cases), 5), ('Assertions', assertions, 3)]:
        match = re.search(r'\[rpytest\]\s+' + label + r'\s*:\s*(\d+)\s*\|\s*(\d+) passed\s*\|' +
                          r'\s*(\d+) xfailed\s*\|\s*(\d+) failed\s*\|\s*(\d+) xpassed\s*\|' +
                          (r'\s*(\d+) skipped\s*\|\s*(\d+) not run' if tail == 5 else ''), output)
        if not match or [int(x) for x in match.groups()] != [expected, expected] + [0] * tail:
            raise ValueError(f'Native {label.lower()} summary is missing or incomplete; expected {expected} passed')
    passed = set(re.findall(r'^\[rpytest\]\s+PASSED\s+([a-zA-Z0-9_]+)\s+-', output, re.MULTILINE))
    if not set(cases).issubset(passed) or not re.search(r'\[rpytest\]\s+Status: PASSED\s*$', output, re.MULTILINE):
        raise ValueError('Native test names or final PASSED status are missing')
    return {'cases': len(cases), 'assertions': assertions, 'failed': 0, 'xfailed': 0,
            'xpassed': 0, 'skipped': 0, 'not_run': 0}


def required_screenshots(test_source):
    names = set(re.findall(r'^\s+screenshot "([^"]+)"', test_source, re.MULTILINE))
    # Independent acceptance landmarks also catch an accidentally omitted test.
    if 'testcase route_01:' in test_source:
        names.update(['first-choice', 'settings', 'chapter-prologue', 'chapter-today',
                      'cg-letter', 'branch-s04_open', 'branch-s04_reserved', 'revisit-choice',
                      'audio-true-voice', 'audio-normal-voice', 'bg-exit-covered', 'bg-exit-after-rain',
                      'bg-s05_shared_path', 'bg-s05_separate_path', 'bg-nearby-cafe'])
        names.update('expression-' + name for name in ('normal', 'smile', 'happy', 'sad', 'angry',
                                                      'surprised', 'embarrassed'))
        names.update('save-load-' + name for name in ('before-cg', 'letter-cg', 'chapter-four',
                     'departure', 'shared-path', 'cafe-before-rain-stop', 'cafe-after-rain-stop', 'normal-ending'))
        names.update(['rollback-letter-choice', 'rollback-rechoice-normal', 'restart-normal-ending',
                      'auto-voice-in-progress', 'skip-final-choice'])
    return sorted(names)


def validate_screenshots(directory, required, native_1080=False):
    for name in required:
        file = directory / (name + '.png')
        if not file.is_file():
            raise ValueError(f'Missing UI evidence: {name}')
        try:
            with Image.open(file) as image:
                image.load()
                size = image.size
        except (OSError, ValueError) as exc:
            raise ValueError(f'Undecodable UI evidence: {name}') from exc
        if native_1080:
            expected = (1280, 720) if name.startswith('scaled-') else (1920, 1080)
            if size != expected:
                raise ValueError(f'Wrong physical UI size: {name}: {size}, expected {expected}')


def validate_suite_evidence(output, test_source, screenshots, evidence):
    summary = validate_native_report(output, test_source)
    required = required_screenshots(test_source)
    native_1080 = 'testcase native_1080_and_scaled_window:' in test_source or 'testcase cross_process_load:' in test_source
    validate_screenshots(screenshots, required, native_1080=native_1080)
    summary['screenshots_checked'] = len(required)
    summary['native_1080'] = native_1080
    (evidence / 'acceptance.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--zip', type=Path)
    operation.add_argument('--report', type=Path, help='Verify source-suite output and screenshots')
    operation.add_argument('--source-sdk', type=Path, help='Execute the source suite with a bounded SDK process')
    parser.add_argument('--timeout', type=positive_timeout, default=DEFAULT_TEST_TIMEOUT,
                        help='Seconds allowed for the complete native suite (default: 2400)')
    args = parser.parse_args()
    test_source = Path('game/testcases.rpy').read_text(encoding='utf-8')
    if args.source_sdk:
        sdk = args.source_sdk.resolve()
        interpreter = sdk / 'lib' / ('py3-windows-x86_64/python.exe' if os.name == 'nt' else 'py3-linux-x86_64/python')
        if not interpreter.is_file() or not (sdk / 'renpy.py').is_file():
            raise SystemExit('Source SDK is incomplete')
        evidence = Path('reports')
        evidence = evidence.resolve()
        # A --savedir alone does not isolate Ren'Py: it also merges game/saves.
        # Keep author/player saves and simultaneous compile/build processes out
        # of the acceptance game, just as the existing voice smoke does.
        with tempfile.TemporaryDirectory(prefix='galgame-source-isolated-') as temp:
            project = Path(temp) / 'project'
            shutil.copytree(Path('game'), project / 'game', ignore=shutil.ignore_patterns('saves'))
            if Path('old-game').is_dir(): shutil.copytree('old-game', project / 'old-game')
            try:
                result = run_source_tests([str(interpreter), '-u', str(sdk / 'renpy.py'), str(project), 'test', 'global',
                    '--report-detailed', '--overwrite-screenshots', '--savedir', str(Path(temp) / 'saves')],
                    cwd=project, evidence=evidence, timeout=args.timeout)
            finally:
                collect_runtime_evidence(project / 'BeforeTheRainStops.exe', evidence)
        if result.returncode:
            raise SystemExit(result.returncode)
        try:
            summary = validate_suite_evidence(result.stdout, test_source, Path('reports/screenshots'), evidence)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(f'Source native evidence accepted: {summary}')
        return
    if args.report:
        try:
            summary = validate_suite_evidence(args.report.read_text(encoding='utf-8-sig'), test_source,
                                              Path('reports/screenshots'), Path('reports'))
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(f'Source native evidence accepted: {summary}')
        return
    with tempfile.TemporaryDirectory(prefix="galgame-package-") as temp:
        destination = Path(temp)
        with zipfile.ZipFile(args.zip) as package:
            instructions = [name for name in package.namelist() if name.endswith('/PLAYER_README.txt')]
            if len(instructions) != 1 or any(name.endswith('/README.md') for name in package.namelist()):
                raise SystemExit('Package must contain dedicated player instructions without the developer README')
            version = Path('VERSION').read_text(encoding='utf-8').strip()
            if f'版本：{version}' not in package.read(instructions[0]).decode('utf-8'):
                raise SystemExit('Player instructions do not match the package version')
            package.extractall(destination)
        exe = next(destination.rglob("BeforeTheRainStops.exe"), None)
        if not exe:
            raise SystemExit("Missing standalone Windows EXE")
        game = exe.parent / "game"
        for forbidden in ["data", "testcases.rpy", "testcases.rpyc", "saves"]:
            if (game / forbidden).exists():
                raise SystemExit(f"Authoring data leaked into package: {forbidden}")
        # Inject tests only into the temporary extraction, never the release ZIP.
        shutil.copy2("game/testcases.rpy", game / "testcases.rpy")
        evidence = Path("reports/package")
        evidence.mkdir(parents=True, exist_ok=True)
        try:
            result = run_native_tests([str(exe), str(exe.parent), "test", "global", "--report-detailed", "--overwrite-screenshots", "--savedir", str(destination / "saves")],
                                      cwd=exe.parent, evidence=evidence, timeout=args.timeout)
        finally:
            screenshots = collect_runtime_evidence(exe, evidence)
        print(result.stdout)
        print(result.stderr)
        if result.returncode:
            raise SystemExit(result.returncode)
        try:
            summary = validate_suite_evidence(result.stdout, test_source, screenshots, evidence)
            # Reuse the same extracted EXE and save directory in a new process.
            reader = render_persistence_tests(load_story())
            (game / 'testcases.rpy').write_text(reader, encoding='utf-8')
            (game / 'testcases.rpyc').unlink(missing_ok=True)
            restart_evidence = evidence / 'persistence'
            try:
                result = run_native_tests([str(exe), str(exe.parent), 'test', 'global', '--report-detailed',
                    '--overwrite-screenshots', '--savedir', str(destination / 'saves')],
                    cwd=exe.parent, evidence=restart_evidence, timeout=min(args.timeout, READER_TEST_TIMEOUT))
            finally:
                screenshots = collect_runtime_evidence(exe, restart_evidence, 'reports/persistence-screenshots')
            print(result.stdout)
            print(result.stderr)
            if result.returncode:
                raise SystemExit(result.returncode)
            restarted = validate_suite_evidence(result.stdout, reader, screenshots, restart_evidence)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(f'Standalone Windows EXE accepted: {summary}; fresh-process load: {restarted}')


if __name__ == "__main__":
    main()
