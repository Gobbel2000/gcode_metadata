#!/usr/bin/env python3

import os

from .ufp_reader import create_ufp_reader

from .base_parser import BaseParser
from .cura_marlin_parser import CuraMarlinParser
from .prusaslicer_parser import PrusaSlicerParser

class GCodeMetadata:

    _parsers = [CuraMarlinParser,
                PrusaSlicerParser,
    ]

    def __init__(self, config=None):
        # Map paths to metadata objects to cache already parsed files
        self._md_cache = {}

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
        self.printer.register_event_handler(
                "klippy:connect", self._handle_connect)

    def _handle_connect(self):
        self.filament_manager = self.printer.lookup_object(
                "filament_manager", None)

    def delete_cache_entry(self, path):
        """Delete a single metadata object from the cache"""
        if path in self._md_cache:
            del self._md_cache[path]

    def flush_cache(self):
        """
        Delete all cached metadata objects, forcing all files to be
        reparsed in the future.
        """
        self._md_cache = {}

    def get_metadata(self, path):
        """
        This is the main method of the module that returns a metadata
        object for the given gcode path. UFP files are also accepted.
        """
        if path in self._md_cache:
            return self._md_cache[path]

        ext = os.path.splitext(path)[1]
        if ext in {".gco", ".gcode"}:
            metadata = self._parse_gcode(path)
        elif ext == ".ufp":
            metadata = create_ufp_reader(path, self)
        else:
            raise ValueError(f"File must be either gcode or ufp file, not {ext}")
        self._md_cache[path] = metadata
        return metadata

    def _parse_gcode(self, path):
        """
        Parse the Metadata for the G-Code and return an object describing
        the file.

        gcode_file can either be a path to the .gcode file or an open
        file pointer. If a stream is provided, be aware that it gets closed
        in this function.
        """
        gcode_file = open(path, "rb")
        head = self._get_head_md(gcode_file)
        tail = self._get_tail_md(gcode_file)
        gcode_file.close()
        ParserClass = self._find_parser(head + tail)
        return ParserClass(head, tail, path)

    def _find_parser(self, lines):
        """
        Return the correct GCode Parser class detect from the given lines.
        If no matching class is found, return BaseParser.
        """
        for p in self._parsers:
            if p._detect(lines):
                return p
        # Use BaseParser as fallback
        return BaseParser

    def _get_head_md(self, fp):
        """
        Retreave the relevant metadata lines from the gcode file,
        which must be given as an open file stream.

        This includes all fully commented lines (starting with ';') up until
        the first non-commented line.
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
        return head

    def _get_tail_md(self, fp):
        """
        Like _get_head_md but read from EOF backwards.
        """
        bufsize = 1024
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
        return tail

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
    general_interface = [
        "get_gcode_stream",
        "get_file_size",
        "get_slicer",
        "get_filetype",
        "get_extruder_count",
        "get_print_dimensions",
        "get_time",
        "get_flavor",
        "get_thumbnail_path",
        ]
    extruder_interface = [
        "get_filament",
        "get_material_guid",
        "get_material_type",
        "get_material_brand",
        "get_material_color",
        "get_density",
        "get_diameter",
        ]
    max_len = max([len(e) for e in general_interface + extruder_interface])
    for fname in general_interface:
        print(fname[4:] + ":" + " " * (max_len - len(fname) + 1)
              + str(getattr(md, fname)()))
    for i in range(md.get_extruder_count()):
        print(f"\nExtruder {i}:")
        for fname in extruder_interface:
            print(fname[4:] + ":" + " " * (max_len - len(fname) + 1)
                  + str(getattr(md, fname)()))
