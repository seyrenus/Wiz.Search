const objApp = WizExplorerApp;
const objDatabase = WizExplorerApp.Database;
const objCommon = WizExplorerApp.CommonUI;
let port = objDatabase.GetMeta("WIZSEARCH", "PORT");
if (port == 0) port = '5000';
const ret = objCommon.GetIntValue("Wiz.Search Server Port", "Set a new port:",
                                   parseInt(port), 1, 65535, 1);
objDatabase.SetMeta("WIZSEARCH", "PORT", ret)
