# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from decimal import Decimal


from django.http import HttpResponse
from django.contrib.auth.models import User

# Create your views here.
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view,authentication_classes,permission_classes,action
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status

from restapi.models import Expenses,Groups,Category
from restapi.serializers import UserSerializer,GroupSerializer,CategorySerializer,ExpensesSerializer,UserExpense
from restapi.custom_exception import UnauthorizedUserException,BadRequestException
from restapi.utils import aggregate,sort_by_time_stamp,multiThreadedReader,transform,response_format





def index(_request):
    return HttpResponse("Hello, world. You're at Rest.")

def get_user_ids(body,type:str):
    user_ids:list[int] = []
    if body.get(type, None) is not None and body[type].get('user_ids', None) is not None:
            user_ids = body[type]['user_ids']
            for user_id in user_ids:
                if not User.objects.filter(id=user_id).exists():
                    raise BadRequestException()
    return user_ids

@api_view(['POST'])
def logout(request):
    request.user.auth_token.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def balance(request):
    user = request.user
    expenses = Expenses.objects.filter(users__in=user.expenses.all())
    final_balance = {}
    for expense in expenses:
        expense_balances = normalize(expense)
        for eb in expense_balances:
            from_user:int = eb['from_user']
            to_user:int = eb['to_user']
            if from_user == user.id:
                final_balance[to_user] = final_balance.get(to_user, 0) - eb['amount']
            if to_user == user.id:
                final_balance[from_user] = final_balance.get(from_user, 0) + eb['amount']
    final_balance = {k: v for k, v in final_balance.items() if v != 0}

    response = [{"user": k, "amount": int(v)} for k, v in final_balance.items()]
    return Response(response, status=status.HTTP_200_OK)


def normalize(expense):
    user_balances = expense.users.all()
    dues:dict = {}
    for user_balance in user_balances:
        dues[user_balance.user] = dues.get(user_balance.user, 0) + user_balance.amount_lent \
                                  - user_balance.amount_owed
    dues = [(k, v) for k, v in sorted(dues.items(), key=lambda item: item[1])]
    start:int = 0
    end:int = len(dues) - 1
    balances:list = []
    while start < end:
        amount:float = min(abs(dues[start][1]), abs(dues[end][1]))
        user_balance = {"from_user": dues[start][0].id, "to_user": dues[end][0].id, "amount": amount}
        balances.append(user_balance)
        dues[start] = (dues[start][0], dues[start][1] + amount)
        dues[end] = (dues[end][0], dues[end][1] - amount)
        if dues[start][1] == 0:
            start += 1
        else:
            end -= 1
    return balances


class user_view_set(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)


class category_view_set(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    http_method_names = ['get', 'post']


class group_view_set(ModelViewSet):
    queryset = Groups.objects.all()
    serializer_class = GroupSerializer

    def get_queryset(self):
        user = self.request.user
        groups = user.members.all()
        if self.request.query_params.get('q', None) is not None:
            groups = groups.filter(name__icontains=self.request.query_params.get('q', None))
        return groups

    def create(self, request, *args, **kwargs):
        user = self.request.user
        data = self.request.data
        group = Groups(**data)
        group.save()
        group.members.add(user)
        serializer = self.get_serializer(group)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['put'], detail=True)
    def members(self, request, pk=None):
        if not  Groups.objects.filter(id=pk).exists():
            raise UnauthorizedUserException()
        group = Groups.objects.get(id=pk)
        body = request.data
        added_ids:list[int] = get_user_ids(body,'add')
        removed_ids:list[int] = get_user_ids(body,'remove')
        group.members.add(*added_ids)
        group.members.remove(*removed_ids)
        group.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=True)
    def expenses(self, _request, pk=None):
        if not  Groups.objects.filter(id=pk).exists():
            raise UnauthorizedUserException()
        group = Groups.objects.get(id=pk)
        expenses = group.expenses_set
        serializer = ExpensesSerializer(expenses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=True)
    def balances(self, _request, pk=None):
        if not  Groups.objects.filter(id=pk).exists():
            raise UnauthorizedUserException()
        group = Groups.objects.get(id=pk)
        expenses = Expenses.objects.filter(group=group)
        dues:dict = {}
        for expense in expenses:
            user_balances = UserExpense.objects.filter(expense=expense)
            for user_balance in user_balances:
                dues[user_balance.user] = dues.get(user_balance.user, 0) + user_balance.amount_lent \
                                          - user_balance.amount_owed
        dues:list[float] = [(k, v) for k, v in sorted(dues.items(), key=lambda item: item[1])]
        start:int = 0
        end:int = len(dues) - 1
        balances:list = []
        while start < end:
            amount:float = min(abs(dues[start][1]), abs(dues[end][1]))
            amount = Decimal(amount).quantize(Decimal(10)**-2)
            user_balance = {"from_user": dues[start][0].id, "to_user": dues[end][0].id, "amount": str(amount)}
            balances.append(user_balance)
            dues[start] = (dues[start][0], dues[start][1] + amount)
            dues[end] = (dues[end][0], dues[end][1] - amount)
            if dues[start][1] == 0:
                start += 1
            else:
                end -= 1

        return Response(balances, status=status.HTTP_200_OK)


class expenses_view_set(ModelViewSet):
    queryset = Expenses.objects.all()
    serializer_class = ExpensesSerializer

    def get_queryset(self):
        user = self.request.user
        if self.request.query_params.get('q', None) is not None:
            expenses = Expenses.objects.filter(users__in=user.expenses.all())\
                .filter(description__icontains=self.request.query_params.get('q', None))
        else:
            expenses = Expenses.objects.filter(users__in=user.expenses.all())
        return expenses

@api_view(['post'])
@authentication_classes([])
@permission_classes([])
def logProcessor(request):
    data = request.data
    num_threads:int = data['parallelFileProcessingCount']
    log_files:list[str] = data['logFiles']
    if num_threads <= 0 or num_threads > 30:
        return Response({"status": "failure", "reason": "Parallel Processing Count out of expected bounds"},
                        status=status.HTTP_400_BAD_REQUEST)
    if len(log_files) == 0:
        return Response({"status": "failure", "reason": "No log files provided in request"},
                        status=status.HTTP_400_BAD_REQUEST)
    logs = multiThreadedReader(urls=data['logFiles'], num_threads=data['parallelFileProcessingCount'])
    sorted_logs = sort_by_time_stamp(logs)
    cleaned = transform(sorted_logs)
    data = aggregate(cleaned)
    response = response_format(data)
    return Response({"response":response}, status=status.HTTP_200_OK)
