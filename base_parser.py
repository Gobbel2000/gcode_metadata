import itertools
from math import pi
import re

class BaseParser:
    """
    Base class for all parsers.

    A parser for a specific slicer should inherit this class.
    For adding metadata the appropriate methods should be overridden,
    however all methods are optional to implement. If unchanged,
    a default value will be set, usually None.

    This is only used as a temporary object, all values are stored
    in a Metadata object which basically executes all get_* methods of
    the parser class.
    """

    """Used by detect() on all lines to figure out if this is the right parser"""
    PATTERN_DETECT = re.compile("(?!)")  # Matches nothing

    """Character that seperates keys from values"""
    DELIMITER = "="

    """Name of the slicer used to generate the G-Code file"""
    SLICER = "Unknown"
    
    def __init__(self):
        self.options = {}
        self.non_option_lines = []

    def detect(self, head=[], tail=[]):
        """
        return True if this is the right parser for this file
        """
        for l in itertools.chain(head, tail):
            if re.search(self.PATTERN_DETECT, l):
                return True
        return False
    
    def parse_options(self, head=[], tail=[]):
        for l in itertools.chain(head, tail):
            if self.DELIMITER in l:
                key, value = l.split(self.DELIMITER, maxsplit=1)
                value = value.strip()
                try:
                    value = eval(value, {}, {})
                except (NameError, SyntaxError):
                    pass
                self.options[key.strip()] = value
            else:
                self.non_option_lines.append(l)

    def get_slicer(self):
        """Name of the slicer used to generate the G-Code file"""
        return self.SLICER
    
    def get_time(self):
        """Total print time in seconds"""
        return None

    def get_filament(self):
        """
        Return the total amount of filament used, all extruders summed up.
        Should return None or a dictionary containing the values
        "length" in mm, "volume" in mm^3 and "weight" in g.
        self.convert_filament() will help with this.
        """
        return self.convert_filament()

    def convert_filament(self, length=None, volume=None, weight=None):
        """
        Given at least one measurement of length, volume or weight,
        return all other measurements, provided that get_diameter()
        and get_density() are implemented.
        """
        diameter = self.get_diameter()
        if diameter is not None:
            area = pi * diameter**2  # mm^2
        else:
            area = None
        density = self.get_density()
        if density is not None:
            density /= 1000  # g/mm^3

        if length:
            if not volume and area:
                volume = length * area
            if not weight and density:
                weight = volume * density
        elif volume:
            if not weight and density:
                weight = volume * density
            if not length and area:
                length = volume / area
        elif weight:
            if not volume and density:
                volume = weight / density
            if not length and area:
                length = volume / area
        return {"length": length, "volume": volume, "weight": weight}

    def get_density(self):
        """Material density in g/cm^3"""
        return 1.24

    def get_diameter(self):
        """Filament diameter in mm"""
        return 1.75

    def get_flavor(self):
        """The G-Code flavor used"""
        return None
