"""Generate Ren'Py interaction tests from the actual graph's route witnesses."""
import argparse
import json
from tools.story_model import ROOT, load_story, enumerate_routes, scene_lines, apply_effects
from tools.compile_story import quote
from tools.extras_tests import render_extras_tests, extras_persistence_assertions

WINDOWED_ACCEPTANCE_INIT = [
    '# Optional local 1920x1080 window: no system display or DPI changes.',
    'init -999 python:',
    '    if renpy.windows and __import__("os").environ.get("RENPY_ACCEPTANCE_WINDOWED") == "1":',
    '        import ctypes',
    '        ctypes.windll.user32.SetProcessDPIAware()',
    '    def rain_acceptance_window():',
    '        if preferences.fullscreen or preferences.maximized or renpy.get_physical_size() != (1920, 1080):',
    '            preferences.maximized = False',
    '            renpy.set_physical_size((1920, 1080))',
    '',
]

def checkpoint_assertions(story, route, line_id, selected, background, expression, music, ambient):
    """Expected authored state at a line, independent of the saved runtime state."""
    node = next(n for n in story['nodes'] if any(x['id'] == line_id for x in scene_lines(n)))
    choices = {c['id']: c for n in story['nodes'] for c in n.get('choices', [])}
    state = story['initial_state']
    for identity in route['choices'][:selected]:
        state = apply_effects(choices[identity]['effects'], state)
    path = route['path'][:route['path'].index(node['id']) + 1]
    assets = {a['id']: a['file'] for a in json.loads((ROOT / 'game/data/asset_manifest.json').read_text(encoding='utf-8'))['assets']}
    return [
        f"    assert eval current_scene == {node['id']!r} and current_chapter == {node['chapter']!r}",
        f"    assert eval visited_scenes == {path!r}",
        '    assert eval ' + ' and '.join(f'{key} == {value!r}' for key, value in state.items()),
        '    assert eval last_ending == ""',
        f"    assert eval renpy.showing({assets[background]!r})",
        (f"    assert eval renpy.get_attributes('heroine') == ({expression!r},)" if expression else
         '    assert eval not renpy.showing("heroine")'),
        f"    assert eval renpy.music.get_playing(channel='music') == {music!r}",
        f"    assert eval renpy.music.get_playing(channel='ambient') == {ambient!r}",
    ]


def render_persistence_tests(story):
    """A second EXE process reads the first process's real late-story slot."""
    route = enumerate_routes(story)['routes'][0]
    line = next(x for n in story['nodes'] for x in scene_lines(n) if x['id'] == 's07_true_l006')
    lines = [
        '# Generated cross-process reader; injected only into a temporary extraction.',
        *WINDOWED_ACCEPTANCE_INIT,
        'testsuite global:',
        '    setup:',
        '        $ _test.transition_timeout = 0.05',
        '        $ _test.timeout = 15.0',
        '        $ _test.screenshot_directory = "reports/persistence-screenshots"',
        '        $ preferences.text_cps = 0',
        '        pause until screen "main_menu"',
        '        run (Function(rain_acceptance_window) if __import__("os").environ.get("RENPY_ACCEPTANCE_WINDOWED") == "1" else Preference("display", "fullscreen"))',
        '        pause until eval renpy.get_physical_size() == (1920, 1080)',
        '    teardown:',
        '        exit',
        '',
        'testcase cross_process_load:',
        *extras_persistence_assertions(),
        '    assert eval renpy.can_load("1-2")',
        '    click id "load_open"',
        '    pause until screen "load"',
        '    click id "slot_2"',
        '    if screen "confirm":',
        '        click id "confirm_yes"',
        f'    pause until {quote(line["text"])}',
        '    pause until eval renpy.music.get_playing(channel="ambient") is None',
    ]
    lines += checkpoint_assertions(story, route, line['id'], 4, 'nearby_cafe', 'smile',
                                   'audio/bgm/next_message_theme.ogg', None)
    lines += ['    pause 0.2', '    screenshot "cross-process-late-load"',
              '    advance until screen "ending_card"', '    assert eval last_ending == "true"', '']
    return '\n'.join(lines)


def render_tests(story):
    report = enumerate_routes(story)
    if report["errors"]:
        raise ValueError(report["errors"])
    choices = {c["id"]: c for n in story["nodes"] for c in n.get("choices", [])}
    first_choice_scene = next(n["id"] for n in story["nodes"] if "choices" in n)
    first_choice_node = next(n for n in story["nodes"] if n["id"] == first_choice_scene)
    saved_expression = next((line["expression"] for line in reversed(first_choice_node["lines"]) if line.get("expression")), "normal")
    first_path = report["routes"][0]["path"]
    saved_path = first_path[:first_path.index(first_choice_scene) + 1]
    chapters = {c["id"]: c for c in story["chapters"]}
    assets = {asset['id']: asset['file'] for asset in json.loads((ROOT / 'game/data/asset_manifest.json').read_text(encoding='utf-8'))['assets']}
    lines = [
        "# Generated by python -m tools.compile_tests. Do not hand-edit.",
        *WINDOWED_ACCEPTANCE_INIT,
        "testsuite global:",
        "    setup:",
        "        $ _test.transition_timeout = 0.05",
        # Full 1080p software-rendered CI advances longer story spans more slowly.
        # Keep every route/assertion, and allow the measured span to finish.
        "        $ _test.timeout = 45.0",
        '        $ _test.screenshot_directory = "reports/screenshots"',
        "        $ preferences.text_cps = 0",
        '        pause until screen "main_menu"',
        '        run (Function(rain_acceptance_window) if __import__("os").environ.get("RENPY_ACCEPTANCE_WINDOWED") == "1" else Preference("display", "fullscreen"))',
        '        pause until eval renpy.get_physical_size() == (1920, 1080)',
        '        assert eval (config.screen_width, config.screen_height) == (1920, 1080)',
        '        screenshot "main-menu"',
        "    before testcase:",
        '        run (Function(rain_acceptance_window) if __import__("os").environ.get("RENPY_ACCEPTANCE_WINDOWED") == "1" else Preference("display", "fullscreen"))',
        '        pause until eval renpy.get_physical_size() == (1920, 1080)',
        "        $ preferences.afm_enable = False",
        "        $ config.skipping = None",
        '        if not screen "main_menu":',
        "            run MainMenu(confirm=False)",
        '        if eval __import__("os").environ.get("RENPY_ACCEPTANCE_WINDOWED") == "1":',
        '            pause 0.1',
        '        click id "menu_start"',
        "    teardown:",
        "        exit",
        "",
    ]
    for index, route in enumerate(report["routes"], 1):
        lines += [f"testcase route_{index:02}:"]
        if index == 1:
            title = quote(story["chapters"][0]["title"])
            lines += [f"    pause until {title}", f"    assert {title}",
                      '    pause 0.2', '    screenshot "chapter-prologue"']
        for choice_index, choice_id in enumerate(route["choices"]):
            if index == 1 and choice_index == 1:
                cg_scene = next((n["id"] for n in story["nodes"] if n.get("background") == "unsent_letter"), None)
                if cg_scene:
                    cg_line = next(n["lines"][0]["text"] for n in story["nodes"] if n["id"] == cg_scene)
                    lines += [f"    advance until {quote(cg_line)}", '    pause 0.2',
                              '    assert eval not renpy.showing("heroine")', '    screenshot "cg-letter"']
            if choice_index == 2:
                branch = next(scene for scene in route["path"] if scene in ("s04_open", "s04_reserved"))
                if index in (1, 5):
                    branch_line = next(n["lines"][0]["text"] for n in story["nodes"] if n["id"] == branch)
                    lines += [f"    advance until {quote(branch_line)}",
                              '    pause 0.2', f'    screenshot "branch-{branch}"']
            if index == 1 and choice_id.startswith("q04_"):
                title = quote(chapters["ch04"]["title"])
                lines += [f"    advance until {title}", f"    assert {title}",
                          '    pause 0.2', '    screenshot "chapter-today"']
                if 'station_exit_covered' in assets:
                    text = quote(next(n['lines'][0]['text'] for n in story['nodes'] if n['id'] == 's04_memory'))
                    lines += [f'    advance until {text}', '    pause 0.2',
                              f"    assert eval renpy.showing({assets['station_exit_covered']!r})",
                              '    screenshot "bg-exit-covered"']
                lines += ['    advance until screen "choice"', '    screenshot "revisit-choice"']
            lines += ['    advance until screen "choice"', f"    click {quote(choices[choice_id]['text'])}"]
            if index in (1, 2) and choice_id.startswith('q03_') and 'station_exit_after_rain' in assets:
                path_scene = 's05_shared_path' if choice_id == 'q03_walk' else 's05_separate_path'
                text = quote(next(n['lines'][0]['text'] for n in story['nodes'] if n['id'] == path_scene))
                lines += [f'    advance until {text}', '    pause 0.2',
                          f"    assert eval renpy.showing({assets['station_exit_after_rain']!r})",
                          '    assert eval renpy.showing("heroine normal")',
                          f'    screenshot "bg-{path_scene}"']
        lines += ['    advance until screen "ending_card"', f"    assert eval (last_ending == {route['ending']!r})"]
        for key, value in route["state"].items():
            lines.append(f"    assert eval ({key} == {value!r})")
        lines += [f"    assert eval (visited_scenes == {route['path']!r})",
                  f"    assert eval (current_chapter == {story['nodes'][-1]['chapter']!r})"]
        lines += [f'    screenshot "route-{index:02}-{route["ending"]}"', '    click id "ending_return"', '    pause until screen "main_menu"', ""]
    lines += [
        "testcase save_load_and_restart:",
        '    advance until screen "choice"',
        '    screenshot "first-choice"',
        f'    assert eval renpy.get_attributes("heroine") == ({saved_expression!r},)',
        '    $ renpy.unlink_save("1-1")',
        '    click id "save_open"',
        '    pause until screen "save"',
        '    click id "slot_1"',
        '    assert eval renpy.can_load("1-1")',
        '    click id "game_return"',
        '    pause until screen "choice"',
        f"    click {quote(choices[report['routes'][0]['choices'][0]]['text'])}",
        '    advance',
        '    $ trust = -99',
        '    $ renpy.show("heroine angry", at_list=[heroine_position])',
        '    assert eval renpy.get_attributes("heroine") == ("angry",)',
        '    click id "load_open"',
        '    pause until screen "load"',
        '    click id "slot_1"',
        '    if screen "confirm":',
        '        click id "confirm_yes"',
        '    pause until screen "choice"',
        f"    assert eval (current_scene == {first_choice_scene!r})",
        f"    assert eval (current_chapter == {first_choice_node['chapter']!r})",
        f"    assert eval (visited_scenes == {saved_path!r})",
        '    assert eval (affection == 0 and trust == 0 and not truth_known)',
        f'    assert eval renpy.get_attributes("heroine") == ({saved_expression!r},)',
        '    assert eval renpy.music.get_playing(channel="music") == "audio/bgm/rain_theme.ogg"',
        '    assert eval renpy.music.get_playing(channel="ambient") == "audio/sfx/rain_ambience.ogg"',
        '    run MainMenu(confirm=False)',
        '    click id "menu_start"',
        '    advance until screen "choice"',
        '    assert eval (affection == 0 and trust == 0 and not truth_known)',
        f"    assert eval (visited_scenes == {saved_path!r} and current_chapter == {first_choice_node['chapter']!r})",
        '',
        'testcase history_preferences_and_audio:',
        '    advance until eval renpy.music.get_playing(channel="voice") is not None',
        '    pause 0.2',
        '    screenshot "first-dialogue"',
        '    click id "history_open"',
        '    assert screen "history"',
        '    pause 0.3',
        '    pause until eval not any(renpy.get_ongoing_transition(layer) for layer in (None, "master", "screens"))',
        '    screenshot "history"',
        '    click id "game_return"',
        '    click id "preferences_open"',
        '    assert screen "preferences"',
        '    pause 0.3',
        '    pause until eval not any(renpy.get_ongoing_transition(layer) for layer in (None, "master", "screens"))',
        '    screenshot "settings"',
        '    click id "mute_all"',
        '    assert eval preferences.get_mute("music")',
        '    assert eval preferences.get_mute("sfx")',
        '    assert eval preferences.get_mute("voice")',
        '    click id "mute_all"',
        '    assert eval not preferences.get_mute("music")',
        '    click id "game_return"',
        '    assert eval renpy.music.get_playing(channel="music") is not None',
        '    assert eval renpy.music.get_playing(channel="ambient") is not None',
        '',
        'testcase voice_and_display:',
        '    click id "preferences_open"',
        '    click id "display_fullscreen"',
        '    assert eval preferences.fullscreen',
        '    click id "display_window"',
        '    assert eval not preferences.fullscreen',
        '    click id "voice_test"',
        '    assert eval renpy.music.get_playing(channel="voice") == config.sample_voice',
        '    click id "game_return"',
        '',
        'testcase auto_and_skip:',
        '    $ preferences.afm_time = 0.1',
        '    $ test_history_length = len(_history_list)',
        '    click id "auto_run"',
        '    assert eval preferences.afm_enable',
        '    pause until eval len(_history_list) > test_history_length',
        '    assert eval len(_history_list) > test_history_length',
        '    click id "auto_run"',
        '    assert eval not preferences.afm_enable',
        '    $ preferences.skip_unseen = False',
        '    click id "preferences_open"',
        '    click id "skip_unseen"',
        '    assert eval preferences.skip_unseen',
        '    click id "game_return"',
        '    click id "skip_run"',
        '    pause until screen "choice"',
        f"    assert eval current_scene == {first_choice_scene!r}",
        '    assert eval (affection == 0 and trust == 0 and not truth_known)',
        '    $ config.skipping = None',
        '    $ preferences.afm_time = 15.0',
        '    $ preferences.skip_unseen = False',
        '',
    ]
    lines += ['testcase character_expressions_in_story:']
    # Follow the actual dialogue: first meeting, old photo, then the conversation.
    for expression in ("smile", "normal", "embarrassed"):
        lines += [
            f'    advance until eval renpy.get_attributes("heroine") == ({expression!r},)',
            '    pause 0.2',
            f'    assert eval renpy.showing("heroine {expression}")',
            f'    screenshot "expression-{expression}"',
        ]
    lines += [
        '    advance until screen "choice"',
        f"    click {quote(choices[report['routes'][0]['choices'][0]]['text'])}",
        '    advance until eval current_scene == "s03_letter"',
        '    advance',
        '    assert eval not renpy.showing("heroine")',
        '    advance until screen "choice"',
        f"    click {quote(choices[report['routes'][0]['choices'][1]]['text'])}",
    ]
    for expression in ("sad", "angry", "surprised", "happy"):
        lines += [
            f'    advance until eval renpy.get_attributes("heroine") == ({expression!r},)',
            '    pause 0.2',
            f'    assert eval renpy.showing("heroine {expression}")',
            f'    screenshot "expression-{expression}"',
        ]
    lines.append("")
    dialogue = {line['id']: line for node in story['nodes'] for line in scene_lines(node)}
    recordings = {voice['voice_id']: voice['file'] for voice in json.loads((ROOT / 'game/data/voice_manifest.json').read_text(encoding='utf-8'))['voices']}

    def at_line(identity):
        return f'    advance until {quote(dialogue[identity]["text"])}'

    def choose(identity):
        return ['    advance until screen "choice"', f'    click {quote(choices[identity]["text"])}']

    def playing(channel, file):
        return f'    assert eval renpy.music.get_playing(channel={channel!r}) == {file!r}'

    lines += ['testcase key_voice_and_sound_cues:'] + choose('q01_care')
    lines += [at_line('s03_letter_l002'), '    pause 0.1', playing('sound', 'audio/sfx/paper_rustle.ogg')]
    lines += choose('q02_honest')
    lines += [at_line('q02_honest_l002'), '    pause 0.1',
              playing('voice', recordings[dialogue['q02_honest_l002']['voice']]),
              at_line('s04_waiting_l019'), '    pause 0.1', playing('sound', 'audio/sfx/message_ping.ogg'), '']

    lines += ['testcase audio_true_ending:'] + choose('q01_care')
    lines += [at_line('s03_letter_l001'),
              '    pause until eval renpy.music.get_playing(channel="music") == "audio/bgm/unspoken_theme.ogg"',
              playing('music', 'audio/bgm/unspoken_theme.ogg')]
    lines += choose('q02_honest')
    lines += [at_line('s04_memory_l001'),
              '    pause until eval renpy.music.get_playing(channel="music") == "audio/bgm/rain_theme.ogg"',
              playing('music', 'audio/bgm/rain_theme.ogg')]
    lines += choose('q04_revisit')
    lines += [at_line('s05_departure_l001'),
              '    pause until eval renpy.music.get_playing(channel="music") == "audio/bgm/next_message_theme.ogg"',
              '    pause until eval renpy.music.get_playing(channel="ambient") == "audio/sfx/rain_light_ambience.ogg"',
              playing('music', 'audio/bgm/next_message_theme.ogg'),
              playing('ambient', 'audio/sfx/rain_light_ambience.ogg')]
    lines += choose('q03_walk')
    lines += [at_line('s07_true_l006'), '    pause until eval renpy.music.get_playing(channel="ambient") is None',
              '    assert eval renpy.music.get_playing(channel="ambient") is None']
    if 'nearby_cafe' in assets:
        lines += [f"    assert eval renpy.showing({assets['nearby_cafe']!r})",
                  '    assert eval renpy.showing("heroine smile")',
                  '    pause 0.2', '    screenshot "bg-nearby-cafe"']
    lines += [at_line('s07_true_l010'), '    pause 0.1',
              playing('voice', recordings[dialogue['s07_true_l010']['voice']]),
              '    screenshot "audio-true-voice"',
              '    advance until screen "ending_card"',
              '    pause until eval renpy.music.get_playing(channel="music") is None',
              '    assert eval renpy.music.get_playing(channel="music") is None',
              '    assert eval renpy.music.get_playing(channel="ambient") is None', '']

    lines += ['testcase audio_normal_ending:'] + choose('q01_care') + choose('q02_honest') + choose('q04_revisit') + choose('q03_leave')
    if 'station_exit_after_rain' in assets:
        lines += [at_line('s08_normal_l001'),
                  f"    assert eval renpy.showing({assets['station_exit_after_rain']!r})",
                  '    assert eval not renpy.showing("heroine")',
                  '    pause 0.2', '    screenshot "bg-exit-after-rain"']
    lines += [at_line('s08_normal_l004'), '    pause 0.1', playing('sound', 'audio/sfx/message_ping.ogg'),
              at_line('s08_normal_l005'), '    pause 0.1',
              playing('voice', recordings[dialogue['s08_normal_l005']['voice']]),
              '    screenshot "audio-normal-voice"',
              at_line('s08_normal_l010'), '    pause until eval renpy.music.get_playing(channel="ambient") is None',
              '    assert eval renpy.music.get_playing(channel="ambient") is None',
              '    advance until screen "ending_card"',
              '    pause until eval renpy.music.get_playing(channel="music") is None',
              '    assert eval renpy.music.get_playing(channel="music") is None', '']

    def save_restore(line_id, name, route, selected, background, expression, music, ambient, slot=1):
        checks = checkpoint_assertions(story, route, line_id, selected, background, expression, music, ambient)
        return [at_line(line_id), f'    pause until eval renpy.music.get_playing(channel="music") == {music!r}',
                f'    pause until eval renpy.music.get_playing(channel="ambient") == {ambient!r}'] + checks + [
            f'    $ renpy.unlink_save("1-{slot}")', '    click id "save_open"',
            '    pause until screen "save"', f'    click id "slot_{slot}"',
            f'    assert eval renpy.can_load("1-{slot}")', '    click id "game_return"',
            '    advance', '    $ affection = -99', '    $ trust = -99', '    $ truth_known = False',
            '    $ renpy.scene()', '    $ renpy.show("black")',
            '    $ renpy.show("heroine angry", at_list=[heroine_position])',
            '    $ renpy.music.stop(channel="music")', '    $ renpy.music.stop(channel="ambient")',
            '    assert eval renpy.showing("black")',
            '    assert eval affection == -99 and trust == -99', '    click id "load_open"',
            '    pause until screen "load"', f'    click id "slot_{slot}"',
            '    if screen "confirm":', '        click id "confirm_yes"',
            f'    pause until {quote(dialogue[line_id]["text"])}',
            f'    pause until eval renpy.music.get_playing(channel="music") == {music!r}',
            f'    pause until eval renpy.music.get_playing(channel="ambient") == {ambient!r}',
        ] + checks + ['    pause 0.2', f'    screenshot "save-load-{name}"']

    true_route, normal_route = report['routes'][:2]
    lines += ['testcase late_save_load_true:'] + choose('q01_care')
    lines += save_restore('s02_boxes_l026', 'before-cg', true_route, 1, 'station', 'normal',
                          'audio/bgm/rain_theme.ogg', 'audio/sfx/rain_ambience.ogg')
    lines += save_restore('s03_letter_l001', 'letter-cg', true_route, 1, 'unsent_letter', None,
                          'audio/bgm/unspoken_theme.ogg', 'audio/sfx/rain_ambience.ogg')
    lines += choose('q02_honest')
    lines += save_restore('s04_memory_l001', 'chapter-four', true_route, 2, 'station_exit_covered', 'normal',
                          'audio/bgm/rain_theme.ogg', 'audio/sfx/rain_ambience.ogg')
    lines += choose('q04_revisit')
    lines += save_restore('s05_departure_l001', 'departure', true_route, 3, 'station_exit_covered', 'normal',
                          'audio/bgm/next_message_theme.ogg', 'audio/sfx/rain_light_ambience.ogg')
    lines += choose('q03_walk')
    lines += save_restore('s05_shared_path_l001', 'shared-path', true_route, 4, 'station_exit_after_rain', 'normal',
                          'audio/bgm/next_message_theme.ogg', 'audio/sfx/rain_light_ambience.ogg')
    lines += save_restore('s07_true_l001', 'cafe-before-rain-stop', true_route, 4, 'nearby_cafe', 'smile',
                          'audio/bgm/next_message_theme.ogg', 'audio/sfx/rain_light_ambience.ogg')
    # Keep slot 2 for a fresh EXE process; slot 1 remains free for other cases.
    lines += save_restore('s07_true_l006', 'cafe-after-rain-stop', true_route, 4, 'nearby_cafe', 'smile',
                          'audio/bgm/next_message_theme.ogg', None, slot=2)
    lines += ['    advance until screen "ending_card"', '    assert eval last_ending == "true"', '']

    lines += ['testcase late_save_load_normal:']
    for identity in normal_route['choices']:
        lines += choose(identity)
    lines += save_restore('s08_normal_l001', 'normal-ending', normal_route, 4, 'station_exit_after_rain', None,
                          'audio/bgm/next_message_theme.ogg', 'audio/sfx/rain_light_ambience.ogg')
    lines += ['    advance until screen "ending_card"', '    assert eval last_ending == "normal"', '']

    rollback_route = next(r for r in report['routes'] if r['choices'] ==
                          ['q01_care', 'q02_defer', 'q04_concrete', 'q03_walk'])
    lines += ['testcase rollback_rechoice:'] + choose('q01_care') + choose('q02_honest')
    lines += [f'    pause until {quote(dialogue["q02_honest_l001"]["text"])}',
              '    assert eval truth_known and affection == 1 and trust == 2',
              '    click id "rollback_run"', '    pause until screen "choice"',
              '    assert eval not truth_known and affection == 1 and trust == 1',
              '    assert eval current_scene == "s03_letter" and "s03_honest" not in visited_scenes',
              '    assert eval not renpy.showing("heroine")', '    screenshot "rollback-letter-choice"']
    for identity in rollback_route['choices'][1:]:
        lines += choose(identity)
    lines += ['    advance until screen "ending_card"', '    assert eval last_ending == "normal"',
              f'    assert eval visited_scenes == {rollback_route["path"]!r}',
              '    assert eval not truth_known and affection == 2 and trust == 1',
              '    screenshot "rollback-rechoice-normal"', '']

    lines += ['testcase restart_true_then_normal:']
    for identity in true_route['choices']:
        lines += choose(identity)
    lines += ['    advance until screen "ending_card"', '    assert eval last_ending == "true"',
              '    click id "ending_return"', '    pause until screen "main_menu"',
              '    click id "menu_start"', '    advance until screen "choice"',
              '    assert eval affection == 0 and trust == 0 and not truth_known and last_ending == ""',
              f'    assert eval visited_scenes == {saved_path!r}',
              playing('music', 'audio/bgm/rain_theme.ogg'),
              playing('ambient', 'audio/sfx/rain_ambience.ogg')]
    for identity in normal_route['choices']:
        lines += choose(identity)
    lines += ['    advance until screen "ending_card"', '    assert eval last_ending == "normal"',
              f'    assert eval visited_scenes == {normal_route["path"]!r}',
              '    assert eval affection == 2 and trust == 3 and truth_known',
              '    assert eval not renpy.showing("heroine")', '    screenshot "restart-normal-ending"', '']

    voice_file = recordings[dialogue['s01_arrival_l005']['voice']]
    asset_manifest = json.loads((ROOT / 'game/data/asset_manifest.json').read_text(encoding='utf-8'))['assets']
    voice_duration = next(a['audio']['duration_seconds'] for a in asset_manifest if a['file'] == voice_file)
    replay_start = len(lines)
    replay_state = '(current_scene, current_chapter, affection, trust, truth_known, tuple(visited_scenes), len(_history_list), _last_say_what)'
    current_replay_click = [
        '    move pos (0.5, 0.4)',
        '    move "重听语音" pos (0.5, 0.5)',
        '    pause 0.1',
        '    $ print("Current replay target:", renpy.get_physical_size(), _last_voice_play, VoiceReplay().get_sensitive(), _last_say_what)',
        '    click "重听语音" pos (0.5, 0.5)',
    ]
    history_replay_click = [
        '    move pos (0.5, 0.4)',
        '    move "重播语音" pos (0.5, 0.5)',
        '    pause 0.1',
        '    $ print("History replay target:", renpy.get_physical_size(), preferences.get_mute("voice"), renpy.music.get_playing(channel="voice"))',
        '    click "重播语音" pos (0.5, 0.5)',
    ]
    lines += ['testcase current_voice_replay_and_restore:', at_line('s01_arrival_l005'),
              '    assert id "voice_replay"',
              '    pause until eval renpy.music.get_playing(channel="voice") is None',
              f'    $ _test.voice_replay_state = {replay_state}',
              *current_replay_click, playing('voice', voice_file),
              f'    assert eval {replay_state} == _test.voice_replay_state',
              '    screenshot "native-voice-replay"',
              '    run Preference("display", "window")',
              '    $ renpy.set_physical_size((1280, 720))',
              '    pause until eval renpy.get_physical_size() == (1280, 720)',
              '    pause 0.3',
              '    assert id "voice_replay"', *current_replay_click, playing('voice', voice_file),
              f'    assert eval {replay_state} == _test.voice_replay_state',
              '    screenshot "scaled-voice-replay"',
              '    $ renpy.unlink_save("1-4")', '    click id "save_open"',
              '    pause until screen "save"', '    click id "slot_4"',
              '    assert eval renpy.can_load("1-4")', '    click id "game_return"',
              '    advance', f'    assert {quote(dialogue["s01_arrival_l006"]["text"])}',
              '    assert not id "voice_replay"',
              '    click id "load_open"', '    pause until screen "load"', '    click id "slot_4"',
              '    if screen "confirm":', '        click id "confirm_yes"',
              f'    pause until {quote(dialogue["s01_arrival_l005"]["text"])}',
              '    assert id "voice_replay"', *current_replay_click, playing('voice', voice_file),
              f'    assert eval {replay_state} == _test.voice_replay_state',
              '    screenshot "scaled-voice-replay-after-load"',
              # Dismiss uses the default say focus; leave the replay button first.
              '    move id "what"', '    advance', '    assert not id "voice_replay"',
              '    click id "rollback_run"',
              f'    pause until {quote(dialogue["s01_arrival_l005"]["text"])}',
              '    assert id "voice_replay"', *current_replay_click, playing('voice', voice_file),
              f'    assert eval {replay_state} == _test.voice_replay_state', '']

    lines += ['testcase history_voice_replay:', at_line('s01_arrival_l005'), '    advance',
              f'    assert {quote(dialogue["s01_arrival_l006"]["text"])}',
              '    assert not id "voice_replay"',
              f'    $ test_history_voice_index = next(i for i, h in enumerate(_history_list) if h.voice and h.voice.filename == {voice_file!r})',
              '    $ test_silent_history_index = len(_history_list) - 1',
              f'    $ _test.voice_replay_state = {replay_state}',
              '    click id "history_open"', '    assert screen "history"',
              f'    assert eval [h.voice.filename for h in _history_list if h.voice and h.voice.filename] == [{voice_file!r}]',
              '    assert eval renpy.get_widget("history", "history_voice_%d" % test_silent_history_index) is None',
              *history_replay_click, playing('voice', voice_file),
              f'    assert eval {replay_state} == _test.voice_replay_state',
              playing('music', 'audio/bgm/rain_theme.ogg'), playing('ambient', 'audio/sfx/rain_ambience.ogg'),
              '    screenshot "native-history-voice-replay"',
              '    run Preference("display", "window")',
              '    $ renpy.set_physical_size((1280, 720))',
              '    pause until eval renpy.get_physical_size() == (1280, 720)',
              '    pause 0.3', *history_replay_click, playing('voice', voice_file),
              '    screenshot "scaled-history-voice-replay"',
              '    click id "menu_preferences"', '    pause until screen "preferences"',
              '    click id "mute_all"', '    assert eval preferences.get_mute("voice")',
              '    click "历史"', '    pause until screen "history"',
              *history_replay_click,
              '    assert eval preferences.get_mute("voice")',
              '    pause until eval renpy.music.get_playing(channel="voice") is None',
              '    assert eval renpy.music.get_playing(channel="voice") is None',
              '    click id "menu_preferences"', '    pause until screen "preferences"',
              '    click id "mute_all"', '    assert eval not preferences.get_mute("voice")',
              '    click "历史"', '    pause until screen "history"',
              *history_replay_click,
              f'    pause until eval renpy.music.get_playing(channel="voice") == {voice_file!r}',
              playing('voice', voice_file),
              '    click id "game_return"', '    assert not screen "history"',
              '    pause until eval renpy.music.get_playing(channel="voice") is None',
              '    assert eval renpy.music.get_playing(channel="voice") is None',
              f'    assert eval {replay_state} == _test.voice_replay_state',
              playing('music', 'audio/bgm/rain_theme.ogg'), playing('ambient', 'audio/sfx/rain_ambience.ogg'),
              '    click id "history_open"', '    click id "menu_preferences"',
              '    assert screen "preferences"', '    click id "voice_test"', playing('voice', voice_file),
              '    click id "game_return"', '    assert not id "voice_replay"', '']

    lines += ['testcase auto_waits_for_replayed_voice:', '    $ preferences.wait_voice = True',
              '    $ preferences.afm_time = 0.1', at_line('s01_arrival_l005'),
              '    $ test_history_length = len(_history_list)', '    click id "auto_run"',
              '    pause 0.5', *current_replay_click,
              '    $ test_replay_started = __import__("time").monotonic()',
              '    assert eval preferences.afm_enable', playing('voice', voice_file),
              '    pause 0.5', '    assert eval len(_history_list) == test_history_length', playing('voice', voice_file),
              '    pause until eval len(_history_list) > test_history_length', '    click id "auto_run"',
              '    assert eval not preferences.afm_enable',
              f'    assert eval __import__("time").monotonic() - test_replay_started >= {voice_duration - 0.15:.3f}',
              '    $ preferences.afm_time = 15.0', '']
    replay_end = len(lines)
    lines += ['testcase auto_waits_for_voice:', '    $ preferences.wait_voice = True',
              '    $ preferences.afm_time = 0.1', at_line('s01_arrival_l005'),
              playing('voice', voice_file), '    $ test_voice_started = __import__("time").monotonic()',
              '    $ test_history_length = len(_history_list)',
              '    click id "auto_run"', '    assert eval preferences.afm_enable', '    pause 0.5',
              playing('voice', voice_file), '    assert eval len(_history_list) == test_history_length',
              '    screenshot "auto-voice-in-progress"',
              '    pause until eval len(_history_list) > test_history_length',
              '    click id "auto_run"', '    assert eval not preferences.afm_enable',
              '    assert eval renpy.music.get_playing(channel="voice") is None',
              # A fast AFM setting can legitimately advance multiple silent lines
              # between runner frames. Check complete playback, not an exact line count.
              f'    assert eval __import__("time").monotonic() - test_voice_started >= {voice_duration - 0.15:.3f}',
              '    $ preferences.afm_time = 15.0', '']

    lines += ['testcase skip_stops_at_later_choices:', '    $ preferences.skip_unseen = True',
              '    $ preferences.skip_after_choices = False']
    for index, identity in enumerate(true_route['choices'], 1):
        lines += ['    click id "skip_run"', '    pause until screen "choice"',
                  '    assert eval config.skipping is None',
                  f'    assert {quote(choices[identity]["text"])}']
        if index == 4:
            lines += ['    screenshot "skip-final-choice"']
        lines += [f'    click {quote(choices[identity]["text"])}', '    advance']
    lines += ['    $ preferences.skip_unseen = False', '    $ config.skipping = None', '']
    # Actual rendered height, not a character-count estimate.
    corpus = [(line['id'], line['text']) for n in story['nodes'] for line in scene_lines(n)]
    lines += ['testcase native_1080_and_scaled_window:',
              '    assert eval (config.screen_width, config.screen_height) == (1920, 1080)',
              f'    $ test_corpus = {corpus!r}',
              '    $ test_text_overflows = [(identity, renpy.render(Text(text, style="say_dialogue"), gui.dialogue_width, 10000, 0, 0).get_size()[1]) for identity, text in test_corpus if renpy.render(Text(text, style="say_dialogue"), gui.dialogue_width, 10000, 0, 0).get_size()[1] > gui.textbox_height - gui.dialogue_ypos - 42]',
              '    $ print("Dialogue overflow check:", test_text_overflows)',
              '    assert eval not test_text_overflows',
              '    assert eval renpy.get_physical_size() == (1920, 1080)',
              '    run MainMenu(confirm=False)',
              '    screenshot "native-main-menu"',
              '    click id "menu_about"',
              '    assert screen "about"',
              '    screenshot "native-about"',
              '    click id "game_return"',
              '    $ renpy.set_physical_size((1280, 720))',
              '    pause until eval renpy.get_physical_size() == (1280, 720)',
              '    assert eval not preferences.fullscreen',
              '    screenshot "scaled-main-menu"',
              '    click id "menu_start"',
              at_line('s01_arrival_l005'),
              '    assert screen "say"',
              '    screenshot "scaled-dialogue"',
              '    click id "history_open"',
              '    assert screen "history"',
              '    screenshot "scaled-history"',
              '    click id "game_return"',
              '    click id "preferences_open"',
              '    assert screen "preferences"',
              '    screenshot "scaled-settings"',
              '    click id "game_return"',
              '    advance until screen "choice"',
              '    assert screen "choice"',
              '    screenshot "scaled-choice"',
              '    click id "save_open"',
              '    assert screen "save"',
              '    screenshot "scaled-save"',
              '    click id "game_return"',
              '    click id "load_open"',
              '    assert screen "load"',
              '    screenshot "scaled-load"',
              '    click id "game_return"',
              '    click id "preferences_open"',
              '    click id "display_fullscreen"',
              '    pause until eval renpy.get_physical_size() == ((__import__("ctypes").windll.user32.GetSystemMetrics(0), __import__("ctypes").windll.user32.GetSystemMetrics(1)) if __import__("os").environ.get("RENPY_ACCEPTANCE_WINDOWED") == "1" else (1920, 1080))',
              '    assert eval preferences.fullscreen',
              '    if eval __import__("os").environ.get("RENPY_ACCEPTANCE_WINDOWED") == "1":',
              '        click id "display_window"',
              '        run Function(renpy.set_physical_size, (1920, 1080))',
              '        pause until eval renpy.get_physical_size() == (1920, 1080)',
              '    screenshot "native-settings"',
              '    click id "game_return"',
              '    assert screen "choice"',
              '    screenshot "native-choice"', '']
    first = lines.index('testcase route_01:')
    display = lines.index('testcase native_1080_and_scaled_window:')
    # Wall-time pauses alone can still capture a software-rendered transition.
    # Wait for the engine's actual transition state before capturing the UI.
    display_lines = []
    for line in lines[display:]:
        if line.strip().startswith('screenshot '):
            display_lines.append('    pause 0.3')
            display_lines.append('    pause until eval not any(renpy.get_ongoing_transition(layer) for layer in (None, "master", "screens"))')
        display_lines.append(line)
    # Run new voice interaction checks before the long all-route regression.
    replay_lines = []
    for line in lines[replay_start:replay_end]:
        if line.strip().startswith('screenshot '):
            replay_lines.append('    pause 0.3')
            replay_lines.append('    pause until eval not any(renpy.get_ongoing_transition(layer) for layer in (None, "master", "screens"))')
        replay_lines.append(line)
    return "\n".join(lines[:first] + display_lines + replay_lines + render_extras_tests(story) + lines[first:replay_start] + lines[replay_end:display])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = render_tests(load_story())
    path = ROOT / "game/testcases.rpy"
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            raise SystemExit("Stale generated interaction tests")
    else:
        path.write_text(content, encoding="utf-8")
    print("Interaction tests are current." if args.check else "Interaction tests generated.")


if __name__ == "__main__":
    main()
