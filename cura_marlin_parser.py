import re

from base_parser import BaseParser

class CuraMarlinParser(BaseParser):

    PATTERN_DETECT = re.compile("Generated with Cura_SteamEngine",
                                flags=re.IGNORECASE)
    DELIMITER = ":"
    SLICER = "Cura"

    @classmethod
    def _detect(cls, head, tail):
        """Slicer info is at end of head, so optimize for that"""
        return super()._detect(reversed(head))

    def get_flavor(self):
        return self.options.get("FLAVOR")

    def get_extruder_count(self):
        """
        The number of extruders can be determined by the number of filament figures.
        """
        filament = self.options.get("Filament used")
        if filament is None:
            return None
        return filament.count(",")

    def get_time(self):
        return self.options.get("TIME")

    def get_diameter(self, extruder=0):
        """Cura normally uses 2.85 instead of 1.75"""
        return 2.85

    def get_filament(self, extruder=None):
        fil = self.options.get("Filament used")
        if fil is None:
            return None
        filament_per_extruder = fil.split(",", 1)
        if extruder is not None:
            filament_per_extruder = filament_per_extruder[extruder:extruder+1]
        if "volumetric" in self.get_flavor().lower():
            # Strip whitespaces and mm3
            volume = sum(iter(float(f.strip()[:-3])
                              for f in filament_per_extruder))
            return self.convert_filament(volume=volume)
        else:
            length_m = sum(iter(float(f.strip(" m"))
                                for f in filament_per_extruder))
            length = length_m * 1000  # Convert to mm
            return self.convert_filament(length=length)
