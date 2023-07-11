# Common Reporting Requests

Currently, metrics and detailed information about success and failures of the instructions and preferences processing is done adhoc, when requested. As this information is only shown within logs we have created a series of saved queries for log insights to report on this data.

Before running these saved queries please check you have the currect permissions and you are using the correct log group, which should be something like `/aws/lambda/lpa-iap-processor-{environment}`.

## Success / Failure Count

Since launch, this is provided daily for the previous day and should provide numbers for `Completed` (successful) and `Error` (failures). Select the saved query (`Instructions-and-Preferences` -> `Count-By-Status`), the day you want the numbers for and then run that.

This is then shared as text manualy to the team channel.

## Details of Failures

In order to improve the processing and also to check the documents on Sirius we have a query that will find all the failed processes, the case number, the templates / matched documents as well as the reason for the failure. Use the query `Instructions-and-Preferences` -> `Failed-Cases` with the date range you wish to retrieve information for.

Once this the results are shown you can then export the result table as an `xlsx` document. Some tidying on the resulting is helpful (cell wrap, headers, filters), but this document can be provided directly for further investigation.