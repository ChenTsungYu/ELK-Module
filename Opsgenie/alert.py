'''
(終版)
List Alerts

docs:
Elastic - kibana
https://discuss.elastic.co/t/bar-chart-filtered-by-day-of-week/155743/2

Opsgenie:
query string filter 格式:
https://docs.opsgenie.com/docs/alerts-search-query-help

URL Encoding Reference :
https://www.w3schools.com/tags/ref_urlencode.ASP
'''

import requests, json, datetime, pytz, re, time
from elasticsearch import Elasticsearch
from secret import *

es = Elasticsearch( # Cloud version
    cloud_id=f"{ElasticHost}",
    http_auth=(f"{ElasticAccount}", f"{ElasticPassword}"),
)

def isBusinessHours(timestring):
    str_datetime = datetime.datetime.strptime(timestring, "%Y-%m-%dT%H:%M:%S.%fZ").time()
    if datetime.time(hour=9) <= str_datetime <= datetime.time(hour=18):
        is_business_hours = "Business Hours"
    else:
        is_business_hours = "Off-Hours"
    return is_business_hours

def getLastDate(now):
    """
    Get last date
    """
    if now.month == 1: return f'12-{now.year - 1}'

    return f'{now.month-1}-{now.year}'

def parseOwener(owener):
    pattern = re.compile(r'.*?@')
    owner_name = re.findall(pattern, owener)
    owner_name_list = owner_name[0][:-1].split('.')
    owner = " ".join(list(map(lambda x:x.capitalize(), owner_name_list)))
    
    return owner

def getAlertNote(headers, alertId):
    try:
        url = f"https://api.opsgenie.com/v2/alerts/{alertId}/notes"
    except:
        print(f'note is not avaliable')
    r = requests.get(url, headers=headers)
    r.encoding = 'utf-8'
    jData = json.loads(r.content)

    notes_list = []
    for note in jData['data']:
        
        if bool(re.match(r'.*?@', note['owner'])):
            note['owner'] = parseOwener(note['owner'])
            
        notes_list.append(f"{note['owner']}: {note['note']}")
    notes = " / \n".join(notes_list)

    if notes == "": notes = "-"

    return notes
    
def main():
    now = datetime.datetime.now()
    current_date = now.strftime('%m-%Y')
    last_date = getLastDate(now)

    page = 1
    offset = 0
    headers = {'user-agent': 'my-app/0.0.1', "Content-Type":"application/json", "Authorization": f"GenieKey {GenieKey}"}

    while page != 0:
        """
        Opsgenie API 可用 query string 下 filter，如日期範圍
        Sample:
        1. 搜尋 10/1/2020 當天: 其中 %3A 表冒號 ":"，細節詳閱 URL Encoding Reference 文件
           https://api.opsgenie.com/v2/alerts?query=createdAt%3A01-10-2020&limit=100&sort=createdAt&offset=0&order=desc       

        2. 搜尋 10/1/2020 以後:
           https://api.opsgenie.com/v2/alerts?query=createdAt>01-10-2020&limit=100&sort=createdAt&offset=0&order=desc       

        3. 搜尋 2020 10月
           https://api.opsgenie.com/v2/alerts?query=(createdAt>01-10-2020)and(createdAt<01-12-2020)&limit=100&sort=createdAt&offset=0&order=desc
        """
        print(f'page {page}:')
        # print(f'01-{last_date} ~ :01-{current_date}')
        time.sleep(3) # Opsgenie 有request 速率限制
        try:
            url = f"https://api.opsgenie.com/v2/alerts?query=(createdAt>01-01-2021)and(createdAt<01-02-2021)&limit=100&sort=createdAt&offset={offset}&order=desc"
            # url = f"https://api.opsgenie.com/v2/alerts?query=(createdAt>01-{last_date})and(createdAt<01-{current_date})&limit=100&sort=createdAt&offset={offset}&order=desc"
        except Exception as e:
            # print(f"region: {region} is't been set")
            print("page Exception: ", e)
            print(f'page {page} is not avaliable')
            break
        
        r = requests.get(url, headers=headers)
        r.encoding = 'utf-8'
        jData = json.loads(r.content)

        try:
            if jData['data'] == []: break
        except:
            print("Exceed the API rate limiting")
            time.sleep(60)
            continue

        for data in jData['data']:
            data["isBusinessHours"] = isBusinessHours(data['createdAt'])
            try:
                data['ownerName'] = parseOwener(data['owner']) if len(data['owner']) > 0 else "-"
            except:
                data['ownerName'] = "System"

            data["tagsAggr"] = '-' if data['tags'] == [] else ', '.join(data['tags']) 
            data["note"] = getAlertNote(headers, data['id'])
            
            # print("data: " ,data)
            es.index(index='opsgenie_alert', body=json.dumps(data))

        offset += 100
        page += 1

if __name__ == "__main__":
    main()
    print("ok")
