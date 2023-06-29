resource "aws_cloudwatch_log_metric_filter" "pdf_sizes_bytes" {
  name           = "PDF Sizes (Bytes)"
  pattern        = "{ $.pdfSize = \"*\" }"
  log_group_name = module.processor_lamdba.lambda_log.name

  metric_transformation {
    name      = "PDFSize"
    namespace = "IaP/PDFStatistics"
    value     = "$.pdfSize"
    unit      = "Bytes"
    dimensions = {
      pdfSize = "$.pdfSize"
    }
  }
}


resource "aws_cloudwatch_log_metric_filter" "pdf_length_pages" {
  name           = "PDF Length (Pages)"
  pattern        = "{ $.pdfLength = \"*\" }"
  log_group_name = module.processor_lamdba.lambda_log.name

  metric_transformation {
    name      = "PDFLength"
    namespace = "IaP/PDFStatistics"
    value     = "$.pdfLength"
    dimensions = {
      pdfLength = "$.pdfLength"
    }

  }
}
