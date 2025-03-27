import urllib.parse #处理特殊字符
import re
import argparse
import logging
import json
import requests
from dingtalk_stream import AckMessage
import dingtalk_stream

# 和风天气API配置
QWEATHER_API_KEY = "c735e7f29aec475da5df9ab28c6853c0"
QWEATHER_LOCATION_API = "https://geoapi.qweather.com/v2/city/lookup"
QWEATHER_NOW_API = "https://devapi.qweather.com/v7/weather/now"

#python your.py --client_id ABC123 --client_secret XYZ789
#在cmd用这个来启动
def define_options():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--client_id', dest='client_id', required=True,
        help='app_key or suite_key from https://open-dev.digntalk.com'
    )
    parser.add_argument(
        '--client_secret', dest='client_secret', required=True,
        help='app_secret or suite_secret from https://open-dev.digntalk.com'
    )
    options = parser.parse_args()
    return options


def setup_logger():
    """设置日志记录  用来调试和追踪运行时的问题，可以较好的修改"""
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s [%(filename)s:%(lineno)d]'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def get_location_id(city_name: str) -> str:
    """获取城市LocationID,处理并调用天气信息"""
    try:
                                #正则表达式清理冗余字符
        city_name = re.sub(r'[：:天气\s]', '', city_name).strip()
        params = {
            "location": urllib.parse.quote(city_name),
            "key": QWEATHER_API_KEY,
        }
        response = requests.get(QWEATHER_LOCATION_API, params=params, timeout=10)
        response.raise_for_status()
        data = response.json() #解析并返回json格式

        if data.get('code') == '200' and data.get('location'):#确保API调用的准确性
            return data['location'][0]['id'] #提取第一个匹配城市的ID
        logging.error(f"定位失败: {data.get('message', '未知错误')}")
        return None
    except Exception as e:
        logging.error(f"定位有误: {str(e)}")
        return None


def get_weather(location_id: str) -> str:
    """获取实时天气数据（使用位置来调用实时天气）"""
    params = {
        "location": location_id,
        "key": QWEATHER_API_KEY,
        "lang":"zh" #天气状态为中文
    }
    try:
        response = requests.get(QWEATHER_NOW_API, params=params, timeout=5)
        data = response.json()
        if data.get('code') == '200':
            now = data['now']
            #从和风天气里的文档里面获取的请求参数
            return (
                "- **天气状况**: {text}\n"
                "- **当前温度**: {temp}℃\n"
                "- **体感温度**: {feelsLike}℃\n"
                "- **相对湿度**: {humidity}%\n"
                "- **更新时间**: {time}".format(
                    text=now['text'],
                    temp=now['temp'],
                    feelsLike=now['feelsLike'],
                    humidity=now['humidity'],
                    time=data['updateTime'][11:16]
                )
            )
        return "获取天气信息失败"
    except Exception as e:
        logging.error(f"天气查询失败: {str(e)}")
        return "天气服务暂时不可用"


class WeatherHandler(dingtalk_stream.ChatbotHandler):
    """处理钉钉消息的Handler类"""
    def __init__(self, logger: logging.Logger = None):
        super().__init__()
        self.logger = logger

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        try:
            incoming_message = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
            content = incoming_message.text.content.strip()

            self.logger.info(f"收到消息内容: {content}")

            # 提取城市名称
            city_match = re.search(r'天气[:：]?\s*(\S+)', content)
            if not city_match:

                self.reply_markdown(
                    "输入提示",
                    "** 格式错误**\n请使用：'天气 城市名' 格式查询\n示例：天气 仙游'",
                    incoming_message
                )
                return AckMessage.STATUS_OK, "OK"

            city_name = city_match.group(1)

            # 获取位置ID
            location_id = get_location_id(city_name)
            if not location_id:
                self.reply_markdown(
                    "查询失败",
                    f"**  城市不存在**\n未找到城市：'{city_name}'",
                    incoming_message
                )
                return AckMessage.STATUS_OK, "OK"

            # 获取天气数据
            weather_info = get_weather(location_id)
            if "失败" in weather_info:
                raise ValueError(weather_info)

            # 构建Markdown来回馈给我
            markdown_content = (
                "### {city}天气\n"
                "{info}\n\n"
                "—— 数据来自[和风天气](https://www.qweather.com)".format(
                    city=city_name,
                    info=weather_info
                )
            )

            self.reply_markdown(
                f"{city_name}天气",  # title
                markdown_content,  # text
                incoming_message  # message对象
            )
            return AckMessage.STATUS_OK, "OK"

        except Exception as e:
            self.logger.error(f"处理异常: {str(e)}", exc_info=True)
            self.reply_markdown(
                "服务异常",
                "** 服务暂时不可用**\n",
                incoming_message
            )
            return AckMessage.STATUS_OK, "OK"


def main():
    logger = setup_logger()
    options = define_options()

    credential = dingtalk_stream.Credential(options.client_id, options.client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_handler(dingtalk_stream.chatbot.ChatbotMessage.TOPIC,WeatherHandler(logger))
    client.start_forever()


if __name__ == '__main__':
    main()