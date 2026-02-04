from django import forms
from .models import Organization
from .models import Player

class OrganizationEmailForm(forms.Form):
    organization_email = forms.EmailField(
        label='Organization Email',
        max_length=50,
        widget=forms.EmailInput(attrs={
            'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors',
            'placeholder': 'Enter Organization Email'
        })
    )

    def clean_organization_email(self):
        email = self.cleaned_data.get('organization_email')
        if Organization.objects.filter(Organization_Email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

class OrganizationLoginForm(forms.Form):
    organization_email = forms.EmailField(
        label='Organization Email',
        max_length=50,
        widget=forms.EmailInput(attrs={
            'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors',
            'placeholder': 'Enter Organization Email'
        })
    )

class OTPForm(forms.Form):
    otp = forms.CharField(
        label='OTP',
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors text-center tracking-[1em] font-display font-bold text-xl',
            'placeholder': 'XXXXXX'
        })
    )

class OrganizationDetailsForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['Organization_Name', 'Organization_UserName', 'Organization_Contact']
        widgets = {
            'Organization_Name': forms.TextInput(attrs={
                'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors',
                'placeholder': 'Organization Name'
            }),
            'Organization_UserName': forms.TextInput(attrs={
                'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors',
                'placeholder': 'Username'
            }),
            'Organization_Contact': forms.NumberInput(attrs={
                'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors',
                'placeholder': 'Contact Number'
            }),
        }

class OrganizationPhotoForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['profile_photo']
        widgets = {
            'profile_photo': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'photo-upload',
                'onchange': 'this.form.submit()'
            }),
        }

class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full bg-brand-dark/50 border border-white/10 rounded-lg p-3 text-white focus:border-accent-cyan outline-none transition-colors placeholder-white/30', 
            'placeholder': 'Enter your email'
        }),
        label="Email Address"
    )

class OTPVerifyForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-brand-dark/50 border border-white/10 rounded-lg p-3 text-white focus:border-accent-cyan outline-none transition-colors placeholder-white/30 text-center tracking-[0.5em] text-xl font-mono', 
            'placeholder': '000000'
        }),
        label="Enter Authentication Code"
    )

class PlayerRegistrationForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['full_name', 'uid', 'mobile_no', 'age']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Full Name'}),
            'uid': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Game ID / UID'}),
            'mobile_no': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Mobile Number'}),
            'age': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Age'}),
        }

    def clean_age(self):
        age = self.cleaned_data.get('age')
        if age < 16:
            raise forms.ValidationError("You must be at least 16 years old to register.")
        return age
