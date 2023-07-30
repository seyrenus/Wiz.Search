const objApp = WizExplorerApp;
const objDatabase = WizExplorerApp.Database;
const objCommon = WizExplorerApp.CommonUI;
const DataPath = objCommon.GetSpecialFolder("DataPath");
const USERID = objDatabase.GetMeta("ACCOUNT", "USERID");
const PluginPath = JSPlugin.PluginPath;
const userdatafolder = `${DataPath}/${USERID}/data`;
const indexfolder = `${userdatafolder}/search`;

objApp.ShowBubbleNotification("Build Index Starting",
    "The progress can be seen in the message console. You will be alerted when the indexing is complete.");
const params = ["index", "-O", `${indexfolder}`, '-W', `${userdatafolder}`];
objCommon.RunProc(`${PluginPath}/dist/wizsearch/wizsearch`, params, true, true);
objApp.ShowBubbleNotification("Build Index Finished", "Full-text indexing is done.");
