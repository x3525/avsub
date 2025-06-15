"""FFmpeg module."""

from __future__ import annotations

import collections
import fractions
import itertools
import math
import os
import subprocess as sp  # nosec
from typing import TYPE_CHECKING

from avsub.consts import *
from avsub.globs import completed, controller, corrupted, untouched

if TYPE_CHECKING:
    from argparse import Namespace


class FFmpeg:
    """FFmpeg handler."""

    cmd = ['ffmpeg', '-n', '-stats']
    style: str

    def build(self, opts: Namespace) -> None:
        """Update the FFmpeg command."""
        cmd = []

        if opts.channel:
            cmd += ['-ac', CHOICES_CHANNEL[opts.channel]]

        if opts.a:
            cmd += ['-codec:a', opts.a]
        if opts.s:
            cmd += ['-codec:s', opts.s]
        if opts.v:
            cmd += ['-codec:v', opts.v]

        cmd += ['-crf', str(opts.compress)]

        cmd += itertools.chain(
            *(['-codec:' + s[0].strip('-'), 'copy'] for s in opts.copy)
        )

        if not opts.disable:
            cmd += ['-map', '0']

        if opts.frame is not None:
            cmd += ['-r', str(opts.frame)]

        cmd += opts.A + opts.S + opts.V

        cmd += [f'-{s[0]}n' for s in opts.remove]

        cmd += ['-map_chapters', str(-int(opts.chapters))]
        cmd += ['-map_metadata', str(-int(opts.metadata))]

        if opts.speed is not None:
            speed_a, speed_v = opts.speed

            by_audio = float(fractions.Fraction(speed_a))
            by_video = float(fractions.Fraction(speed_v))

            k = CHOICES_SPEED[speed_a]
            n = int(math.log(by_audio, k))

            extra = by_audio / (k ** n)

            cmd += ['-af', ','.join([f'atempo={k}'] * n + [f'atempo={extra}'])]
            cmd += ['-vf', f'setpts=PTS/{by_video}']

        if opts.trim is not None:
            seek = (opts.trim[0] * 3600) + (opts.trim[1] * 60) + opts.trim[2]
            stop = (opts.trim[3] * 3600) + (opts.trim[4] * 60) + opts.trim[5]
            cmd += ['-ss', str(seek), '-to', str(stop)]

        loglevel = collections.defaultdict(lambda: '40', {0: '24', 1: '32'})

        cmd += ['-loglevel', loglevel[opts.loglevel]]

        if opts.ffmpeg:
            cmd += opts.ffmpeg.strip().split()

        self.cmd += cmd

        style = []

        style += [f'Fontname={opts.fontname}']
        style += [f'Fontsize={abs(opts.fontsize)}']

        style += [f'PrimaryColour={CHOICES_SUB_COLOR_CHART[opts.primary]}']
        style += [f'OutlineColour={CHOICES_SUB_COLOR_CHART[opts.outline]}']

        style += [f'Alignment={CHOICES_SUB_ALIGN[opts.alignment]}']

        self.style = ','.join(style)

    def subtitle(self, file: str) -> None:
        """Update the FFmpeg command with the given subtitle file."""
        self.cmd += ['-vf', f"subtitles={file}:force_style='{self.style}'"]

    def execute(self, files: list[str]) -> None:
        """Execute the FFmpeg command."""
        total = len(files)
        align = len(str(total))

        i = itertools.count(1)

        while not controller.is_set() and files:
            file = files.pop(0)

            print('[*]', f"Running [{next(i):>{align}}/{total}] -> '{file}'")

            output = untouched[file]

            # Also for files with the same name but different extensions
            if os.path.exists(output):
                print('[ ]', f"File '{output}' already exists. Passing.")
                continue

            cmd = self.cmd + [output, '-i', file]

            try:
                sp.run(cmd, stdin=sp.DEVNULL, check=True)  # nosec
            except FileNotFoundError:
                print('[!]', 'FFmpeg could not be executed. Exiting.')
                return
            except sp.CalledProcessError:
                # Output will be deleted on exit
                corrupted.update({file: untouched.pop(file)})
            else:
                # Output will not be deleted on exit
                completed.update({file: untouched.pop(file)})
