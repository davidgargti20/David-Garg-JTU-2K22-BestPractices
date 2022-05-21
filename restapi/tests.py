# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from restapi.models import Category, Groups, Expenses, UserExpense
from django.contrib.auth.models import User

# TODO: Write a test


class UserTestCase(TestCase):
    def create_user(self, username, password):
        return User.objects.create(username=username, password=password)

    def test_user_creation(self):
        w = self.create_user(username="test1", password="test@123")
        self.assertTrue(isinstance(w, User))
        self.assertEqual(w.username, "test1")


class CategoryTestCase(TestCase):
    def create_category(self, name):
        return Category.objects.create(name=name)

    def test_category_creation(self):
        w = self.create_category(name="testcategory")
        self.assertTrue(isinstance(w, Category))
        self.assertEqual(w.name, "testcategory")


class GroupTestCase(TestCase):
    def create_group(self, name):
        return Groups.objects.create(name=name)

    def test_group_creation(self):
        w = self.create_group(name="testgroup")
        self.assertTrue(isinstance(w, Groups))
        self.assertEqual(w.name, "testgroup")


class ExpensesTestCase(TestCase):
    def create_expenses(self, description, total_amount):
        category, _ = Category.objects.get_or_create(name="testcategory")
        return Expenses.objects.create(
            description=description, total_amount=total_amount, category=category
        )

    def test_expenses_creation(self):
        w = self.create_expenses(description="description", total_amount=100)
        self.assertTrue(isinstance(w, Expenses))
        self.assertEqual(w.description, "description")
        self.assertEqual(w.total_amount, 100)


class UserExpenseTestCase(TestCase):
    def create_userexpense(self, expense, user, amount_owed, amount_lent):
        return UserExpense.objects.create(
            expense=expense, user=user, amount_owed=amount_owed, amount_lent=amount_lent
        )

    def test_user_expenses(self):
        user = User.objects.create(username="test1", password="test@123")
        category = Category.objects.create(name="testcategory")
        expense = Expenses.objects.create(
            description="description", total_amount=100, category=category
        )
        w = self.create_userexpense(
            expense=expense, user=user, amount_owed=100, amount_lent=0
        )
        self.assertTrue(isinstance(w, UserExpense))
        self.assertEqual(w.expense, expense)
        self.assertEqual(w.amount_owed, 100)
