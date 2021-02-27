from datetime import datetime
import pytz
def ConvertToLocalTime() -> "轉換成台北時間":
    # Create datetime object
    timestring = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    str_datetime = datetime.strptime(timestring, "%Y-%m-%dT%H:%M:%S.%fZ")
    local_datetime = pytz.timezone('Asia/Taipei').localize(str_datetime).astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return local_datetime