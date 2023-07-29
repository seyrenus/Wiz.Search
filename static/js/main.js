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

    // TODO: 检查并启动 Server
    // 绑定 RequestClose，以关闭服务器。

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
                tableData: []
            }
        },
        mounted: function () {
            this.hasInit = true
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
                const userdatafolder = `${DataPath}/${USERID}/data`
                const indexfolder = `${userdatafolder}/search`
                const params = [
                    `${PluginPath}/wizsearch.py`, "search",
                    "-O", `${indexfolder}`, '-W', `${userdatafolder}`,
                    "-p", `${pageNum}`, `${this.keyword}`]
                console.log(params)
                objCommon.RunExe(`${PluginPath}/venv/Scripts/python.exe`, params)
                    .then(function (response) {
                        result = JSON.parse(response)
                        self.tableData = result['data'];
                        self.total = result['total'];
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
            }
        },
        watch: {}
    });

});
