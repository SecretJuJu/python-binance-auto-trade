# Secrets Manager Secret Version (actual values)
resource "aws_secretsmanager_secret_version" "binance_credentials" {
  count     = var.binance_api_key != "" && var.binance_secret != "" ? 1 : 0
  secret_id = aws_secretsmanager_secret.binance_credentials.id
  secret_string = jsonencode({
    api_key = var.binance_api_key
    secret  = var.binance_secret
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
} 