# Infraestructura de ejemplo para "Orders API" - usa LocalStack, no AWS real.
# Para correr LocalStack: docker run -d -p 4566:4566 localstack/localstack

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
  # Credenciales ficticias que LocalStack acepta. Contra AWS real no van en el código:
  # se toman del entorno (perfil SSO / rol de CI).
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3  = "http://localhost:4566"
    kms = "http://localhost:4566"
  }
}

# Llave KMS administrada por el equipo para cifrar los reportes (con rotación anual).
resource "aws_kms_key" "orders_reports" {
  description             = "Cifrado de reportes de órdenes (orders-reports-bucket)"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

# Bucket donde se guardan los reportes de órdenes generados por el worker.
# Los reportes contienen datos de clientes: el bucket es privado y cifrado.
# Logging de acceso omitido en el lab: requiere un bucket de logs dedicado.
#trivy:ignore:AWS-0089
resource "aws_s3_bucket" "orders_reports" {
  bucket = "orders-reports-bucket"
}

# Desactiva las ACLs: el acceso se controla solo con IAM y bucket policy.
resource "aws_s3_bucket_ownership_controls" "orders_reports" {
  bucket = aws_s3_bucket.orders_reports.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Bloquea cualquier exposición pública, aunque alguien agregue luego una ACL o policy pública.
resource "aws_s3_bucket_public_access_block" "orders_reports" {
  bucket                  = aws_s3_bucket.orders_reports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "orders_reports" {
  bucket = aws_s3_bucket.orders_reports.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.orders_reports.arn
    }
    bucket_key_enabled = true
  }
}

# Versionado habilitado para poder recuperar reportes sobrescritos o borrados por error.
resource "aws_s3_bucket_versioning" "orders_reports_versioning" {
  bucket = aws_s3_bucket.orders_reports.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Controla el costo del versionado: las versiones anteriores expiran a los 90 días.
resource "aws_s3_bucket_lifecycle_configuration" "orders_reports" {
  bucket = aws_s3_bucket.orders_reports.id
  rule {
    id     = "expirar-versiones-anteriores"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
  depends_on = [aws_s3_bucket_versioning.orders_reports_versioning]
}

# Rechaza cualquier request que no use TLS.
data "aws_iam_policy_document" "orders_reports_tls_only" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.orders_reports.arn,
      "${aws_s3_bucket.orders_reports.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "orders_reports" {
  bucket     = aws_s3_bucket.orders_reports.id
  policy     = data.aws_iam_policy_document.orders_reports_tls_only.json
  depends_on = [aws_s3_bucket_public_access_block.orders_reports]
}
