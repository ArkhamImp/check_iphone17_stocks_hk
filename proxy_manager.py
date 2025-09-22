"""
代理管理器
提供代理功能，通过不同IP发送请求以降低被封锁的风险
"""

import random

class ProxyManager:
    """
    代理管理器类
    管理代理服务器列表，提供随机代理选择功能
    """
    def __init__(self):
        # 初始化代理列表为空
        self._proxy_list = []
        self._enabled = False
    
    def add_proxy(self, proxy):
        """
        添加代理到列表
        
        参数:
            proxy: 代理服务器地址，格式为 "http://user:pass@host:port" 或 "http://host:port"
        """
        if proxy and proxy not in self._proxy_list:
            self._proxy_list.append(proxy)
    
    def remove_proxy(self, proxy):
        """
        从列表中移除代理
        
        参数:
            proxy: 要移除的代理地址
        """
        if proxy in self._proxy_list:
            self._proxy_list.remove(proxy)
    
    def clear_proxies(self):
        """清空代理列表"""
        self._proxy_list = []
    
    def set_proxies(self, proxies):
        """
        设置整个代理列表
        
        参数:
            proxies: 代理地址列表
        """
        if isinstance(proxies, list):
            self._proxy_list = proxies.copy()
    
    def get_random_proxy(self):
        """
        获取一个随机代理
        
        返回:
            如果代理列表为空或代理功能未启用，返回None
            否则返回随机选择的代理字典格式
        """
        if not self._enabled or not self._proxy_list:
            return None
        
        proxy_url = random.choice(self._proxy_list)
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    
    def enable(self):
        """启用代理功能"""
        self._enabled = True
    
    def disable(self):
        """禁用代理功能"""
        self._enabled = False
    
    def is_enabled(self):
        """返回代理功能是否启用"""
        return self._enabled
    
    def get_proxy_list(self):
        """获取当前代理列表"""
        return self._proxy_list.copy()
    
    def get_status(self):
        """获取代理管理器状态信息"""
        return {
            "enabled": self._enabled,
            "proxy_count": len(self._proxy_list),
            "proxies": self._proxy_list
        }

# 创建全局代理管理器实例
proxy_manager = ProxyManager()

# 示例使用方法
if __name__ == "__main__":
    # 添加一些代理（示例，实际使用时需要替换为有效的代理）
    proxy_manager.add_proxy("http://proxy1.example.com:8080")
    proxy_manager.add_proxy("http://proxy2.example.com:8080")
    
    # 启用代理
    proxy_manager.enable()
    
    # 获取随机代理
    proxy = proxy_manager.get_random_proxy()
    print(f"使用代理: {proxy}")
    
    # 在requests中使用
    # response = requests.get("https://example.com", proxies=proxy)
