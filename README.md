# Wiz.Search
为知笔记离线搜索

## 部署 [wiz-search](https://github.com/restran/wiz-search) 
以下为archlinux系linux的部署方式
1. `git clone https://github.com/restran/wiz-search
2. 安装pyenv(用来管理多版本python) `sudo pacman -S pyenv`
3. 安装python3.7.0 `pyenv install 3.7.0`
4. 设置wiz-search目录自动使用3.7.0版本python `cd folderOfWizSearch; pyenv local 3.7.0`
5. 修改原wiz-search的requirements.
```
flask
mountains
SQLAlchemy==1.4.2
records==0.5.3
werkzeug
beautifulsoup4
whoosh
jieba==0.40
future
html5lib
```
6. 安装依赖 `pip install -r requirements.txt`
7. 建立索引 `python index.py`
8. 运行app `python app.py`

## 安装插件
把Wiz.Search目录复制到 ~/.wiznote/plugins

## 使用
重启wiznoteplus, 就能在首页看到WizSearch了
