import ifcopenshell
import ifcopenshell.api.root
import ifcopenshell.api.unit
import ifcopenshell.api.context
import ifcopenshell.api.project
import ifcopenshell.api.spatial
import ifcopenshell.api.geometry
import ifcopenshell.api.aggregate
import ifcopenshell.util.shape_builder

import time
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString
import numpy as np


class IFCProject:
    def __init__(self):
        self.ifc_file = ifcopenshell.api.project.create_file()
        self.project = ifcopenshell.api.root.create_entity(self.ifc_file, ifc_class="IfcProject",
                                                           name="Example Project")

        # Define units
        ifcopenshell.api.unit.assign_unit(self.ifc_file)

        # Create a modeling geometry context
        self.context = ifcopenshell.api.context.add_context(self.ifc_file, context_type="Model")
        self.body_context = ifcopenshell.api.context.add_context(self.ifc_file, context_type="Model",
                                                                 context_identifier="Body", target_view="MODEL_VIEW",
                                                                 parent=self.context)

        self.creation_date = int(time.time())
        self.elements = []

    def add_pipe(self, coordinates, arc_indices=None, diameter=10):
        builder = ifcopenshell.util.shape_builder.ShapeBuilder(self.ifc_file)
        # Check if the coordinates contain z-values, default to 0 if not
        if len(coordinates[0]) == 3:
            curve_points = [(float(x), float(y), float(z)) for x, y, z in coordinates]
        else:
            curve_points = [(float(x), float(y), 0) for x, y in coordinates]

        # Create the polyline and the swept disk solid
        curve = builder.polyline(curve_points, arc_points=arc_indices)
        swept_curve = builder.create_swept_disk_solid(curve, radius=diameter / 2)

        # Create a body representation
        body = ifcopenshell.util.representation.get_context(self.ifc_file, "Model", "Body", "MODEL_VIEW")
        representation = builder.get_representation(body, swept_curve)

        # Let's create a new wall
        pipe = ifcopenshell.api.root.create_entity(self.ifc_file, ifc_class="IfcPipeSegment")

        # Assign our new body geometry back to our wall
        ifcopenshell.api.geometry.assign_representation(self.ifc_file, product=pipe, representation=representation)

        # Place our wall in the ground floor
        #ifcopenshell.api.spatial.assign_container(self.ifc_file, relating_structure=self.storey, products=[pipe])
        self.elements.append(pipe)

    def finalize_project(self):
        site = ifcopenshell.api.root.create_entity(self.ifc_file, ifc_class="IfcSite", name="Example Site")
        building = ifcopenshell.api.root.create_entity(self.ifc_file, ifc_class="IfcBuilding", name="Example Building")
        storey = ifcopenshell.api.root.create_entity(self.ifc_file, ifc_class="IfcBuildingStorey", name="Ground Floor")

        ifcopenshell.api.aggregate.assign_object(self.ifc_file, relating_object=self.project, products=[site])
        ifcopenshell.api.aggregate.assign_object(self.ifc_file, relating_object=site, products=[building])
        ifcopenshell.api.aggregate.assign_object(self.ifc_file, relating_object=building, products=[storey])
        ifcopenshell.api.spatial.assign_container(self.ifc_file, relating_structure=storey, products=self.elements)

    def write_ifc_file(self, path):
        self.ifc_file.write(path)
        print(f"IFC file created at: {path}")


def read_shapefile(shp_path):
    gdf = gpd.read_file(shp_path)
    if not all(isinstance(geom, LineString) for geom in gdf.geometry):
        raise ValueError("All geometries in the shapefile must be of type LineString")
    return gdf


def convert_to_mm(coordinates):
    """Convert coordinates from meters to millimeters and round to integers."""
    converted_coordinates = []
    for coord in coordinates:
        if len(coord) == 3:
            x, y, z = coord
            converted_coordinates.append((int(x * 1000), int(y * 1000), int(z * 1000)))
        else:
            x, y = coord
            converted_coordinates.append((int(x * 1000), int(y * 1000), 0))
    return converted_coordinates


def adjust_coordinates(coordinates, curve_distance=1.0):
    def offset_point(p1, p2, distance):
        """Returns a point offset from p2 towards p1 by the given distance."""
        vec = np.array(p2) - np.array(p1)
        vec_length = np.linalg.norm(vec)
        unit_vec = vec / vec_length
        return tuple(np.array(p2) - unit_vec * distance)

    new_coords = [coordinates[0]]
    arc_indices = []

    for i in range(1, len(coordinates) - 1):
        prev_vertex = coordinates[i - 1]
        curr_vertex = coordinates[i]
        next_vertex = coordinates[i + 1]

        before = offset_point(prev_vertex, curr_vertex, curve_distance)
        after = offset_point(next_vertex, curr_vertex, curve_distance)

        new_coords.append(before)
        new_coords.append(curr_vertex)
        arc_indices.append(len(new_coords) - 1)
        new_coords.append(after)

    new_coords.append(coordinates[-1])
    if len(new_coords[0]) == 3:
        new_coords = [(float(x), float(y), float(z)) for x, y, z in new_coords]
    else:
        new_coords = [(float(x), float(y), 0) for x, y in new_coords]
    return new_coords, arc_indices


def create_ifc_file(shp_path, ifc_path, diameter=200):
    gdf = read_shapefile(shp_path)
    project = IFCProject()

    for line in gdf.geometry:
        coordinates, arc_indices = adjust_coordinates(list(line.coords), curve_distance=5)
        project.add_pipe(convert_to_mm(coordinates), arc_indices, diameter)

    project.finalize_project()
    project.write_ifc_file(ifc_path)


def list_numeric_fields(shp_file):
    """List all numeric fields (int/float) in the shapefile."""
    gdf = gpd.read_file(shp_file)
    numeric_fields = []
    for column, dtype in gdf.dtypes.items():
        print(f"Column: {column}, Dtype: {dtype}")  # Debugging line
        if pd.api.types.is_numeric_dtype(dtype):
            numeric_fields.append(column)
    return numeric_fields


def shp_to_ifc(shp_file, ifc_file, diameter_field):
    gdf = read_shapefile(shp_file)
    project = IFCProject()

    for _, row in gdf.iterrows():
        line = row.geometry
        diameter = row[diameter_field]
        coordinates, arc_indices = adjust_coordinates(list(line.coords), curve_distance=5)
        project.add_pipe(convert_to_mm(coordinates), arc_indices, diameter)

    project.finalize_project()
    project.write_ifc_file(ifc_file)
