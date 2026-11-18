variable "region" {
  description = "Region de AWS"
  type        = string
  default     = "us-east-1"
}

variable "ami" {
  description = "ID de la AMI (Ubuntu Server 24.04 LTS)"
  type        = string
}

variable "instance_type" {
  description = "Tipo de instancia EC2"
  type        = string
  default     = "t2.micro"
}

variable "instance_name" {
  description = "Nombre (tag Name) de la instancia"
  type        = string
  default     = "practica06-terraform"
}

variable "key_name" {
  description = "Nombre del Key Pair existente en AWS"
  type        = string
  default     = "practica04"
}