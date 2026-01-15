import os
import sys
import yaml
import argparse
import importlib

from pathlib import Path
from pydantic import BaseModel

from . import __version__ as v
from .form_operators import FormOperator


class CommandLineConfig(BaseModel):
    pass_directory: str
    fail_directory: str
    form_metadata_directory: str


class keyvalue(argparse.Action):
    # Constructor calling
    def __call__(
        self,
        parser,
        namespace,
        values,
        option_string=None,
    ):
        setattr(namespace, self.dest, dict())

        for value in values:
            # split it into key and value
            key, value = value.split("=")
            # assign into dictionary
            getattr(namespace, self.dest)[key] = value


class Main(object):
    def __init__(self):
        HERE = os.getcwd()
        sys.path.insert(0, HERE)

        parser = argparse.ArgumentParser(
            description="Runs variours form tools from the command line",
            usage="""<command> [<args>]\n\n
            commands:\n
            process-form        Use a valid form-tools config and form metadata to\n
                                extract and save field thumbnails from a form
            extract-meta        Extracts form-metadata from a form template
            """,
        )

        parser.add_argument("command", help="Subcommand to run")

        parser.add_argument(
            "-v",
            "--version",
            action="version",
            version="%(prog)s {version}".format(version=v),
        )

        args = parser.parse_args(sys.argv[1:2])

        if not hasattr(self, args.command.replace("-", "_")):
            parser.print_help()
            exit(1)

        getattr(self, args.command.replace("-", "_"))()

    def process_form(self):
        parser = argparse.ArgumentParser(
            description=(
                "Use a valid form-tools config and form metadata\n"
                "to extract and save field thumbnails from a form"
            )
        )

        parser.add_argument("form-path", type=str, help="Local or S3 path to form")
        parser.add_argument(
            "config", type=str, help="Local path to config for form operator"
        )

        parser.add_argument(
            "--pass-directory",
            type=str,
            help="Local or S3 path to directory for storing outputs",
        )
        parser.add_argument(
            "--fail-directory",
            type=str,
            help="Local or S3 path to directory for storing outputs",
        )
        parser.add_argument(
            "--form-metadata-directory",
            type=str,
            help="Local path to form metadata directory",
        )
        parser.add_argument(
            "--return-as-bytes",
            type=bool,
            default=False,
            help="Store processed form field images as bytes in a parquet dataset",
        )
        parser.add_argument(
            "--encode-type",
            type=str,
            default=".jpg",
            help=(
                "Image encoding type / image suffix "
                "(e.g. .jpg, .png) for storing field images"
            ),
        )
        parser.add_argument(
            "--debug",
            type=bool,
            default=False,
            help="Whether to output processing imaging steps",
        )

        args = parser.parse_args(sys.argv[2:])

        config_path = Path(args.config)
        if config_path.suffix in [".yml", ".yaml"]:
            with open(config_path, "r") as f:
                raw_config = yaml.safe_load(f)

        else:
            raise ValueError("Config path should be to a yaml file")

        form_path = getattr(args, "form-path")
        form_path_suffix = Path(form_path).suffix.replace(".", "")

        config = (
            raw_config[form_path_suffix]
            if form_path_suffix in raw_config
            else raw_config
        )

        form_operator = FormOperator.create_from_config(config)

        pass_directory = (
            args.pass_directory
            if not None
            else CommandLineConfig(**config).pass_directory
        )
        fail_directory = (
            args.fail_directory
            if not None
            else CommandLineConfig(**config).fail_directory
        )
        form_meta_directory = (
            args.form_metadata_directory
            if not None
            else CommandLineConfig(**config).form_metadata_directory
        )

        _ = form_operator.run_full_pipeline(
            form_path=form_path,
            pass_dir=pass_directory,
            fail_dir=fail_directory,
            form_meta_directory=form_meta_directory,
            as_bytes=args.return_as_bytes,
            encode_type=args.encode_type,
            debug=args.debug,
        )

    def extract_meta(self):
        parser = argparse.ArgumentParser(
            description=(
                "Use a valid form-tools config and form metadata\n"
                "to extract and save field thumbnails from a form"
            )
        )

        parser.add_argument(
            "form-template-path", type=str, help="Local path to form template document"
        )
        parser.add_argument(
            "output-path", type=str, help="Local path for form meta output"
        )

        parser.add_argument(
            "--extractor",
            type=str,
            default="pdf",
            help="Extractor to use (e.g. pdf). Currently only supports pdf.",
        )
        parser.add_argument(
            "--extractor-options",
            nargs="*",
            action=keyvalue,
            help="Options for instanitating extractor class as key-value pairs",
        )
        parser.add_argument(
            "--pages-to-keep",
            type=int,
            nargs="*",
            default=None,
            help="Pages of template to keep / store in metadata",
        )
        parser.add_argument(
            "--form-image-directory",
            type=str,
            help="Directory to store the template page images",
        )
        parser.add_argument(
            "--form-image-directory-overwrite",
            type=bool,
            default=False,
            help="Set to `True` to overwrite the image directory if it already exists",
        )

        args = parser.parse_args(sys.argv[2:])

        module_name = args.extractor.lower() + "_form_extractor"
        module = importlib.import_module(
            f"form_tools.form_meta.extractors.{module_name}"
        )

        class_name = (
            args.extractor[0].upper() + args.extractor[1:].lower() + "FormMetaExtractor"
        )
        extractor_options = (
            {} if args.extractor_options is None else args.extractor_options
        )
        extractor_class = getattr(module, class_name)
        extractor = extractor_class(**extractor_options)

        meta = extractor.extract_meta(
            form_template_path=getattr(args, "form-template-path"),
            pages_to_keep=args.pages_to_keep,
            form_image_dir=args.form_image_directory,
            form_image_dir_overwrite=args.form_image_directory_overwrite,
        )

        _ = meta.to_json(getattr(args, "output-path"), indent=4)
