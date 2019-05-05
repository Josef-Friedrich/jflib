import smtplib
from email.utils import formatdate
from email.mime.text import MIMEText
from email.header import Header


def send_email(from_addr: str, to_addr: str, subject: str, body: str,
               smtp_login: str, smtp_password: str, smtp_server: str):
    """
    Send a email.

    :param from_addr: The email address of the sender.
    :param to_addr: The email address of the recipient.
    :param subject: The email subject.
    :param body: The email body.
    :param smtp_login: The SMTP login name.
    :param smtp_password: The SMTP password.
    :param smtp_server: The URL of the SMTP server, for
      example: `smtp.example.com:587`.

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
