from flask import Flask, render_template, jsonify
import requests
import json
import time
import threading
from datetime import datetime

app = Flask(__name__)

# 添加自定义模板过滤器
@app.template_filter('to_json')
def to_json(value):
    return json.dumps(value)

# Apple 库存查询 API 端点
API_ENDPOINT = "https://www.apple.com/hk/shop/fulfillment-messages"

# iPhone 17 Pro Max 的产品型号代码
IPHONE_17_PRO_MAX_MODELS = {
    "iPhone 17 Pro Max 256GB - 宇宙橙": "MFYN4ZA/A",
    "iPhone 17 Pro Max 512GB - 宇宙橙": "MFYT4ZA/A",
    "iPhone 17 Pro Max   1TB - 宇宙橙": "MFYW4ZA/A",
    "iPhone 17 Pro Max   2TB - 宇宙橙": "MG004ZA/A",
    "iPhone 17 Pro Max 256GB - 深墨蓝": "MFYP4ZA/A",
    "iPhone 17 Pro Max 512GB - 深墨蓝": "MFYU4ZA/A",
    "iPhone 17 Pro Max   1TB - 深墨蓝": "MFYX4ZA/A",
    "iPhone 17 Pro Max   2TB - 深墨蓝": "MG014ZA/A",
    "iPhone 17 Pro Max 256GB -    银": "MFYM4ZA/A",
    "iPhone 17 Pro Max 512GB -    银": "MFYQ4ZA/A",
    "iPhone 17 Pro Max   1TB -    银": "MFYV4ZA/A",
    "iPhone 17 Pro Max   2TB -    银": "MFYY4ZA/A",
    "iPhone 17 Pro 256GB - 宇宙橙": "MG8H4ZA/A",
    "iPhone 17 Pro 512GB - 宇宙橙": "MG8M4ZA/A",
    "iPhone 17 Pro   1TB - 宇宙橙": "MG8Q4ZA/A",
    "iPhone 17 Pro 256GB - 深墨蓝": "MG8J4ZA/A",
    "iPhone 17 Pro 512GB - 深墨蓝": "MG8N4ZA/A",
    "iPhone 17 Pro   1TB - 深墨蓝": "MG8R4ZA/A",
    "iPhone 17 Pro 256GB -    银": "MG8G4ZA/A",
    "iPhone 17 Pro 512GB -    银": "MG8K4ZA/A",
    "iPhone 17 Pro   1TB -    银": "MG8P4ZA/A",
}

# 型号的容量列表
CAPACITIES = ["256GB", "512GB", "1TB", "2TB"]

# 型号的颜色列表
COLORS = ["宇宙橙", "深墨蓝", "银色"]

# 将型号按系列、颜色和容量分组
MODEL_DETAILS = {
    "iPhone 17 Pro Max": {
        "宇宙橙": {
            "256GB": "iPhone 17 Pro Max 256GB - 宇宙橙",
            "512GB": "iPhone 17 Pro Max 512GB - 宇宙橙",
            "1TB": "iPhone 17 Pro Max   1TB - 宇宙橙",
            "2TB": "iPhone 17 Pro Max   2TB - 宇宙橙"
        },
        "深墨蓝": {
            "256GB": "iPhone 17 Pro Max 256GB - 深墨蓝",
            "512GB": "iPhone 17 Pro Max 512GB - 深墨蓝",
            "1TB": "iPhone 17 Pro Max   1TB - 深墨蓝",
            "2TB": "iPhone 17 Pro Max   2TB - 深墨蓝"
        },
        "银色": {
            "256GB": "iPhone 17 Pro Max 256GB -    银",
            "512GB": "iPhone 17 Pro Max 512GB -    银",
            "1TB": "iPhone 17 Pro Max   1TB -    银",
            "2TB": "iPhone 17 Pro Max   2TB -    银"
        }
    },
    "iPhone 17 Pro": {
        "宇宙橙": {
            "256GB": "iPhone 17 Pro 256GB - 宇宙橙",
            "512GB": "iPhone 17 Pro 512GB - 宇宙橙",
            "1TB": "iPhone 17 Pro   1TB - 宇宙橙"
        },
        "深墨蓝": {
            "256GB": "iPhone 17 Pro 256GB - 深墨蓝",
            "512GB": "iPhone 17 Pro 512GB - 深墨蓝",
            "1TB": "iPhone 17 Pro   1TB - 深墨蓝"
        },
        "银色": {
            "256GB": "iPhone 17 Pro 256GB -    银",
            "512GB": "iPhone 17 Pro 512GB -    银",
            "1TB": "iPhone 17 Pro   1TB -    银"
        }
    }
}

# 系列支持的容量
SERIES_CAPACITIES = {
    "iPhone 17 Pro Max": ["256GB", "512GB", "1TB", "2TB"],
    "iPhone 17 Pro": ["256GB", "512GB", "1TB"]
}

# 提取所有型号
ALL_MODELS = []
for series, colors in MODEL_DETAILS.items():
    for color, capacities in colors.items():
        for capacity, model in capacities.items():
            ALL_MODELS.append(model)

# 全局变量存储最新的库存数据
stock_data = {}
last_updated = None
is_checking = False

def check_stock_for_model(model_name, model_code):
    """为指定型号检查库存"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    
    params = {
        "parts.0": model_code,
        "location": "Hong Kong",
    }
    
    try:
        response = requests.get(API_ENDPOINT, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        stores_data = data.get("body", {}).get("content", {}).get("pickupMessage", {}).get("stores", [])
        
        if not stores_data:
            return {"error": "未能获取库存信息"}
        
        stores_availability = []
        for store in stores_data:
            store_name = store.get("storeName")
            parts_availability = store.get("partsAvailability", {})
            model_stock_info = parts_availability.get(model_code)
            
            if model_stock_info:
                pickup_status = model_stock_info.get("pickupSearchQuote", "未知状态")
                pickup_display = model_stock_info.get("pickupDisplay", "unknown")
                stores_availability.append({
                    "store": store_name,
                    "status": pickup_status,
                    "available": pickup_display == "available"
                })
        
        return stores_availability
    except Exception as e:
        return {"error": str(e)}

def check_all_models_stock():
    """检查所有型号的库存"""
    global stock_data, last_updated, is_checking
    
    if is_checking:
        return
    
    is_checking = True
    
    try:
        new_stock_data = {}
        
        for model_name, model_code in IPHONE_17_PRO_MAX_MODELS.items():
            new_stock_data[model_name] = check_stock_for_model(model_name, model_code)
            # 避免请求过于频繁
            time.sleep(1)
        
        stock_data = new_stock_data
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    finally:
        is_checking = False

def background_stock_checker():
    """后台定期检查库存"""
    while True:
        check_all_models_stock()
        # 每1分钟更新一次
        time.sleep(60)

@app.route('/')
def index():
    """主页"""
    # 传递更详细的模型数据
    model_details_json = json.dumps(MODEL_DETAILS)
    series_capacities_json = json.dumps(SERIES_CAPACITIES)
    
    return render_template('index.html', 
                          model_details_json=model_details_json,
                          models=IPHONE_17_PRO_MAX_MODELS,
                          series_list=list(MODEL_DETAILS.keys()),
                          colors_list=COLORS,
                          capacities_list=CAPACITIES,
                          series_capacities_json=series_capacities_json)

@app.route('/api/stock')
def get_stock():
    """获取库存数据的API"""
    return jsonify({
        "stock": stock_data,
        "lastUpdated": last_updated
    })

@app.route('/api/refresh', methods=['POST'])
def refresh_stock():
    """手动刷新库存"""
    threading.Thread(target=check_all_models_stock).start()
    return jsonify({"status": "refreshing"})

if __name__ == '__main__':
    # 启动后台线程检查库存
    stock_checker_thread = threading.Thread(target=background_stock_checker, daemon=True)
    stock_checker_thread.start()
    
    # 初始化库存数据
    check_all_models_stock()
    
    app.run(host='0.0.0.0', port=5000)
