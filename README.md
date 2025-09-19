# iPhone库存监控网页应用

这个应用可以实时监控香港Apple Store的iPhone库存状态，并以美观的网页界面展示。

## 功能特点

- 实时监控iPhone库存状态
- 按型号和颜色分组展示
- 自动定时刷新数据
- 支持手动刷新库存
- 美观的用户界面

## 安装与运行

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 运行应用：

```bash
python app.py
```

3. 打开浏览器，访问 [http://127.0.0.1:5000](http://127.0.0.1:5000)

## 技术栈

- 后端：Flask
- 前端：
  - Vue.js - 响应式界面
  - Bootstrap 5 - 页面布局和样式
  - Font Awesome - 图标
  - Axios - API请求
