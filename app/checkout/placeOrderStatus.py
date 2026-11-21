class PlaceOrderStatus:
    def __init__(self, isSuccess: bool, error: str, cartId: int):
        self._isSuccess = isSuccess
        self._errors = error
        self._cartId = cartId

    @property
    def isSuccess(self):
        return self._isSuccess

    @property
    def error(self):
        return self._error

    @property
    def cartId(self):
        return self._cartId

    @isSuccess.setter
    def isSuccess(self, status):
        self._isSuccess = status

    @error.setter
    def error(self, error):
        self._error = error

    @cartId.setter
    def cartId(self, cartId):
        self._cartId = cartId
