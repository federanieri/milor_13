// THRON.init params
const CLIENT_ID = "milorgroupdev";
const APP_ID = "CS-C20V9V";
const APP_KEY = "uVjz9TvERgsHSNgmD2Sh2T1hhPKHnLV3OPUH8y6bYqUpsI8TFB4U15T322JHuFQX";
// params
//const CONTENT_ID = "<YOUR_CONTENT_ID>";
// THRON.init callback
const ready = function(session){
    console.log("INIT session ready:", session);
    const contentCollection = THRON.contentCollection.getFromSessionOwnerFolder();
    contentCollection.prefetchComplete.then(
        function(){
            console.log("Content information loaded", contentCollection.items);
        }
    );
};
// library initialization
THRON.init({
    clientId: CLIENT_ID,
    appId: APP_ID,
    appKey: APP_KEY
}).then(ready);