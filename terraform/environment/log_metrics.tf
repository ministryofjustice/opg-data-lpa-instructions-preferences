resource "aws_cloudwatch_log_metric_filter" "pdf_sizes_bytes" {
  name           = "PDF Sizes (Bytes)"
  pattern        = { $.pdf_size == "*" }
  log_group_name = aws_cloudwatch_log_group.lambda.name

  metric_transformation {
    name          = "PDFSize"
    namespace     = "IaPPDFStatistics"
    value         = $.pdf_size
    unit          = "bytes"
  }
}


resource "aws_cloudwatch_log_metric_filter" "pdf_length_pages" {
  name           = "PDF Length (Pages)"
  pattern        = { $.pdf_length == "*" }
  log_group_name = aws_cloudwatch_log_group.lambda.name

  metric_transformation {
    name          = "PDFLength"
    namespace     = "IaPPDFStatistics"
    value         = $.pdf_length
  }
}
