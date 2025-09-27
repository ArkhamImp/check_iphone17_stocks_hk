from flask import Flask, render_template, jsonify, request
import requests
import json
import time
import random
import threading
from datetime import datetime
from user_agents import get_random_user_agent
from proxy_manager import proxy_manager
from urllib.parse import quote

app = Flask(__name__)

# 添加自定义模板过滤器
@app.template_filter('to_json')
def to_json(value):
    return json.dumps(value)

# Apple 库存查询 API 端点
API_ENDPOINT = "https://www.apple.com/hk/shop/fulfillment-messages"
#API_ENDPOINT = "https://www.apple.com/cn/shop/fulfillment-messages"

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
last_updated = {}
is_checking = {}
model_checking_status = {}

# 默认配置参数
CONFIG = {
    'refresh_interval': 3,  # 默认刷新间隔（秒）
    'request_delay': 0.5,  # 请求间隔（秒）- 每次请求后等待的时间
    'batch_size': 5,  # 批次大小 - 每批处理的型号数量
    'use_proxy': False,  # 是否使用代理
    'proxy_list': []  # 代理服务器列表
}

# 请求时间控制
last_request_time = time.time()
request_lock = threading.Lock()

def delay_request():
    """控制请求间隔"""
    global last_request_time
    with request_lock:
        current_time = time.time()
        elapsed = current_time - last_request_time
        if elapsed < CONFIG['request_delay']:
            time.sleep(CONFIG['request_delay'] - elapsed)
        last_request_time = time.time()

def check_stock_for_model(model_name, model_code, batch_mode=False, max_retries=2):
    """为指定型号检查库存
    
    参数:
        model_name: 型号名称
        model_code: 型号代码
        batch_mode: 是否为批量模式 (如果是，则失败时会重试而不是立即返回错误)
        max_retries: 最大重试次数
    """
    # 使用随机用户代理
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.apple.com/hk/shop/buy-iphone/",
    }
    
    params = {
        "parts.0": model_code,
        "location": "Hong Kong",
    }
    
    for attempt in range(max_retries + 1):
        try:
            # 简单延迟机制控制请求速率
            delay_request()
            
            # 获取代理（如果启用）
            proxies = proxy_manager.get_random_proxy() if CONFIG['use_proxy'] else None
            
            # 发送请求，可选使用代理
            response = requests.get(API_ENDPOINT, params=params, headers=headers, proxies=proxies)
            response.raise_for_status()
            data = response.json()
            
            stores_data = data.get("body", {}).get("content", {}).get("PickupMessage", {}).get("stores", [])
            
            if not stores_data:
                if batch_mode and attempt < max_retries:
                    # 在批量模式下，如果还有重试次数，休息一下再重试
                    time.sleep(1.0 + random.random())
                    continue
                return {"error": "未能获取库存信息"}
            
            stores_availability = []
            for store in stores_data:
                store_name = store.get("storeName")
                parts_availability = store.get("partsAvailability", {})
                
                
                if parts_availability:
                    model_stock_info = parts_availability.get(model_code)
                    pickup_status = model_stock_info.get("pickupSearchQuote", "未知状态")
                    pickup_display = model_stock_info.get("pickupDisplay", "unknown")
                    stores_availability.append({
                        "store": store_name,
                        "status": pickup_status,
                        "available": pickup_display == "available"
                    })
            
            # 如果成功处理了数据，返回结果
            return stores_availability
            
        except Exception as e:
            if batch_mode and attempt < max_retries:
                # 在批量模式下，如果还有重试次数，休息一下再重试
                time.sleep(1.0 + random.random())
                continue
            return {"error": str(e)}
    
    # 如果所有尝试都失败
    return {"error": "多次尝试后仍无法获取数据"}

def check_single_model_stock(model_name, model_code, batch_mode=False):
    """检查单个型号的库存
    
    参数:
        model_name: 型号名称
        model_code: 型号代码
        batch_mode: 是否为批量模式，批量模式下会非阻塞地处理请求
    """
    global stock_data, last_updated, is_checking, model_checking_status
    
    # 如果已经在检查中且非批量模式，则直接返回
    if is_checking.get(model_name, False) and not batch_mode:
        return
    
    is_checking[model_name] = True
    model_checking_status[model_name] = True
    
    try:
        # 使用批量模式查询
        result = check_stock_for_model(model_name, model_code, batch_mode=batch_mode)
        stock_data[model_name] = result
        last_updated[model_name] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        stock_data[model_name] = {"error": str(e)}
        last_updated[model_name] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    finally:
        is_checking[model_name] = False
        model_checking_status[model_name] = False

def check_all_models_stock(batch_mode=True):
    """检查所有型号的库存
    
    参数:
        batch_mode: 是否使用批量模式，批量模式下会并行处理请求，减少阻塞
    """
    # 创建线程列表
    active_threads = []
    max_concurrent = CONFIG['batch_size']  # 最大并发数量
    
    # 计算当前有多少个型号
    total_models = len(IPHONE_17_PRO_MAX_MODELS)
    print(f"正在检查 {total_models} 个型号的库存，最大并发数: {max_concurrent}")
    
    # 处理所有型号
    for idx, (model_name, model_code) in enumerate(IPHONE_17_PRO_MAX_MODELS.items()):
        # 限制并发线程数量
        while len(active_threads) >= max_concurrent:
            # 检查哪些线程已完成并移除
            active_threads = [t for t in active_threads if t.is_alive()]
            if len(active_threads) >= max_concurrent:
                # 如果仍然达到最大并发，等待短暂时间
                time.sleep(0.2)
        
        # 创建并启动新线程
        thread = threading.Thread(
            target=check_single_model_stock, 
            args=(model_name, model_code, batch_mode),
            daemon=True
        )
        thread.start()
        active_threads.append(thread)
        
        # 在日志中显示进度
        print(f"启动查询 [{idx+1}/{total_models}] {model_name}")
    
    # 如果不是批量模式，等待所有线程完成
    if not batch_mode:
        for thread in active_threads:
            thread.join()

def background_stock_checker():
    """后台定期检查库存 - 使用随机间隔和配置的刷新时间避免被封锁"""
    while True:
        # 使用批量模式检查所有型号
        check_all_models_stock(batch_mode=True)
        
        # 使用配置的刷新间隔，添加一些随机性
        interval = CONFIG['refresh_interval']
        # 在配置间隔的基础上增加20%的随机性
        next_round_wait = interval * (0.9 + (0.2 * random.random()))
        time.sleep(next_round_wait)

@app.route('/')
def index():
    """主页"""
    # 传递更详细的模型数据和配置
    model_details_json = json.dumps(MODEL_DETAILS)
    series_capacities_json = json.dumps(SERIES_CAPACITIES)
    config_json = json.dumps(CONFIG)
    
    return render_template('index.html', 
                          model_details_json=model_details_json,
                          models=IPHONE_17_PRO_MAX_MODELS,
                          series_list=list(MODEL_DETAILS.keys()),
                          colors_list=COLORS,
                          capacities_list=CAPACITIES,
                          series_capacities_json=series_capacities_json,
                          config_json=config_json)

@app.route('/api/stock')
def get_stock():
    """获取库存数据的API"""
    return jsonify({
        "stock": stock_data,
        "lastUpdated": last_updated,
        "checkingStatus": model_checking_status
    })

@app.route('/api/refresh', methods=['POST'])
def refresh_stock():
    """手动刷新库存"""
    threading.Thread(target=check_all_models_stock, kwargs={"batch_mode": True}, daemon=True).start()
    return jsonify({"status": "refreshing"})

@app.route('/api/refresh/<model_name>', methods=['POST'])
def refresh_single_model(model_name):
    """手动刷新单个型号的库存"""
    if model_name in IPHONE_17_PRO_MAX_MODELS:
        model_code = IPHONE_17_PRO_MAX_MODELS[model_name]
        # 使用非批量模式，确保立即处理
        threading.Thread(target=check_single_model_stock, args=(model_name, model_code, False), daemon=True).start()
        return jsonify({"status": "refreshing", "model": model_name})
    else:
        return jsonify({"error": "Model not found"}), 404

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取当前配置信息"""
    return jsonify(CONFIG)

@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置信息"""
    data = request.get_json()
    
    if 'refresh_interval' in data:
        try:
            new_interval = float(data['refresh_interval'])
            if 5 <= new_interval <= 60:  # 限制刷新间隔在5-60秒之间
                CONFIG['refresh_interval'] = new_interval
            else:
                return jsonify({"error": "刷新间隔必须在5到60秒之间"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "刷新间隔必须是有效数字"}), 400
    
    if 'request_delay' in data:
        try:
            new_delay = float(data['request_delay'])
            if 0.1 <= new_delay <= 2.0:
                CONFIG['request_delay'] = new_delay
            else:
                return jsonify({"error": "请求延迟必须在0.1到2.0秒之间"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "请求延迟必须是有效数字"}), 400
    
    if 'batch_size' in data:
        try:
            new_size = int(data['batch_size'])
            if 1 <= new_size <= 20:
                CONFIG['batch_size'] = new_size
            else:
                return jsonify({"error": "批次大小必须在1到20之间"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "批次大小必须是有效整数"}), 400
    
    # 处理代理设置
    if 'use_proxy' in data:
        try:
            use_proxy = bool(data['use_proxy'])
            CONFIG['use_proxy'] = use_proxy
            
            # 更新代理管理器状态
            if use_proxy:
                proxy_manager.enable()
            else:
                proxy_manager.disable()
                
        except Exception as e:
            return jsonify({"error": f"更新代理设置失败: {str(e)}"}), 400
    
    # 处理代理列表
    if 'proxy_list' in data and isinstance(data['proxy_list'], list):
        try:
            proxy_list = data['proxy_list']
            CONFIG['proxy_list'] = proxy_list
            
            # 更新代理管理器的代理列表
            proxy_manager.clear_proxies()
            for proxy in proxy_list:
                if proxy and isinstance(proxy, str) and proxy.strip():
                    proxy_manager.add_proxy(proxy.strip())
                    
        except Exception as e:
            return jsonify({"error": f"更新代理列表失败: {str(e)}"}), 400
    
    return jsonify({"status": "success", "config": CONFIG})

@app.route('/api/proxy/status', methods=['GET'])
def get_proxy_status():
    """获取代理状态"""
    return jsonify(proxy_manager.get_status())

def find_free_port(start_port=5000, max_port=5010):
    """查找可用端口"""
    import socket
    for port in range(start_port, max_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return None

if __name__ == '__main__':
    try:
        # 启动后台线程检查库存
        stock_checker_thread = threading.Thread(target=background_stock_checker, daemon=True)
        stock_checker_thread.start()
        
        # 在后台线程中初始化库存数据，使用批量模式并行请求
        init_thread = threading.Thread(
            target=check_all_models_stock,
            kwargs={"batch_mode": True},
            daemon=True
        )
        init_thread.start()
        
        # 查找可用端口
        port = 5001
        
        print(f"正在启动服务器，端口: {port}")
        # 使用localhost而不是0.0.0.0，减少权限问题
        app.run(host='localhost', port=port, debug=True)
        
    except OSError as e:
        print(f"启动服务器失败: {e}")
        print("如果看到'以一种访问权限不允许的方式做了一个访问套接字的尝试'错误，请尝试:")
        print("1. 检查端口是否已被占用")
        print("2. 以管理员权限运行程序")
        print("3. 关闭防火墙或添加例外")
        print("4. 如果启用了代理，请检查代理设置")
