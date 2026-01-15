# Extracting metadata from a template

Identifying bounding boxes for a form template is a difficult task to do manually. `form-tools` therefore comes with extractors (currently only for enriched pdf templates) to create and pre-populate `FormMetadata` compliant JSON files with field names and bounding box properties, as well as create a compatible form template image directory.

!!! note
    The output metadata will not be able to be used immediately to align a scanned image to the template as the `form_identifier` key and `identifier` key for each `form_page` in the metadata will need to be populated with a valid regular expression so that the correct page in the scanned image can be compared with the correct page in the template images.

## PDF Extractor

### Command Line

#### **General**

Say you have a enriched pdf form template `my_form.pdf`. To create a `FormMetadata` compliant JSON file `my_form_meta.json` and a corresponding form template image directory `template_images` from the command line you would run:

```
form-tools extract-meta my_form.pdf my_form_meta.json --form-image-directory template_images
```

More generally, you would run:

```
form-tools extract-meta form-template-path output-path [OPTIONS]
```

#### **Options**

| Name        | Type | Description | Default |
| ----------- | :----: | ----------- | :-------: |
| --extractor | `str` | Extractor to use (e.g. pdf). Currently only supports pdf. | `pdf` |
| --extractor-options | `key-value` (e.g. `key1=value1 key2=value2`) | Key-value pairs as options for instantiating the extractor class. See python API usage below for more information. | `None` |
| --pages-to-keep | `int` | List of page numbers from the form template to process. **Note**: In the generated form template image directory the first page listed will be stored as page 1. The second will be stored as page 2 etc. | `None` |
| --form-image-directory | `str` | Directory path for storing template page images. **Note**: If not specified, images will be stored in a temporary directory and will not be available for further processing. | `None` |
| --form-image-directory-overwrite | `bool` | Set to `True` to overwrite the image directory if it already exists. | `False` |

### Python API

You can also implement the above functionality directly in Python. To do so, you'll need to make use of the `PdfFormMetaExtractor` class. Under the hood, the extractor uses
`pdf2image.convert_from_bytes` to convert the pdf to a series of images, and you can pass options to it when initialising the extractor.

```py
from form_tools.form_meta.extractors.pdf_form_extractor import PdfFormMetaExtractor

# Instantiate extractor with base settings
pfme = PdfFormMetaExtractor()

# Instantiate extractor with custom
# `pdf2image` dpi setting to 400
pfme = PdfFormMetaExtractor(
    dpi=400
)
```

You can then use the initialised extractor to generate metadata for the template:

```py
# Create FormMetadata object and populate
# image directory template_images
form_metadata = pfme.extract_meta(
    form_template_path="my_form.pdf",
    form_image_dir="template_images"
)

# Write FormMetadata to json file
form_metadata.to_json(
    "my_form_meta.json",
)
```

See the [API documentation](../api/extractors/pdf.md) for further options to pass to `extract_meta`.
