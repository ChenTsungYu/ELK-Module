"""
(未完)
doc:
https://docs.aws.amazon.com/cli/latest/reference/support/describe-trusted-advisor-checks.html
https://docs.aws.amazon.com/cli/latest/reference/support/describe-trusted-advisor-check-result.html
https://gist.github.com/sebsto/468670c7c0d5feeade69
"""
import base64, subprocess, json, shlex, pytz, re
from datetime import datetime
# from elasticsearch import Elasticsearch
from secret import *

# es = Elasticsearch([f'http://{Elastic_account}:{Elastic_password}@{Elastic_host}'])

resources_list_command = f'aws support describe-trusted-advisor-checks --language "en" --region us-east-1 --output json'
resources_output = subprocess.check_output(shlex.split(resources_list_command))
resources_output

jData = json.loads(resources_output)

def cleanhtml(raw_html) -> "Remove all tags excluded <a> tags":
    cleanr = re.compile(r'<(?!a|/a).*?>')
    cleantext = cleanr.sub('', raw_html)
    return cleantext


for check in jData['checks']:
    print('name: ', check['name']);print();
    print('ID: ', check['id']);print();
    print('category: ', check['category']);print();
    print(check['description'])
    # check = cleanhtml(check['description'])
    # check = check.split("\n")
    # check = list(filter(None, check))
    # print(check)
    print("======")