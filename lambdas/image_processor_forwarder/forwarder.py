import urllib3
import json

def handler(event, context):
    url = "http://{}:9011/2015-03-31/functions/function/invocations".format(context.function_name)

    http = urllib3.PoolManager()
    res = http.request('POST', url, body=json.dumps(event))

    return json.loads(res.data)
