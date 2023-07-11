resource "aws_cloudwatch_query_definition" "iap_count_by_status" {
  name         = "Instructions-and-Preferences/Count-By-Status"
  query_string = <<EOF
# Used to report on the success failure rate of document processing
fields status, @timestamp, @message
| filter ispresent(status)
| stats count(*) by status
| sort @timestamp asc
EOF
}


resource "aws_cloudwatch_query_definition" "iap_error_messages" {
  name         = "Instructions-and-Preferences/Failed-Cases"
  query_string = <<EOF
# Used to report on which case numbers have failed and the reasons for that failure
# which is then followed up manually
# This can be exported as a xlsx doc directly for eases 
fields @timestamp, coalesce(@requestId, request_id) as RequestID
| filter @message like 'ERROR'
| parse @message 'document_templates": [*]' as docs
| parse @message 'matched_templates": [*]' as matched
| parse @message 'ERROR - * *' as pre, error
| sort @timestamp asc, RequestID asc
| stats latest(@timestamp) as Time, latest(uid) as CaseNumber, latest(error) as ReasonFailed, latest(docs) as DocumentTemplates, latest(matched) as MatchedTemplates by RequestID
| display fromMillis(Time) as TimeStamp, CaseNumber, ReasonFailed, DocumentTemplates, MatchedTemplates, RequestID
EOF
}