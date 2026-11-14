"""The debug tool's scene list: generated file up to date, every row well-formed, every poke alias known."""
import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG = os.path.join(ROOT, 'tools', 'debug')


class SceneList(unittest.TestCase):
    def test_generated_file_is_current(self):
        r = subprocess.run([sys.executable, '-X', 'utf8', os.path.join(DEBUG, 'gen_scenes.py'), '--check'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_rows(self):
        with open(os.path.join(DEBUG, 'warp.lua'), encoding='utf-8') as f:
            lua = f.read()
        aliases = set(re.findall(r'^\s+(\w+) = P \+', lua, re.M))
        self.assertIn('area', aliases)
        names = set()
        with open(os.path.join(DEBUG, 'scenes.gba.txt'), encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                if not line or line.startswith('#'):
                    continue
                col = line.split('\t')
                self.assertEqual(len(col), 7, line)
                name, scene, sub, pokes, presses = col[:5]
                self.assertNotIn(name, names, 'duplicate ' + name)
                names.add(name)
                self.assertTrue(0 <= int(scene) < 256 and 0 <= int(sub) < 256, line)
                for tok in pokes.split():
                    if tok == '-' or tok.startswith('@'):
                        continue
                    key, _, val = tok.partition('=')
                    self.assertTrue(key in aliases or key.startswith('0x'), 'unknown poke %s in %s' % (key, name))
                    int(val, 0)
                for step in presses.split(';'):
                    step = step.strip()
                    self.assertTrue(step == '-' or re.fullmatch(r'\d+ \S+', step) or re.fullmatch(r'mash\d+[a-z]*', step),
                                    'bad press %r in %s' % (step, name))


if __name__ == '__main__':
    unittest.main()
