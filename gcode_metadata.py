#!/usr/bin/env python3

import os

from ufp_reader import UFPReader

from cura_marlin_parser import CuraMarlinParser
from prusaslicer_parser import PrusaSlicerParser

PARSERS = [CuraMarlinParser,
           PrusaSlicerParser,
]

class GCodeMetadata:

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
            gcode_file = open(gcode_file, "rb")
        head, tail = self.filter_metadata_lines(gcode_file)
        gcode_file.close()
        parser = None
        for p in PARSERS:
            if p._detect(head, tail):
                parser = p
                break
        if parser is None:
            raise ValueError(f"Couldn't find matching parser for {path}")
        return parser(head, tail)

    """
    def _parse_ufp(self, path):
        Extract thumbnail and material file from the UFP and return file
        pointer to the gcode file.
        return
        with ZipFile(path, "r") as zip_obj:
            thumbnail_dir = os.path.dirname(path) + "/.thumbnails/"
            if not os.path.exists(thumbnail_dir):
                os.mkdir(thumbnail_dir)
            thumbnail_path = thumbnail_dir + os.path.basename(path) + ".png"
            with open(thumbnail_path, "wb") as thumbnail_target:
                thumbnail_target.write(zip_obj.read("/Metadata/thumbnail.png"))

            if self.filament_manager:
                fm = self.filament_manager
                # Find out if the material file with this guid already exists
                material_paths = [p for p in zip_obj.namelist()
                                  if p.startswith("/Materials/")]
                guids = []
                # If sliced for 2 extruders there can be 2 material files
                for mp in material_paths:
                    with zip_obj.open(mp) as material_fp:
                        guid = fm.get_info(material_fp, "./m:metadata/m:GUID")
                        material_fp.seek(0)
                        if not (guid in fm.guid_to_path
                            and fm.get_info(material_fp, "./m:metadata/m:version")
                                == fm.get_info(guid, "./m:metadata/m:version")):
                            # New material, needs to be extracted
                            new_material_path = fm.material_dir + os.path.basename(mp)
                            with open(new_material_path, "wb") as material_target:
                                # This might overwrite the old file
                                material_fp.seek(0)
                                material_target.write(material_fp.read())
                            fm.read_single_file(new_material_path)
                    guids.append(guid)
                self.extra_data["material_guids"] = guids
            gcode_fp = zip_obj.open("/3D/model.gcode", "r")  # Persists after closing zip_obj
        return gcode_fp
    """

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
    path = sys.argv[1]
    mm = GCodeMetadata()
    md = mm.get_metadata(path)
    print(md.get_time(), md.get_filament())
