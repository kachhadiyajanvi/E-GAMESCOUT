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
    aadhar_card = forms.ImageField(required=True, label="Upload Aadhar Card (For Age Verification)")
    
    class Meta:
        model = Player
        fields = ['full_name', 'uid', 'mobile_no', 'aadhar_card'] # Age is calculated via AI
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'w-full bg-brand-gray/50 border border-white/10 rounded p-3 text-white focus:border-accent-cyan outline-none transition-colors', 'placeholder': 'Enter Full Name'}),
            'uid': forms.TextInput(attrs={'class': 'w-full bg-brand-gray/50 border border-white/10 rounded p-3 text-white focus:border-accent-cyan outline-none transition-colors', 'placeholder': 'Enter Game ID'}),
            'mobile_no': forms.NumberInput(attrs={'class': 'w-full bg-brand-gray/50 border border-white/10 rounded p-3 text-white focus:border-accent-cyan outline-none transition-colors', 'placeholder': 'Enter Mobile Number'}),
        }

    def clean_mobile_no(self):
        mobile_no = self.cleaned_data.get('mobile_no')
        if not mobile_no.isdigit():
            raise forms.ValidationError("Mobile number must contain only digits.")
        if len(mobile_no) != 10:
            raise forms.ValidationError("Mobile number must be exactly 10 digits.")
        return mobile_no

    def clean_uid(self):
        uid = self.cleaned_data.get('uid')
        if len(uid) < 10 or len(uid) > 12:
            raise forms.ValidationError("Game UID must be between 10 and 12 characters.")
        return uid

    def clean_age(self):
        # This is a fallback in case it's somehow submitted, 
        # but primarily we rely on the view logic.
        return self.cleaned_data.get('age')
