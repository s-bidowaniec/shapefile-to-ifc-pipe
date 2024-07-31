import os
import gooey
from gooey import Gooey, GooeyParser
from utils import shp_to_ifc, list_numeric_fields


@Gooey(
    program_name="Shapefile to IFC Converter",
    program_description="Convert a Shapefile to an IFC file with specified pipe diameter field",
    default_size=(800, 600)
)
def main():
    parser = GooeyParser(description="Shapefile to IFC Converter")

    parser.add_argument('shp_path', widget='FileChooser', help='Path to the input Shapefile')
    parser.add_argument('ifc_path', widget='FileSaver', help='Path to save the output IFC file')
    parser.add_argument('diameter_field', help='Field name in the Shapefile that contains the diameter of the pipes')

    args = parser.parse_args()

    # Validate the diameter field
    numeric_fields = list_numeric_fields(args.shp_path)
    if args.diameter_field not in numeric_fields:
        raise ValueError(f"The field '{args.diameter_field}' does not exist or is not numeric in the shapefile.")

    # Run the conversion
    shp_to_ifc(args.shp_path, args.ifc_path, args.diameter_field)

if __name__ == '__main__':
    main()
