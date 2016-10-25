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

    console.log(page, msg_id, cat_key, cat_name, main_link, msg_uuid, color);

    // Заменяем на крутящуюся иконку
    var cat_span = document.getElementById(msg_id + '_category');
    old_cat_span = cat_span.innerHTML;
    cat_span.innerHTML = '<i class="fa fa-spinner" aria-hidden="true"></i>';

    // Формирвем запрос
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/js/message/' + msg_uuid + '/' + cat_key, true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = function() {

        // console.log(page, cat_name, color, msg_id);

        if (xhr.readyState != 4) return false;
        if (xhr.status != 200) {
            // Ошибка
            console.log(xhr.status + ' Ошибка : ' + xhr.statusText);
            on_error(cat_span, old_cat_span);
        } else {
            // Все нормально
            console.log(xhr.status + ' Все нормально : ' + xhr.statusText);
            on_success(page, cat_span, color, cat_name, msg_id);

            if (page == 'True') {

                var modal_data = JSON.parse(xhr.responseText);
                var modal_element = document.getElementById('problem_list_modal');
                console.log('modal_data : ', modal_data)

                var text = '<div class="row" style="margin: 2px;"><div class="col-md-6 col-md-offset-3">';
                for (var i=0; i<modal_data[3].length; i++) {
                    text += '<a class=\"btn btn-warning btn-lg btn-block\" onclick="problem_choice(\'';
                    text += msg_uuid + '\', \'' + modal_data[3][i].uuid + '\', this); return false;\">';
                    text += `${modal_data[3][i].title}` + '</a>';
                };

                text += '</div></div><div class="row"><div class="col-md-12" align="center"><br>или<br></div></div>';
                console.log(text);

                text += '<div class="row"><div class="col-md-6 col-md-offset-3" align="left">';
                text += '<form style="margin-bottom: 3em;">';
                text += '<div class="form-group"><input type="hidden" name="form_msg_uuid" id="form_msg_uuid" value="';
                text += msg_uuid + '"><textarea class="form-control" id="new_problem_title" name="new_problem_title" cols="30" rows="3"';
                text += 'placeholder="опишите новую проблему..."></textarea></div><br><p align="center">';
                text += 'Ответственный</p><div class="form-group form-inline">';
                for (var i=0; i<modal_data[1].length; i++) {
                    text += '<div class="radio"><label><input type="radio" name="responsible" id="responsible" value="';
                    text += modal_data[1][i].uuid + '">';
                    text += modal_data[1][i].name + ' ' + modal_data[1][i].surname;
                    text += '</label></div>';
                }
                 text += '</div><input class="btn btn-success btn-block" value="Создать" onclick="send_new_problem();"></form>';
                 text += '</div></div>';

                console.log(text);
                modal_element.innerHTML = text;
                $('#problem_modal').modal('toggle');
            };
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
    xhr.open('POST', '/api/js/problem/link/' + problem_uuid + '/' + msg_uuid, true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = function() {

        // console.log(page, cat_name, color, msg_id);

        if (xhr.readyState != 4) return false;
        if (xhr.status != 200) {
            // Ошибка
            console.log(xhr.status + ' : ' + xhr.statusText);
            alert('Api.JS.Problem.Link(). Произошла внутренняя ошибка. Пожалуйста, сообщите о ней администратору.');
        } else {
            // Все нормально
            console.log(xhr.status + ' : ' + xhr.statusText);
            $('#problem_modal').modal('toggle');
        };
    };

    xhr.send('');

    return false;

}

function send_new_problem () {

    var form_msg_uuid = document.getElementById('form_msg_uuid').value;
    var title = document.getElementById('new_problem_title').value;
    var resp = document.getElementById('responsible').value;

    console.log("Form data: ", form_msg_uuid, title, resp);


    // Формирвем запрос
    var xhr = new XMLHttpRequest();
    var body = 'new_problem_title=' + encodeURIComponent(title);
    xhr.open('POST', '/api/js/problem/create/' + form_msg_uuid + '/' + resp, true);

    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = function() {

        // console.log(page, cat_name, color, msg_id);

        if (xhr.readyState != 4) return false;
        if (xhr.status != 200) {
            // Ошибка
            console.log(xhr.status + ' : ' + xhr.statusText);
            alert('Api.JS.Problem.Create(). Произошла внутренняя ошибка. Пожалуйста, сообщите о ней администратору.');
        } else {
            // Все нормально
            console.log(xhr.status + ' : ' + xhr.statusText);
            $('#problem_modal').modal('toggle');
        };
    };

    xhr.send(body);

    return false;

}
