import json
import os
import pandas as pd
import requests

def get_chain_message():
    """如果本地有这个文件 直接读取"""
    filename='chains_mini.json'

    #本地读取
    if os.path.exists(filename):
        try:
            with open(filename,'r',encoding='utf-8') as f :
                return json.load(f)
        except FileNotFoundError:
            print(f"the file not found ,next download it")

    #本地文件不存在下载
    try:
        url='https://chainid.network/chains_mini.json'
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # 检查HTTP
        #保存本地
        with open(filename,'w',encoding='utf-8') as f:
            json.dump(response.json(),f,indent=2)
        return response.json()
    except requests.exceptions.RequestException as err:
        print(f"请求失败:{err}")
        return None

def enter_excel(data):
    """把获取到的输出到excel里"""
    if not data:
        print("没有数据输出")
        return
    try:
        #输出全部()如果要选择部分 则用columns
        #df【columns】.to-excel
        df = pd.json_normalize(data)

        df.to_excel("EVM_chain.xlsx",index=False)
        print("成功导出全部内容到excel里了")
    except Exception as err:
        print(f"导出失败:{err}")

if __name__ == '__main__' :
    #获取
    chain_data=get_chain_message()

    if chain_data:
        #导出到excel
        enter_excel(chain_data)
    else:
        print("失败")