# Configuring processing

Let's say you have a form metadata file for your template and a populated image directory. Before you attempt to process instances of your form you will need to construct a YAML configuration file with the settings you want to use for governing the cleaning, optical character recognition (OCR) and alignment processes.

## Cleaning

`form-tools` comes with the option of specifying functions for cleansing your images before attempting matching and alignment (minimal number available at the moment). All of these functions can be found in the `form-tools.form_operators.preprocessors` module. Let's say we wanted to use the `remove_specks` function from that module, to get rid of black specks in our document, and pass the keyword argument `adaptive_thresholding=True`. In our config we would specify:

```yaml title="config.yaml"
preprocessing_transforms:
  - name: remove_specks
    kwargs:
      adaptive_thresholding: True
```

## Optical Character Recognition (OCR)

To ensure that each page in the scanned document is aligned against the correct page in the form template an OCR engine is used to extract text from the scanned document and check it against the identifiers for the form and it's pages in the form metadata. An OCR engine is also used to make sure each scanned page is rotated if it's orientation is incorrect. You can specify the OCR engine to use for both operations in the config as follows (currently only `tesseract` is supported):

```yaml title="config.yaml"
ocr_options:
  rotation_engine: tesseract
  text_extraction_engine: tesseract
```

## Alignment

The alignment process is the most complicated part of the `form-tools` configuration given that there are a number of algorithms involved in the whole process. For an overview / guide through the concepts involved in this process please refer to the [`opencv` documentation](https://docs.opencv.org/3.4/db/d27/tutorial_py_table_of_contents_feature2d.html).

### Keypoint detector

There are two keypoint detector algorithms currently supported in `form-tools`:

* [Scale Invariant Feature Transform (SIFT)](https://docs.opencv.org/3.4/da/df5/tutorial_py_sift_intro.html)
* [Oriented FAST and Rotated BRIEF (ORB)](https://docs.opencv.org/3.4/d1/d89/tutorial_py_orb.html)

Here's an example of how to set SIFT as the detector:

```yaml title="config.yaml"
detector:
   name: SIFT
```

You can optionally pass additional `opencv` arguments to be used as part of the detectors creation as follows:

```yaml
detector:
   name: SIFT
   args:
    - arg1 # These are dummy arguments for illustration
    - arg2
   kwargs:
      key: value # Dummy keyword value pair
```

### Keypoint matcher

The primary keypoint matching algorithms supported by `form-tools` are:

* Brute Force (BF)
* Fast Library for Approximate Nearest Neighbors (FLANN)

For instance, a valid configuration for implementing FLANN would be:

```yaml title="config.yaml"
matcher:
  id: FLANN
  args:
    - algorithm: 1
      trees: 5
    - check: 50
```

Other matchers can be chosen by passing the appropriate `opencv` integer value for the mather to `id` in the config. As for detectors, arguments and keyword arguments for initialising the matcher can be passed via the config file.

In addition to setting the matcher, you can also specify further parameters to determine what are 'good' matches.

* `knn`: Setting this parameter means that $k$-Nearest Neighbours will be used to return the $k$ best matches between keypoint descriptors
* `proportion`: If $proportion=p$ then either the top $100*p\text{ }\%$ matches will be used for comparison, or, if $knn\ge2$ then a keypoint $x$ will be kept only if $\text{dist}(knn_{1}(x)) < p * \text{dist}(knn_{2}(x))$.

For example, the following will ensure 2 nearest neighbours are calculated and the ratio test above is applied with a proprotion of 0.7.

```yaml title="config.yaml"
knn: 2
proportion: 0.7
```

### Homography Matrix

Once detection and matching has been completed and a final set of matches have been produced a homography matrix will be calculated, which relates the transformation between two planes, and allows us to perform perspective correction. In other words, allows us to align our scanned document to the template images so that one can be superimposed on the other with minimal observable differences. You can find out more about homography [here](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html) and [here](https://docs.opencv.org/3.4/d1/de0/tutorial_py_feature_homography.html).

In particular, the following options can be set and passed to `opencv`'s `findHomography` function under the `homography_options` parameter:

* `method`: Defaults to RANSAC if not specified
* `threshold`: Sets `ransacReprojThreshold`. Defaults to 3 if `method` has been set.

In addition, you may want to determine whether a resulting matrix shouldn't be used. This would be the case where the matrix is singular (i.e. it's collapsing space in on itself). Mathematically, this would happen when the determinant of the matrix is 0. Given that we're working with approximations, we might want to consider a matrix as being singular if it's determinant is sufficiently close to 0. For example, we might want to treat any matrix with a determinant whose absolute value is less than 0.05 as being singular. We can do this by setting the `singular_matrix_threshold` as follows:

```yaml title="config.yaml"
homography_options:
  singular_matrix_threshold: 0.05
```

This will mean if the absolute value of the determinant of a homography matrix is below 0.05 then an error will be generated and the alignment process will terminate.

## Command Line Extensions

### Output and metadata locations

The command line tool for processing a scanned form allows you to specify the metadata directory and output locations either directly in the config file or as additional options passed to the `process-form` command.

If you want to specify these locations in the config then you would do so as follows:

```yaml title="config.yaml"
pass_directory: s3://my-bucket/pass_directory
fail_directory: s3://my-bucket/fail_directory
form_metadata_directory: metadata
```

### Dealing with different file types

In some cases you might receive scanned versions of your form in different file formats which might need to be treated slightly differently. For example, you might receive one scanned form as a pdf file and another as a tif file.

The command line interface can receive a config file that provides different options for each of these file formats. For example, let's say we want to use `adaptive_thresholding` for `remove_specks` during preprocessing for tif files, but not for pdfs and that we want to use a proportion of 0.9 for matches for the former but 0.7 for the latter. Then we would write our config as follows:

```yaml title="config.yaml"
pdf:
  detector:
    name: SIFT
  matcher:
    id: FLANN
    args:
      - algorithm: 1
        trees: 5
      - check: 50
  knn: 2
  proportion: 0.9
  ocr_options:
    rotation_engine: tesseract
    text_extraction_engine: tesseract
  homography_options:
    singular_matrix_threshold: 0.05
  preprocessing_transforms:
    - name: remove_specks
      kwargs:
        adaptive_thresholding: False

tif:
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
  homography_options:
    singular_matrix_threshold: 0.05
  preprocessing_transforms:
    - name: remove_specks
      kwargs:
        adaptive_thresholding: True
```
