# Wiz.Search

为知笔记离线搜索 Wiz.Search，是在 [restran/wiz-search](https://github.com/restran/wiz-search) 项目的基础上发展出来的。

## 下载插件

在 Release 页面选择对应平台的压缩包下载。

## 安装插件

在 `~/.wiznote/plugins` 中创建 `Wiz.Search` 目录，将下载好的压缩包解压到该文件夹里。

## 使用方法

按照下面方法使用本插件：

1. 重启 WizNotePlus, 就能在主界面工具栏看到 Wiz.Search 的图标。
2. 点击图表右侧的下拉箭头，选择 “Build Index” ，等待全文搜索数据库的索引工作。
3. 等索引完成后才能点击 Wiz.Search 的图标，开启离线搜索界面。
4. 全文索引操作 “Build Index” 需要定期手动执行以将新笔记或新内容加入到索引中。
5. 该插件在运行时会默认在 5000 端口启动一个服务以处理搜索请求，如果端口被占用可通过 Wiz.Search 下拉菜单中的 “Change Port” 更改。
