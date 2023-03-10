//===== Reference Zones from management =====

data "aws_route53_zone" "environment_cert" {
  name     = "${local.account.opg_hosted_zone}."
  provider = aws.management
}

//===== Create certificates for sub domains =====

resource "aws_acm_certificate" "environment_cert" {
  count                     = local.branch_build_flag ? 0 : 1
  domain_name               = "*.${data.aws_route53_zone.environment_cert.name}"
  validation_method         = "DNS"
  subject_alternative_names = [data.aws_route53_zone.environment_cert.name]
  lifecycle {
    create_before_destroy = true
  }
}

data "aws_acm_certificate" "environment_cert" {
  count       = local.branch_build_flag ? 1 : 0
  domain      = "*.${trimsuffix(data.aws_route53_zone.environment_cert.name, ".")}"
  types       = ["AMAZON_ISSUED"]
  most_recent = true
}

resource "aws_route53_record" "validation" {
  count    = local.branch_build_flag ? 0 : 1
  name     = sort(aws_acm_certificate.environment_cert[0].domain_validation_options[*].resource_record_name)[0]
  type     = sort(aws_acm_certificate.environment_cert[0].domain_validation_options[*].resource_record_type)[0]
  zone_id  = data.aws_route53_zone.environment_cert.id
  records  = [sort(aws_acm_certificate.environment_cert[0].domain_validation_options[*].resource_record_value)[0]]
  ttl      = 60
  provider = aws.management
}

//===== Create A records =====

resource "aws_route53_record" "environment_record" {
  name     = local.a_record
  type     = "A"
  zone_id  = data.aws_route53_zone.environment_cert.id
  provider = aws.management

  alias {
    evaluate_target_health = true
    name                   = aws_api_gateway_domain_name.lpa_iap.regional_domain_name
    zone_id                = aws_api_gateway_domain_name.lpa_iap.regional_zone_id
  }
}
