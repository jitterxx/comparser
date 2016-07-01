// Determine the correct object to use
var notification = window.Notification || window.mozNotification || window.webkitNotification;

// The user needs to allow this
if ('undefined' === typeof notification)
    alert('Web notification not supported');
else
    notification.requestPermission(function(permission){});

// A function handler
function Notify(titleText, bodyText, url)
{
    if ('undefined' === typeof notification)
        return false;       //Not supported....
    var noty = new notification(
        titleText, {
            body: bodyText,
            dir: 'auto', // or ltr, rtl
            lang: 'EN', //lang used within the notification.
            tag: 'notificationPopup', //An element ID to get/set the content
            icon: '' //The URL of an image to be used as an icon
        }
    );
    noty.onclick = function () {
        console.log('notification.Click');
        var win = window.open(url, '_blank');
        win.focus();
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
window.setInterval(function() {
    console.log('poll...');
    GetData2("on");

}, 5000);    //poll every 5 secs.


function GetData(data) {
    //console.log('Выполняем запрос');
    var resp = { status: 0, data: "" };
    var xhr = new XMLHttpRequest();
    var body = 'user_uuid=' + encodeURIComponent(data);
    xhr.open('POST', '/control_center/get_notify', true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = function() {
      if (xhr.readyState != 4) return ;
      if (xhr.status != 200) {
        // alert( xhr.status + ': ' + xhr.statusText);
        console.log('Ошибка. ' + xhr.status + ': ' + xhr.statusText);
      } else {
        // alert( xhr.status + ': ' + xhr.statusText);
        console.log(xhr.status, xhr.statusText, xhr.responseText)
      }
    }
    xhr.send(body);
    return xhr.responseText;
};

function GetData2(param1) {
    jQuery.ajax({
        url: '/control_center/get_notify',
        dataType: 'json',
        data: {user_uuid:'1234'},    //Include your own data, think about CSRF!
        success: function (data, textStatus) {
            console.log("data :", data);
            Notify("Уведомление", data, "");
        }
    });
};
