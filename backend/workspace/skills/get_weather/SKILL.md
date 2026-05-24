---
name: 天气查询
description: 查询指定城市的实时天气信息
---

# 天气查询技能

## 功能

获取指定城市的当前天气状况。

## 使用步骤

1. **使用 `fetch_url` 工具访问心知天气 API**：
   - 参数格式：`{"url": "https://api.seniverse.com/v3/weather/now.json?key=SUdNOV-BcTkRES0BO&location={城市名}&language=zh-Hans&unit=c"}`
   - 示例：`{"url": "https://api.seniverse.com/v3/weather/now.json?key=SUdNOV-BcTkRES0BO&location=shaoxing&language=zh-Hans&unit=c"}`

2. 解析返回的 JSON 数据

3. 提取关键信息：温度、天气状况

4. 以友好的格式回复用户

## 工具调用示例

查询北京天气：

```json
{
  "url": "https://api.seniverse.com/v3/weather/now.json?key=SUdNOV-BcTkRES0BO&location=beijing&language=zh-Hans&unit=c"
}
```

返回数据解析：
- `results[0].location.name` - 城市名称
- `results[0].now.text` - 天气描述
- `results[0].now.temperature` - 当前温度

## 回复格式

> 🌤 **绍兴** 
> 
> 天气：晴  
> 温度：8°C
