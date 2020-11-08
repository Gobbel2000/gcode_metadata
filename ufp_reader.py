import os
import xml.etree.ElementTree as ET
from zipfile import ZipFile

class UFPReader:
    """
    This class acts as an additional level ontop of the Parser base class
    that takes care of opening the UFP file and adds additional functionality
    unique to that format.
    """

    _gcode_path = "/3D/model.gcode"
    _gcode_relationship_path = "/3D/_rels/model.gcode.rels"

    _thumbnail_relationship_type = "http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"
    _material_relationship_type = "http://schemas.ultimaker.org/package/2018/relationships/material"

    def __init__(self, path, module):
        self.path = path
        self._zip_obj = ZipFile(path)

        self._gcode_parser = module._parse_gcode(self.get_gcode_stream())

        self.thumbnail_path = None
        self._relationships = self._get_relationships()
        virtual_thumbnail_path = next(iter(e["Target"] for e in self._relationships
                                 if e["Type"] == self._thumbnail_relationship_type), None)
        if virtual_thumbnail_path:
            self._extract_thumbnail(virtual_thumbnail_path)

    def get_gcode_stream(self):
        if self._gcode_path not in self._zip_obj.namelist():
            raise FileNotFoundError("Can't locate .gcode file in UFP package")
        return self._zip_obj.open(self._gcode_path)

    def _get_relationships(self):
        """
        Return the file relationships from the gcode file in the UFP package.
        Each element is a dictionary containing the fields Target, Type and Id.
        """
        if self._gcode_relationship_path not in self._zip_obj.namelist():
            return []
        with self._zip_obj.open(self._gcode_relationship_path) as rel_fp:
            root = ET.parse(rel_fp).getroot()
        ns = {"": "http://schemas.openxmlformats.org/package/2006/relationships"}
        relationships = [e.attrib for e in root.findall("Relationship", ns)]
        # Make sure the list is sorted right
        relationships.sort(key = lambda e: e.get("Id"))
        return relationships

    def _extract_thumbnail(self, virtual_path):
        thumbnail_dir = os.path.dirname(self.path) + "/.thumbnails/"
        if not os.path.exists(thumbnail_dir):
            os.mkdir(thumbnail_dir)
        thumbnail_path = thumbnail_dir + os.path.basename(self.path) + ".png"
        with open(thumbnail_path, "wb") as thumbnail_target:
            thumbnail_target.write(self._zip_obj.read(virtual_path))
        self.thumbnail_path = thumbnail_path

    def __getattr__(self, name):
        """
        This function gets called only when a request couldn't be answered,
        i.e. an AttributeError was raised. We route over to the gcode parser,
        effectively extending this class by the gcode parser.
        """
        return getattr(self._gcode_parser, name)

    def __del__(self):
        self._zip_obj.close()
