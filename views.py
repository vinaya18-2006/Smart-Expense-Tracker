from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import Expense
from .forms import ExpenseForm
from datetime import date, timedelta
import csv
import json

CATEGORY_KEYWORDS = {
    'Food': ['food', 'restaurant', 'pizza', 'burger', 'coffee', 'lunch', 'dinner', 'snack'],
    'Travel': ['uber', 'taxi', 'bus', 'train', 'flight', 'hotel', 'travel'],
    'Entertainment': ['movie', 'game', 'music', 'party', 'event'],
    'Shopping': ['clothes', 'shoes', 'grocery', 'market'],
    'Utilities': ['electricity', 'water', 'gas', 'internet', 'phone'],
    'Health': ['doctor', 'medicine', 'hospital', 'pharmacy'],
    'Other': []
}

def predict_category(description):
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in desc_lower for keyword in keywords):
            return category
    return 'Other'

def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    filter_type = request.GET.get('filter', 'all')
    today = date.today()
    if filter_type == 'today':
        expenses = Expense.objects.filter(user=request.user, date=today)
    elif filter_type == 'week':
        start_week = today - timedelta(days=today.weekday())
        expenses = Expense.objects.filter(user=request.user, date__gte=start_week)
    elif filter_type == 'month':
        start_month = today.replace(day=1)
        expenses = Expense.objects.filter(user=request.user, date__gte=start_month)
    else:
        expenses = Expense.objects.filter(user=request.user)
    
    # For charts, calculate category sums
    category_data = {}
    for expense in expenses:
        category_data[expense.category] = category_data.get(expense.category, 0) + float(expense.amount)
    
    category_data_json = json.dumps(category_data)
    
    return render(request, 'dashboard.html', {
        'expenses': expenses,
        'filter_type': filter_type,
        'category_data_json': category_data_json,
    })

@login_required
def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            if not expense.category:
                expense.category = predict_category(expense.description)
            expense.save()
            return redirect('dashboard')
    else:
        form = ExpenseForm()
    return render(request, 'add_expense.html', {'form': form})

@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'edit_expense.html', {'form': form})

@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        expense.delete()
        return redirect('dashboard')
    return render(request, 'delete_expense.html', {'expense': expense})

@login_required
def download_report(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expenses.csv"'
    writer = csv.writer(response)
    writer.writerow(['Description', 'Amount', 'Date', 'Category', 'Notes'])
    expenses = Expense.objects.filter(user=request.user)
    for expense in expenses:
        writer.writerow([expense.description, expense.amount, expense.date, expense.category, expense.notes])
    return response
