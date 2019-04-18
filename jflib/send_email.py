import smtplib
from email.utils import formatdate
from email.mime.text import MIMEText
from email.header import Header


def send_email(from_addr, to_addr, subject, body, smtp_login, smtp_password,
               smtp_server):
    """
    Send a email.

    :param str from_addr: The from email address.
    :param str to_addr: The to email address.
    :param str subject: The email subject.
    :param str body: The email body.
    :param str smtp_login: The SMTP login name.
    :param str smtp_password: The SMTP password.
    :param str smtp_server: For example smtp.example.com:587

    :return: Problems
    """
    message = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')

    message['Subject'] = Header(subject, 'utf-8')
    message['From'] = from_addr
    message['To'] = to_addr
    message['Date'] = formatdate(localtime=True)

    server = smtplib.SMTP(smtp_server)
    server.starttls()
    server.login(smtp_login, smtp_password)
    problems = server.sendmail(from_addr, [to_addr], message.as_string())
    server.quit()
    return problems
