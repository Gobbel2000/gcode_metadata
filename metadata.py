class Metadata:
    """High-level object containing the metadata of a G-Code file."""

    def __init__(self, parser):
        self.slicer = parser.get_slicer()
        self.flavor = parser.get_flavor()
        self.time = parser.get_time()
        self.material_density = parser.get_density()
        self.material_diameter = parser.get_diameter()
        
        filament = parser.get_filament()
        self.filament_length = filament["length"]
        self.filament_volume = filament["volume"]
        self.filament_weight = filament["weight"]
