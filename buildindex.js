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
objApp.Window.OpenMessageConsole();

proc = objCommon.RunProc(`${PluginPath}/dist/wizsearch/wizsearch`, params, true, true);
proc.WaitForFinished();

if (proc.ExitStatus() == 0 && proc.ExitCode() == 0
        && proc.Error() == 5) {
    objApp.ShowBubbleNotification("Build Index Finished", "Full-text indexing is done.");
} else {
    switch (proc.Error()) {
        case 0:
            errorMessage = "Failed to start the process.";
            break;
        case 1:
            errorMessage = "The process crashed.";
            break;
        case 2:
            errorMessage = "The process timed out.";
            break;
        case 4:
            errorMessage = "An error occurred when writing to the process.";
            break;
        case 3:
            errorMessage = "An error occurred when reading from the process.";
            break;
        default:
            errorMessage = "An unknown error occurred.";
            break;
    }

    objCommon.ShowMessage("Error!", errorMessage, 2);
}

