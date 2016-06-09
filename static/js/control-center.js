/* JavaScript for control center */


function SendData(data) {
    //console.log('Выполняем запрос');
    var xhr = new XMLHttpRequest();
    var body = 'msg_id=' + encodeURIComponent(data);
    xhr.open('POST', '/control_center/show_full_thread', true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = function() {
      if (xhr.readyState != 4) return;
      if (xhr.status != 200) {
        alert( xhr.status + ': ' + xhr.statusText);
        console.log(xhr.status + ': ' + xhr.statusText);
        // var e = document.getElementById('tr_'+data.period_code);
        // e.className = e.className.replace('', 'danger');
      } else {
        alert( xhr.status + ': ' + xhr.statusText);
        console.log(xhr.status + ': ' + xhr.statusText);
        //console.log(document.getElementById('save_alert').className);
        //console.log(document.getElementById('save_alert').className.replace('hidden', 'show'));
        //var e = document.getElementById('tr_'+data.period_code);
        //e.className = e.className.replace('', 'success');
        //console.log(document.getElementById('save_alert').className.replace('hidden', 'show'));

      }
    }
    xhr.send(body);
    return xhr.responseText;
};


/* Thread load function for popup */

function LoadThread (msg_id) {
    var e = document.getElementById(msg_id);

    var data = {
        msg_id: msg_id
        };

    html = SendData(data);

    e.innerHTML(html);
}