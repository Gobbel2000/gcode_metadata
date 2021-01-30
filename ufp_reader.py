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
        # This line is important, otherwise __getattr__ could recurse indefinitely
        self._gcode_parser = None

        self.path = path
        self._module = module
        self._zip_obj = ZipFile(path)

        self._gcode_parser = module._parse_gcode(self.get_gcode_stream())

        self.thumbnail_path = None
        self._material_guids = []
        self._relationships = self._get_relationships()
        self._extract_thumbnail()
        self._extract_materials()

    def get_gcode_stream(self):
        if self._gcode_path not in self._zip_obj.namelist():
            raise FileNotFoundError("Can't locate .gcode file in UFP package")
        return self._zip_obj.open(self._gcode_path)

    def get_file_size(self):
        if self._gcode_path not in self._zip_obj.namelist():
            raise FileNotFoundError("Can't locate .gcode file in UFP package")
        return self._zip_obj.getinfo(self._gcode_path).file_size

    def _get_relationships(self):
        """
        Return the file relationships from the gcode file in the UFP package.
        Each element is a dictionary containing the fields Target, Type and Id.
        """
        if self._gcode_relationship_path not in self._zip_obj.namelist():
            return []
        with self._zip_obj.open(self._gcode_relationship_path) as rel_fp:
            root = ET.parse(rel_fp).getroot()
        ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
        relationships = [e.attrib for e in root.findall("r:Relationship", ns)]
        # Make sure the list is sorted right
        relationships.sort(key = lambda e: e.get("Id"))
        return relationships

    def _extract_thumbnail(self):
        """Write the thumbnail into the .thumbnails directory"""
        virtual_path = next(iter(e["Target"] for e in self._relationships
                if e["Type"] == self._thumbnail_relationship_type), None)
        if virtual_path is None:
            return
        thumbnail_dir = os.path.dirname(self.path) + "/.thumbnails/"
        if not os.path.exists(thumbnail_dir):
            os.mkdir(thumbnail_dir)
        thumbnail_path = thumbnail_dir + os.path.basename(self.path) + ".png"
        with open(thumbnail_path, "wb") as thumbnail_target:
            thumbnail_target.write(self._zip_obj.read(virtual_path))
        self.thumbnail_path = thumbnail_path

    def _extract_materials(self):
        """
        In case a material file isn't present yet on this system, it gets
        extracted and added to the filament manager.
        """
        fm = self._module.filament_manager
        if fm is None:
            return
        material_paths = [e["Target"] for e in self._relationships
                          if e["Type"] == self._material_relationship_type]
        for material in material_paths:
            material_file = self._zip_obj.open(material)
            guid = fm.get_info(material_file, "./m:metadata/m:GUID")
            material_file.seek(0)
            version = fm.get_info(material_file, "./m:metadata/m:version")
            if not (guid in fm.guid_to_path and
                    version == fm.get_info(guid, "./m:metadata/m:version")):
                # New material, needs to be extracted
                new_material_path = os.path.join(fm.material_dir, os.path.basename(material))
                material_file.seek(0)
                with open(new_material_path, "wb") as fp:
                    fp.write(material_file.read())
                fm.read_single_file(new_material_path)
            material_file.close()
            self._material_guids.append(guid)

    def get_filetype(self):
        return "ufp"

    def get_material_guid(self, extruder=0):
        if not self._material_guids:
            return None
        # If multiple extruders use the same material there are less
        # materials than extruders
        extruder = min(extruder, len(self._material_guids) - 1)
        guid = self._material_guids[extruder]
        return guid

    def get_material_info(self, xpath, extruder=0):
        fm = self._module.filament_manager
        guid = self.get_material_guid(extruder)
        if fm is None or guid is None:
            return None
        return fm.get_info(guid, xpath)

    def get_material_type(self, extruder=0):
        return self.get_material_info("./m:metadata/m:name/m:material", extruder)

    def get_material_brand(self, extruder=0):
        return self.get_material_info("./m:metadata/m:name/m:brand", extruder)

    def get_material_color(self, extruder=0):
        return self.get_material_info("./m:metadata/m:color_code", extruder)

    def get_density(self, extruder=0):
        return (self.get_material_info("./m:properties/m:density", extruder)
                or self._gcode_parser.get_density(extruder))

    def get_diameter(self, extruder=0):
        return (self.get_material_info("./m:properties/m:diameter", extruder)
                or self._gcode_parser.get_density(extruder))

    def get_thumbnail_path(self):
        return self.thumbnail_path

    def __getattr__(self, name):
        """
        This function gets called only when a request couldn't be answered,
        i.e. an AttributeError was raised. We route over to the gcode parser,
        effectively extending this class by the gcode parser.
        """
        return getattr(self._gcode_parser, name)

    def __del__(self):
        self._zip_obj.close()
