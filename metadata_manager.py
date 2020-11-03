#!/usr/bin/env python3

import sys

from cura_marlin_parser import CuraMarlinParser
from prusaslicer_parser import PrusaSlicerParser
from metadata import Metadata

PARSERS = [CuraMarlinParser,
           PrusaSlicerParser,
]

class MetadataManager:

    def __init__(self, config=None):
        if config is None:
            return
        self.config = config
        self.printer = config.get_printer()
        self.printer.register_event_handler("klippy:connect", self._handle_connect)
        self.filament_manager = None

    def _handle_connect(self):
        self.filament_manager = self.printer.lookup_object(
                "filament_manager", None)

    def get_metadata(self, path):
        """
        This is the main method of the module that returns a metadata
        object for the given gcode path.
        """
        head, tail = self.filter_metadata_lines(path)
        parser = None
        for p in PARSERS:
            inst = p()
            if inst.detect(head, tail):
                parser = inst
                break
        if parser is None:
            raise ValueError("Couldn't find matching parser for %s" % path)
        parser.parse_options(head, tail)
        metadata = Metadata(parser)
        return metadata

    def filter_metadata_lines(self, path):
        """
        Retreave the relevant metadata lines from the gcode file.

        This includes all fully commented lines (starting with ';') up until
        the first non-commented line, and the last lines accordingly.
        The leading semicolon is stripped.
        """
        bufsize = 1024
        with open(path, "rb") as fp:
            head = []
            last_line = b""
            keep_reading = True
            while keep_reading:
                buf = fp.read(bufsize)
                if not buf:  # There are only comments in the file
                    break
                new_lines = buf.split(b"\n")
                new_lines[0] = last_line + new_lines[0]
                last_line = new_lines.pop()
                for l in new_lines:
                    l = l.strip()
                    if l.startswith(b';'):
                        head.append(l[1:].decode())
                    elif l == b'':
                        continue
                    else:
                        keep_reading = False
                        break
            tail = []
            blocks_offset = -1
            last_line = b""
            keep_reading = True
            while keep_reading:
                try:
                    fp.seek(blocks_offset * bufsize, 2)
                except OSError:  # Trying to go before BOF
                    break
                blocks_offset -= 1
                buf = fp.read(bufsize)
                new_lines = buf.split(b'\n')
                new_lines[-1] += last_line
                last_line = new_lines.pop(0)
                for l in reversed(new_lines):
                    l = l.strip()
                    if l.startswith(b';'):
                        tail.append(l[1:].decode())
                    elif l == b'':
                        continue
                    else:
                        keep_reading = False
                        break
            tail.reverse()
        return head, tail

def load_config(config):
    module = MetadataManager(config)
    return module

if __name__ == "__main__":
    path = sys.argv[1]
    mm = MetadataManager()
    md = mm.get_metadata(path)
    print(md)
