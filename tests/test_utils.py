import pytest
import os
import ifcopenshell
import geopandas as gpd
from shapely.geometry import LineString
from src.utils import shp_to_ifc, read_shapefile, adjust_coordinates, create_ifc_file, list_numeric_fields, IFCProject


# Create a temporary directory for test inputs / outputs
@pytest.fixture(scope='session')
def input_dir():
    input_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tests/input'))
    os.makedirs(input_path, exist_ok=True)
    return input_path


@pytest.fixture(scope='session')
def output_dir():
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tests/output'))
    os.makedirs(output_path, exist_ok=True)
    return output_path


# helpers
def inspect_ifc_units(ifc_path):
    ifc_file = ifcopenshell.open(ifc_path)
    units = ifc_file.by_type("IfcUnitAssignment")
    assert units, "No units found in the IFC file."
    for unit in units:
        print(f"Units: {unit}")


def validate_ifc_structure(ifc_path):
    ifc_file = ifcopenshell.open(ifc_path)
    entities = ifc_file.by_type("IfcPipeSegment")
    assert entities, "No IfcPipeSegment entities found in the IFC file."


# Test reading shapefile
def test_read_shapefile():
    # Create a sample GeoDataFrame with LineString geometries
    gdf = gpd.GeoDataFrame(geometry=[LineString([(0, 0), (1, 1), (2, 2)])])
    gdf.to_file('../tests/input/sample_input.shp')

    # Read the shapefile
    result_gdf = read_shapefile('../tests/input/sample_input.shp')

    # Check that the geometries are LineString
    assert all(isinstance(geom, LineString) for geom in result_gdf.geometry)


# Test adjusting coordinates
def test_adjust_coordinates():
    coordinates = [(0, 0), (5, 3), (9, 4), (12, 6)]
    new_coords, arc_indices = adjust_coordinates(coordinates)

    # Check the number of new coordinates
    assert len(new_coords) == 8  # 2 new points for each inner vertex + original vertices

    # Check the arc indices
    assert arc_indices == [2, 5]  # Indices of original inner vertices in the new coordinates


# Test IFCProject methods with sample coordinates without adjusting
def test_ifc_project_with_sample_coordinates(output_dir):
    # Define sample coordinates and arc indices
    coordinates = [(0., 0., 0.), (100., 0., 0.), (171., 29., 0.), (200., 100., 0.), (200., 200., 0.), (350.,300.0,100.), (300.,350.0,100.)]
    arc_indices = [2, 5]

    # Create an IFCProject instance
    project = IFCProject()

    # Add pipe to the project using sample coordinates without adjusting
    project.add_pipe(coordinates, arc_indices)

    # Finalize the project
    project.finalize_project()

    # Write the IFC file
    output_ifc_path = os.path.join(output_dir, 'test_with_sample_coordinates.ifc')
    project.write_ifc_file(output_ifc_path)

    # Check that the IFC file was created
    assert os.path.exists(output_ifc_path)

    # Inspect the IFC file to ensure it contains unit information
    inspect_ifc_units(output_ifc_path)

    # Additional validation for the structure of the IFC file
    validate_ifc_structure(output_ifc_path)


# Test creating IFC file from shp
def test_create_ifc_file(output_dir):
    # Create a sample GeoDataFrame with LineString geometries
    gdf = gpd.GeoDataFrame(geometry=[LineString([(0, 0), (100, 50), (300, 400)])])
    gdf.to_file('../tests/input/sample_input.shp')

    # Create the IFC file
    output_ifc_path = os.path.join(output_dir, 'test.ifc')
    create_ifc_file('../tests/input/sample_input.shp', output_ifc_path)

    # Check that the IFC file was created
    assert os.path.exists(output_ifc_path)

    # Inspect the IFC file to ensure it contains unit information
    inspect_ifc_units(output_ifc_path)

    # Additional validation for the structure of the IFC file
    validate_ifc_structure(output_ifc_path)


def create_test_shapefile(filepath):
    """Create a test shapefile with a diameter field."""
    data = {
        'geometry': [
            LineString([(0., 0., 0.), (100., 0., 0.), (171., 29., 0.), (200., 100., 0.), (200., 200., 0.), (350.,300.0,100.), (300.,350.0,100.)]),
            LineString([(2, 20), (3, 35), (4, 60)])
        ],
        'diameter': [100, 500]
    }
    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
    gdf.to_file(filepath)


def test_shp_to_ifc(input_dir, output_dir):
    shp_path = os.path.join(input_dir, 'test_shapefile_field.shp')
    ifc_path = os.path.join(output_dir, 'test_output_field.ifc')

    # Create a test shapefile
    create_test_shapefile(shp_path)

    # Run the shp_to_ifc function
    shp_to_ifc(shp_path, ifc_path, 'diameter')

    # Check that the IFC file was created
    assert os.path.exists(ifc_path)

    # Check the content of the IFC file (you can expand this as needed)
    ifc_file = ifcopenshell.open(ifc_path)
    entities = ifc_file.by_type("IfcPipeSegment")
    assert len(entities) == 2
    for entity in entities:
        assert entity.Representation is not None


def test_list_numeric_fields(input_dir):
    gdf = gpd.GeoDataFrame({
        'geometry': [LineString([(-50, 0), (10, 5), (25, 40)])],
        'int_f': [1],
        'float_f': [1.1],
        'str_f': ['text']
    }, crs="EPSG:4326")
    filepath = os.path.join(input_dir, 'temp_shapefile.shp')
    gdf.to_file(filepath)

    numeric_fields = list_numeric_fields(filepath)
    assert 'int_f' in numeric_fields
    assert 'float_f' in numeric_fields
    assert 'str_f' not in numeric_fields