fastapi + MongoDB + pydantic + rq + uvicorn

# 开发
`git clone https://github.com/Nataila/fastapi-template`

### 创建虚拟环境（optional）
`set env`
### 安装依赖
`pip install -r requirement.txt`
### 本地配置
`cp core/config/local_settings.example.py core/config/local_settings.py`
### 启动项目
`python main.py`
### 启动worker(optional目前发送邮件需要)
`rq worker`
### crontab任务
`python crontab/tasks.py`

### 全局依赖
wkhtmltopdf==0.12.3

# 部署
**todo**

# pdfkit乱码问题
`http://kaito-kidd.com/2015/03/12/python-html2pdf/`
`sudo apt-get install ttf-wqy-zenhei`
