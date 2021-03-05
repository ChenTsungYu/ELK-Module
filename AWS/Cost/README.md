# 紀錄 Kibana 上新增的 Scripted fields (for AWS Cost)
## 計算 Modified + Terminate 的 savings 總和
Name: totalSaving
Script:
```java
doc['ModifyRecommendationDetail.TargetInstances.EstimatedMonthlySavings'].sum() + doc['TerminateRecommendationDetail.EstimatedMonthlySavings'].sum()
```
## 注意
### 金額數值的資料型別為字串
Cost explorer API 匯出的資料會將金額數值轉為字串的形式( 見[範例](./sample/ec2_right_sizing.json) )，若直接倒到Elasticsearch，在 Kibana 拉圖表會有問題(字串沒辦法做計算)。
#### Solution
透過事先 Mapping 的方式來轉換目標欄位的資料型別，目前採用的做法: 預先建立 Mapping Template 來對特定的 index pattern 做定義，建立 Mapping Template 的範本可[點此處](./template/cost_optimizing.json)查看。
