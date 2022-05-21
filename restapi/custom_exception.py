from rest_framework.exceptions import APIException


class UnauthorizedUserException(APIException):
    status_code:int = 404
    default_detail:str = "Not Found"
    default_code:str = "Records unavailable"

class BadRequestException(APIException):
    status_code:int = 400
    default_detail:str = "Invalid Request"
    default_code:str = "Bad Request"