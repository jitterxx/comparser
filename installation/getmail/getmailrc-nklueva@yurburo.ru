[retriever]
type = SimpleIMAPSSLRetriever
server = imap.yandex.ru
username = 
password = 
mailboxes = ("INBOX", "Отправленные",)

[filter-1]
type = Filter_external
path = /home/yurburo/service/bin/python
arguments = ('/home/yurburo/service/srv/email_eater_stdin_imap.py',)
ignore_stderr = false
user = yurburo

[destination]
type = Maildir
path = ~/Maildir/

[options]
read_all = false
read_new = true
max_messages_per_session = 1
message_log = ~/yurburo_getmail.log

