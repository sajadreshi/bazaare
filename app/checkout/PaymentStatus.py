class PaymentStatus:

    def __init__(self, isSuccess: bool,
                 error: str,
                 paymentMethod: str,
                 accountNumber: str,
                 accountName: str,
                 expiryMonth: int,
                 expiryYear: int,
                 transactionId: str,
                 transactionStatus: str,
                 authCode: str,
                 requestedAmount: float,
                 approvedAmount: float,
                 ):
        self._isSuccess = isSuccess
        self._errors = error
        self._paymentMethod = paymentMethod
        self._accountNumber = accountNumber
        self._accountName = accountName
        self._expiryMonth = expiryMonth
        self._expiryYear = expiryYear
        self._transactionId = transactionId
        self._transactionStatus = transactionStatus
        self._authCode = authCode
        self._requestedAmount = requestedAmount
        self._approvedAmount = approvedAmount

    @property
    def isSuccess(self):
        return self._isSuccess

    @property
    def error(self):
        return self._error
    
    @property
    def paymentMethod(self):
        return self._paymentMethod
    
    @property
    def accountNumber(self):
        return self._accountNumber

    @property
    def accountName(self):
        return self._accountName

    @property
    def expiryMonth(self):
        return self._expiryMonth

    @property
    def expiryYear(self):
        return self._expiryYear

    @property
    def transactionId(self):
        return self._transactionId

    @property
    def transactionStatus(self):
        return self._transactionStatus

    @property
    def authCode(self):
        return self._authCode

    @property
    def requestedAmount(self):
        return self._requestedAmount

    @property
    def approvedAmount(self):
        return self._approvedAmount

    @isSuccess.setter
    def isSuccess(self, status):
        self._isSuccess = status

    @error.setter
    def error(self, error):
        self._error = error
        
    @paymentMethod.setter
    def paymentMethod(self,paymentMethod):
        self._paymentMethod = paymentMethod    

    @accountNumber.setter
    def accountNumber(self, accountNumber):
        self._accountNumber = accountNumber

    @accountName.setter
    def accountName(self, accountName):
        self._accountName = accountName

    @expiryMonth.setter
    def expiryMonth(self, expiryMonth):
        self._expiryMonth = expiryMonth

    @expiryYear.setter
    def expiryYear(self, expiryYear):
        self._expiryYear = expiryYear

    @transactionId.setter
    def transactionId(self, transactionId):
        self._transactionId = transactionId

    @transactionStatus.setter
    def transactionStatus(self, transactionStatus):
        self._transactionStatus = transactionStatus

    @authCode.setter
    def error(self, authCode):
        self._authCode = authCode

    @requestedAmount.setter
    def requestedAmount(self, requestedAmount):
        self._requestedAmount = requestedAmount

    @approvedAmount.setter
    def approvedAmount(self, approvedAmount):
        self._approvedAmount = approvedAmount
