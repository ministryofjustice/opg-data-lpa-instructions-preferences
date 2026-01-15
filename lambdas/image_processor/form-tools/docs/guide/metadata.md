# Using and creating metadata for your form

To use the preprocessing functionality of `form-tools` you will first need
metadata to represent your form template. JSON metadata compliant with `form-tools`
can be created with the tools in `form_tools.form_meta`.

## Basic use

The `FormMetadata` class is used to represent `form-tools` compliant form template metadata.
The class is built on top of the existing `Metadata` class in the [`mojap-metadata`](https://github.com/moj-analytical-services/mojap-metadata) package and therefore inherits most of the functionality from
that class. For example, to create a blank JSON template for your metadata you could run:

```py
from form_tools.form_meta import FormMetadata

meta = FormMetadata()

_ = meta.to_json(
    "blank_template.json",
    indent=4,
)
```

This will generate the following JSON file:

```json
{
    "$schema": "https://moj-analytical-services.github.io/metadata_schema/mojap_metadata/v1.3.0.json",
    "name": "",
    "description": "",
    "file_format": "",
    "sensitive": false,
    "columns": [],
    "primary_key": [],
    "partitions": [],
    "form_pages": [],
    "form_formats": null,
    "form_identifier": "",
    "from_template": "",
    "excluded_sections": null
}
```

Or, if you already have a compliant metadata file `template.json` you can load it in by running:

```py
from form_tools.form_meta import FormMetadata

meta = FormMetadata.from_json("template.json")
```

## Form Fields

A key difference between the base `Metadata` class and the `FormMetadata` class is what is included in the `columns` property. In the base `Metadata` class all that's expected is the name of a particular column in a dataset along with it's corresponding data type. For form metadata however, we also require information on where the field is located on a page and which is the corresponding page of the template. We indicate this by specifying `bounding_box` and `page_number` properties for each field / column:

```json
"columns": [
    {
        "name": "my_string_field",
        "page_number": 1,
        "bounding_box": {
            "left": 100,
            "width": 100,
            "top": 600,
            "height": 20
        },
        "type": "string"
    }
]
```

!!! note
    Bounding box coordinates assume the origin is the top-left hand corner of the form page image. So, to specify a bounding box of size 10 x 10 at top left hand corner you would set `left=0, top=0, width=10, height=10`.

Form fields can be accessed and updated using the `FormMetadata` class. For instance, to add the above column as a field into a blank template you could run the following:

```py
from form_tools.form_meta import FormMetadata

meta = FormMetadata()

new_field = {
    "name": "my_string_field",
    "page_number": 1,
    "bounding_box": {
        "left": 100,
        "width": 100,
        "top": 600,
        "height": 20
    },
    "type": "string"
}

existing_fields = meta.form_fields
existing_fields.append(new_field)

# To set fields you will need to update the columns
# property not form_fields as it is read only
meta.columns = existing_fields

# Print new fields
meta.form_fields
```

You can then access the new form field and its properties by name.

```py
my_string_field = meta.form_field("my_string_field")

# Print page number for field
my_string_field.page_number

# Get left bounding box coordinate
my_string_field.bounding_box.left

# Get bounding box dictionary
my_string_field.bounding_box.to_dict()
```

## Form Pages

For your template's metadata you will also be expected
to provide information for each page against the `from_pages`
property e.g.

```json
"form_pages": [
    {
        "page_number": 1,
        "identifier": "first page",
        "required": true,
        "duplicates": false
    },
    {
        "page_number": 2,
        "identifier": "second page",
        "required": true,
        "duplicates": false
    }
]
```

where:

* `page_number`: This should be the number corresponding
    to the image for the page as found in the form template
    image directory (more on that below)
* `identifier`: This should be a valid regular expression
    that can be used to identify whether the text stripped from an image using optical character recognition (OCR) is a
    page in the given form
* `required`: Indicates whether the page needs to be present
    in a given document to count as a valid form
* `duplicates`: Indicates whether a document is allowed to have
    multiple instances of the same page

As with form fields, form pages can be set via and their properties accessed via the python API:

```py
pages = [
    {
        "page_number": 1,
        "identifier": "first page",
        "required": True,
        "duplicates": False
    },
    {
        "page_number": 2,
        "identifier": "second page",
        "required": True,
        "duplicates": False
    }
]

meta.form_pages = pages

# Get first page
first_page = meta.form_page(1)

# Get the first page's identifier
first_page.identifier
```

!!! warning
    Your metadata should have form pages listed for each page referenced in its form fields.

## Form Properties

Form metadata files are also expected to include a number of high level properties which can also be set via the python API.

* `form_formats`: A list of valid file formats for the scanned forms (e.g. pdf, tif)
* `form_identifier`: A regular expression that identifies a document as a candidate for being an instance of a form from the
text extracted from its pages
* `form_template`: Path to local directory containing the form templates images (an image per page)
* `excluded_sections`: A list of regular expressions to use to discount a document as being an instance of a form from it's extracted text
