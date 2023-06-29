resource "aws_cloudwatch_log_metric_filter" "pdf_sizes_bytes" {
  name           = "PDF Sizes (Bytes)"
  pattern        = "{ $.pdfSize == \"*\" }"
  log_group_name = module.processor_lamdba.lambda_log.name

  metric_transformation {
    name      = "PDFSize"
    namespace = "IaPPDFStatistics"
    value     = "$.pdfSize"
    unit      = "Bytes"
    dimensions = {
      pdf_size = "$.pdfSize"
    }
  }
}


resource "aws_cloudwatch_log_metric_filter" "pdf_length_pages" {
  name           = "PDF Length (Pages)"
  pattern        = "{ $.pdfLength == \"*\" }"
  log_group_name = module.processor_lamdba.lambda_log.name

  metric_transformation {
    name      = "PDFLength"
    namespace = "IaPPDFStatistics"
    value     = "$.pddLength"
    dimensions = {
      pdf_length = "$.pdfLength"
    }

  }
}
