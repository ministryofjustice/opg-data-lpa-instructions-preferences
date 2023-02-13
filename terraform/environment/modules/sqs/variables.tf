variable "alarm_actions_enabled" {
  description = "If when an alarm is triggered, it should alert real people via pagerduty."
  type        = bool
  default     = true
}

variable "name" {
  description = "This is the human-readable name of the queue. If omitted, Terraform will assign a random name."
  type        = string
  default     = null
}

variable "message_retention_seconds" {
  description = "The number of seconds Amazon SQS retains a message. Integer representing seconds, from 60 (1 minute) to 1209600 (14 days)"
  type        = number
  default     = 1209600
}

variable "visibility_timeout_seconds" {
  description = "The visibility timeout for the queue. An integer from 0 to 43200 (12 hours)"
  type        = number
  default     = 30
}

variable "fifo_queue" {
  description = "Boolean designating a FIFO queue"
  type        = bool
  default     = true
}

variable "content_based_deduplication" {
  description = "Enables content-based deduplication for FIFO queues"
  type        = bool
  default     = true
}

variable "kms_master_key_id" {
  description = "The ID of an AWS-managed customer master key (CMK) for Amazon SQS or a custom CMK"
  type        = string
  default     = "alias/aws/sqs"
}

variable "kms_data_key_reuse_period_seconds" {
  description = "The length of time, in seconds, for which Amazon SQS can reuse a data key to encrypt or decrypt messages before calling AWS KMS again. An integer representing seconds, between 60 seconds (1 minute) and 86,400 seconds (24 hours)"
  type        = number
  default     = 300
}

variable "max_message_size" {
  description = "The limit of how many bytes a message can contain before Amazon SQS rejects it. An integer from 1024 bytes (1 KiB) up to 262144 bytes (256 KiB)"
  type        = number
  default     = 262144
}


variable "redrive_policy" {
  description = "The JSON policy to set up the Dead Letter Queue, see AWS docs. Note: when specifying maxReceiveCount, you must specify it as an integer (5), and not a string (\"5\")"
  type        = string
  default     = ""
}

variable "alarm_sns_topic_arn" {
  description = "ARN of the SNS topic for alarm notifications"
  default     = ""
}

variable "allowed_arn_list" {
  description = "List of ARNs allowed to access the queue"
  type        = list(string)
}

variable "enable_message_age_alarm" {
  description = "Boolean to enable an alarm when there's a message older than the threshold"
  type        = bool
  default     = false
}

variable "message_age_alarm_threshold" {
  description = "The age in seconds of a message that should trigger the alarm"
  type        = number
  default     = 86400
}
