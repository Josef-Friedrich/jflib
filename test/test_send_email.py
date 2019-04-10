import unittest
from unittest import mock
from jflib.send_email import send_email


class TestSendEmail(unittest.TestCase):

    def test_send_email(self):
        with mock.patch('smtplib.SMTP') as SMTP:
            send_email(
                from_addr='from@example.com',
                to_addr='to@example.com',
                subject='Subject',
                body='Message',
                smtp_login='Login',
                smtp_password='Password',
                smtp_server='smtp.example.com:587'
            )

        SMTP.assert_called_with('smtp.example.com:587')
        server = SMTP.return_value
        server.login.assert_called_with('Login', 'Password')
        call_args = server.sendmail.call_args[0]
        self.assertEqual(call_args[0], 'from@example.com')
        self.assertEqual(call_args[1], ['to@example.com'])
        self.assertIn(
            'From: from@example.com\nTo: to@example.com\n',
            call_args[2]
        )
