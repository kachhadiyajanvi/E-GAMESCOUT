from django import forms
from web.models import Organization, Tournament, Contract, Bid
from web.models import Player

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
        if Organization.objects.filter(Organization_Email=email, is_archived=False).exists():
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
            'class': 'w-full bg-brand-dark/50 border border-white/10 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-colors text-center tracking-[0.5em] font-display font-bold text-xl',
            'placeholder': '0 0 0 0 0 0'
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
            'class': 'cyber-input w-full rounded-lg pl-11 pr-4 py-3 placeholder-white/30',
            'placeholder': 'Enter your email'
        }),
        label="Email Address"
    )

class OTPVerifyForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'cyber-input w-full rounded-lg p-3 placeholder-white/30 text-center tracking-[0.5em] text-xl font-mono text-white',
            'placeholder': '0 0 0 0 0 0'
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
            'full_name': forms.TextInput(attrs={'class': 'cyber-input w-full rounded-lg pl-11 pr-4 py-3 opacity-70 cursor-not-allowed', 'placeholder': 'Enter Full Name', 'readonly': 'readonly'}),
            'age': forms.TextInput(attrs={'class': 'cyber-input w-full rounded-lg pl-11 pr-4 py-3 opacity-70 cursor-not-allowed', 'placeholder': 'Age', 'readonly': 'readonly'}),
            'uid': forms.TextInput(attrs={'class': 'cyber-input w-full rounded-lg pl-11 pr-4 py-3', 'placeholder': 'Enter Game ID'}),
            'mobile_no': forms.NumberInput(attrs={'class': 'cyber-input w-full rounded-lg pl-11 pr-4 py-3', 'placeholder': 'Enter Mobile Number'}),
            'aadhar_number': forms.TextInput(attrs={'class': 'cyber-input w-full rounded-lg pl-11 pr-4 py-3 opacity-70 cursor-not-allowed', 'placeholder': 'Aadhar Number', 'readonly': 'readonly'}),
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
        if Player.objects.filter(aadhar_number=aadhar, is_archived=False).exists():
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
        fields = ['username', 'profile_photo', 'address']
        widgets = {
             'username': forms.TextInput(attrs={
                'class': 'cyber-input w-full rounded-lg pl-11 pr-4 py-3', 
                'placeholder': 'gamer_tag',
                'required': 'required'
            }),
             'address': forms.TextInput(attrs={
                'class': 'cyber-input w-full rounded-lg pl-11 pr-4 py-3', 
                'placeholder': 'City, State, Country'
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
        fields = ['Name', 'Status', 'PrizePool', 'description', 'max_teams', 'start_date', 'end_date', 'is_offline', 'venue', 'show_roadmap', 'roadmap_content', 'prize_distribution']
        widgets = {
            'Name': forms.TextInput(attrs={
                'class': 'w-full bg-[#0B0C10] border border-[#45A29E]/20 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#66FCF1] focus:ring-1 focus:ring-[#66FCF1] transition-all cyber-input',
                'placeholder': 'e.g. Winter Championship 2024',
                'required': 'required'
            }),
            'Status': forms.Select(attrs={
                'class': 'w-full bg-[#0B0C10] border border-[#45A29E]/20 rounded px-4 py-3 text-white focus:outline-none focus:border-[#66FCF1] transition-all cyber-input'
            }),
            'PrizePool': forms.NumberInput(attrs={
                'class': 'w-full bg-[#0B0C10] border border-[#45A29E]/20 rounded pl-8 pr-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#66FCF1] focus:ring-1 focus:ring-[#66FCF1] transition-all cyber-input',
                'placeholder': '50000',
                'step': '0.01',
                'min': '0',
                'required': 'required'
            }),
             'description': forms.Textarea(attrs={
                'class': 'w-full bg-[#0B0C10] border border-[#45A29E]/20 rounded px-4 py-3 text-white placeholder-gray-500 resize-none focus:outline-none focus:border-[#66FCF1] focus:ring-1 focus:ring-[#66FCF1] transition-all cyber-input',
                'placeholder': 'Enter tournament details, rules, and format...',
                'rows': 4,
                'required': 'required'
            }),
            'max_teams': forms.NumberInput(attrs={
                'class': 'w-full bg-[#0B0C10] border border-[#45A29E]/20 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#66FCF1] focus:ring-1 focus:ring-[#66FCF1] transition-all cyber-input',
                'placeholder': 'e.g. 16',
                'min': '2',
                'required': 'required'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'w-full bg-[#0B0C10] border border-[#45A29E]/20 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#66FCF1] focus:ring-1 focus:ring-[#66FCF1] transition-all cyber-input',
                'style': 'color-scheme: dark;',
                'type': 'datetime-local',
                'required': 'required'
            }),
            'end_date': forms.DateTimeInput(attrs={
                 'class': 'w-full bg-[#0B0C10] border border-[#45A29E]/20 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#66FCF1] focus:ring-1 focus:ring-[#66FCF1] transition-all cyber-input',
                'style': 'color-scheme: dark;',
                'type': 'datetime-local',
                'required': 'required'
            }),
             'venue': forms.TextInput(attrs={
                'class': 'w-full bg-[#0B0C10] border border-[#45A29E]/20 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#66FCF1] focus:ring-1 focus:ring-[#66FCF1] transition-all cyber-input',
                'placeholder': 'e.g. Los Angeles Convention Center'
            }),
             'roadmap_content': forms.Textarea(attrs={
                'class': 'hidden',
                'id': 'roadmap_content'
            }),
             # Hidden inputs for booleans/JSON are handled manually or via simple widgets
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

    def clean(self):
        cleaned_data = super().clean()
        
        # Date Validation
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if not start_date:
            self.add_error('start_date', "Start date is mandatory.")
        if not end_date:
            self.add_error('end_date', "End date is mandatory.")
        
        if start_date and end_date:
            from django.utils import timezone
            # Allow a small buffer (e.g., 5 mins) for "now" to account for form fill time
            if start_date < timezone.now() - timezone.timedelta(minutes=5):
                self.add_error('start_date', "Start date cannot be in the past.")
            if end_date < start_date:
                self.add_error('end_date', "End date must be after or equal to the start date.")
        
        # Venue Validation
        is_offline = cleaned_data.get('is_offline')
        venue = cleaned_data.get('venue')
        if is_offline and not venue:
            self.add_error('venue', "Venue is required for offline (LAN) tournaments.")
            
        # Prize Validation
        prize_pool = cleaned_data.get('PrizePool')
        prize_distribution = cleaned_data.get('prize_distribution')

        if not prize_distribution or prize_distribution == "[]" or prize_distribution == "":
            raise forms.ValidationError("At least one prize distribution (e.g., 1st Place) must be added.")

        if prize_pool is not None and prize_distribution:
            # If it comes as a string (from hidden input), try to parse it
            if isinstance(prize_distribution, str):
                import json
                try:
                    prize_distribution = json.loads(prize_distribution)
                except json.JSONDecodeError:
                    raise forms.ValidationError("Invalid Prize Distribution Format")

            if not prize_distribution or len(prize_distribution) == 0:
                raise forms.ValidationError("At least one prize distribution must be added.")

            total_distribution = 0.0
            if isinstance(prize_distribution, list):
                for item in prize_distribution:
                    # Item could be dict like {'position': 1, 'amount': 1000} or just amount
                    amount = item.get('amount') if isinstance(item, dict) else item
                    try:
                        if amount is None or float(amount) <= 0:
                             raise forms.ValidationError("Prize value is mandatory and must be greater than 0 for all positions.")
                        total_distribution += float(amount)
                    except (ValueError, TypeError):
                        raise forms.ValidationError("Invalid prize amount provided.")

            if float(prize_pool) < total_distribution:
                raise forms.ValidationError("Total prize distribution cannot exceed the tournament prize pool.")
                
            # Keep parsed data
            cleaned_data['prize_distribution'] = prize_distribution
            
        return cleaned_data

class AddPlayerForm(forms.Form):
    name = forms.CharField(
        label='Player Full Name',
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-[#0B0C10] border border-[#45A29E]/20 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#66FCF1] focus:ring-1 focus:ring-[#66FCF1] transition-all cyber-input',
            'placeholder': 'Enter player full name',
            'required': 'required'
        })
    )
    email = forms.EmailField(
        label='Player Email',
        max_length=100,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full bg-[#0B0C10] border border-[#45A29E]/20 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#66FCF1] focus:ring-1 focus:ring-[#66FCF1] transition-all cyber-input',
            'placeholder': 'Enter player email address',
            'required': 'required'
        })
    )
    game_id = forms.CharField(
        label='Game ID (UID)',
        max_length=12,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-[#0B0C10] border border-[#45A29E]/20 rounded px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#66FCF1] focus:ring-1 focus:ring-[#66FCF1] transition-all cyber-input',
            'placeholder': 'Enter 10-12 character Game ID',
            'required': 'required',
            'pattern': '.{10,12}',
            'title': 'Game ID must be between 10 and 12 characters.'
        })
    )

    def clean_game_id(self):
        game_id = self.cleaned_data.get('game_id')
        if not game_id:
            raise forms.ValidationError("Game ID is required.")
        
        game_id_str = str(game_id).strip()
        
        if len(game_id_str) < 10 or len(game_id_str) > 12:
            raise forms.ValidationError("Game ID must be between 10 and 12 characters.")
            
        return game_id_str

class OrganizationSignatureForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['organization_signature']
        widgets = {
            'organization_signature': forms.FileInput(attrs={
                'class': 'w-full bg-white border border-gray-300 rounded px-4 py-2 text-gray-700 focus:outline-none focus:border-blue-500',
                'required': 'required'
            })
        }

class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = ['player', 'salary', 'responsibilities', 'sponsor_promotion', 'duration', 'termination_rules']
        widgets = {
            'player': forms.Select(attrs={
                'class': 'w-full bg-white border border-gray-300 rounded px-4 py-3 text-gray-700 focus:outline-none focus:border-blue-500 transition-colors',
                'required': 'required'
            }),
            'salary': forms.NumberInput(attrs={
                'class': 'w-full bg-white border border-gray-300 rounded px-4 py-3 text-gray-700 placeholder-gray-400 focus:outline-none focus:border-blue-500 transition-colors',
                'placeholder': 'Enter Player Salary',
                'required': 'required'
            }),
            'responsibilities': forms.Textarea(attrs={
                'class': 'w-full bg-white border border-gray-300 rounded px-4 py-3 text-gray-700 placeholder-gray-400 focus:outline-none focus:border-blue-500 transition-colors',
                'placeholder': 'List Player & Organization Responsibilities...',
                'rows': 4,
                'required': 'required'
            }),
            'sponsor_promotion': forms.Textarea(attrs={
                'class': 'w-full bg-white border border-gray-300 rounded px-4 py-3 text-gray-700 placeholder-gray-400 focus:outline-none focus:border-blue-500 transition-colors',
                'placeholder': 'Sponsor Promotion requirements (e.g., reels, jersey)...',
                'rows': 3,
                'required': 'required'
            }),
            'duration': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-gray-300 rounded px-4 py-3 text-gray-700 placeholder-gray-400 focus:outline-none focus:border-blue-500 transition-colors',
                'placeholder': 'e.g., 1 Year, 6 Months',
                'required': 'required'
            }),
            'termination_rules': forms.Textarea(attrs={
                'class': 'w-full bg-white border border-gray-300 rounded px-4 py-3 text-gray-700 placeholder-gray-400 focus:outline-none focus:border-blue-500 transition-colors',
                'placeholder': 'Termination Rules...',
                'rows': 3,
                'required': 'required'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if organization:
            # Filter players to only show those belonging to this organization
            players = Player.objects.filter(organization=organization)
            
            # Fetch accepted bids for these players to show price in label
            accepted_bids = Bid.objects.filter(organization=organization, status='Accepted')
            bid_map = {b.player_id: b.amount for b in accepted_bids}
            
            choices = []
            for p in players:
                price = bid_map.get(p.id)
                label = f"{p.full_name} ({p.uid})"
                if price:
                    label += f" - Bid Price: ₹{price}"
                choices.append((p.id, label))
            
            self.fields['player'].choices = [('', '---------')] + choices
