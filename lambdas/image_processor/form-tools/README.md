# form-tools

The raw data for many case management and data systems exist as paper forms. `form-tools` is a package to help with preprocessing scanned images of these paper forms for further analysis and / or processing. It does this by making use of a template for the form to match and align scanned versions of the document to it, before taking thumbnails of the fields in the scanned document.

## Before you begin

* `form-tools` makes use of the [`pdf2image`](https://github.com/Belval/pdf2image) package for converting document images stored as pdf to image files. As such, you'll need to install `poppler`. See the `pdf2image` readme for guidance on how to do so.
* The current default OCR engine for matching pages in a form template to its scanned image is [`tesseract`](https://github.com/tesseract-ocr/tesseract). Please follow the instructions at the link for how to install it.
* Computer vision is performed by using the `opencv` library. This project makes use of the pre-compiled python library for `opencv` which will be installed by default but you may wish to install `opencv` from source instead.

On Ubuntu, you can install all the necessary packages by running

```
sudo apt-get install tesseract-ocr libtesseract-dev libleptonica-dev pkg-config poppler-utils
```

You will also need to specify the location of the test data for tesseract before using the library. You can do this by setting the `TESSDATA_PREFIX` environment variable. To locate the tessdata directory on a mac run `brew list tesseract`. On linux the data should be located at `/usr/share/tesseract-ocr/4.00/tessdata/`.

## Installation

To install the library run:

```
pip install form-tools
```

## Basic use

### Extracting form metadata

Say you have a form with a pdf template `my_form.pdf`. To pre-process scanned copies of the form you'll first need to create an image directory for your template as well as a `FormMetadata` compliant json file.

To do this from the command line and output the metadata to `my_form_meta.json` and your images to a directory `template_images` you would run:

```
form-tools extract-meta my_form.pdf my_form_meta.json --form-image-directory template_images
```

To interact with the API directly in python you should use the built in `PdfFormMetaExtractor` class.

```py
from form_tools.form_meta.extractors.pdf_form_extractor import PdfFormMetaExtractor

# Instantiate extractor
pfme = PdfFormMetaExtractor()

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

The output metadata should contain bounding box coordinates for each field in the form that correspond to regions in the images outputted to `template_images`.

**Note**: The output metadata will not be able to be used immediately to align a scanned image to the template as the `form_identifier` key and `identifier` key for each `form_page` in the metadata will need to be populated with a valid regular expression so that the correct page in the scanned image can be compared with the correct page in the template images.

### Aligning scanned images to a template

Once you have a complete form metadata file for your template and a populated image directory you can attempt to align a scanned form, say `my_scanned_form.pdf` to the template and extract field thumbnails.

You will first need to prepare a config file to specify the `opencv` algorithms to use for the alignment process. An example `config.yaml` would be as follows:

```yaml
detector:
  name: SIFT
matcher:
  id: FLANN
  args:
    - algorithm: 1
      trees: 5
    - check: 50
knn: 2
proportion: 0.7
ocr_options:
  rotation_engine: tesseract
  text_extraction_engine: tesseract
pass_directory: s3://my-bucket/pass_directory
fail_directory: s3://my-bucket/fail_directory
form_metadata_directory: metadata
```

This config specifies that the `SIFT` algorithm should be used for keypoint detection and the `FLANN` algorithm should be used for keypoint matching, with 70% of the best keypoints kept (using KNN to decide on which of these are best). Also, note that we've put the output metadata in a `metadata` subdirectory in our working directory.

To align the scanned image from the command line you would then run:

```
form-tools process-form my_scanned_form.pdf config.yaml
```

To interact with the API directly in python you would use the `FormOperator` class.


> **Note**: The scanned image could be stored in an AWS S3 bucket. In that case you would pass the S3 path (e.g. `s3://my-bucket/my_scanned_form.pdf`). Only the config and metadata directory need to be located in your local working directory.

## Running documentation locally

`mkdocs` is used to document `form-tools`. To run the documentation locally, run `mkdocs serve` on the command line and follow the link to the local host.
