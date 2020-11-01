import copy

class Metadata:
    """High-level object containing the metadata of a G-Code file."""

    def __init__(self, parser):
        """parser should be a subclass of BaseParser"""
        self.slicer = parser.get_slicer()
        self.flavor = parser.get_flavor()
        self.time = parser.get_time()
        self.material_density = parser.get_density()
        self.material_diameter = parser.get_diameter()
        
        filament = parser.get_filament()
        self.filament_length = filament["length"]
        self.filament_volume = filament["volume"]
        self.filament_weight = filament["weight"]

    def get_dict(self):
        return copy.copy(self.__dict__)

    def __str__(self):
        data = {k: v for k, v in self.__dict__.items()
                if not k.startswith("_")}
        longest_key = max(len(k) for k in data)
        lines = []
        for k, v in data.items():
            lines.append(k + ":" + " "*(longest_key + 1 - len(k)) + str(v))
        return "\n".join(lines)
