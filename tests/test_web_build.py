import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from tools.build.web import add_pwa, stage_project

class WebPackagingTests(unittest.TestCase):
    def fixture(self, root):
        (root/'index.html').write_text('''<html lang="en-us"><body><canvas></canvas><script>
      // Register the service worker.
      if (navigator.serviceWorker) { navigator.serviceWorker.register('./service-worker.js'); }
  </script></body></html>''',encoding='utf-8')
        (root/'manifest.json').write_text(json.dumps({'icons':[]}))
        (root/'renpy.wasm').write_bytes(b'fixed engine')

    def test_catalog_hashes_final_files_and_pins_application_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); self.fixture(root)
            catalog=add_pwa(root,'1.2.0')
            self.assertEqual(json.loads((root/'manifest.json').read_text(encoding='utf-8'))['scope'],'./')
            self.assertIn('lang="zh-CN"',(root/'index.html').read_text(encoding='utf-8'))
            for entry in catalog['files']:
                data=(root/entry['path']).read_bytes()
                self.assertEqual(entry['bytes'],len(data))
                self.assertEqual(entry['sha256'],hashlib.sha256(data).hexdigest())
            sw=(root/'service-worker.js').read_text(encoding='utf-8')
            self.assertNotIn('self.skipWaiting()',sw)
            self.assertIn('await caches.delete(CACHE)',sw)
            self.assertIn('__rain_complete__',sw)

    def test_unrecognized_sdk_html_refuses_silent_registration_duplication(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); self.fixture(root)
            (root/'index.html').write_text('<body>changed SDK</body>')
            with self.assertRaisesRegex(ValueError,'registration layout changed'):
                add_pwa(root,'1.2.0')

    def test_staging_preserves_author_saves_and_uses_authored_material(self):
        with tempfile.TemporaryDirectory() as temp:
            author=Path(temp)/'author'; staged=Path(temp)/'staged'
            (author/'game/gui').mkdir(parents=True)
            (author/'game/data').mkdir()
            (author/'game/saves').mkdir()
            persistent=author/'game/saves/persistent'
            persistent.write_bytes(b'player data must stay untouched')
            (author/'progressive_download.txt').write_text('- image game/**\n')
            Image.new('RGBA',(256,256),(17,43,54,255)).save(author/'game/gui/window_icon.png')
            Image.new('RGB',(32,18),(17,43,54)).save(author/'game/background.png')
            (author/'game/data/asset_manifest.json').write_text(json.dumps({'assets':[{'id':'station','file':'background.png'}]}))
            with patch('tools.build.web.ROOT',author): stage_project(staged)
            self.assertFalse((staged/'game/saves').exists())
            self.assertEqual(persistent.read_bytes(),b'player data must stay untouched')
            self.assertFalse((author/'web-icon.png').exists())
            self.assertEqual((staged/'web-presplash.png').read_bytes(),(author/'game/background.png').read_bytes())
            self.assertEqual((staged/'progressive_download.txt').read_text(),'- image game/**\n')

if __name__ == '__main__': unittest.main()
