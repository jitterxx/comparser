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
};


function user_check_category(page, msg_id, cat_key, cat_name, main_link, msg_uuid, color) {

    // console.log(page, msg_id, cat_key, cat_name, main_link, msg_uuid, color);

    // Заменяем на крутящуюся иконку
    var cat_span = document.getElementById(msg_id + '_category');
    old_cat_span = cat_span.innerHTML;
    cat_span.innerHTML = '<i class="fa fa-spinner" aria-hidden="true"></i>';

    // Формирвем запрос
    var xhr = new XMLHttpRequest();
    xhr.open('GET', main_link + msg_uuid + '/' + cat_key + '/js', true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = function() {

        // console.log(page, cat_name, color, msg_id);

        if (xhr.readyState != 4) return false;
        if (xhr.status != 200) {
            // Ошибка
            // console.log(xhr.status + ' : ' + xhr.statusText);
            on_error(cat_span, old_cat_span);
        } else {
            // Все нормально
            // console.log(xhr.status + ' : ' + xhr.statusText);
            on_success(page, cat_span, color, cat_name, msg_id);
            if (page == 'True') { $('#modal_' + msg_uuid).modal('toggle');}
        };
    };

    xhr.send('');

    return false;
};

function on_error(cat_span, old_cat_span) {
    // console.log('on_error :', cat_span, old_cat_span)
    // ошибка
    cat_span.innerHTML = old_cat_span;
    // окошко уведомления
    alert('Api.UserTrain(). Произошла внутренняя ошибка. Пожалуйста, сообщите о ней администратору.');
    return false;
};

function on_success(page, cat_span, color, cat_name, msg_id) {
    // console.log('on_success :', page, cat_span, color, cat_name, msg_id);
    // True - оставить на странице, False - скрыть сообщение
    var msg = document.getElementById('message_' + msg_id);
    if (page == 'True') {
        cat_span.innerHTML = '<span class="text-' + color + '">' + cat_name + '</span>';
        // console.log(msg.classList);
        msg.classList.remove('panel-warning');
        msg.classList.add('panel-' + color);

    } else {
        var msg = document.getElementById('message_' + msg_id);
        //console.log(msg.classList);
        msg.classList.add('hidden');
    }

    return false;

}

function problem_choice (msg_uuid, problem_uuid, modal_obj) {

    // Формирвем запрос
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/problem/link/' + problem_uuid + '/' + msg_uuid + '/js', true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = function() {

        // console.log(page, cat_name, color, msg_id);

        if (xhr.readyState != 4) return false;
        if (xhr.status != 200) {
            // Ошибка
            console.log(xhr.status + ' : ' + xhr.statusText);

        } else {
            // Все нормально
            console.log(xhr.status + ' : ' + xhr.statusText);
            $('#modal_' + msg_uuid).modal('toggle');
        };
    };

    xhr.send('');

    return false;

}
