"""Render the website while preserving the author's edited README.

Run from this project with: uv run python scripts/render_tutorial.py
This script only writes local build outputs; it does not publish or commit.
Use --update-readme only when deliberately replacing README.md from blog.qmd.
"""
import argparse
from html import unescape
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

class FigureImage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.alt = None
        self.source = None

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            values = dict(attrs)
            self.alt = values.get('alt')
            self.source = values.get('src')

def export_readme():
    source = ROOT / '.cache' / 'readme-export' / 'README.md'
    text = source.read_text(encoding='utf-8')
    block = re.search(r'<div id="fig-test-predictions">.*?</div>', text, re.S)
    if block is None:
        raise RuntimeError('Expected tutorial figure was not found; README was not replaced.')
    image = FigureImage()
    image.feed(block.group())
    if not image.source or not image.alt:
        raise RuntimeError('The figure needs a valid source and alt text.')
    relative = Path('docs/blog_files/figure-html') / Path(image.source).name
    if not (ROOT / relative).is_file():
        raise RuntimeError('Render the HTML figure before exporting the README.')
    caption = re.search(r'(Figure[^<]+)', block.group(), re.S)
    if caption is None:
        raise RuntimeError('Expected a figure caption.')
    caption_text = ' '.join(unescape(caption.group()).split())
    replacement = f'![{image.alt}]({relative.as_posix()})\n\n*{caption_text}*'
    text = text[:block.start()] + replacement + text[block.end():]
    text = text.replace('\nConnor Gordon\n2026-10-16\n', '\n\n*Connor Gordon · October 16, 2026*\n')
    (ROOT / 'README.md').write_text(text, encoding='utf-8')
    print('Updated README.md from the executed tutorial; the figure is shared with docs/.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update-readme', action='store_true',
                        help='Explicitly replace README.md with Markdown generated from blog.qmd.')
    args = parser.parse_args()
    quarto = shutil.which('quarto')
    if not quarto:
        raise RuntimeError('Install Quarto and make sure it is on PATH.')
    env = os.environ.copy()
    env['QUARTO_PYTHON'] = sys.executable
    for key, directory in (
        ('JUPYTER_RUNTIME_DIR', 'jupyter-runtime'),
        ('JUPYTER_DATA_DIR', 'jupyter-data'),
        ('JUPYTER_CONFIG_DIR', 'jupyter-config'),
        ('IPYTHONDIR', 'ipython'),
        ('MPLCONFIGDIR', 'matplotlib'),
    ):
        env[key] = str(ROOT / '.cache' / directory)
    subprocess.run([quarto, 'render', '--execute-daemon', '0'], cwd=ROOT, env=env, check=True)
    (ROOT / '.nojekyll').touch(exist_ok=True)
    (ROOT / 'docs' / '.nojekyll').touch(exist_ok=True)
    if args.update_readme:
        subprocess.run([
            quarto, 'render', 'blog.qmd', '--to', 'gfm', '--output', 'README.md',
            '--output-dir', '.cache/readme-export', '--execute-daemon', '0',
        ], cwd=ROOT, env=env, check=True)
        export_readme()
    else:
        print('Website rendered. Your edited README.md was preserved.')

if __name__ == '__main__':
    main()
