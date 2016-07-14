window.name = "dialogs_parent";


// Determine the correct object to use
var notification = window.Notification || window.mozNotification || window.webkitNotification;

// The user needs to allow this
if ('undefined' === typeof notification)
    alert('Web notification not supported');
else
    notification.requestPermission(function(permission){});

// A function handler
function Notify(data)
{
    var titleText = data.title;

    if ('undefined' === typeof notification)
        return false;       //Not supported....
    var noty = new notification(
        titleText, {
            body: data.text,
            dir: 'auto', // or ltr, rtl
            lang: 'RU', //lang used within the notification.
            tag: 'notificationPopup', //An element ID to get/set the content
            icon: '/static/img/rocket-logo-small-transparent.png' //The URL of an image to be used as an icon
        }
    );
    noty.onclick = function () {
        //console.log('notification.Click');
        //console.log("URL: ", data.url);
        //var win = window.open(data.url);
        var win = window.open("", "dialogs_parent");
        win.focus();
        win.location.reload();
    };
    noty.onerror = function () {
        console.log('notification.Error');
    };
    noty.onshow = function () {
        console.log('notification.Show');
    };
    noty.onclose = function () {
        console.log('notification.Close');
    };
    return true;
}


//Poll our backend for notifications, set some reasonable timeout for your application
var notification_interval = setInterval(function() {
    console.log('Notification poll...');
    GetData2("on");

}, 60000);    //poll every 60 secs.

function GetData2(param1) {
    jQuery.ajax({
        url: '/control_center/get_notify',
        dataType: 'json',
        data: {user_uuid:'1234'},    //Include your own data, think about CSRF!
        success: function (data, textStatus) {
            console.log("data :", data);
            if (data.show) {
                Notify(data);
            }
        }
    });
};
