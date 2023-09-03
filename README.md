# Wiz.Search

为知笔记离线搜索插件 Wiz.Search，是在 [restran/wiz-search](https://github.com/restran/wiz-search) 项目的基础上发展出来的。

## 下载插件

请勿直接克隆本仓库或者使用源代码压缩包，因为插件的正确运行依赖于相应的 Python 环境，我们将提供打包好的插件以供使用。

请在 [Release 页面](https://github.com/altairwei/Wiz.Search/releases) 下载对应平台的正式版。或者在 [Actions 页面](https://github.com/seyrenus/Wiz.Search/actions) 选择某个开发中的连续构建，然后在 Artifacts 栏目中下载测试版。

## 安装插件

在 `~/.wiznote/plugins` 中创建 `Wiz.Search` 目录，将下载好的压缩包解压到该文件夹里。

插件安装方法可以参考 WizNotePlus [插件安装指南](https://github.com/altairwei/WizNotePlus/wiki/%E6%8F%92%E4%BB%B6%E5%AE%89%E8%A3%85%E6%8C%87%E5%8D%97)。

## 使用方法

按照下面方法使用本插件：

1. 重启 WizNotePlus, 就能在主界面工具栏看到 Wiz.Search 的图标。
2. 点击图表右侧的下拉箭头，选择 “Build Index” ，等待全文搜索数据库的索引工作。注意查看运行日志，确保索引构建成功。
3. 等索引完成后才能点击 Wiz.Search 的图标，开启离线搜索界面。
4. 全文索引操作 “Build Index” 需要定期手动执行以将新笔记或新内容加入到索引中。
5. 该插件在运行时会默认在 5000 端口启动一个服务以处理搜索请求，如果端口被占用可通过 Wiz.Search 下拉菜单中的 “Change Port” 更改。

## 如何开发

注意：Windows 平台下，Python 的 venv 目录结构与 Linux/MacOS 平台不一致，需要自行修改命令。

1. 确保 Python >= 3.7
2. 创建并激活虚拟环境：

    ```shell
    python -m venv venv
    source venv/bin/activate

    # Windows:
    # .\\venv\\Scripts\\activate
    ```

3. 安装 Python 依赖：

    ```shell
    python -m pip install -r requirements.txt
    ```

4. 打包插件：

    ```shell
    python -m PyInstaller --add-data 'venv/lib/python3.7/site-packages/jieba:jieba' wizsearch.py

    # Windows:
    # python -m PyInstaller --add-data 'venv\\Lib\\site-packages\\jieba;jieba' wizsearch.py
    ```
