from form_tools.form_operators import FormOperator

form_operator = FormOperator.create_from_config(f"extraction/opg-config.yaml")

_ = form_operator.run_full_pipeline(
    form_path="extraction/LP1H-Scan.pdf",
    pass_dir=f"extraction/pass",
    fail_dir=f"extraction/fail",
    form_meta_directory=f"extraction/metadata",
)
