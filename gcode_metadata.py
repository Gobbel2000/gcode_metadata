#!/usr/bin/env python3

import os

from ufp_reader import UFPReader

from cura_marlin_parser import CuraMarlinParser
from prusaslicer_parser import PrusaSlicerParser

class GCodeMetadata:

    _parsers = [CuraMarlinParser,
                PrusaSlicerParser,
    ]

    def __init__(self, config=None):
        self.filament_manager = None
        if config is None:
            import site
            site.addsitedir(os.path.dirname(os.path.dirname(
                            os.path.realpath(__file__))))
            import filament_manager
            self.filament_manager = filament_manager.load_config(None)
            return
        self.config = config
        self.printer = config.get_printer()
        self.printer.register_event_handler("klippy:connect", self._handle_connect)

    def _handle_connect(self):
        self.filament_manager = self.printer.lookup_object(
                "filament_manager", None)

    def get_metadata(self, path):
        """
        This is the main method of the module that returns a metadata
        object for the given gcode path. UFP files are also accepted.
        """
        ext = os.path.splitext(path)[1]
        if ext in {".gco", ".gcode"}:
            return self._parse_gcode(path)
        elif ext == ".ufp":
            return UFPReader(path, self)
        else:
            raise ValueError(f"File must be either gcode or ufp file, not {ext}")

    def _parse_gcode(self, gcode_file):
        """
        Parse the Metadata for the G-Code and return an object describing
        the file.

        gcode_file can either be a path to the .gcode file or an open
        file pointer. If a stream is provided, be aware that it gets closed
        in this function.
        """
        if not hasattr(gcode_file, "read"):
            # Path is given, open stream
            path = gcode_file
            gcode_file = open(path, "rb")
        else:
            path = None
        head, tail = self.filter_metadata_lines(gcode_file)
        gcode_file.close()
        parser = None
        for p in self._parsers:
            if p._detect(head, tail):
                parser = p
                break
        if parser is None:
            raise ValueError(f"Couldn't find matching parser for {path}")
        return parser(head, tail, path)

    def filter_metadata_lines(self, fp):
        """
        Retreave the relevant metadata lines from the gcode file,
        which must be given as an open file stream.

        This includes all fully commented lines (starting with ';') up until
        the first non-commented line, and the last lines accordingly.
        The leading semicolon is stripped.
        """

        bufsize = 1024
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
    module = GCodeMetadata(config)
    return module

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.exit("A path to parse must be provided")
    path = sys.argv[1]
    mm = GCodeMetadata()
    md = mm.get_metadata(path)
    print(md.get_time(), md.get_filament())
    print(md.get_extruder_count())
    for i in range(md.get_extruder_count()):
        print(md.get_material_guid(i))
        print(md.get_material_color(i))
