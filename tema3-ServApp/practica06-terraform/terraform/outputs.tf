output "ip_publica" {
  description = "IP publica de la instancia"
  value       = aws_instance.servidor.public_ip
}

output "id_instancia" {
  description = "ID de la instancia EC2"
  value       = aws_instance.servidor.id
}