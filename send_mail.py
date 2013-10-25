#!/usr/bin/env python
# -*- coding: utf-8 -*-

import smtplib
from email.mime.text import MIMEText

mailto_list=["lishiwen@playcrab.com","bxhrainbow@qq.com"]
mail_host="smtp.exmail.qq.com"
mail_user="lishiwen@playcrab.com"
mail_pass="password"

def send_mail(to_list, sub, content):
    me = mail_user + "<" + mail_user + ">"
    msg = MIMEText(content.encode('utf-8'), "html", "utf-8")
    msg['Subject'] = sub
    msg['From'] = me
    msg['To'] = ";".join(to_list)
    try:
        s = smtplib.SMTP()
        s.connect(mail_host)
        s.login(mail_user,mail_pass)
        s.sendmail(me, to_list, msg.as_string())
        s.close()
        return True
    except Exception, e:
        print str(e)
        return False

if __name__ == '__main__':
    if send_mail(mailto_list,"subject","content"):
        print "ok"
    else:
        print "err"
