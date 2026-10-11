define config.name = _("雨停之前")
define config.version = "1.2.0"
define config.window_title = "雨停之前 · AI Galgame"
define gui.show_name = True
define gui.about = _("雨夜的旧车站，两位久未联系的旧友，和一封没有寄出的信。\n\n创作与工程：AureliusWu / AI 辅助\n图像：OpenAI 图像生成\n关键语音：Qwen3-TTS 1.7B / Serena\n音乐与音效：原创程序合成\n字体：Source Han Sans / SIL OFL 1.1\n\nv1.0 完整短篇。版本验收记录见发行说明；完整来源见随游戏附带的 CREDITS.md。")
define build.name = "BeforeTheRainStops"
define build.version = config.version
define build.destination = "dist"
define config.save_directory = "AureliusWu-BeforeTheRainStops-v1"
define config.has_sound = True
define config.has_music = True
define config.has_voice = True
define config.default_music_volume = 0.4
define config.default_sfx_volume = 0.3
define config.default_voice_volume = 0.8
define config.sample_voice = "audio/voice/heroine_s01_arrival_l005_v1.ogg"
define config.default_language = "schinese"
define config.default_text_cps = 32
define config.window = "auto"
define config.enter_transition = dissolve
define config.exit_transition = dissolve
define config.after_load_transition = None
define config.end_game_transition = dissolve
define config.physical_width = 1280
define config.physical_height = 720
define config.window_icon = "gui/window_icon.png"

init python:
    # Explicit allow-list: authoring data, source assets and tools stay out of ZIP.
    build.classify("game/cache/**", None)
    build.classify("game/saves/**", None)
    build.classify("game/tests/**", None)
    build.classify("game/testcases.*", None)
    build.classify("game/data/**", None)
    build.classify("**~", None)
    build.classify("**.bak", None)
    build.classify("**.rpy", None)
    build.classify("game/**", "all")
    build.classify("PLAYER_README.txt", "all")
    build.classify("CREDITS.md", "all")
    build.classify("LICENSE", "all")
    build.classify("licenses/**", "all")
    build.classify("**", None)
    build.documentation("PLAYER_README.txt")
    build.documentation("CREDITS.md")
