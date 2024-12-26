/**
 * Created by restran on 2019/5/7.
 */
const options = {
    color: '#bffaf3',
    failedColor: '#874b4b',
    thickness: '5px',
    transition: {
        speed: '0.2s',
        opacity: '0.6s',
        termination: 300
    },
    autoRevert: true,
    location: 'left',
    inverse: false
};

Vue.use(VueProgressBar, options);
axios.defaults.headers.post['Content-Type'] = 'application/json; charset=utf-8';

// Initialize WizNote APIs
new QWebChannel(qt.webChannelTransport, async function(channel) {
    var objectNames = ["WizExplorerApp"];
    for (var i = 0; i < objectNames.length; i++) {
        var key = objectNames[i];
        window[key] = channel.objects[key];
    }

    // Get APIs
    const objApp = WizExplorerApp;
    const objDatabase = WizExplorerApp.Database;
    const objCommon = WizExplorerApp.CommonUI;
    const objPlugin = channel.objects["JSPlugin"];
    const objModule = channel.objects["JSPluginModule"];
    const PluginPath = objPlugin.PluginPath
    const DataPath = await objCommon.GetSpecialFolder("DataPath");
    const USERID = await objDatabase.GetMeta("ACCOUNT", "USERID");

    const userdatafolder = `${DataPath}/${USERID}/data`;
    const indexfolder = `${userdatafolder}/search`;
    let port = await objDatabase.GetMeta("WIZSEARCH", "PORT");
    if (port == 0) port = '5000';
    const params = [
        "server", "--port", port,
        "-O", `${indexfolder}`, '-W', `${userdatafolder}`];
    const proc = await objCommon.RunProc(`${PluginPath}/dist/wizsearch/wizsearch`, params, false, true);
    window.addEventListener("beforeunload", () => proc.kill());

    new Vue({
        el: '#app',
        data: function () {
            return {
                keyword: '',
                siteName: '为知搜',
                hasInit: false,
                hasSearch: false,
                total: 0,
                pageSize: 20,
                currentPage: 1,
                loading: false,
                tableData: [],
                search_in: 'content',
                createDateRange: [],
                selectedFolder: [],
                currentPath: [],
                modifyDateRange: [],
                folderOptions: []
            }
        },
        mounted: function () {
            this.hasInit = true
            //this.loadFolders();  // 修改为点击时加载
        },
        methods: {
            search: function () {
                this.loadPageList(1);
            },
            viewDocument: async function(doc_guid) {
                const doc = await objDatabase.DocumentFromGUID(doc_guid);
                if (doc != null) {
                    objApp.Window.ViewDocument(doc, true);
                }
                doc.deleteLater();
            },
            loadPageList: function (pageNum = 1) {
                var self = this;
                self.hasSearch = false;
                self.loading = true;
                var postData = {
                    'keyword': this.keyword,
                    'page_num': pageNum,
                    'search_in': this.search_in,
                    'create_start_date': this.createDateRange ? this.createDateRange[0] : null,
                    'create_end_date': this.createDateRange ? this.createDateRange[1] : null,
                    'modify_start_date': this.modifyDateRange ? this.modifyDateRange[0] : null,
                    'modify_end_date': this.modifyDateRange ? this.modifyDateRange[1] : null,
                    'folder_path': this.actualFolderPath
                };
                
                // 这里加上随机数，避免缓存
                axios.post(`http://127.0.0.1:${port}/api/search?_t=` + Math.random(), postData)
                    .then(function (response) {
                        if (typeof response.data === 'string') {
                            try {
                                response.data = JSON.parse(response.data)
                            } catch (e) {
                                console.log(e)
                            }
                        }

                        self.tableData = response.data['data'];
                        self.total = response.data['total'];
                        self.hasSearch = true;
                        self.loading = false;
                    })
                    .catch(function (error) {
                        self.showErrorMsg(error);
                        self.hasSearch = true;
                        self.loading = false;
                    });
            },
            handleCurrentChange: function (val) {
                this.currentPage = val;
                console.log(`当前页: ${val}`);
                this.loadPageList(val);
            },
            showErrorMsg: function (e) {
                this.$message({
                    message: e,
                    type: 'warning',
                    duration: 3000,
                    showClose: true
                });
            },
            updateFolders: function () {
                if (!this.folderOptions || this.folderOptions.length === 0) {
                    this.loadFolders();
                }
            },
            async loadFolders() {
                try {
                    const response = await axios.get(`http://127.0.0.1:${port}/api/folders`);
                    if (response.data && response.data.success) {
                        this.folderOptions = this.transformFolderData(response.data.data);
                        console.log('Folder options:', this.folderOptions);
                    }
                } catch (error) {
                    this.showErrorMsg('获取目录结构失败, 请检查wizsearch是否正常启动');
                    console.error(error);
                }
            },
            transformFolderData(folders) {
                return folders.map(folder => {
                    const item = {
                        name: folder.name,
                        label: folder.name,
                        path: folder.path
                    };
                    
                    // 只有当有子节点时才添加"全部"选项
                    if (folder.children && folder.children.length > 0) {
                        // 创建子节点数组
                        let children = [];
                        
                        // 添加"全部"子节点
                        children.push({
                            name: `${folder.name}(全部)`,
                            label: '全部',
                            path: folder.path  // 使用父节点的路径
                        });
                        
                        // 添加原有的子节点
                        children = children.concat(this.transformFolderData(folder.children));
                        
                        item.children = children;
                    }
                    
                    return item;
                });
            },
            handleNodeClick(node) {
                console.log('handleNodeClick', node);
                this.selectedFolder = node.name;
                this.actualFolderPath = node.path;
            },
            handleFolderChange(value) {
                if (!value) {
                    this.selectedFolder = null;
                    this.actualFolderPath = null;
                    return;
                }

                // 找到选中节点的信息
                const found = this.findNodeByName(this.folderOptions, value[value.length - 1]);
                if (found) {
                    this.selectedFolder = value;
                    // 如果选中的是"全部"节点，使用其父节点的路径
                    this.actualFolderPath = found.path;
                }
            },
            handleExpandChange(expandedNodes, node) {
                this.currentPath = expandedNodes;
            },
            findNodeByName(options, name) {
                for (const option of options) {
                    if (option.name === name) {
                        return option;
                    }
                    if (option.children && option.children.length > 0) {
                        const found = this.findNodeByName(option.children, name);
                        if (found) return found;
                    }
                }
                return null;
            },
            getParentsByPath(list, targetPath) {
                for (let i in list) {
                    if (list[i].path === targetPath) {
                        return [list[i].name];
                    }
                    if (list[i].children) {
                        let node = this.getParentsByPath(list[i].children, targetPath);
                        if (node !== undefined) {
                            node.unshift(list[i].name);
                            return node;
                        }
                    }
                }
            }
        },
        watch: {}
    });

});
