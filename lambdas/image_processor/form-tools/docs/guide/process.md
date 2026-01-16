# Process a scanned form

The below assumes that you've created a valid [form metadata](metadata.md) for your form
with a corresponding form template image directory and a valid [configuration](config.md) file
ready for processing your scanned document(s).

## Command Line

### General

To process a given scanned document from the command line you would run:

```
form-tools process-form form-path config [OPTIONS]

```

where:

* `form-path` is the local or S3 path to the scanned document you want to process
* `config` is the local path to the YAML config file to be used for processing

### Options

| Name        | Type | Description | Default |
| ----------- | :----: | ----------- | :-------: |
| `--pass-directory` | `str` | Local or S3 path to the directory for storing outputs for a successfully processed form. Will override the pass directory specified in the config if provided. | `None` |
| `--fail-directory` | `str`| Local or S3 path to the directory for storing copies of a scanned form which failed processing. Will override the fail directory specified in the config if provided. | `None` |
| `--form-metadata-directory` | `str` | Local path to form metadata directory. Will override the form metadata directory specified in the config if provided. | `None` |
| `--return-as-bytes` | `bool` | Will store processed form field images as bytes in a parquet dataset if set to true. | `False` |
| `--encode-type` | `str` | Image encoding type / image suffix (e.g. .jpg, .png) for storing field images. | `.jpg` |

## Python API

The main class to use for processing a form directly in Python is the `FormOperator` class. The easiest way of instantiating an operator is by using the `create_from_config` method.

```py
from form_tools.form_operators import FormOperator

form_operator = FormOperator.create_from_config("config.yaml")
```

You can then use the [`run_full_pipeline`](../api/form_operator_classes/form_operator.md#form_tools.form_operators.form_operator.FormOperator.run_full_pipeline) method to apply the cleaning, OCR and alignment steps as configured in your config file.

```py
_ = form_operator.run_full_pipeline(
    form_path="my_scanned_form.pdf",
    pass_dir="s3://my-bucket/pass_directory",
    fail_dir="s3://my-bucket/fail_directory",
    form_meta_directory="metadata",
)
```

Optionally, you can also pass an additional keyword argument `debug=True` to `run_full_pipeline`. This will result in `opencv` generating images of the keypoint matches and aligned images during the run. You will need to press the down arrow key to progress through the code execution so only use this when experimenting locally.

## Outputs

Outputs will be partitioned in your pass directory at `run=timestamp/meta=meta_id/field_name=field/` if outputs have been chosen to be stored as image thumbnails or at `run=timestamp/meta=meta_id/` if they have been chosen to be stored as binary in a parquet file.
