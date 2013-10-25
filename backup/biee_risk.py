#!/home/qfpay/python/bin/python
# -*- coding: utf-8 -*-
# 2012年 09月 20日 星期四 17:14:37 CST


import os
import time
import ConfigParser
import sys
import math
import re


HOME = str(os.path.dirname(os.path.abspath(__file__))).split(r'/risk')[0]
sys.path.append(HOME)

from mysql_conn import MysqlCur
from oracle_conn import OracleCur

os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'


class BiRisk:

    def __init__(self, bi_conf, ri_conf):
        self.ri_conf = ri_conf
        self.conn = OracleCur(bi_conf)
        self.used_user = []
        self.risk_data = []
        self.risk_model_list = []

        self.get_used_user()


    def get_used_user(self):
        cur = self.conn
        sql = "select user_id from f_client_rfm where first_use !='0'"
        ret_usr = cur.execute(sql)
        print 'used: %d' % len(ret_usr)
        self.used_user = ret_usr


    def get_data(self, strdate):
        self.data['ss'] = ''


    def get_date_id(self, str_date):
        cur = self.conn
        sql = "select date_id from dm_date where date_value = '%s'" % str_date
        ret = cur.execute(sql)
        try:
            return int(ret[0][0])
        except:
            return 0


    def handle(self, str_yest, date_id_yest):

        for user in self.used_user:
            data = {}
            data['user_id'] = user[0]
            data['date_id'] = date_id_yest

            risk_amt = RiskAmt(self.conn, self.ri_conf, user[0], str_yest, date_id_yest)
            data['per_deb_cri'] = risk_amt.get_per_deb_cre()
            data['per_hun'] = risk_amt.get_per_hun()

            ten_explode = risk_amt.get_ten_exp()
            data['ten_min_per'] = ten_explode.get('ten_per')
            data['ten_min_num'] = ten_explode.get('ten_num')
            data['day_accum'] = risk_amt.get_day_accum()
            card_ch = risk_amt.get_card_ch()
            data['mon_cardch'] = card_ch.get('cardch')
            data['mon_ch_num'] = card_ch.get('ch_num')
            data['per_untime'] = risk_amt.get_untime()
#            print data

            self.risk_data.append(data)

            risk_model = {}

            risk_model['user_id'] = user[0]
            risk_model['date_id'] = date_id_yest
            risk_model['condition_1'] = self.get_condition_1(data['per_deb_cri'], data['per_hun'])
            risk_model['condition_2'] = self.get_condition_2(data['ten_min_per'], data['ten_min_num'])
            risk_model['condition_3'] = self.get_condition_3(data['day_accum'])
            risk_model['condition_4'] = self.get_condition_4(data['mon_cardch'], data['mon_ch_num'])
            risk_model['condition_5'] = self.get_condition_5(data['per_untime'])
            risk_model['risk_index'] = risk_model['condition_1'] + risk_model['condition_2'] + risk_model['condition_3'] + risk_model['condition_4'] + risk_model['condition_5']
            if risk_model['risk_index'] > 0:
                self.risk_model_list.append(risk_model)


    def get_condition_1(self, per_deb_cri, per_hun):
        try:
            per_deb_cri = float(per_deb_cri)
            per_hun = float(per_hun)
            argv1 = float(self.ri_conf.get('model_1_condition_1', 'argv1'))
            argv2 = float(self.ri_conf.get('model_1_condition_1', 'argv2'))
#            print per_hun,per_deb_cri,argv2,argv1

            if per_deb_cri <= argv1 and per_hun >= argv2:
                return 2
            else:
                return 0
        except:
            return 0


    def get_condition_2(self, ten_min_per, ten_min_num):
        try:
            ten_min_per = float(ten_min_per)
            ten_min_num = float(ten_min_num)
            argv1 = float(self.ri_conf.get('model_1_condition_2', 'argv1'))
            argv2 = float(self.ri_conf.get('model_1_condition_2', 'argv2'))
            #print ten_min_per,argv1,ten_min_num,argv2

            if ten_min_per >= argv1 or ten_min_num >= argv2:
                return 1
            else:
                return 0
        except:
            return 0


    def get_condition_3(self, day_accum):
        try:
            day_accum = int(day_accum)
            argv1 = int(self.ri_conf.get('model_1_condition_3', 'argv1'))
            #print day_accum,argv1

            if day_accum >= argv1:
                return 0.5
            else:
                return 0
        except:
            return 0


    def get_condition_4(self, mon_cardch, mon_ch_num):
        try:
            mon_cardch = int(mon_cardch)
            mon_ch_num = int(mon_ch_num)
            argv1 = float(self.ri_conf.get('model_1_condition_4', 'argv1'))
            argv2 = float(self.ri_conf.get('model_1_condition_4', 'argv2'))
            #print mon_cardch,argv1,mon_ch_num,argv2

            if mon_cardch >= argv1 or mon_ch_num >= argv2:
                return 1
            else:
                return 0
        except:
            return 0


    def get_condition_5(self, per_untime):
        try:
            per_untime = float(per_untime)
            argv1 = float(self.ri_conf.get('model_1_condition_5', 'argv1'))

            if per_untime >= argv1:
                return 1
            else:
                return 0
        except:
            return 0


    def commit(self):
        yest = time.time() - 60*60*24
        str_yest = time.strftime('%Y-%m-%d', time.localtime(yest))
        date_id_yest = self.get_date_id(str_yest)

        self.handle(str_yest, date_id_yest)

        cur = self.conn
        if self.risk_data:
            sql = "insert into risk_usr_day values(:date_id,:user_id,:per_deb_cri,:per_hun,:ten_min_per,:ten_min_num,:day_accum,:mon_cardch,:mon_ch_num,:per_untime)"
            cur.insert(sql, self.risk_data)

        if self.risk_model_list:
            sql = "insert into risk_model_1 values(:date_id,:user_id,:risk_index,:condition_1,:condition_2,:condition_3,:condition_4,:condition_5)"
            cur.insert(sql, self.risk_model_list)


    def commit_all(self):
        date_start = "2012-09-23 00:50:00"
        time_start = time.mktime(time.strptime(date_start, "%Y-%m-%d %H:%M:%S"))

        while time_start < (int(time.time())-60*60*24):
            str_yest = time.strftime('%Y-%m-%d', time.localtime(time_start))
            date_id_yest = self.get_date_id(str_yest)

            self.handle(str_yest, date_id_yest)

            time_start += 60*60*24
            print str_yest

        cur = self.conn
        if self.risk_data:
            cur.truncate('risk_usr_day')
            sql = "insert into risk_usr_day values(:date_id,:user_id,:per_deb_cri,:per_hun,:ten_min_per,:ten_min_num,:day_accum,:mon_cardch,:mon_ch_num,:per_untime)"
            cur.insert(sql, self.risk_data)

        if self.risk_model_list:
            cur.truncate('risk_model_1')
            sql = "insert into risk_model_1 values(:date_id,:user_id,:risk_index,:condition_1,:condition_2,:condition_3,:condition_4,:condition_5)"
            cur.insert(sql, self.risk_model_list)



class RiskAmt:
    def __init__(self, conn, ri_conf, user_id, strdate, date_id):
        self.conn = conn
        self.ri_conf = ri_conf
        self.user_id = user_id
        self.date_id = date_id
        self.date = {}
        self.cri_sum = 0
        self.deb_sum = 0
        self.user_sum = 0
        self.hun_sum = 0
        self.day_trade = []
        self.mon_trade = []

        self.get_date(strdate)
        self.get_cri_sum()
        self.get_deb_sum()
        self.get_trade_day()
        self.get_trade_mon()


    def get_untime(self):
        morni_time = "%s 06:00:00" % self.date.get('str_date')
        night_time = "%s 22:00:00" % self.date.get('str_date')

        norm_trade = 0
        for trade in self.day_trade:
            ttime = trade.get('TXDTM')
            if ttime > morni_time and ttime < night_time:
                norm_trade += 1

        if not self.day_trade:
            return u'该日无交易'
        elif norm_trade:
            return u'%.2f' % ((len(self.day_trade)-norm_trade)*100.0/norm_trade)
        else:
            return u'无正常交易'


    def get_day_accum(self):
        card_dic = {}
        for trade in self.day_trade:
            if trade.get('CARDCD') not in card_dic.keys():
                card_dic[trade.get('CARDCD')] = 1
            else:
                card_dic[trade.get('CARDCD')] += 1

        return len(self.day_trade) - len(card_dic)


    def get_card_ch(self):
        card_dic = {}
        for trade in self.mon_trade:
            if trade.get('CONTACT') is not None:
                if trade.get('CONTACT') not in card_dic.keys():
                    card_dic[trade.get('CONTACT')] = 1
                else:
                    card_dic[trade.get('CONTACT')] += 1

#        print self.user_id,len(self.mon_trade),card_dic
        if card_dic:
            cardch, ch_num = 0, 0
            for each in card_dic.keys():
                if card_dic[each] > 1:
                    ch_num += 1
                    cardch += int(card_dic[each])
            return {'cardch': cardch-ch_num, 'ch_num': ch_num}
        else:
            return {'cardch': 0, 'ch_num':0}


    def get_per_deb_cre(self):
        if not self.cri_sum:
            return u'该月无信用卡交易'
        else:
            return u'%.2f' % (self.deb_sum * 100.0 / self.cri_sum)


    def get_per_hun(self):
        self.get_user_sum()
        if not self.user_sum:
            return u'该月没有交易'
        else:
            return u'%.2f' % (self.hun_sum * 100.0 / self.user_sum)


    def get_user_sum(self):
        cur = self.conn
 #       sql = "select txamt from f_trade_record where user_id=%s and trade_type_id='000000' and trade_result_id='0000' and cancel_type_id=0" % (self.user_id)
        sql = "select txamt from f_trade_record where user_id=%s and trade_type_id='000000' and trade_result_id='0000' and cancel_type_id=0 and txdtm>'%s' and txdtm<'%s'" % (self.user_id, self.date.get('mon_beg'), self.date.get('mon_end'))
        ret = cur.query(sql)
        if ret:
            self.user_sum = self.get_sum_amt(ret)
            self.hun_sum = self.get_sum_hun(ret)


    def get_trade_day(self):
        cur = self.conn
#        sql = "select user_id,txdtm,cardcd from f_trade_record where user_id=%s and trade_type_id='000000' and trade_result_id='0000' and cancel_type_id=0 order by trade_id" % (self.user_id)
        sql = "select user_id,txdtm,cardcd from f_trade_record where user_id=%s and trade_type_id='000000' and trade_result_id='0000' and cancel_type_id=0 and date_id=%s order by trade_id" % (self.user_id, self.date_id)
        ret = cur.query(sql)

        if ret:
            self.day_trade = ret


    def get_trade_mon(self):
        cur = self.conn
#        sql = "select user_id,txdtm,cardcd from f_trade_record where user_id=%s and trade_type_id='000000' and trade_result_id='0000' and cancel_type_id=0 order by trade_id" % (self.user_id)
        sql = "select user_id,contact from f_trade_record where user_id=%s and trade_type_id='000000' and trade_result_id='0000' and cancel_type_id=0 and txdtm>'%s' and txdtm<'%s' order by trade_id" % (self.user_id, self.date.get('mon_beg'), self.date.get('mon_end'))
        ret = cur.query(sql)

        if ret:
            self.mon_trade = ret


    def get_ten_exp(self):
        if not self.day_trade:
            return {'ten_per': 0, 'ten_num': 0}
        step = 10
        len_trade = len(self.day_trade)

        n = 0
        exp_list = [0,]
        while(n < len_trade):
            if_ex = self.if_explode(step, self.day_trade, n)
            if if_ex.get('res'):
                exp_list.append(int(if_ex.get('leng')) / 3.0)
            n += int(if_ex.get('leng'))

        return {'ten_per': max(exp_list), 'ten_num': len(exp_list) - 1}


    def if_explode(self, step, trade_list, n):
        txdtm = trade_list[n].get('TXDTM')
        time_later = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.mktime(time.strptime(txdtm, "%Y-%m-%d %H:%M:%S")) + 60*step))

        ex_list = []
        ex_list.append(trade_list[n])
        for t in trade_list[n+1:]:
            if t.get('TXDTM') <= time_later:
                ex_list.append(t)

        if len(ex_list) >= 3:
#            print ex_list, n
            return {'res':True, 'leng':len(ex_list)}
        else:
            return {'res':False, 'leng':1}


    def get_cri_sum(self):
        cur = self.conn
  #      sql = "select user_id,txamt from f_trade_record where user_id=%s and trade_type_id='000000' and trade_result_id='0000' and cancel_type_id=0 and (card_type_id = '02' or card_type_id = '03' or card_type_id = '05' or card_type_id is null)" % (self.user_id)
        sql = "select user_id,txamt from f_trade_record where user_id=%s and trade_type_id='000000' and trade_result_id='0000' and cancel_type_id=0 and (card_type_id = '02' or card_type_id = '03' or card_type_id = '05' or card_type_id is null) and txdtm>'%s' and txdtm<'%s'" % (self.user_id, self.date.get('mon_beg'), self.date.get('mon_end'))
        ret = cur.query(sql)
        if ret:
#            print 'cri',len(ret)
#            return self.get_sum_amt(ret)
            self.cri_sum = self.get_sum_amt(ret)
#        else:
#            return 0


    def get_deb_sum(self):
        cur = self.conn
  #      sql = "select user_id,txamt from f_trade_record where user_id=%s and trade_type_id='000000' and trade_result_id='0000' and cancel_type_id=0 and (card_type_id = '01' or card_type_id = '04')" % (self.user_id)
        sql = "select user_id,txamt from f_trade_record where user_id=%s and trade_type_id='000000' and trade_result_id='0000' and cancel_type_id=0 and (card_type_id = '01' or card_type_id = '04') and txdtm>'%s' and txdtm<'%s'" % (self.user_id, self.date.get('mon_beg'), self.date.get('mon_end'))
        ret = cur.query(sql)
        if ret:
#            return self.get_sum_amt(ret)
            self.deb_sum = self.get_sum_amt(ret)
#        else:
#            return 0


    def get_sum_amt(self, trades):
        sum_amt = 0
        for t in trades:
            sum_amt += t.get('TXAMT', 0)

        return sum_amt/100.0


    def get_sum_hun(self, trades):
        sum_amt = 0
        for t in trades:
            amt = t.get('TXAMT', 0)
            if self.ifhun(amt):
                sum_amt += amt

        return sum_amt/100.0


    def get_date(self, strdate):
        cur = self.conn
        all_date = {}
        old_date = time.strptime(strdate, "%Y-%m-%d")
        all_date['mon_beg'] = "%d-%02d-01 00:00:00" % (old_date.tm_year, old_date.tm_mon)
        all_date['mon_end'] = "%d-%02d-31 24:00:00" % (old_date.tm_year, old_date.tm_mon)
        all_date['str_date'] = strdate

        self.date = all_date


    def ifhun(self, n):
        if n == 0:
            return False
        else:
            return n/10000 == int(math.ceil(n/10000.0))


class HtmlTable:
    def __init__(self):
        self.head = '''
        <html>
            <head>
                <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
                <style type="text/css">
                .table_title{
                color: #233234;
                font-size: 1.5em;
                position: relative;
                margin: 20px auto;
                }
                .risk_table{
                position: relative;
                margin: 20px auto;
                font-size: 0.9em;
                width: 1000px;
                }
                td{
                text-align: center;
                }
                </style>
            </head>
            ${body}
        </html>'''
        self.table_title = '''
        <table border='1' cellspacing='0' class="risk_table">
            <caption class="table_title">${title}</caption>
            <p>${num_risk}</p>
            ${entity}
        </table>'''
        self.table_head = '''
        <tr>
            <th bgcolor=#ffffff>${user_id}</th>
            <th bgcolor=#E6B8B7>${risk_index}</th>
            <th bgcolor=#CFE9E9>${condition_1}</th>
            <th bgcolor=#E6D9C4>${condition_2}</th>
            <th bgcolor=#FFD2E3>${condition_3}</th>
            <th bgcolor=#FFD5D5>${condition_4}</th>
            <th bgcolor=#F9ECE4>${condition_5}</th>
            <th bgcolor=#CFE9E9>${per_deb_cri}</th>
            <th bgcolor=#CFE9E9>${per_hun}</th>
            <th bgcolor=#E6D9C4>${ten_min_per}</th>
            <th bgcolor=#E6D9C4>${ten_min_num}</th>
            <th bgcolor=#FFD2E3>${day_accum}</th>
            <th bgcolor=#FFD5D5>${mon_cardch}</th>
            <th bgcolor=#FFD5D5>${mon_ch_num}</th>
            <th bgcolor=#F9ECE4>${per_untime}</th>
        </tr>
        '''
        self.table_row = '''
        <tr>
            <td bgcolor=#ffffff>${USER_ID}</td>
            <td bgcolor=#E6B8B7>${RISK_INDEX}</td>
            <td bgcolor=#CFE9E9>${CONDITION_1}</td>
            <td bgcolor=#E6D9C4>${CONDITION_2}</td>
            <td bgcolor=#FFD2E3>${CONDITION_3}</td>
            <td bgcolor=#FFD5D5>${CONDITION_4}</td>
            <td bgcolor=#F9ECE4>${CONDITION_5}</td>
            <td bgcolor=#CFE9E9>${PER_DEB_CRI}</td>
            <td bgcolor=#CFE9E9>${PER_HUN}</td>
            <td bgcolor=#E6D9C4>${TEN_MIN_PER}</td>
            <td bgcolor=#E6D9C4>${TEN_MIN_NUM}</td>
            <td bgcolor=#FFD2E3>${DAY_ACCUM}</td>
            <td bgcolor=#FFD5D5>${MON_CARDCH}</td>
            <td bgcolor=#FFD5D5>${MON_CH_NUM}</td>
            <td bgcolor=#F9ECE4>${PER_UNTIME}</td>
        </tr>
        '''


    def format2str(self, temp, data):
        keys = re.findall(u'\$\{[a-zA-Z0-9_]+\}', temp)
        newtemp = temp
        for key in keys:
            name = key[2:-1]
            newtemp = newtemp.replace(key, unicode(data[name]))
        return newtemp


    def gettable(self, title, num_risk, headdata, rowsdata):
        head = self.format2str(self.table_head, headdata)

        tbody = ''
        if rowsdata:
            for rdata in rowsdata:
                tbody += self.format2str(self.table_row, rdata)

        tdata = {"title": title, "num_risk": num_risk,"entity": head+tbody}
        body = self.format2str(self.table_title, tdata)
        html = self.format2str(self.head, {'body': body})
        return html


class DayReport:

    def __init__(self, bi_conf, ri_conf):
        self.conn = OracleCur(bi_conf)
        self.risk_list = []

        self.get_risk_list()


    def get_risk_list(self):
        yest = time.time() - 60*60*24
        str_yest = time.strftime('%Y-%m-%d', time.localtime(yest))
        date_id_yest = self.get_date_id(str_yest)

        cur = self.conn
        sql = "select user_id,risk_index,condition_1,condition_2,condition_3,condition_4,condition_5 from risk_model_1 where date_id=%s" % date_id_yest
        ret = cur.query(sql)
        if not ret:
            print 'no risk user'
            return 

        each_user = ret[0]
#        for each_user in ret:
        sql = "select per_deb_cri,per_hun,ten_min_per,ten_min_num,day_accum,mon_cardch,mon_ch_num,per_untime from risk_usr_day where date_id=%s and user_id=%s" % (date_id_yest, each_user.get('USER_ID'))
        user_more = cur.query(sql)[0]
        each_user['PER_DEB_CRI'] = ('%.2f' % float(user_more.get('PER_DEB_CRI')))+' %'
        each_user['PER_HUN'] = ('%.2f' % float(user_more.get('PER_HUN')))+' %'
        each_user['TEN_MIN_PER'] = user_more.get('TEN_MIN_PER')
        each_user['TEN_MIN_NUM'] = user_more.get('TEN_MIN_NUM')
        each_user['DAY_ACCUM'] = user_more.get('DAY_ACCUM')
        each_user['MON_CARDCH'] = user_more.get('MON_CARDCH')
        each_user['MON_CH_NUM'] = user_more.get('MON_CH_NUM')
        each_user['PER_UNTIME'] = ('%.2f' % float(user_more.get('PER_UNTIME')))+' %'

        each_user['CONDITION_1'] = self.get_mark(each_user.get('CONDITION_1'))
        each_user['CONDITION_2'] = self.get_mark(each_user.get('CONDITION_2'))
        each_user['CONDITION_3'] = self.get_mark(each_user.get('CONDITION_3'))
        each_user['CONDITION_4'] = self.get_mark(each_user.get('CONDITION_4'))
        each_user['CONDITION_5'] = self.get_mark(each_user.get('CONDITION_5'))

        self.risk_list.append(each_user)


    def get_mark(self, argv):
        try:
            argv = float(argv)
            if argv > 0:
                return u'\u221a'
            else:
                return u'x'
        except:
            return u'x'


    def get_date_id(self, str_date):
        cur = self.conn
        sql = "select date_id from dm_date where date_value = '%s'" % str_date
        ret = cur.execute(sql)
        try:
            return int(ret[0][0])
        except:
            return 0

    def send_mail(self, to_list, mail_host, mail_user, mail_pass, sub, context):
        from email.MIMEText import MIMEText
        from email.MIMEMultipart import MIMEMultipart
        import smtplib
        msg = MIMEText(context.encode("UTF-8"),"html","UTF-8")
        msg['Subject'] = sub
        msg['From'] = mail_user
        msg['To'] = ";".join(to_list)
        try:
           send_smtp = smtplib.SMTP()
           send_smtp.connect(mail_host)
           send_smtp.login(mail_user, mail_pass)
           send_smtp.sendmail(mail_user,to_list, msg.as_string())
           send_smtp.close()
           return True
        except Exception,e:
           print(str(e))
           return False


    def send_day_report(self):
        headdata = {
            'user_id': u'商户ID',
            'risk_index': u'风险分数',
            'condition_1': u'金额异常',
            'condition_2': u'爆发交易',
            'condition_3': u'分单交易',
            'condition_4': u'换卡交易',
            'condition_5': u'时间异常',
            'per_deb_cri': u'月借信比',
            'per_hun': u'月整百比',
            'ten_min_per': u'10分爆发比',
            'ten_min_num': u'10分爆发次',
            'day_accum': u'日分单次',
            'mon_cardch': u'月换卡次',
            'mon_ch_num': u'月换卡消费者数',
            'per_untime': u'时间异常比'
        }

        table = HtmlTable()
        html = table.gettable(u'每日商户风险统计', u"每日风险商户数： %d" % len(self.risk_list), headdata, self.risk_list)
    #    print html


        to_list = ('442875089@qq.com',)
        mail_host = 'smtp.exmail.qq.com'
        mail_user = 'lishiwen@qfpay.com'
        mail_pass = ''
        sub = '每日风险统计'
        self.send_mail(to_list, mail_host, mail_user, mail_pass, sub, html)


def run(argv):
    bi_conf = ConfigParser.ConfigParser()
    bi_conf.read(os.path.join(HOME, 'biee.conf'))

    ri_conf = ConfigParser.ConfigParser()
    ri_conf.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'risk.conf'))

#    birisk = BiRisk(bi_conf, ri_conf)
#
#    if argv == 'day':
#        birisk.commit()
#
#    elif argv == 'all':
#        birisk.commit_all()

    report = DayReport(bi_conf, ri_conf)
    report.send_day_report()

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] != 'day' and sys.argv[1] != 'all':
        print 'argv error:\tbiee_risk.py [day] | [all]'
        sys.exit(-1)
    run(sys.argv[1])
