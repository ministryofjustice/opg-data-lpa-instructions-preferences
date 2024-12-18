variable "bucket_name" {
  description = "Name of the bucket."
  type        = string
}

variable "account_name" {
  description = "Account friendly that the current environment resides in."
  type        = string
}

variable "force_destroy" {
  description = " A boolean that indicates all objects should be deleted from the bucket so that the bucket can be destroyed without error. These objects are not recoverable."
  default     = false
  type        = bool
}

variable "block_public_acls" {
  description = "Whether Amazon S3 should block public ACLs for this bucket."
  default     = true
  type        = bool
}

variable "block_public_policy" {
  description = "Whether Amazon S3 should block public bucket policies for this bucket."
  default     = true
  type        = bool
}

variable "ignore_public_acls" {
  description = "Whether Amazon S3 should ignore public ACLs for this bucket."
  default     = true
  type        = bool
}

variable "restrict_public_buckets" {
  description = "Whether Amazon S3 should restrict public bucket policies for this bucket. Enabling this setting does not affect the previously stored bucket policy, except that public and cross-account access within the public bucket policy, including non-public delegation to specific accounts, is blocked."
  default     = true
  type        = bool
}

variable "kms_key_id" {
  description = "kms key to encrypt s3 bucket with"
  type        = string
}

variable "enable_lifecycle" {
  description = "Set to true to delete items in the bucket after 6 months."
  default     = false
  type        = bool
}

variable "expiration_days" {
  description = "Number of days to expire the items in the bucket. Only takes effect when enable_lifecycle is set to true."
  default     = "1825"
  type        = string
}

variable "non_current_expiration_days" {
  description = "Lifecycle expiration days for non current version"
  default     = "365"
  type        = string
}
