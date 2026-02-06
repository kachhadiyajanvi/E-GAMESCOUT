from django import forms
from .models import Organization, Tournament
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
                'placeholder': 'Organization Name',
                'required': 'required'
            }),
            'Organization_UserName': forms.TextInput(attrs={
                'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors',
                'placeholder': 'Username',
                'required': 'required'
            }),
            'Organization_Contact': forms.TextInput(attrs={
                'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors',
                'placeholder': 'Contact Number (10 digits)',
                'required': 'required',
                'maxlength': '10'
            }),
        }
    
    def clean_Organization_Name(self):
        name = self.cleaned_data.get('Organization_Name')
        if not name or not name.strip():
            raise forms.ValidationError("Organization Name is required.")
        return name.strip()
    
    def clean_Organization_UserName(self):
        username = self.cleaned_data.get('Organization_UserName')
        if not username or not username.strip():
            raise forms.ValidationError("Username is required.")
        return username.strip()
    
    def clean_Organization_Contact(self):
        contact = self.cleaned_data.get('Organization_Contact')
        if not contact:
            raise forms.ValidationError("Contact Number is required.")
        
        # Convert to string and remove any whitespace
        contact_str = str(contact).strip()
        
        # Check if it contains only digits
        if not contact_str.isdigit():
            raise forms.ValidationError("Contact Number must contain only digits.")
        
        # Check if it's exactly 10 digits
        if len(contact_str) != 10:
            raise forms.ValidationError("Contact Number must be exactly 10 digits.")
        
        return contact_str

class OrganizationPhotoForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['profile_photo', 'instagram_username', 'instagram_link']
        widgets = {
            'profile_photo': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'photo-upload',
                'onchange': 'this.form.submit()'
            }),
            'instagram_username': forms.TextInput(attrs={
                'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors',
                'placeholder': 'Instagram Username (without @)'
            }),
            'instagram_link': forms.URLInput(attrs={
                'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors',
                'placeholder': 'https://instagram.com/yourprofile'
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

class AadharUploadForm(forms.Form):
    aadhar_card = forms.ImageField(required=True, label="Upload Aadhar Card (For Identity Verification)")

class PlayerRegistrationForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['full_name', 'age', 'uid', 'mobile_no', 'aadhar_number'] # Age & Aadhar extracted via AI
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'w-full bg-brand-gray/50 border border-white/10 rounded p-3 text-white focus:border-accent-cyan outline-none transition-colors opacity-70 cursor-not-allowed', 'placeholder': 'Enter Full Name', 'readonly': 'readonly'}),
            'age': forms.TextInput(attrs={'class': 'w-full bg-brand-gray/50 border border-white/10 rounded p-3 text-white focus:border-accent-cyan outline-none transition-colors opacity-70 cursor-not-allowed', 'placeholder': 'Age', 'readonly': 'readonly'}),
            'uid': forms.TextInput(attrs={'class': 'w-full bg-brand-gray/50 border border-white/10 rounded p-3 text-white focus:border-accent-cyan outline-none transition-colors', 'placeholder': 'Enter Game ID'}),
            'mobile_no': forms.NumberInput(attrs={'class': 'w-full bg-brand-gray/50 border border-white/10 rounded p-3 text-white focus:border-accent-cyan outline-none transition-colors', 'placeholder': 'Enter Mobile Number'}),
            'aadhar_number': forms.TextInput(attrs={'class': 'w-full bg-brand-gray/50 border border-white/10 rounded p-3 text-white focus:border-accent-cyan outline-none transition-colors opacity-70 cursor-not-allowed', 'placeholder': 'Aadhar Number', 'readonly': 'readonly'}),
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

    def clean_aadhar_number(self):
        aadhar = self.cleaned_data.get('aadhar_number')
        if not aadhar:
             raise forms.ValidationError("Aadhar Number is required.")
        # Check uniqueness (though model handles it, nice to have custom error)
        if Player.objects.filter(aadhar_number=aadhar).exists():
             raise forms.ValidationError("This Aadhar Number is already registered.")
        return aadhar

    def clean_age(self):
        # Age is not in form fields, it's handled in view/model, but if it were:
        age = self.cleaned_data.get('age')
        if age and age < 16:
            raise forms.ValidationError("You must be at least 16 years old to register.")
        return age

class PlayerProfileForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['username', 'profile_photo']
        widgets = {
             'username': forms.TextInput(attrs={
                'class': 'flex-1 bg-transparent border-none outline-none text-white', 
                'placeholder': 'gamer_tag',
                'required': 'required'
            }),
             'profile_photo': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'photo-upload',
                'onchange': 'this.form.submit()'
            }),
        }
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError("Username is required.")
        # Check uniqueness, excluding current user is tricky here without passing user instance, 
        # but ModelForm handles basic uniqueness. 
        # For custom unique check excluding self, we'd need to init with instance (which we do in view).
        return username

class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ['Name', 'Status', 'PrizePool']
        widgets = {
            'Name': forms.TextInput(attrs={
                'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors',
                'placeholder': 'Tournament Name',
                'required': 'required'
            }),
            'Status': forms.Select(attrs={
                'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors'
            }),
            'PrizePool': forms.NumberInput(attrs={
                'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors',
                'placeholder': 'Prize Pool Amount',
                'step': '0.01',
                'min': '0',
                'required': 'required'
            }),
        }
    
    def clean_Name(self):
        name = self.cleaned_data.get('Name')
        if not name or not name.strip():
            raise forms.ValidationError("Tournament Name is required.")
        return name.strip()
    
    def clean_PrizePool(self):
        prize_pool = self.cleaned_data.get('PrizePool')
        if prize_pool is None or prize_pool < 0:
            raise forms.ValidationError("Prize Pool must be a positive number.")
        return prize_pool
