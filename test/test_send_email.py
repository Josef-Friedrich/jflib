import unittest
from unittest import mock
from jflib.send_email import send_email


class TestSendEmail(unittest.TestCase):

    def test_send_email(self):
        with mock.patch('smtplib.SMTP') as SMTP:
            send_email(
                from_addr='from@example.com',
                to_addr_list=['to@example.com'],
                cc_addr_list=['cc@example.com'],
                subject='Subject',
                message='Message',
                login='Login',
                password='Password',
                smtpserver='smtp.example.com:587'
            )

        SMTP.assert_called_with('smtp.example.com:587')
        server = SMTP.return_value
        server.login.assert_called_with('Login', 'Password')
        server.sendmail.assert_called_with(
            'from@example.com',
            ['to@example.com'],
            'From: from@example.com\nTo: to@example.com\nCc: cc@example.com\n'
            'Subject: Subject\n\nMessage'
        )
