const objApp = WizExplorerApp;
const objDatabase = WizExplorerApp.Database;
const objCommon = WizExplorerApp.CommonUI;
const DataPath = objCommon.GetSpecialFolder("DataPath");
const USERID = objDatabase.GetMeta("ACCOUNT", "USERID");
const PluginPath = JSPlugin.PluginPath;
const userdatafolder = `${DataPath}/${USERID}/data`;
const indexfolder = `${userdatafolder}/search`;

const params = [
    `${PluginPath}/wizsearch.py`, "index",
    "-O", `${indexfolder}`, '-W', `${userdatafolder}`];

objApp.ShowBubbleNotification("Build Index Starting", "See message console...");
objCommon.RunProc(`${PluginPath}/venv/Scripts/python.exe`, params, true, true);
objApp.ShowBubbleNotification("Build Index Finished", "Full-text indexing is done.");
