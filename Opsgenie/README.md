# Opsgenie API 串接至 Elasticsearch
- [Alert](./alert.py) [示意圖](./image/Opsgenie_Alert.png)

# Kibana 上的 scripted field 做客製化欄位 (版本為 7.6)
藉由 Kibana 上的 scripted field 在現有的欄位上寫規則
## Alerts per Day of Week
如增加 Monday～Sunday 的欄位名稱，用於區分 Datatime Field 是星期幾。
### 步驟:
1. 點擊左方導覽條的 [Management](./image/kibana_management.png) 進入管理介面
2. 點擊 Kibana 下的 [Index Pattern](./image/kibana_pattern.png)
3. 選擇目標 Pattern（看 Index 是建在哪個 Pattern 下）
4. 找到上方的 Tab，選擇 [Scripted fields](./image/kibana_Scripted_fields.png)
5. 點擊右下方的 [Add scripted field](./image/kibana_Add_Scripted_fields.png)
6. 輸入自訂的 Script 名稱，並於下方的 **Script** 填入規則
```bash
["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
[doc['createdAt'].value.dayOfWeek] 
```
其中`createdAt` 為想要轉換的DateTime Field，範例[點此](./image/kibana_Add_Scripted.png)
7. 回到Kibana 的 Horizontal Bar，選擇 **Bucket** -> **X-axis** -> **Terms** -> **Fields** 輸入剛剛建立的 Script Field Name，重新Apply 即可完成，[如圖](./image/kibana_choose_dayweek.png)

## Alert Priority
API 撈出來 `Priority` 的結果為 `P1`~`P5`，若要轉換成別的表示法，一樣可用新增 `scripted field` 來增加新欄位，如：
> P1 => Critical;
> P2 => Hight;
> P3 => Moderate;
> P4 => Low;
> P5 => Informational;
```
doc['priority.keyword'].value == 'P1' ? 'Critical' : doc['priority.keyword'].value == 'P2' ? 'Hight' : doc['priority.keyword'].value == 'P3' ? 'Moderate' : doc['priority.keyword'].value == 'P4' ? 'Low' : 'Informational'
```