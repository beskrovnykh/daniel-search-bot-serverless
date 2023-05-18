from chalice.local import LocalGateway
from chalice.config import Config

from app import app


def test_message_handler():
    lg = LocalGateway(app, Config())
    response = lg.handle_request(method='POST', path='/message_handler', headers={}, body='{}'.encode())
    assert response['statusCode'] == 200


test_message_handler()
