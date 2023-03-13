resource "aws_service_discovery_private_dns_namespace" "lpa_iap" {
  name = "lpa-iap-${var.environment}.ecs"
  vpc  = var.vpc_id
}

resource "aws_service_discovery_service" "lpa_iap_mock_sirius" {
  name = "mock-sirius"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.lpa_iap.id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }

  force_destroy = true
}
