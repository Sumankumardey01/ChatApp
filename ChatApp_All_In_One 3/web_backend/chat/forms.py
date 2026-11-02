from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            "placeholder": "you@example.com",
            "autocomplete": "email",
        }),
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class StartConversationForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Username",
        widget=forms.TextInput(attrs={
            "placeholder": "Enter a ChatApp username",
            "autocomplete": "off",
        }),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("No ChatApp user was found with that username.")
        return username
